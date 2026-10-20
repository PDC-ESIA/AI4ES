"""Provas reais do isolamento. Opt-in exige imagem previamente construída."""
import os

import pytest

from shared.qa_sandbox import executar_isolado

pytestmark = pytest.mark.skipif(os.environ.get("QA_SANDBOX_INTEGRATION") != "1",
                                reason="Requer Docker e imagem ai4es-qa-sandbox:local")


def test_container_nao_acessa_host_segredos_ou_rede(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "chave-do-host")
    privado = tmp_path / "arquivo-privado.txt"
    privado.write_text("PROMPT INTERNO")
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / ".env").write_text("API_KEY=segredo")
    codigo = f'''
import os
import socket
from pathlib import Path
import pytest

def test_isolamento():
    assert 'GOOGLE_API_KEY' not in os.environ
    assert not Path({str(privado)!r}).exists()
    assert not Path('/var/run/docker.sock').exists()
    assert not Path('/input/suite/.env').exists()
    assert os.getuid() != 0
    with pytest.raises(OSError):
        socket.create_connection(('1.1.1.1', 443), timeout=1)
    with pytest.raises(OSError):
        Path('/input/suite/nova.py').write_text('x')
'''
    (suite / "test_isolamento.py").write_text(codigo, encoding="utf-8")
    resultado = executar_isolado(suite, "test_isolamento.py")
    assert resultado["exit_code"] == 0
    assert resultado["passed"] == 1


@pytest.mark.parametrize("codigo", [
    "import fs from 'node:fs';",
    "const x = process['env'];",
    "const x = import('node:child_process');",
])
def test_parser_typescript_rejeita_spec(tmp_path, codigo):
    suite = tmp_path / "suite"
    app = tmp_path / "app"
    suite.mkdir()
    app.mkdir()
    (suite / "test.spec.ts").write_text(codigo)
    (app / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
    resultado = executar_isolado(suite, "test.spec.ts", modo="playwright",
                                projeto=app, entrypoint="main:app", timeout=60)
    assert resultado["exit_code"] != 0


def test_playwright_alcanca_somente_alvo_no_container(tmp_path):
    suite = tmp_path / "suite"
    app = tmp_path / "app"
    suite.mkdir()
    app.mkdir()
    (app / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n"
        "@app.get('/health')\ndef health(): return {'ok': True}\n")
    (suite / "test.spec.ts").write_text(
        "import { test, expect } from '@playwright/test';\n"
        "test('local', async ({ request }) => {\n"
        "const r = await request.get('http://127.0.0.1:8765/health');\n"
        "expect(r.status()).toBe(200); });\n")
    resultado = executar_isolado(suite, "test.spec.ts", modo="playwright",
                                projeto=app, entrypoint="main:app", timeout=60)
    assert resultado["exit_code"] == 0
    assert resultado["passed"] == 1
