"""Testes dos resolvedores usados pelo ExecutorOrchestrator."""

from src.agents.dockerfile_resolver.agent import (
    _extrair_dockerfile,
    _remover_cerca_markdown as remover_cerca_dockerfile,
    criar_agente as criar_dockerfile_resolver,
)
from src.agents.test_command_resolver.agent import (
    _extrair_comando,
    _remover_cerca_markdown as remover_cerca_comando,
    criar_agente as criar_test_command_resolver,
)


class _Context:
    def __init__(self, state):
        self.state = state


def test_extrai_dockerfile_com_marcacoes():
    ctx = _Context(
        {
            "dockerfile_resolution_raw": (
                "DOCKERFILE_INICIO\nFROM python:3.12-slim\nEXPOSE 8000\nDOCKERFILE_FIM"
            )
        }
    )
    assert _extrair_dockerfile(ctx) is None
    assert ctx.state["dockerfile_resolution"]["dockerfile"] == (
        "FROM python:3.12-slim\nEXPOSE 8000"
    )


def test_extrai_dockerfile_remove_cerca_markdown():
    ctx = _Context(
        {
            "dockerfile_resolution_raw": (
                "DOCKERFILE_INICIO\n```dockerfile\nFROM alpine\n```\nDOCKERFILE_FIM"
            )
        }
    )
    _extrair_dockerfile(ctx)
    assert ctx.state["dockerfile_resolution"] == {"dockerfile": "FROM alpine"}
    assert remover_cerca_dockerfile("texto\n```\n") == "texto\n```\n"


def test_dockerfile_invalido_produz_none():
    for raw in ("", "FROM alpine", "DOCKERFILE_INICIO\n\nDOCKERFILE_FIM"):
        ctx = _Context({"dockerfile_resolution_raw": raw})
        _extrair_dockerfile(ctx)
        assert ctx.state["dockerfile_resolution"] == {"dockerfile": None}


def test_extrai_comando_com_marcacoes_e_cerca():
    ctx = _Context(
        {"test_command_resolution_raw": "COMANDO_INICIO\n```sh\npytest -q\n```\nCOMANDO_FIM"}
    )
    assert _extrair_comando(ctx) is None
    assert ctx.state["test_command_resolution"] == {"comando": "pytest -q"}
    assert remover_cerca_comando("npm test") == "npm test"


def test_comando_invalido_produz_none():
    for raw in ("", "pytest", "COMANDO_INICIO\n\nCOMANDO_FIM"):
        ctx = _Context({"test_command_resolution_raw": raw})
        _extrair_comando(ctx)
        assert ctx.state["test_command_resolution"] == {"comando": None}


def test_criar_agente_devolve_instancias_independentes():
    docker_a, docker_b = criar_dockerfile_resolver(), criar_dockerfile_resolver()
    command_a, command_b = criar_test_command_resolver(), criar_test_command_resolver()
    assert docker_a is not docker_b
    assert command_a is not command_b
    assert docker_a.after_agent_callback is not None
    assert command_a.after_agent_callback is not None
