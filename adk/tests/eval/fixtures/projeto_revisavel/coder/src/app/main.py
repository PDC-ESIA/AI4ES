"""API de consulta ao catalogo de livros (RF-001, RF-002)."""

import json  # noqa: F401 -- import nao usado, plantado para a analise estatica

from fastapi import FastAPI

app = FastAPI(title="Catalogo de Livros")

_CATALOGO = [
    {
        "id": 1,
        "titulo": "Dom Casmurro",
        "autor": "Machado de Assis",
        "disponivel": True,
    },
    {
        "id": 2,
        "titulo": "A Hora da Estrela",
        "autor": "Clarice Lispector",
        "disponivel": False,
    },
    {
        "id": 3,
        "titulo": "Memorias Postumas",
        "autor": "Machado de Assis",
        "disponivel": True,
    },
]


@app.get("/livros")
def listar_livros(autor: str | None = None):
    """Lista o catalogo, opcionalmente filtrado por autor."""
    try:
        livros = sorted(_CATALOGO, key=lambda livro: livro["titulo"])
        if autor:
            alvo = autor.lower()
            livros = [livro for livro in livros if alvo in livro["autor"].lower()]
        return livros
    except Exception:
        # Problema plantado: engole qualquer erro e devolve 200 com lista vazia,
        # escondendo a falha do cliente.
        return []
