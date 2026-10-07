"""Preparação do workspace do coder e do ambiente onde o executor roda.

Por instância, o workspace do coder (`coder/src/`) recebe:

1. O repositório no estado da imagem oficial: o `/testbed` é copiado de dentro
   de `swebench/sweb.eval.x86_64.<id>` — os mesmos bytes que o harness oficial
   usa na correção, sem clonar o GitHub.
2. Uma fotografia git desse estado (`snapshot.py`), base do patch final.
3. Três arquivos do benchmark na raiz:
   - `Dockerfile`: parte da imagem oficial, põe o env conda `testbed` no PATH
     (o harness roda `/bin/sh -c`, que não ativa conda), copia o código editado
     para `/testbed` — o mesmo caminho da avaliação oficial, para onde aponta a
     instalação editável — e faz de `/app`, onde o `DockerSandbox` executa os
     comandos, um symlink para ele.
   - `.dockerignore`: tira o `.git` do contexto de build (o sandbox reconstrói
     a imagem a cada rodada).
   - `run.json`: `sandbox: docker`, `surface: none` e um `build` inócuo; o
     campo `test` fica para o coder declarar.

`ensure_benchmark_files` é a verificação usada pelo plugin de guarda antes de
cada rodada do executor: o prompt de sistema do coder manda usar `sandbox`
direct e virtualenv, o que executaria o repositório no HOST, sem dependências.
Restaurar o ambiente não altera o julgamento — apenas impede que a rodada meça
o ambiente errado — e toda restauração é registrada como violação.
"""

from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import snapshot

# Diretório do artefato dentro do container (`sandbox._DOCKER_WORKDIR`).
CONTAINER_WORKDIR = "/app"
TESTBED_DIR = "/testbed"
CONDA_TESTBED_BIN = "/opt/miniconda3/envs/testbed/bin"

DOCKERFILE_NAME = "Dockerfile"
DOCKERIGNORE_NAME = ".dockerignore"
MANIFEST_NAME = "run.json"
BENCHMARK_FILES = (DOCKERFILE_NAME, DOCKERIGNORE_NAME, MANIFEST_NAME)

DOCKERIGNORE_CONTENT = ".git\n"

VIOLACAO_DOCKERFILE = "dockerfile_restaurado"
VIOLACAO_DOCKERIGNORE = "dockerignore_restaurado"
VIOLACAO_SANDBOX = "sandbox_restaurado"
OBSERVACAO_RUN_JSON_AUSENTE = "run_json_ausente"
OBSERVACAO_RUN_JSON_INVALIDO = "run_json_invalido"
OBSERVACAO_VENV = "venv_no_manifesto"

# Violações = o benchmark precisou restaurar o ambiente. Observações = fatos
# registrados sem intervenção (o gate/harness do executor lida com eles).
VIOLACOES = frozenset({VIOLACAO_DOCKERFILE, VIOLACAO_DOCKERIGNORE, VIOLACAO_SANDBOX})


def render_dockerfile(image: str) -> str:
    """Dockerfile que roda o código editado dentro do ambiente oficial.

    O código fica no MESMO caminho da avaliação oficial (`/testbed`, para onde
    aponta a instalação editável) e `/app` — onde o `DockerSandbox` executa os
    comandos — vira um symlink para ele. O contrário (código em `/app`,
    `/testbed` como symlink) faz o pytest enxergar o mesmo `conftest.py` por
    dois caminhos e abortar a coleta com "Plugin name already registered"
    (observado no astropy).
    """
    return (
        "# Gerado pelo benchmark SWE-bench (issue #417). Não editar.\n"
        f"FROM {image}\n"
        f"ENV PATH={CONDA_TESTBED_BIN}:$PATH\n"
        f"RUN rm -rf {TESTBED_DIR}\n"
        f"COPY . {TESTBED_DIR}\n"
        f"RUN rm -rf {CONTAINER_WORKDIR} && ln -s {TESTBED_DIR} {CONTAINER_WORKDIR}\n"
        f"WORKDIR {TESTBED_DIR}\n"
    )


def seed_manifest() -> dict:
    """`run.json` inicial: ambiente fixado, testes a cargo do coder."""
    return {
        "schema_version": "1",
        "surface": "none",
        "sandbox": "docker",
        "build": ["python --version"],
        "test": [],
        "acceptance_tests": {},
    }


