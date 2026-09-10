"""Testes determinísticos dos guardrails de shared/security.py (sem LLM)."""

import os

from shared.security import ambiente_minimo_python, redigir_segredos


# ---------------------------------------------------------------------------
# redigir_segredos
# ---------------------------------------------------------------------------


def test_redige_authorization_bearer():
    texto = "Authorization: Bearer abc123"
    resultado = redigir_segredos(texto)
    assert "abc123" not in resultado
    assert "[REDACTED]" in resultado


def test_redige_api_key():
    texto = "api_key=sk-proj-xyz"
    resultado = redigir_segredos(texto)
    assert "sk-proj-xyz" not in resultado
    assert "[REDACTED]" in resultado


def test_redige_password():
    texto = "password: hunter2"
    resultado = redigir_segredos(texto)
    assert "hunter2" not in resultado
    assert "[REDACTED]" in resultado


def test_redige_token_com_espacos_ao_redor_do_igual():
    texto = "token = ghp_abc"
    resultado = redigir_segredos(texto)
    assert "ghp_abc" not in resultado
    assert "[REDACTED]" in resultado


def test_redige_credencial_em_url():
    texto = "https://user:senha@host.com/path"
    resultado = redigir_segredos(texto)
    # O par usuário:senha inteiro é substituído por [REDACTED] (a regex não
    # preserva o usuário) — comportamento herdado sem alteração do E2E.
    assert "senha" not in resultado
    assert "user:senha" not in resultado
    assert "host.com/path" in resultado
    assert "[REDACTED]" in resultado


def test_nao_altera_texto_sem_segredo():
    texto = "3 passed, 0 failed in 0.42s\nAssertionError: esperado 5, obtido 4"
    assert redigir_segredos(texto) == texto


# ---------------------------------------------------------------------------
# ambiente_minimo_python
# ---------------------------------------------------------------------------


def test_google_api_key_nao_aparece_no_ambiente(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "vazou")
    env = ambiente_minimo_python()
    assert "GOOGLE_API_KEY" not in env
    assert "vazou" not in env.values()


def test_database_url_nao_aparece_no_ambiente(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
    env = ambiente_minimo_python()
    assert "DATABASE_URL" not in env
    assert all("postgresql://" not in v for v in env.values())


def test_path_e_mantido_quando_existe_no_host(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    env = ambiente_minimo_python()
    assert env.get("PATH") == "/usr/bin:/bin"


def test_pythonpath_passado_por_parametro_e_juntado_com_pathsep():
    env = ambiente_minimo_python(pythonpath=["/a/b", "/a/b/src"])
    assert env["PYTHONPATH"] == os.pathsep.join(["/a/b", "/a/b/src"])


def test_pythonpath_preexistente_no_host_nao_e_herdado(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "/algo/do/host")
    env = ambiente_minimo_python()
    assert "PYTHONPATH" not in env

    env_com_param = ambiente_minimo_python(pythonpath=["/explicito"])
    assert env_com_param["PYTHONPATH"] == "/explicito"
    assert "/algo/do/host" not in env_com_param["PYTHONPATH"]


def test_variavel_da_allowlist_ausente_no_host_nao_aparece(monkeypatch):
    monkeypatch.delenv("USERPROFILE", raising=False)
    env = ambiente_minimo_python()
    assert "USERPROFILE" not in env


# ---------------------------------------------------------------------------
# Integração leve: prova end-to-end de que o segredo não vaza para o
# subprocesso do pytest_runner.
# ---------------------------------------------------------------------------


def test_executar_pytest_tool_nao_vaza_google_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("GOOGLE_API_KEY", "segredo-nao-deve-vazar")

    workspace = tmp_path
    suite = workspace / "tests" / "inputs" / "sec_001"
    suite.mkdir(parents=True)
    test_file = suite / "test_sec_001.py"
    test_file.write_text(
        "import os\n\n"
        "def test_google_api_key_ausente():\n"
        "    assert os.environ.get('GOOGLE_API_KEY') is None\n",
        encoding="utf-8",
    )

    from shared.tools.pytest_runner import executar_pytest_tool

    result = executar_pytest_tool("tests/inputs/sec_001/test_sec_001.py")

    assert result["status"] == "sucesso", result
    assert result["testes_passaram"] == 1
    assert result["testes_falharam"] == 0
