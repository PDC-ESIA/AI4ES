"""Jornada pelo navegador (Playwright) contra um produto web real.

Precisa de um Python com `pytest-playwright` e o Chromium instalado; aponte-o
em AI4ES_TESTE_PLAYWRIGHT_PYTHON (ex.: o venv da trilha python-web). Sem ele,
os testes são pulados.
"""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path

import pytest

from shared.tools.coding_tools.jornada import ARQUIVO_JORNADA, FALHOU, PASSOU, executar_jornada

PY = os.environ.get("AI4ES_TESTE_PLAYWRIGHT_PYTHON", "")
pytestmark = pytest.mark.skipif(not PY, reason="AI4ES_TESTE_PLAYWRIGHT_PYTHON não definido")

_APP = '''
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response

app = FastAPI()
FOTOS = []
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)
IMG = "IMAGEM"

@app.get("/", response_class=HTMLResponse)
def painel():
    imgs = "".join(f'<img src="{IMG}" alt="{n}">' for n in FOTOS)
    return f"""<html><head>
      <script src="https://unpkg.com/htmx.org@1.9.2"></script></head><body>
      <form action="/fotos" method="post" enctype="multipart/form-data">
        <input type="file" name="arquivo"><button>Enviar</button>
      </form>
      <div id="galeria">{imgs}</div>
      <button hx-get="/contagem" hx-target="#total">Contar</button><span id="total"></span>
    </body></html>"""

@app.post("/fotos")
def enviar(arquivo: UploadFile = File(...)):
    FOTOS.append(arquivo.filename)
    return RedirectResponse("/", status_code=303)

@app.get("/contagem", response_class=HTMLResponse)
def contagem():
    return f"{len(FOTOS)} foto(s)"

@app.get("/media/ok.png")
def ok():
    return Response(PNG, media_type="image/png")
'''

_JORNADA = '''
from playwright.sync_api import Page, expect

def test_jornada_01_envia_foto_e_ve_na_galeria(page: Page):
    page.goto("/")
    page.locator("input[type=file]").set_input_files(
        [{"name": "a.png", "mimeType": "image/png", "buffer": b"x"}]
    )
    page.get_by_role("button", name="Enviar").click()
    expect(page.locator("#galeria img")).to_have_count(1)
    page.get_by_role("button", name="Contar").click()          # htmx de verdade
    expect(page.locator("#total")).to_have_text("1 foto(s)")
'''


def _porta() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _produto(raiz: Path, imagem: str) -> Path:
    raiz.mkdir(parents=True)
    (raiz / "loja.py").write_text(_APP.replace('"IMAGEM"', repr(imagem)))
    (raiz / "tests" / "journey").mkdir(parents=True)
    (raiz / ARQUIVO_JORNADA).write_text(_JORNADA)
    porta = _porta()
    (raiz / "run.json").write_text(json.dumps({
        "surface": "service", "build": [],
        "run": f"{PY} -m uvicorn loja:app --port {porta}",
        "port": porta, "healthcheck": "/", "test": [f"{PY} -m pytest -v"],
    }))
    return raiz


def test_jornada_web_passa_com_o_produto_certo(tmp_path):
    resultado = executar_jornada(_produto(tmp_path / "ok", "/media/ok.png"))
    assert resultado.status == PASSOU, resultado.saida


def test_conftest_reprova_imagem_quebrada(tmp_path):
    resultado = executar_jornada(_produto(tmp_path / "quebrada", "/media/nao-existe.png"))
    assert resultado.status == FALHOU
    assert "GET /media/nao-existe.png -> 404" in resultado.saida
