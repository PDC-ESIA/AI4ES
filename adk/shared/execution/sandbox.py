"""Sandbox plugável para execução isolada dos comandos do manifesto.

Duas estratégias, mesma interface (`Sandbox`):

- `DirectSandbox` (padrão): copia o artefato para um diretório temporário
  efêmero e executa os comandos via subprocess, com env limpo, timeout de
  wall-clock e limites de recurso (`resource.setrlimit`: CPU, endereçamento,
  file descriptors). É ordens de magnitude mais barato que subir um container
  por execução — essencial para benchmarks com muitos problemas.

- `DockerSandbox` (opt-in): isolamento forte de rede/FS via container. Sobe um
  container efêmero (a partir do `Dockerfile` do artefato, se houver, senão de
  uma imagem-base) e executa build/run/test via `exec_run`, publicando a porta
  do serviço no host.

RISCO CONHECIDO: `DirectSandbox` executa comandos gerados por LLM diretamente no
host, sem isolamento de container. É uma troca consciente de segurança por
velocidade; use `DockerSandbox` quando o isolamento forte for necessário.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

try:
    import resource  # POSIX-only; ausente no Windows
except ImportError:
    resource = None  # type: ignore[assignment]

import docker

# Defaults dos limites de recurso do DirectSandbox. RLIMIT_AS é endereçamento
# VIRTUAL (não RSS): precisa ser generoso para não estrangular o interpretador
# na largada. Ajustáveis no construtor; cada limite é aplicado best-effort.
_DEFAULT_MEM_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB de espaço de endereçamento
_DEFAULT_CPU_SECONDS = 60  # teto de CPU (rede de segurança além do wall-clock)
_DEFAULT_NOFILE = 1024  # descritores de arquivo abertos

# Chaves de ambiente preservadas ao montar um env limpo. Nada além disto é
# herdado do processo pai — segredos/vars do host não vazam para o comando.
_CLEAN_ENV_KEYS = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TERM")

# Defaults do DockerSandbox.
_DOCKER_DEFAULT_BASE_IMAGE = "python:3.12-slim"  # usado quando não há Dockerfile
_DOCKER_WORKDIR = "/app"  # diretório do artefato dentro do container
_DOCKER_MEM_LIMIT = "512m"
_DOCKER_CPU_QUOTA = 50000  # 50% de 1 core (período padrão de 100ms)
_DOCKER_SERVICE_LOG = f"{_DOCKER_WORKDIR}/.sandbox_service.log"


@dataclass
class CommandResult:
    """Resultado da execução de um comando no sandbox."""

    exit_code: Optional[int]
    stdout: str
    stderr: str
    timed_out: bool = False


@runtime_checkable
class Sandbox(Protocol):
    """Interface plugável de execução isolada consumida pelo harness."""

    def setup(self, source_dir: Path) -> None:
        """Prepara o ambiente a partir do artefato em `source_dir`."""
        ...

    def exec(
        self, command: str, *, timeout: int, env: Optional[dict[str, str]] = None
    ) -> CommandResult:
        """Executa `command` de forma bloqueante e retorna o resultado."""
        ...

    def start_service(
        self, command: str, *, env: Optional[dict[str, str]] = None
    ) -> None:
        """Inicia `command` em segundo plano (serviço de rede)."""
        ...

    def logs(self) -> str:
        """Retorna os logs acumulados do serviço em segundo plano."""
        ...

    def cleanup(self) -> None:
        """Encerra processos e remove artefatos temporários."""
        ...


def _clean_env(extra: Optional[dict[str, str]]) -> dict[str, str]:
    """Monta um ambiente mínimo, sem herdar variáveis do host."""
    base = {k: os.environ[k] for k in _CLEAN_ENV_KEYS if k in os.environ}
    base.setdefault("PYTHONUNBUFFERED", "1")
    if extra:
        base.update(extra)
    return base


def _make_preexec(mem_bytes: int, cpu_seconds: int, nofile: int):
    """Cria um preexec_fn que aplica limites de recurso e isola o grupo.

    Cada `setrlimit` é best-effort: se a plataforma não suportar um limite, ele
    é ignorado em vez de abortar o processo filho. `os.setsid` cria um novo
    grupo de processos, permitindo encerrar serviços em segundo plano por grupo.
    Em plataformas sem `resource` (ex.: Windows) retorna `None`, o que faz o
    `subprocess` ignorar o preexec.
    """
    if resource is None:
        return None

    def _apply() -> None:
        for res, soft in (
            (resource.RLIMIT_CPU, cpu_seconds),
            (resource.RLIMIT_AS, mem_bytes),
            (resource.RLIMIT_NOFILE, nofile),
        ):
            try:
                resource.setrlimit(res, (soft, soft))
            except (ValueError, OSError):
                pass
        try:
            os.setsid()
        except OSError:
            pass

    return _apply


class DirectSandbox:
    """Executa comandos em subprocess dentro de um diretório temporário efêmero.

    Isolamento MÍNIMO por design: diretório temporário + timeout + limites de
    recurso + env limpo. Não isola rede nem filesystem do host — para isso, use
    `DockerSandbox`.
    """

    def __init__(
        self,
        *,
        workdir_subpath: str = ".",
        mem_bytes: int = _DEFAULT_MEM_BYTES,
        cpu_seconds: int = _DEFAULT_CPU_SECONDS,
        nofile: int = _DEFAULT_NOFILE,
    ) -> None:
        self._workdir_subpath = workdir_subpath
        self._mem_bytes = mem_bytes
        self._cpu_seconds = cpu_seconds
        self._nofile = nofile
        self._root: Optional[Path] = None
        self._proc: Optional[subprocess.Popen] = None
        self._service_log: Optional[Path] = None

    @property
    def root(self) -> Path:
        if self._root is None:
            raise RuntimeError("Sandbox não inicializado: chame setup() antes.")
        return self._root

    @property
    def workdir(self) -> Path:
        """Diretório de trabalho efetivo (raiz + workdir do manifesto)."""
        return (self.root / self._workdir_subpath).resolve()

    def setup(self, source_dir: Path) -> None:
        """Copia o artefato de `source_dir` para um diretório temporário novo."""
        self._root = Path(tempfile.mkdtemp(prefix="ai4se-sandbox-"))
        shutil.copytree(source_dir, self._root, dirs_exist_ok=True)

    def exec(
        self, command: str, *, timeout: int, env: Optional[dict[str, str]] = None
    ) -> CommandResult:
        """Executa `command` via `/bin/sh -c`, bloqueando até o fim ou timeout."""
        preexec = _make_preexec(self._mem_bytes, self._cpu_seconds, self._nofile)
        try:
            proc = subprocess.run(
                ["/bin/sh", "-c", command],
                cwd=str(self.workdir),
                env=_clean_env(env),
                capture_output=True,
                text=True,
                timeout=timeout,
                preexec_fn=preexec,
            )
            return CommandResult(
                exit_code=proc.returncode,
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                exit_code=None,
                stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                stderr=exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
                timed_out=True,
            )

    def start_service(
        self, command: str, *, env: Optional[dict[str, str]] = None
    ) -> None:
        """Inicia `command` em segundo plano, redirecionando saída para um log."""
        self._service_log = self.root / ".sandbox_service.log"
        preexec = _make_preexec(self._mem_bytes, self._cpu_seconds, self._nofile)
        log_fh = self._service_log.open("wb")
        self._proc = subprocess.Popen(
            ["/bin/sh", "-c", command],
            cwd=str(self.workdir),
            env=_clean_env(env),
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            preexec_fn=preexec,
        )

    def logs(self) -> str:
        """Lê os logs acumulados do serviço em segundo plano (se houver)."""
        if self._service_log and self._service_log.is_file():
            return self._service_log.read_text(encoding="utf-8", errors="replace")
        return ""

    def cleanup(self) -> None:
        """Encerra o grupo de processos do serviço e remove o diretório temp."""
        if self._proc is not None:
            try:
                os.killpg(os.getpgid(self._proc.pid), 15)  # SIGTERM ao grupo
            except (ProcessLookupError, PermissionError, OSError):
                try:
                    self._proc.terminate()
                except OSError:
                    pass
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(self._proc.pid), 9)  # SIGKILL
                except OSError:
                    pass
            self._proc = None
        if self._root is not None and self._root.exists():
            shutil.rmtree(self._root, ignore_errors=True)
        self._root = None


class DockerSandbox:
    """Executa comandos dentro de um container efêmero, com isolamento forte.

    Estratégia de setup:
    - Se o artefato traz um `Dockerfile`, a imagem é construída a partir dele
      (a stack fica a cargo do coder — agnóstico). O código é assado na imagem.
    - Caso contrário, usa uma imagem-base genérica (`base_image`) e monta o
      artefato como volume em `/app`. Os comandos `build` do manifesto (ex.:
      `pip install`, `npm ci`) instalam as dependências no container em runtime.

    O container é mantido vivo com `tail -f /dev/null`; build/run/test são
    disparados via `exec_run`. O `run` de serviço é iniciado em segundo plano com
    a saída redirecionada para um log lido por `logs()`. A porta do serviço, se
    informada, é publicada no host (`port:port`) para o healthcheck do harness.
    """

    def __init__(
        self,
        *,
        port: Optional[int] = None,
        workdir_subpath: str = ".",
        base_image: str = _DOCKER_DEFAULT_BASE_IMAGE,
        mem_limit: str = _DOCKER_MEM_LIMIT,
        cpu_quota: int = _DOCKER_CPU_QUOTA,
        container_workdir: str = _DOCKER_WORKDIR,
    ) -> None:
        self._port = port
        self._workdir_subpath = workdir_subpath
        self._base_image = base_image
        self._mem_limit = mem_limit
        self._cpu_quota = cpu_quota
        self._container_workdir = container_workdir
        self._service_log_path = f"{container_workdir}/.sandbox_service.log"
        self._image_tag = f"ai4se-sandbox:{uuid.uuid4().hex[:12]}"
        self._container_name = f"ai4se-sandbox-{uuid.uuid4().hex[:12]}"
        self._root: Optional[Path] = None
        self._client = None
        self._container = None
        self._built_image = False

    @property
    def root(self) -> Path:
        if self._root is None:
            raise RuntimeError("Sandbox não inicializado: chame setup() antes.")
        return self._root

    @property
    def _exec_workdir(self) -> str:
        """Diretório de trabalho efetivo dentro do container (workdir do manifesto)."""
        if self._workdir_subpath in (".", "", None):
            return self._container_workdir
        return f"{self._container_workdir}/{self._workdir_subpath}"

    def _ensure_container(self):
        if self._container is None:
            raise RuntimeError("Sandbox não inicializado: chame setup() antes.")
        return self._container

    def setup(self, source_dir: Path) -> None:
        """Copia o artefato, constrói/seleciona a imagem e sobe o container."""
        self._root = Path(tempfile.mkdtemp(prefix="ai4se-docker-"))
        shutil.copytree(source_dir, self._root, dirs_exist_ok=True)
        self._client = docker.from_env()

        image = self._base_image
        volumes = None
        if (self._root / "Dockerfile").is_file():
            self._client.images.build(
                path=str(self._root), tag=self._image_tag, rm=True, forcerm=True
            )
            image = self._image_tag
            self._built_image = True
        else:
            # Sem Dockerfile: monta o código como volume e usa a imagem-base.
            volumes = {str(self._root): {"bind": self._container_workdir, "mode": "rw"}}

        ports = None
        if self._port is not None:
            ports = {f"{self._port}/tcp": ("0.0.0.0", self._port)}

        self._container = self._client.containers.run(
            image=image,
            name=self._container_name,
            command=["/bin/sh", "-c", "tail -f /dev/null"],
            detach=True,
            working_dir=self._container_workdir,
            volumes=volumes,
            ports=ports,
            mem_limit=self._mem_limit,
            cpu_quota=self._cpu_quota,
            environment={},
        )

    def _decode_output(self, output) -> tuple[str, str]:
        pair = output if isinstance(output, tuple) else (output, None)
        stdout = (pair[0] or b"").decode("utf-8", errors="replace")
        stderr = (pair[1] or b"").decode("utf-8", errors="replace")
        return stdout, stderr

    def exec(
        self, command: str, *, timeout: int, env: Optional[dict[str, str]] = None
    ) -> CommandResult:
        """Executa `command` no container, com teto de tempo via `timeout(1)`."""
        container = self._ensure_container()
        wrapped = f"timeout {int(timeout)} /bin/sh -c {shlex.quote(command)}"
        res = container.exec_run(
            ["/bin/sh", "-c", wrapped],
            workdir=self._exec_workdir,
            environment=env or {},
            demux=True,
        )
        stdout, stderr = self._decode_output(res.output)
        return CommandResult(
            exit_code=res.exit_code,
            stdout=stdout,
            stderr=stderr,
            timed_out=res.exit_code == 124,  # convenção do coreutils `timeout`
        )

    def start_service(
        self, command: str, *, env: Optional[dict[str, str]] = None
    ) -> None:
        """Inicia `command` em segundo plano dentro do container (saída → log)."""
        container = self._ensure_container()
        redirected = f"exec {command} > {self._service_log_path} 2>&1"
        container.exec_run(
            ["/bin/sh", "-c", redirected],
            workdir=self._exec_workdir,
            environment=env or {},
            detach=True,
        )

    def logs(self) -> str:
        """Lê o log do serviço em segundo plano de dentro do container."""
        if self._container is None:
            return ""
        res = self._container.exec_run(
            ["/bin/sh", "-c", f"cat {self._service_log_path} 2>/dev/null || true"]
        )
        stdout, _ = self._decode_output(res.output)
        return stdout

    def cleanup(self) -> None:
        """Remove o container, a imagem construída (se houver) e o diretório temp."""
        if self._container is not None:
            try:
                self._container.remove(force=True)
            except Exception:
                pass
            self._container = None
        if self._built_image and self._client is not None:
            try:
                self._client.images.remove(self._image_tag, force=True)
            except Exception:
                pass
        if self._root is not None and self._root.exists():
            shutil.rmtree(self._root, ignore_errors=True)
        self._root = None


def create_sandbox(
    kind: str, *, port: Optional[int] = None, workdir_subpath: str = ".", **kwargs
) -> Sandbox:
    """Fábrica de sandbox a partir do campo `sandbox` do manifesto.

    Args:
        kind: 'direct' (padrão) ou 'docker' (opt-in).
        port: porta do serviço a publicar (usada só pelo DockerSandbox).
        workdir_subpath: subdiretório de trabalho relativo à raiz do artefato.
        **kwargs: repassados ao construtor do sandbox escolhido.

    Raises:
        ValueError: para um tipo de sandbox desconhecido.
    """
    if kind == "direct":
        return DirectSandbox(workdir_subpath=workdir_subpath, **kwargs)
    if kind == "docker":
        return DockerSandbox(port=port, workdir_subpath=workdir_subpath, **kwargs)
    raise ValueError(f"Tipo de sandbox desconhecido: '{kind}'.")
