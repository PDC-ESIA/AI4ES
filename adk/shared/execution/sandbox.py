"""Sandbox plugável para execução isolada dos comandos do manifesto.

Duas estratégias, mesma interface (`Sandbox`):

- `DirectSandbox` (padrão): copia o artefato para um diretório temporário
  efêmero e executa os comandos via subprocess, com env limpo, timeout de
  wall-clock e limites de recurso (`resource.setrlimit`: CPU, endereçamento,
  file descriptors). É ordens de magnitude mais barato que subir um container
  por execução — essencial para benchmarks com muitos problemas.

- `DockerSandbox` (opt-in): isolamento forte de rede/FS via container. Será
  habilitado na Fase 4, migrando as heurísticas de `harness_docker.py`.

RISCO CONHECIDO: `DirectSandbox` executa comandos gerados por LLM diretamente no
host, sem isolamento de container. É uma troca consciente de segurança por
velocidade; use `DockerSandbox` quando o isolamento forte for necessário.
"""

from __future__ import annotations

import os
import resource
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

# Defaults dos limites de recurso do DirectSandbox. RLIMIT_AS é endereçamento
# VIRTUAL (não RSS): precisa ser generoso para não estrangular o interpretador
# na largada. Ajustáveis no construtor; cada limite é aplicado best-effort.
_DEFAULT_MEM_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB de espaço de endereçamento
_DEFAULT_CPU_SECONDS = 60  # teto de CPU (rede de segurança além do wall-clock)
_DEFAULT_NOFILE = 1024  # descritores de arquivo abertos

# Chaves de ambiente preservadas ao montar um env limpo. Nada além disto é
# herdado do processo pai — segredos/vars do host não vazam para o comando.
_CLEAN_ENV_KEYS = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TERM")


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
    """

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


def create_sandbox(kind: str, **kwargs) -> Sandbox:
    """Fábrica de sandbox a partir do campo `sandbox` do manifesto.

    Args:
        kind: 'direct' (padrão) ou 'docker' (opt-in).
        **kwargs: repassados ao construtor do sandbox escolhido.

    Raises:
        NotImplementedError: para 'docker' até a Fase 4 migrar as heurísticas.
        ValueError: para um tipo de sandbox desconhecido.
    """
    if kind == "direct":
        return DirectSandbox(**kwargs)
    if kind == "docker":
        raise NotImplementedError(
            "DockerSandbox será habilitado na Fase 4 (migração de harness_docker)."
        )
    raise ValueError(f"Tipo de sandbox desconhecido: '{kind}'.")
