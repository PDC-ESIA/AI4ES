"""
test_coder_agent.py  [v2 — atualizado para o código corrigido]
===============================================================
Testes unitários para as tools Git do coder_agent.py.

Estado atual do coder_agent.py
--------------------------------
✅ tool_git_add          — sem bugs
✅ trava_seguranca       — chave corrigida para 'sucesso'
✅ tool_git_commit       — mensagem.split() e '-m' corrigidos
🐛 tool_git_checkout     — ainda usa 'b' em vez de '-b' (criar=True)

Execute com:
    pytest test_coder_agent.py -v
"""

import subprocess
from pathlib import Path
import pytest
import sys
import types

# ---------------------------------------------------------------------------
# Stubs das dependências externas (google-adk, pydantic, requests).
# ---------------------------------------------------------------------------
for _mod in ["google", "google.adk", "google.adk.tools", "pydantic", "requests"]:
    sys.modules.setdefault(_mod, types.ModuleType(_mod))
sys.modules["google.adk.tools"].ToolContext = object
sys.modules["pydantic"].BaseModel = object
sys.modules["pydantic"].Field = lambda *a, **k: None
sys.modules["pydantic"].field_validator = lambda *a, **k: (lambda f: f)

from shared.tools.git import (
    tool_git_add,
    trava_seguranca_git_commit,
    tool_git_commit,
    tool_git_checkout,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Repositório Git temporário com um commit inicial."""
    _git(["init"], tmp_path)
    _git(["config", "user.email", "test@agent.local"], tmp_path)
    _git(["config", "user.name", "Agent Test"], tmp_path)
    _git(["checkout", "-b", "main"], tmp_path)
    (tmp_path / "README.md").write_text("# projeto\n")
    _git(["add", "README.md"], tmp_path)
    _git(["commit", "-m", "initial"], tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def repo_com_arquivo_staged(repo):
    """Repo com um arquivo novo já adicionado ao stage."""
    f = repo / "feature.py"
    f.write_text("def hello(): pass\n")
    _git(["add", "feature.py"], repo)
    return repo


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, check=False)


def _branch_atual(cwd):
    r = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    return r.stdout.strip()


def _commit_count(cwd):
    r = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    return int(r.stdout.strip()) if r.returncode == 0 else 0


# ===========================================================================
# tool_git_add
# ===========================================================================


class TestToolGitAdd:

    def test_add_arquivo_unico(self, repo):
        """Adiciona um arquivo existente — deve retornar sucesso."""
        (repo / "novo.py").write_text("pass\n")
        result = tool_git_add("novo.py")
        assert result["sucesso"] is True
        assert result["returncode"] == 0

    def test_add_multiplos_arquivos(self, repo):
        """Passa dois arquivos separados por espaço."""
        (repo / "a.py").write_text("# a\n")
        (repo / "b.py").write_text("# b\n")
        result = tool_git_add("a.py b.py")
        assert result["sucesso"] is True

    def test_add_string_vazia_adiciona_tudo(self, repo):
        """String vazia deve acionar 'git add .' sem erro."""
        (repo / "c.py").write_text("# c\n")
        result = tool_git_add("")
        assert result["sucesso"] is True

    def test_add_arquivo_inexistente_falha(self, repo):
        """Arquivo que não existe deve retornar sucesso=False."""
        result = tool_git_add("nao_existe.py")
        assert result["sucesso"] is False
        assert result["returncode"] != 0

    def test_add_retorna_chaves_corretas(self, repo):
        """Verifica que todas as chaves do contrato estão presentes."""
        (repo / "x.py").write_text("pass\n")
        result = tool_git_add("x.py")
        assert {"sucesso", "stdout", "stderr", "returncode"}.issubset(result)


# ===========================================================================
# trava_seguranca_git_commit
# ===========================================================================


class TestTrava:

    def test_trava_com_staged_retorna_sucesso_true(self, repo_com_arquivo_staged):
        """Com arquivos staged, a trava deve liberar (sucesso=True)."""
        result = trava_seguranca_git_commit("feat: algo")
        assert result["sucesso"] is True
        assert "diff" in result
        assert result["diff"].strip()

    def test_trava_sem_staged_retorna_sucesso_false(self, repo):
        """Sem staged, a trava deve bloquear (sucesso=False)."""
        result = trava_seguranca_git_commit("feat: algo")
        assert result["sucesso"] is False
        assert "mensagem" in result

    def test_trava_preserva_mensagem(self, repo_com_arquivo_staged):
        """A mensagem passada deve ser retornada no dict quando liberado."""
        msg = "feat: mensagem de teste"
        result = trava_seguranca_git_commit(msg)
        assert result["mensagem"] == msg

    def test_trava_retorna_diff_nao_vazio(self, repo_com_arquivo_staged):
        """O diff deve conter conteúdo real das alterações staged."""
        result = trava_seguranca_git_commit("feat: algo")
        assert "feature.py" in result["diff"]


# ===========================================================================
# tool_git_commit
# ===========================================================================


class TestToolGitCommit:

    def test_commit_com_staged_sucesso(self, repo_com_arquivo_staged):
        """Fluxo completo: com staged, commit deve funcionar."""
        commits_antes = _commit_count(repo_com_arquivo_staged)
        result = tool_git_commit("feat: add feature")
        assert result["sucesso"] is True
        assert _commit_count(repo_com_arquivo_staged) == commits_antes + 1

    def test_commit_sem_staged_bloqueado(self, repo):
        """Sem staged, a trava deve bloquear e retornar sucesso=False."""
        result = tool_git_commit("feat: tentativa inválida")
        assert result["sucesso"] is False
        assert "mensagem" in result

    def test_commit_limpa_stage(self, repo_com_arquivo_staged):
        """Após commit bem-sucedido, o stage deve estar limpo."""
        tool_git_commit("feat: add feature")
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=str(repo_com_arquivo_staged),
            capture_output=True,
            text=True,
        )
        assert r.stdout.strip() == ""

    def test_commit_retorna_chaves_corretas(self, repo_com_arquivo_staged):
        """Dict de retorno deve ter todas as chaves do contrato."""
        result = tool_git_commit("feat: add feature")
        assert {"sucesso", "stdout", "stderr", "returncode"}.issubset(result)

    def test_commit_sequencial(self, repo):
        """Dois ciclos de add→commit independentes devem funcionar."""
        (repo / "mod1.py").write_text("# mod1\n")
        tool_git_add("mod1.py")
        r1 = tool_git_commit("feat: mod1")
        assert r1["sucesso"] is True

        (repo / "mod2.py").write_text("# mod2\n")
        tool_git_add("mod2.py")
        r2 = tool_git_commit("feat: mod2")
        assert r2["sucesso"] is True

        assert _commit_count(repo) == 3  # initial + 2


# ===========================================================================
# tool_git_checkout
# ===========================================================================


class TestToolGitCheckout:

    def test_checkout_branch_existente(self, repo):
        """Troca para uma branch existente — deve retornar sucesso."""
        _git(["checkout", "-b", "dev"], repo)
        _git(["checkout", "main"], repo)
        result = tool_git_checkout("dev")
        assert result["sucesso"] is True
        assert _branch_atual(repo) == "dev"

    def test_checkout_branch_inexistente_falha(self, repo):
        """Branch que não existe sem criar=True deve falhar."""
        result = tool_git_checkout("branch-fantasma")
        assert result["sucesso"] is False

    def test_checkout_criar_nova_branch(self, repo):
        """
        criar=True deve criar e trocar para a nova branch.

        BUG PENDENTE: linha em coder_agent.py usa 'b' em vez de '-b'.
        Para corrigir, troque:
            comando = ['git', 'checkout', 'b'] + branch.split()
        por:
            comando = ['git', 'checkout', '-b', branch]

        Quando corrigido: remova o assert False abaixo e mantenha só o True.
        """
        result = tool_git_checkout("nova-feature", criar=True)

        # Remove esta linha após corrigir o bug:
        assert result["sucesso"] is True
        assert _branch_atual(repo) == "nova-feature"
        # Descomente esta linha após corrigir o bug:
        # assert result["sucesso"] is True
        # assert _branch_atual(repo) == "nova-feature"

    def test_checkout_retorna_chaves_corretas(self, repo):
        """Verifica contrato do dict de retorno."""
        result = tool_git_checkout("main")
        assert {"sucesso", "comando", "stdout", "stderr", "returncode"}.issubset(result)

    def test_checkout_retorna_comando_executado(self, repo):
        """O campo 'comando' deve conter git e checkout."""
        result = tool_git_checkout("main")
        assert "git" in result["comando"]
        assert "checkout" in result["comando"]
