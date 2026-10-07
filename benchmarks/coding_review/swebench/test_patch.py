"""Testes da fotografia git e da extração do patch (repositórios git temporários)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from benchmarks.coding_review.swebench import environment
from benchmarks.coding_review.swebench.patch import (
    MOTIVO_ARTEFATO_CODER,
    MOTIVO_BENCHMARK,
    MOTIVO_CACHE,
    MOTIVO_GITIGNORE,
    MOTIVO_TEST_PATCH,
    MOTIVO_VENV,
    exclusion_reason,
    extract_patch,
)
from benchmarks.coding_review.swebench.snapshot import (
    SnapshotError,
    ignored_untracked,
    take_snapshot,
)

_GIT_ID = ["-c", "user.name=bench", "-c", "user.email=bench@example.com"]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *_GIT_ID, "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Repositório no estado de um `/testbed`: HEAD + alterações do pre_install."""
    raiz = tmp_path / "testbed"
    (raiz / "pkg").mkdir(parents=True)
    (raiz / "tests").mkdir()
    (raiz / "pkg" / "mod.py").write_text("def f():\n    return 1\n")
    (raiz / "pkg" / "velho.py").write_text("X = 1\n")
    (raiz / "tests" / "test_mod.py").write_text("def test_f():\n    pass\n")
    (raiz / "setup.cfg").write_text("[tool:pytest]\naddopts = -q\n")
    (raiz / ".gitignore").write_text("*.so\n")
    _git(raiz, "init", "-q")
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-q", "-m", "base")
    # pre_install da imagem: árvore suja + artefato de build ignorado.
    (raiz / "setup.cfg").write_text("[tool:pytest]\naddopts = -q -rA\n")
    (raiz / "pkg" / "_ext.so").write_bytes(b"\x7fELF")
    return raiz


def _simular_coder(repo: Path) -> None:
    (repo / "pkg" / "mod.py").write_text("def f():\n    return 2\n")
    (repo / "pkg" / "novo.py").write_text("Y = 2\n")
    (repo / "pkg" / "velho.py").unlink()
    (repo / "PLAN.md").write_text("# plano\n")
    (repo / "pkg" / "__pycache__").mkdir()
    (repo / "pkg" / "__pycache__" / "mod.cpython-312.pyc").write_bytes(b"\x00")
    (repo / "tests" / "test_novo.py").write_text("def test_n():\n    pass\n")
    (repo / "run.json").write_text('{"surface": "none", "test": ["python -m pytest"]}\n')


def test_patch_contem_so_a_correcao(repo: Path):
    base, ignorados = take_snapshot(repo), ignored_untracked(repo)
    environment.write_benchmark_files(repo, "img:latest")
    _simular_coder(repo)

    resultado = extract_patch(repo, base, test_patch_paths=("tests/test_novo.py",),
                              baseline_ignored=ignorados)

    assert resultado.files == ["pkg/mod.py", "pkg/novo.py", "pkg/velho.py"]
    assert resultado.excluded == {
        ".dockerignore": MOTIVO_BENCHMARK,
        "Dockerfile": MOTIVO_BENCHMARK,
        "run.json": MOTIVO_BENCHMARK,
        "PLAN.md": MOTIVO_ARTEFATO_CODER,
        "pkg/__pycache__/mod.cpython-312.pyc": MOTIVO_CACHE,
        "tests/test_novo.py": MOTIVO_TEST_PATCH,
    }
    # O que o pre_install já tinha mudado NÃO volta no patch.
    assert "setup.cfg" not in resultado.patch
    assert "_ext.so" not in resultado.patch
    assert resultado.patch.endswith("\n")


def test_patch_aplica_sobre_a_arvore_do_pre_install(repo: Path, tmp_path: Path):
    base = take_snapshot(repo)
    environment.write_benchmark_files(repo, "img:latest")
    _simular_coder(repo)
    resultado = extract_patch(repo, base)

    # Reproduz o /testbed do harness oficial: HEAD + mesmas alterações do pre_install.
    alvo = tmp_path / "alvo"
    subprocess.run(["git", "clone", "-q", str(repo), str(alvo)], check=True)
    shutil.copy(repo / "setup.cfg", alvo / "setup.cfg")
    arquivo_patch = tmp_path / "model.patch"
    arquivo_patch.write_text(resultado.patch)
    _git(alvo, "apply", "--check", str(arquivo_patch))
    _git(alvo, "apply", str(arquivo_patch))

    assert (alvo / "pkg" / "mod.py").read_text() == "def f():\n    return 2\n"
    assert (alvo / "pkg" / "novo.py").is_file()
    assert not (alvo / "pkg" / "velho.py").exists()


def test_patch_vazio_quando_o_coder_nao_muda_codigo(repo: Path):
    base, ignorados = take_snapshot(repo), ignored_untracked(repo)
    environment.write_benchmark_files(repo, "img:latest")
    resultado = extract_patch(repo, base, baseline_ignored=ignorados)
    assert resultado.empty and resultado.files == []
    assert set(resultado.excluded) == {"Dockerfile", ".dockerignore", "run.json"}


