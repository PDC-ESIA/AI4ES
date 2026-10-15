"""Catálogo de problemas do SlopCodeBench (listagem + sorteio do subset).

O catálogo oficial (`gabeorlanski/scb-problems`) é um diretório "plano": cada
subdiretório com `config.yaml` é um problema, com os arquivos

- ``config.yaml``: ``entry_file``, ``timeout`` e o mapa de ``checkpoints``
  (cada um com ``order``);
- ``checkpoint_N.md``: a spec que o agente vê naquele checkpoint (lida e
  renderizada pelo próprio harness, em ``grading.render_prompt``);
- ``tests/`` e ``solutions/``: usados SOMENTE pelo avaliador oficial.

Este módulo lê apenas ``config.yaml``. Nunca abre ``tests/`` nem
``solutions/`` — o coder não pode ter acesso a eles, direta ou indiretamente.

Como no HumanEval, o catálogo é baixado dinamicamente na primeira execução
(``.tar.gz`` do GitHub, num commit FIXO) para ``datasets/``, que não é
versionado. ``--problems-path`` ou ``SCBENCH_PROBLEMS_PATH`` (a mesma variável
do harness oficial) permitem usar um checkout local no lugar do download.
"""

from __future__ import annotations

import os
import random
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yaml

# Variável de ambiente usada pelo próprio harness oficial para um catálogo local.
PROBLEMS_PATH_ENV = "SCBENCH_PROBLEMS_PATH"
DEFAULT_SEED = 42

# Commit fixado do catálogo oficial (gabeorlanski/scb-problems).
CATALOG_COMMIT = "38d627ecf668a88f88f8d260f8df8df6116e9b03"
CATALOG_URL = (
    f"https://github.com/gabeorlanski/scb-problems/archive/{CATALOG_COMMIT}.tar.gz"
)
DEFAULT_DATASETS_DIR = Path(__file__).resolve().parent / "datasets"
# Marcador gravado só ao fim da preparação: um download interrompido não conta.
DOWNLOAD_MARKER = ".download_completo"


@dataclass(frozen=True)
class ScbProblem:
    """Um problema do SlopCodeBench, com o necessário para dirigir o coder."""

    name: str
    path: Path
    entry_file: str
    checkpoints: tuple[str, ...]

    @property
    def num_checkpoints(self) -> int:
        return len(self.checkpoints)


def ensure_catalog(
    datasets_dir: Path = DEFAULT_DATASETS_DIR, *, url: str = CATALOG_URL
) -> Path:
    """Garante o catálogo no commit fixado, baixando-o se ainda não existir.

    Returns:
        Diretório do catálogo (``datasets/scb-problems-<commit>``).
    """
    destino = datasets_dir / f"scb-problems-{CATALOG_COMMIT}"
    if (destino / DOWNLOAD_MARKER).is_file():
        return destino

    print(f"[dataset] Baixando catálogo do SlopCodeBench de {url} …")
    download_tarball(url, destino)
    mark_complete(destino, CATALOG_COMMIT)
    print(f"[dataset] Catálogo salvo em {destino}.")
    return destino


def download_tarball(url: str, destino: Path) -> None:
    """Baixa um ``.tar.gz`` do GitHub e extrai seu diretório de topo em `destino`.

    Compartilhado com `grading.ensure_harness`. Não grava o marcador de conclusão:
    quem chama decide quando a preparação terminou (ver `mark_complete`).
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destino.parent) as tmp:
        arquivo = Path(tmp) / "download.tar.gz"
        with urllib.request.urlopen(url) as resp:  # noqa: S310 — URL oficial fixa
            arquivo.write_bytes(resp.read())
        with tarfile.open(arquivo) as tar:
            tar.extractall(tmp, filter="data")
        # O tarball do GitHub tem um único diretório de topo.
        (extraido,) = [p for p in Path(tmp).iterdir() if p.is_dir()]
        if destino.exists():
            shutil.rmtree(destino)
        extraido.rename(destino)


def mark_complete(destino: Path, commit: str) -> None:
    """Grava o marcador que indica download (e preparação) concluídos."""
    (destino / DOWNLOAD_MARKER).write_text(commit, encoding="utf-8")


def resolve_problems_root(
    problems_path: Path | None = None,
    *,
    datasets_dir: Path = DEFAULT_DATASETS_DIR,
) -> Path:
    """Resolve o catálogo: argumento > variável de ambiente > download fixado."""
    raiz = problems_path or (
        Path(os.environ[PROBLEMS_PATH_ENV])
        if os.environ.get(PROBLEMS_PATH_ENV)
        else None
    )
    if raiz is None:
        return ensure_catalog(datasets_dir)
    raiz = raiz.expanduser().resolve()
    if not raiz.is_dir():
        raise FileNotFoundError(f"Catálogo do SlopCodeBench não encontrado: {raiz}")
    return raiz


def source_commit(root: Path) -> str | None:
    """Commit de um download fixado (marcador) ou de um checkout git local."""
    marcador = root / DOWNLOAD_MARKER
    if marcador.is_file():
        return marcador.read_text(encoding="utf-8").strip()
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except OSError:
        return None
    except subprocess.SubprocessError:
        return None


def _load_problem(problem_dir: Path) -> ScbProblem:
    config = yaml.safe_load((problem_dir / "config.yaml").read_text(encoding="utf-8"))
    checkpoints = sorted(
        config["checkpoints"].items(), key=lambda item: item[1].get("order", 0)
    )
    return ScbProblem(
        name=config.get("name", problem_dir.name),
        path=problem_dir,
        entry_file=config["entry_file"],
        checkpoints=tuple(nome for nome, _ in checkpoints),
    )


def list_problem_names(root: Path) -> list[str]:
    """Nomes de todos os problemas, em ordem alfabética.

    A ordenação garante que o sorteio não dependa da ordem do filesystem.
    """
    return sorted(
        child.name
        for child in root.iterdir()
        if child.is_dir() and (child / "config.yaml").is_file()
    )


def load_problems(
    root: Path,
    *,
    limit: int | None = None,
    seed: int = DEFAULT_SEED,
    names: list[str] | None = None,
) -> list[ScbProblem]:
    """Carrega o subset de problemas a executar.

    Args:
        root: diretório do catálogo.
        limit: se informado (e sem `names`), sorteia `limit` problemas.
        seed: seed do sorteio — a mesma seed devolve sempre o mesmo subset.
        names: se informado, usa exatamente estes problemas (na ordem dada).

    Returns:
        Lista de `ScbProblem` na ordem de execução.
    """
    disponiveis = list_problem_names(root)

    if names:
        faltando = sorted(set(names) - set(disponiveis))
        if faltando:
            raise ValueError(f"Problemas inexistentes no catálogo: {faltando}")
        escolhidos = list(names)
    elif limit is not None and limit < len(disponiveis):
        escolhidos = random.Random(seed).sample(disponiveis, limit)
    else:
        escolhidos = disponiveis

    return [_load_problem(root / nome) for nome in escolhidos]
