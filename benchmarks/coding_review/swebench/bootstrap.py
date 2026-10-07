"""Bootstrap do processo ANTES de importar qualquer agente do `adk/`.

Os agentes do `workflow_coding_review` resolvem o workspace e fazem o binding
das tools no momento do IMPORT, e leem o modelo de `ADK_LLM_MODEL` também no
import. Por isso `sys.path`, `.env`, modelo e `WORKSPACE_OUTPUT_DIR` precisam
estar fixados antes de o `run.py` importar o loop.

Diferenças deliberadas em relação ao bootstrap do HumanEval:
- a memória de lições (mem0) é DESLIGADA à força, mesmo que o `.env` a ligue:
  lições gravadas numa instância vazariam para a seguinte e as amostras
  deixariam de ser independentes;
- os providers LLM são registrados importando o pacote `shared`, o mesmo
  caminho da produção (ele registra o `GithubCopilotLiteLlm`, que injeta os
  headers de IDE), em vez de registrar o `LiteLlm` genérico.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ADK_DIR = _REPO_ROOT / "adk"

# Variável que liga a memória de lições do workflow (ver
# `adk/shared/coding_review_lesson_memory/config.py`).
MEMORY_ENV_VAR = "AI4ES_MEMORY_ENABLED"


def repo_root() -> Path:
    """Caminho absoluto da raiz do repositório."""
    return _REPO_ROOT


def adk_dir() -> Path:
    """Caminho absoluto do diretório da aplicação ADK (`adk/`)."""
    return _ADK_DIR


def ensure_adk_on_path() -> None:
    """Coloca `adk/` no `sys.path` (imports absolutos `shared`/`src`)."""
    adk_path = str(_ADK_DIR)
    if adk_path not in sys.path:
        sys.path.insert(0, adk_path)


def prepare_environment(
    workspace_dir: Path,
    *,
    env_file: Path | None = None,
    model: str | None = None,
) -> None:
    """Prepara `sys.path`, variáveis de ambiente e os providers LLM.

    Args:
        workspace_dir: diretório usado como `WORKSPACE_OUTPUT_DIR` do fluxo.
        env_file: `.env` a carregar (default: `adk/.env`).
        model: se informado, sobrescreve `ADK_LLM_MODEL`.
    """
    if not _ADK_DIR.is_dir():
        raise RuntimeError(f"Diretório ADK não encontrado: {_ADK_DIR}")

    ensure_adk_on_path()
    _load_dotenv(env_file or (_ADK_DIR / ".env"))

    if model:
        os.environ["ADK_LLM_MODEL"] = model

    # Depois do .env de propósito: o benchmark não pode herdar a memória ligada.
    os.environ[MEMORY_ENV_VAR] = "false"

    workspace_dir.mkdir(parents=True, exist_ok=True)
    os.environ["WORKSPACE_OUTPUT_DIR"] = str(workspace_dir.resolve())

    _configure_llm_providers()


def _load_dotenv(env_path: Path) -> None:
    """Carrega o `.env` sem sobrescrever variáveis já definidas no ambiente."""
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except ImportError:
        for linha in env_path.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            os.environ.setdefault(chave.strip(), valor.strip())


def _configure_llm_providers() -> None:
    """Registra os providers pelo pacote `shared`, como a produção faz."""
    import shared  # noqa: F401 — registra github_copilot/openrouter e o fail-fast do LiteLLM
    from google.adk.models.lite_llm import LiteLlm
    from google.adk.models.registry import LLMRegistry

    # `github/*` não é registrado pelo `shared`; `adk/app/main.py` o registra.
    LLMRegistry._register(r"github/.*", LiteLlm)
