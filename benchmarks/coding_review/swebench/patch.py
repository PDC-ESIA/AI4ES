"""Extração do patch final do loop — a "resposta" entregue ao harness oficial.

O patch é o diff entre a fotografia tirada logo após a preparação do workspace
(ver `snapshot.py`) e o estado ao fim do loop, MENOS o que não é correção:

- arquivos que o próprio benchmark semeou na raiz (`Dockerfile`,
  `.dockerignore`, `run.json`) e o `PLAN.md` que o coder às vezes cria;
- caches e virtualenvs (`__pycache__`, `*.pyc`, `.pytest_cache`, `venv/`...);
- caminhos que o `test_patch` oficial toca. O eval do SWE-bench restaura esses
  arquivos e aplica o `test_patch` por cima; um arquivo novo criado pelo coder
  no mesmo caminho faria o `git apply` do gabarito falhar e a instância contaria
  como não resolvida por motivo técnico. Usar o `test_patch` só para FILTRAR,
  depois do loop, não vaza nada ao coder.

O diff é montado ARQUIVO A ARQUIVO: um arquivo cujo diff não é UTF-8 (ex.:
fixture em latin-1) sai como `GIT binary patch` em vez de corromper — e
invalidar — o patch inteiro. Arquivos NOVOS escondidos pelo `.gitignore` do
repositório não entram no patch (o `git apply` do harness também não os
veria no `git diff` de um humano), mas ficam registrados para auditoria.

Cada exclusão é registrada com o motivo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import snapshot

BENCHMARK_ROOT_FILES = frozenset({"Dockerfile", ".dockerignore", "run.json"})
CODER_ROOT_ARTIFACTS = frozenset({"PLAN.md"})
_CACHE_DIRS = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache", ".tox"})
_VENV_ROOT_DIRS = frozenset({"venv", ".venv"})
_CACHE_SUFFIXES = (".pyc", ".pyo")

MOTIVO_BENCHMARK = "arquivo_do_benchmark"
MOTIVO_ARTEFATO_CODER = "artefato_do_coder"
MOTIVO_CACHE = "cache"
MOTIVO_VENV = "virtualenv"
MOTIVO_TEST_PATCH = "colide_com_test_patch"
MOTIVO_GITIGNORE = "ignorado_pelo_gitignore"
MOTIVO_NAO_UTF8 = "diff_nao_utf8"
# Ruído gerado, sem interesse de auditoria quando aparece entre os ignorados.
_MOTIVOS_RUIDO = frozenset({MOTIVO_CACHE, MOTIVO_VENV})


@dataclass
class PatchResult:
    """O patch extraído e a auditoria do que entrou e do que ficou de fora."""

    patch: str
    files: list[str] = field(default_factory=list)
    excluded: dict[str, str] = field(default_factory=dict)
    binary_fallback: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.patch.strip()


def exclusion_reason(path: str, test_patch_paths: frozenset[str]) -> str | None:
    """Motivo para deixar `path` fora do patch, ou `None` se ele entra."""
    partes = PurePosixPath(path).parts
    if len(partes) == 1 and path in BENCHMARK_ROOT_FILES:
        return MOTIVO_BENCHMARK
    if len(partes) == 1 and path in CODER_ROOT_ARTIFACTS:
        return MOTIVO_ARTEFATO_CODER
    if _CACHE_DIRS.intersection(partes) or path.endswith(_CACHE_SUFFIXES):
        return MOTIVO_CACHE
    if partes and partes[0] in _VENV_ROOT_DIRS:
        return MOTIVO_VENV
    if path in test_patch_paths:
        return MOTIVO_TEST_PATCH
    return None


def _diff_texto(repo: Path, base: str, final: str, caminho: str) -> tuple[str | None, bool]:
    """Diff do arquivo como texto; binário se o texto não for UTF-8.

    Returns:
        `(diff, usou_binario)`; `diff` é `None` se nem o binário for ASCII.
    """
    bruto = snapshot.diff_file(repo, base, final, caminho)
    try:
        return bruto.decode("utf-8"), False
    except UnicodeDecodeError:
        pass
    bruto = snapshot.diff_file(repo, base, final, caminho, binary=True)
    try:
        return bruto.decode("ascii"), True
    except UnicodeDecodeError:
        return None, True


def extract_patch(
    repo: Path,
    base_tree: str,
    *,
    test_patch_paths: tuple[str, ...] = (),
    baseline_ignored: frozenset[str] | set[str] = frozenset(),
) -> PatchResult:
    """Fotografa o estado final e devolve o patch filtrado contra `base_tree`.

    Args:
        baseline_ignored: arquivos ignorados que já existiam na preparação
            (`snapshot.ignored_untracked` logo após extrair o `/testbed`); só os
            que surgirem depois são registrados como `ignorado_pelo_gitignore`.
    """
    final_tree = snapshot.take_snapshot(repo)
    alvo_test_patch = frozenset(test_patch_paths)
    resultado = PatchResult(patch="")
    partes: list[str] = []

    for caminho in snapshot.changed_paths(repo, base_tree, final_tree):
        motivo = exclusion_reason(caminho, alvo_test_patch)
        if motivo is not None:
            resultado.excluded[caminho] = motivo
            continue
        diff, usou_binario = _diff_texto(repo, base_tree, final_tree, caminho)
        if diff is None:
            resultado.excluded[caminho] = MOTIVO_NAO_UTF8
            continue
        if usou_binario:
            resultado.binary_fallback.append(caminho)
        resultado.files.append(caminho)
        partes.append(diff if diff.endswith("\n") else diff + "\n")

    for caminho in sorted(snapshot.ignored_untracked(repo) - set(baseline_ignored)):
        motivo = exclusion_reason(caminho, alvo_test_patch)
        if motivo in _MOTIVOS_RUIDO:
            continue
        resultado.excluded.setdefault(caminho, motivo or MOTIVO_GITIGNORE)

    resultado.patch = "".join(partes)
    return resultado
