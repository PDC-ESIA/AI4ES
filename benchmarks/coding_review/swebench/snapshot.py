"""Fotografias git do workspace, sem commit, sem ref e sem tocar no índice real.

Por que não fazer o diff contra o `base_commit`: o `/testbed` das imagens
oficiais já chega MODIFICADO pelo `pre_install` de alguns repositórios (ex.:
sphinx e pytest reescrevem `tox.ini`/`setup.cfg` com `sed`). O harness oficial
aplica o patch do modelo sobre essa árvore já modificada; um diff contra o
`base_commit` carregaria de novo essas mudanças e o `git apply` falharia.

A fotografia resolve isso: logo depois de extrair o `/testbed`, gravamos o estado
exato da árvore como um objeto *tree* do git, e o patch final é o diff entre essa
tree e a do fim do loop.

Como: um índice TEMPORÁRIO (`GIT_INDEX_FILE`) recebe `read-tree HEAD` (para
manter arquivos rastreados mesmo que o `.gitignore` os cubra) e depois
`add -A` (arquivos novos, alterados e removidos, respeitando o `.gitignore` —
o que deixa de fora os `.so`/`egg-info` do build in-tree de astropy e
scikit-learn). `write-tree` devolve o hash. Nada disso cria commit, move HEAD ou
altera o índice do repositório.

O git roda com configuração NEUTRA: sem config global/de sistema do host
(`diff.noprefix`, `diff.external`, `core.autocrlf`, `core.excludesFile`...
mudariam o patch ou o que é considerado ignorado) e com as chaves que afetam o
formato do diff fixadas por `-c`, o que também sobrepõe a config do repositório.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

# Config global e de sistema do host fora do jogo.
_ENV_NEUTRO = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
# Chaves que mudam o formato do diff ou a leitura da árvore, fixadas no padrão
# que o `git apply` do harness oficial espera.
_OPCOES_NEUTRAS = (
    "-c", "core.autocrlf=false",
    "-c", "core.safecrlf=false",
    "-c", "core.quotePath=false",
    "-c", "diff.noprefix=false",
    "-c", "diff.mnemonicPrefix=false",
    "-c", "diff.relative=false",
    "-c", "diff.srcPrefix=a/",
    "-c", "diff.dstPrefix=b/",
)
_DIFF_FLAGS = ("--binary", "--no-color", "--no-renames", "--full-index",
               "--no-ext-diff", "--no-textconv")


class SnapshotError(RuntimeError):
    """Falha ao executar o git para fotografar ou comparar o workspace."""


def _git(
    repo: Path, *args: str, env: dict[str, str] | None = None, stdin: bytes | None = None
) -> bytes:
    completo = {**os.environ, **_ENV_NEUTRO, **(env or {})}
    try:
        resultado = subprocess.run(
            ["git", *_OPCOES_NEUTRAS, "-C", str(repo), *args],
            check=True,
            capture_output=True,
            env=completo,
            input=stdin,
        )
    except subprocess.CalledProcessError as exc:
        erro = exc.stderr.decode("utf-8", errors="replace").strip()
        raise SnapshotError(f"git {' '.join(args)} falhou: {erro}") from exc
    return resultado.stdout


def _caminhos(saida: bytes) -> list[str]:
    """Lista de caminhos de uma saída `-z` (bytes não-UTF-8 preservados)."""
    return sorted(
        os.fsdecode(caminho) for caminho in saida.split(b"\0") if caminho
    )


def _has_head(repo: Path) -> bool:
    try:
        _git(repo, "rev-parse", "--verify", "--quiet", "HEAD")
    except SnapshotError:
        return False
    return True


def take_snapshot(repo: Path) -> str:
    """Grava o estado atual da árvore de trabalho e devolve o hash da tree."""
    if not (repo / ".git").exists():
        raise SnapshotError(f"{repo} não é um repositório git.")
    with tempfile.TemporaryDirectory(prefix="swebench-idx-") as tmp:
        env = {"GIT_INDEX_FILE": str(Path(tmp) / "index")}
        if _has_head(repo):
            _git(repo, "read-tree", "HEAD", env=env)
        _git(repo, "add", "-A", "--", ".", env=env)
        return _git(repo, "write-tree", env=env).decode("ascii").strip()


def changed_paths(repo: Path, base_tree: str, final_tree: str) -> list[str]:
    """Caminhos que diferem entre duas trees (sem detecção de renomeação)."""
    return _caminhos(
        _git(repo, "diff", "--name-only", "-z", "--no-renames", base_tree, final_tree)
    )


def ignored_untracked(repo: Path) -> set[str]:
    """Arquivos não rastreados que o `.gitignore` do repositório esconde."""
    return set(
        _caminhos(
            _git(repo, "ls-files", "-z", "--others", "--ignored", "--exclude-standard")
        )
    )


def _pattern_de_atributo(caminho: str) -> str:
    """Caminho como pattern de `.gitattributes` (C-quoted: aceita espaços)."""
    escapado = caminho.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escapado}"'


def diff_file(
    repo: Path, base_tree: str, final_tree: str, caminho: str, *, binary: bool = False
) -> bytes:
    """Diff aplicável (`git apply`) de UM arquivo entre duas trees.

    Com `binary=True` o arquivo é marcado como binário por um `.gitattributes`
    temporário, e o git emite um `GIT binary patch` (texto ASCII em base85):
    a saída para conteúdo que não é UTF-8, que não caberia no JSON das
    predições sem corromper os bytes.
    """
    pathspec = f":(literal){caminho}"
    if not binary:
        return _git(repo, "diff", *_DIFF_FLAGS, base_tree, final_tree, "--", pathspec)
    with tempfile.TemporaryDirectory(prefix="swebench-attr-") as tmp:
        atributos = Path(tmp) / "attributes"
        atributos.write_text(f"{_pattern_de_atributo(caminho)} binary\n", encoding="utf-8")
        return _git(
            repo, "-c", f"core.attributesFile={atributos}",
            "diff", *_DIFF_FLAGS, base_tree, final_tree, "--", pathspec,
        )


def apply_patch(repo: Path, patch: str) -> None:
    """Aplica um patch na árvore de trabalho (`git apply`, config neutra)."""
    if patch.strip():
        _git(repo, "apply", "--whitespace=nowarn", "-", stdin=patch.encode("utf-8"))