def test_fotografia_nao_cria_commit_nem_mexe_no_indice(repo: Path):
    head, status = _git(repo, "rev-parse", "HEAD"), _git(repo, "status", "--porcelain")
    arvore = take_snapshot(repo)
    assert len(arvore) == 40
    assert _git(repo, "rev-parse", "HEAD") == head
    assert _git(repo, "status", "--porcelain") == status
    assert _git(repo, "rev-list", "--count", "HEAD").strip() == "1"


def test_fotografia_exige_repositorio_git(tmp_path: Path):
    with pytest.raises(SnapshotError, match="não é um repositório git"):
        take_snapshot(tmp_path)


@pytest.mark.parametrize(
    "caminho, esperado",
    [
        ("Dockerfile", MOTIVO_BENCHMARK),
        ("docs/Dockerfile", None),
        ("PLAN.md", MOTIVO_ARTEFATO_CODER),
        ("docs/PLAN.md", None),
        ("a/__pycache__/b.pyc", MOTIVO_CACHE),
        ("a/b.pyc", MOTIVO_CACHE),
        (".pytest_cache/v/x", MOTIVO_CACHE),
        ("venv/lib/x.py", MOTIVO_VENV),
        ("src/venv_utils.py", None),
        ("tests/t.py", MOTIVO_TEST_PATCH),
        ("django/core/validators.py", None),
    ],
)
def test_motivos_de_exclusao(caminho, esperado):
    assert exclusion_reason(caminho, frozenset({"tests/t.py"})) == esperado


def _aplicar_em_copia(repo: Path, patch: str, tmp_path: Path) -> Path:
    """Aplica o patch num clone (HEAD) com as alterações do pre_install."""
    alvo = tmp_path / "alvo"
    subprocess.run(["git", "clone", "-q", str(repo), str(alvo)], check=True)
    shutil.copy(repo / "setup.cfg", alvo / "setup.cfg")
    arquivo = tmp_path / "model.patch"
    arquivo.write_text(patch)
    _git(alvo, "apply", str(arquivo))
    return alvo


def test_patch_independe_da_config_git_do_host(repo: Path, tmp_path: Path, monkeypatch):
    config_hostil = tmp_path / "gitconfig"
    config_hostil.write_text(
        "[diff]\n\tnoprefix = true\n\tmnemonicPrefix = true\n"
        "[core]\n\tautocrlf = true\n\texcludesFile = " + str(tmp_path / "exclude") + "\n"
    )
    (tmp_path / "exclude").write_text("*.py\n")  # esconderia todo o código
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config_hostil))

    base, ignorados = take_snapshot(repo), ignored_untracked(repo)
    (repo / "pkg" / "mod.py").write_text("def f():\n    return 2\n")
    (repo / "pkg" / "novo.py").write_text("Y = 2\n")
    resultado = extract_patch(repo, base, baseline_ignored=ignorados)

    assert resultado.files == ["pkg/mod.py", "pkg/novo.py"]
    assert "diff --git a/pkg/mod.py b/pkg/mod.py" in resultado.patch
    alvo = _aplicar_em_copia(repo, resultado.patch, tmp_path)
    assert (alvo / "pkg" / "novo.py").read_text() == "Y = 2\n"


def test_arquivo_nao_utf8_sai_como_patch_binario(repo: Path, tmp_path: Path):
    (repo / "dados.txt").write_bytes("café\n".encode("latin-1"))
    _git(repo, "add", "dados.txt")
    _git(repo, "commit", "-q", "-m", "fixture latin-1")
    base, ignorados = take_snapshot(repo), ignored_untracked(repo)
    novo = "café com açúcar\n".encode("latin-1")
    (repo / "dados.txt").write_bytes(novo)
    (repo / "pkg" / "mod.py").write_text("def f():\n    return 2\n")

    resultado = extract_patch(repo, base, baseline_ignored=ignorados)

    assert resultado.files == ["dados.txt", "pkg/mod.py"]
    assert resultado.binary_fallback == ["dados.txt"]
    assert "GIT binary patch" in resultado.patch
    resultado.patch.encode("ascii")  # cabe no JSON das predições sem perda
    alvo = _aplicar_em_copia(repo, resultado.patch, tmp_path)
    assert (alvo / "dados.txt").read_bytes() == novo
    assert (alvo / "pkg" / "mod.py").read_text() == "def f():\n    return 2\n"


def test_arquivo_novo_escondido_pelo_gitignore_fica_registrado(repo: Path):
    base, ignorados = take_snapshot(repo), ignored_untracked(repo)
    (repo / "pkg" / "gerado_pelo_coder.so").write_bytes(b"\x00")
    (repo / "pkg" / "mod.py").write_text("def f():\n    return 2\n")

    resultado = extract_patch(repo, base, baseline_ignored=ignorados)

    assert resultado.files == ["pkg/mod.py"]
    assert resultado.excluded == {"pkg/gerado_pelo_coder.so": MOTIVO_GITIGNORE}
    assert "pkg/_ext.so" not in resultado.excluded  # já existia na preparação