def write_benchmark_files(workspace: Path, image: str) -> None:
    """Grava `Dockerfile`, `.dockerignore` e `run.json` na raiz do workspace."""
    (workspace / DOCKERFILE_NAME).write_text(render_dockerfile(image), encoding="utf-8")
    (workspace / DOCKERIGNORE_NAME).write_text(DOCKERIGNORE_CONTENT, encoding="utf-8")
    (workspace / MANIFEST_NAME).write_text(
        json.dumps(seed_manifest(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _manifest_uses_venv(manifest: dict) -> bool:
    comandos = [*(manifest.get("build") or []), *(manifest.get("test") or [])]
    if isinstance(manifest.get("run"), str):
        comandos.append(manifest["run"])
    return any(
        isinstance(cmd, str) and ("venv" in cmd or "virtualenv" in cmd)
        for cmd in comandos
    )


def ensure_benchmark_files(workspace: Path, image: str) -> list[str]:
    """Restaura o ambiente do benchmark, se o coder o desfez.

    Returns:
        Lista de ocorrências desta verificação — violações (restaurações) e
        observações. Vazia quando tudo está como o benchmark deixou.
    """
    ocorrencias: list[str] = []

    dockerfile = workspace / DOCKERFILE_NAME
    esperado = render_dockerfile(image)
    if not dockerfile.is_file() or dockerfile.read_text(encoding="utf-8") != esperado:
        dockerfile.write_text(esperado, encoding="utf-8")
        ocorrencias.append(VIOLACAO_DOCKERFILE)

    dockerignore = workspace / DOCKERIGNORE_NAME
    if (
        not dockerignore.is_file()
        or dockerignore.read_text(encoding="utf-8") != DOCKERIGNORE_CONTENT
    ):
        dockerignore.write_text(DOCKERIGNORE_CONTENT, encoding="utf-8")
        ocorrencias.append(VIOLACAO_DOCKERIGNORE)

    manifesto = workspace / MANIFEST_NAME
    if not manifesto.is_file():
        # Sem run.json o gate do executor recusa a rodada: nada executa no host.
        ocorrencias.append(OBSERVACAO_RUN_JSON_AUSENTE)
        return ocorrencias
    try:
        dados = json.loads(manifesto.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        ocorrencias.append(OBSERVACAO_RUN_JSON_INVALIDO)
        return ocorrencias
    if not isinstance(dados, dict):
        ocorrencias.append(OBSERVACAO_RUN_JSON_INVALIDO)
        return ocorrencias

    if dados.get("sandbox") != "docker":
        dados["sandbox"] = "docker"
        manifesto.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        ocorrencias.append(VIOLACAO_SANDBOX)
    if _manifest_uses_venv(dados):
        ocorrencias.append(OBSERVACAO_VENV)
    return ocorrencias


# ---------------------------------------------------------------------------
# Extração do /testbed da imagem oficial
# ---------------------------------------------------------------------------


class EnvironmentPreparationError(RuntimeError):
    """Falha ao obter o repositório de dentro da imagem oficial."""


def _filtro_extracao(pulados: list[str]):
    """Filtro `data` do tarfile, pulando (em vez de abortar) o membro inseguro."""

    def filtro(membro: tarfile.TarInfo, destino: str) -> tarfile.TarInfo | None:
        try:
            return tarfile.data_filter(membro, destino)
        except tarfile.FilterError:
            pulados.append(membro.name)
            return None

    return filtro


def _ensure_image(client, image: str) -> None:
    from docker.errors import ImageNotFound
    from docker.utils import parse_repository_tag

    try:
        client.images.get(image)
    except ImageNotFound:
        repositorio, tag = parse_repository_tag(image)
        print(f"[environment] Baixando imagem {image} …")
        client.images.pull(repositorio, tag=tag or "latest")


def extract_testbed(image: str, dest: Path, *, client=None) -> list[str]:
    """Copia o `/testbed` da imagem para `dest` (que deve estar vazio).

    Returns:
        Membros do tar pulados por serem inseguros (ex.: symlink absoluto).
    """
    if client is None:
        import docker

        client = docker.from_env()
    _ensure_image(client, image)

    dest.mkdir(parents=True, exist_ok=True)
    if any(dest.iterdir()):
        raise EnvironmentPreparationError(f"Destino não está vazio: {dest}")

    pulados: list[str] = []
    container = client.containers.create(image, command=["true"])
    try:
        stream, _ = container.get_archive(TESTBED_DIR)
        with tempfile.TemporaryDirectory(prefix="testbed-", dir=dest.parent) as tmp:
            tar_path = Path(tmp) / "testbed.tar"
            with tar_path.open("wb") as fh:
                for pedaco in stream:
                    fh.write(pedaco)
            staging = Path(tmp) / "staging"
            with tarfile.open(tar_path) as tar:
                tar.extractall(staging, filter=_filtro_extracao(pulados))
            raiz = staging / Path(TESTBED_DIR).name
            if not raiz.is_dir():
                raise EnvironmentPreparationError(
                    f"{TESTBED_DIR} ausente no arquivo extraído de {image}."
                )
            for item in raiz.iterdir():
                shutil.move(str(item), str(dest / item.name))
    finally:
        container.remove(force=True)
    return pulados


@dataclass
class SeedResult:
    """Resultado da preparação do workspace de uma instância."""

    baseline_tree: str
    conflicts: list[str] = field(default_factory=list)
    skipped_members: list[str] = field(default_factory=list)
    # Ignorados pelo `.gitignore` já presentes na imagem (ex.: artefatos de
    # build in-tree): só os que surgirem depois entram na auditoria do patch.
    baseline_ignored: frozenset[str] = frozenset()


def clear_directory(path: Path) -> None:
    """Remove e recria `path` vazio."""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def seed_workspace(workspace: Path, image: str, *, client=None) -> SeedResult:
    """Prepara o workspace do coder para uma instância.

    A fotografia é tirada ANTES de gravar os arquivos do benchmark, então eles
    aparecem no diff final e são filtrados por nome (`patch.py`). `conflicts`
    registra quando o próprio repositório já tinha um desses arquivos na raiz.
    """
    clear_directory(workspace)
    pulados = extract_testbed(image, workspace, client=client)
    baseline = snapshot.take_snapshot(workspace)
    ignorados = frozenset(snapshot.ignored_untracked(workspace))
    conflitos = [nome for nome in BENCHMARK_FILES if (workspace / nome).exists()]
    write_benchmark_files(workspace, image)
    return SeedResult(
        baseline_tree=baseline,
        conflicts=conflitos,
        skipped_members=pulados,
        baseline_ignored=ignorados,
    )
