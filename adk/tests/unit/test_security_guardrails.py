"""Testes determinísticos dos guardrails de shared/security.py (sem LLM)."""

import os

import pytest

from shared.security import (
    ambiente_minimo_python,
    detectar_credenciais,
    detectar_riscos_codigo,
    redigir_segredos,
)


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
# detectar_riscos_codigo
# ---------------------------------------------------------------------------


def test_detecta_leitura_de_env_via_environ_get():
    riscos = detectar_riscos_codigo(
        "import os\ndef test_x():\n    assert os.environ.get('GOOGLE_API_KEY')\n"
    )
    assert any("ambiente" in r for r in riscos)


def test_detecta_leitura_de_env_via_environ_subscript():
    riscos = detectar_riscos_codigo(
        "import os\ndef test_x():\n    assert os.environ['GOOGLE_API_KEY']\n"
    )
    assert any("ambiente" in r for r in riscos)


def test_detecta_leitura_de_env_via_getenv():
    riscos = detectar_riscos_codigo(
        "import os\ndef test_x():\n    assert os.getenv('SECRET')\n"
    )
    assert any("ambiente" in r for r in riscos)


def test_detecta_subprocess_run():
    riscos = detectar_riscos_codigo(
        "import subprocess\ndef test_x():\n    subprocess.run(['ls'])\n"
    )
    assert any("processo" in r for r in riscos)


def test_detecta_eval_e_exec():
    riscos_eval = detectar_riscos_codigo("def test_x():\n    eval('1+1')\n")
    riscos_exec = detectar_riscos_codigo("def test_x():\n    exec('x = 1')\n")
    assert any("dinâmico" in r for r in riscos_eval)
    assert any("dinâmico" in r for r in riscos_exec)


def test_detecta_import_dinamico():
    riscos_dunder = detectar_riscos_codigo("def test_x():\n    __import__('os')\n")
    riscos_importlib = detectar_riscos_codigo(
        "import importlib\ndef test_x():\n    importlib.import_module('os')\n"
    )
    assert any("import dinâmico" in r for r in riscos_dunder)
    assert any("import dinâmico" in r for r in riscos_importlib)


def test_nao_detecta_os_path_join():
    # `os` é legítimo para manipular paths — não pode virar falso positivo.
    codigo = (
        "import os\n"
        "def test_x():\n"
        "    caminho = os.path.join('a', 'b')\n"
        "    assert caminho == 'a/b' or caminho == 'a\\\\b'\n"
    )
    assert detectar_riscos_codigo(codigo) == []


def test_nao_detecta_referencia_em_comentario_ou_string():
    # Prova que a análise é AST (semântica), não regex sobre o texto bruto:
    # a MESMA string "os.environ.get" aparece aqui só como comentário/literal,
    # nunca como uma chamada real.
    codigo = (
        "def test_x():\n"
        "    # exemplo: os.environ.get('X') NAO deve ser chamado aqui\n"
        "    msg = \"nunca use os.environ.get em testes\"\n"
        "    assert msg\n"
    )
    assert detectar_riscos_codigo(codigo) == []


def test_detecta_requisicao_de_rede_a_host_externo():
    riscos = detectar_riscos_codigo(
        "import requests\n"
        "def test_x():\n"
        "    requests.get('https://exemplo-externo.com/api')\n"
    )
    assert any("rede" in r for r in riscos)


def test_nao_detecta_requisicao_de_rede_a_loopback():
    riscos = detectar_riscos_codigo(
        "import requests\n"
        "def test_x():\n"
        "    requests.get('http://127.0.0.1:8000/health')\n"
    )
    assert riscos == []

    riscos_localhost = detectar_riscos_codigo(
        "import requests\n"
        "def test_x():\n"
        "    requests.get('http://localhost:8000/health')\n"
    )
    assert riscos_localhost == []


def test_lista_vazia_para_teste_pytest_normal():
    codigo = (
        "import pytest\n\n"
        "def test_soma():\n"
        "    assert 1 + 1 == 2\n\n"
        "def test_erro():\n"
        "    with pytest.raises(ValueError):\n"
        "        raise ValueError('x')\n"
    )
    assert detectar_riscos_codigo(codigo) == []


# ---------------------------------------------------------------------------
# detectar_credenciais
# ---------------------------------------------------------------------------


def test_detecta_credencial_api_key():
    achados = detectar_credenciais('api_key = "sk-proj-abc123xyz"\n')
    assert achados


def test_detecta_credencial_password():
    achados = detectar_credenciais('password = "hunter2real"\n')
    assert achados


@pytest.mark.parametrize(
    "valor", ["fake", "xxx", "dummy", "changeme", "<credencial redigida>"]
)
def test_nao_detecta_placeholder_obvio(valor):
    achados = detectar_credenciais(f'api_key = "{valor}"\n')
    assert achados == []


# ---------------------------------------------------------------------------
# Integração em _validar_e_sanitizar_codigo
# ---------------------------------------------------------------------------


def test_sanitizar_codigo_limpo_passa_normalmente():
    from src.agents.qa_agent.subagents.receive_requirements.sanitizer import (
        _validar_e_sanitizar_codigo,
    )

    codigo = "import pytest\n\ndef test_ok():\n    assert 1 == 1\n"
    resultado = _validar_e_sanitizar_codigo(codigo, "HU-001")
    assert resultado == codigo


def test_sanitizar_codigo_com_os_environ_levanta_valueerror():
    from src.agents.qa_agent.subagents.receive_requirements.sanitizer import (
        _validar_e_sanitizar_codigo,
    )

    codigo = (
        "import os\n\n"
        "def test_x():\n"
        "    assert os.environ.get('GOOGLE_API_KEY') is not None\n"
    )
    with pytest.raises(ValueError, match="risco de segurança"):
        _validar_e_sanitizar_codigo(codigo, "HU-002")


def test_sanitizar_codigo_com_credencial_hardcoded_levanta_valueerror():
    from src.agents.qa_agent.subagents.receive_requirements.sanitizer import (
        _validar_e_sanitizar_codigo,
    )

    codigo = (
        "def test_x():\n"
        "    api_key = \"sk-proj-abc123xyz789real\"\n"
        "    assert api_key\n"
    )
    with pytest.raises(ValueError, match="risco de segurança"):
        _validar_e_sanitizar_codigo(codigo, "HU-003")


def test_sanitizar_placeholder_pass_ctrl63_continua_sem_regressao():
    from src.agents.qa_agent.subagents.receive_requirements.sanitizer import (
        _validar_e_sanitizar_codigo,
    )

    codigo = "def test_x():\n    '''doc'''\n    pass<ctrl63>\n"
    resultado = _validar_e_sanitizar_codigo(codigo, "HU-004")
    assert "pass<ctrl63>" not in resultado
    assert "pass\n" in resultado


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
