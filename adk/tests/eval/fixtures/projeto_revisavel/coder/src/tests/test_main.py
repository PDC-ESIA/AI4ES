"""Testes do catalogo de livros."""

from fastapi.testclient import TestClient

from app.main import app

cliente = TestClient(app)


def test_listar_devolve_o_catalogo_ordenado():
    resposta = cliente.get("/livros")
    assert resposta.status_code == 200
    titulos = [livro["titulo"] for livro in resposta.json()]
    assert titulos == sorted(titulos)


def test_filtro_por_autor_ignora_caixa():
    resposta = cliente.get("/livros", params={"autor": "machado"})
    assert resposta.status_code == 200
    assert len(resposta.json()) == 2
