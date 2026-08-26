"""conftest.py — Camada 1 (infraestrutura).

Testes determinísticos: schemas Pydantic, ferramentas (tools), workspace,
harness Docker, orquestração ADK sem depender de julgamento de qualidade
("é isso que o código faz", não "isso é uma boa resposta"). `tmp_path` e
`monkeypatch` já vêm prontos do pytest — as fixtures abaixo só compõem
sobre eles o que é específico deste projeto (base_dir de tools, schemas
de exemplo).

O pré-cache de módulos ADK/Pydantic (necessário porque `test_git_tools.py`
substitui `pydantic.BaseModel` em `sys.modules`) agora vive no conftest
global (`tests/conftest.py`), que é carregado antes deste — não precisa
ser repetido aqui.

collect_ignore: exclui arquivos com problemas pré-existentes:
- test_filesystem_tools.py — conflito de merge não resolvido (SyntaxError)
- test_geracao_condicional.py — importa adk.agents.roles.* (caminho removido
  na consolidação dos Times)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import pytest

collect_ignore = [
    "test_filesystem_tools.py",
    "test_geracao_condicional.py",
]


# ---------------------------------------------------------------------------
# Fixtures de mocks/wrappers de tools
# ---------------------------------------------------------------------------

@pytest.fixture
def tool_base_dir(tmp_path: Path) -> Path:
    """Diretório base isolado para tools que aceitam `base_dir` (workspace-bound)."""
    return tmp_path


@pytest.fixture
def tool_criar_arquivo_bound(tool_base_dir: Path) -> Callable[..., dict]:
    """`tool_criar_arquivo` pré-vinculada a um `base_dir` isolado por teste.

    Evita repetir `base_dir=str(tmp_path)` em cada chamada dentro do teste::

        def test_algo(tool_criar_arquivo_bound):
            resultado = tool_criar_arquivo_bound("modulo.py", "print(1)")
            assert resultado["sucesso"]
    """
    from shared.tools.coding_tools.filesystem_coding import tool_criar_arquivo

    def _chamar(caminho: str, conteudo: str, **kwargs: Any) -> dict:
        return tool_criar_arquivo(caminho, conteudo, base_dir=str(tool_base_dir), **kwargs)

    return _chamar


@pytest.fixture
def tool_ler_arquivo_bound(tool_base_dir: Path) -> Callable[..., str]:
    """`tool_ler_arquivo` pré-vinculada ao mesmo `base_dir` de `tool_criar_arquivo_bound`."""
    from shared.tools.coding_tools.filesystem_coding import tool_ler_arquivo

    def _chamar(caminho: str, **kwargs: Any) -> str:
        return tool_ler_arquivo(caminho, base_dir=str(tool_base_dir), **kwargs)

    return _chamar


@pytest.fixture
def mock_docker_client():
    """`MagicMock` mínimo com a superfície do SDK `docker` usada pelo harness.

    Cobre `images.build`, `containers.run/get` e `exec_run` com um retorno
    de sucesso "neutro" — testes que precisam de comportamento específico
    (ex.: falha de build) devem sobrescrever os atributos relevantes.
    """
    from unittest.mock import MagicMock

    client = MagicMock()
    client.images.build.return_value = (
        MagicMock(),
        [{"stream": "Successfully built abc123"}],
    )
    container = MagicMock()
    container.status = "running"
    container.attrs = {"State": {"ExitCode": 0}}
    container.logs.return_value = b""
    client.containers.run.return_value = container
    return client


# ---------------------------------------------------------------------------
# Fixtures de schemas Pydantic (instâncias de exemplo)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_phase_manifest() -> dict:
    """Dict válido para `shared.manifest.PhaseManifest.model_validate(...)`."""
    from tests.fixtures.test_data import SAMPLE_CODING_MANIFEST

    return dict(SAMPLE_CODING_MANIFEST)


@pytest.fixture
def sample_manifest_model():
    """Instância já validada de `PhaseManifest`, pronta para uso direto no teste."""
    from shared.manifest import PhaseManifest

    from tests.fixtures.test_data import SAMPLE_CODING_MANIFEST

    return PhaseManifest.model_validate(SAMPLE_CODING_MANIFEST)
