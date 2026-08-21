"""Bootstrap do ambiente de execução do benchmark HumanEval.

Responsabilidade única: preparar o processo ANTES de importar o Coder Agent.
Isso é crítico porque o módulo do coder (`.../coder/agent.py`) resolve o
diretório de workspace e faz o *binding* das suas tools de filesystem no momento
do IMPORT — logo, `WORKSPACE_OUTPUT_DIR` e o `sys.path` precisam estar corretos
antes disso.

O bootstrap:
- Coloca o diretório `adk/` no `sys.path` (para resolver `shared` e `src`).
- Carrega o `.env` do `adk/` (modelo LLM, timeouts, etc.).
- Registra o provider LiteLLM para os modelos `github_copilot/*` (espelha
  `adk/app/main.py`), senão o ADK não seleciona o backend correto.
- Fixa `WORKSPACE_OUTPUT_DIR` no diretório de workspace do benchmark.

Chame `prepare_environment(...)` UMA vez, no início do `run.py`, e só então
importe os módulos que dependem do coder.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Raiz do repositório (…/AI4ES) e diretório da aplicação ADK (…/AI4ES/adk).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADK_DIR = _REPO_ROOT / "adk"


def repo_root() -> Path:
    """Caminho absoluto da raiz do repositório."""
    return _REPO_ROOT


def adk_dir() -> Path:
    """Caminho absoluto do diretório da aplicação ADK (`adk/`)."""
    return _ADK_DIR


def prepare_environment(
    workspace_dir: Path,
    *,
    env_file: Path | None = None,
    model: str | None = None,
) -> None:
    """Prepara `sys.path`, variáveis de ambiente e o provider LiteLLM.

    Args:
        workspace_dir: diretório usado como `WORKSPACE_OUTPUT_DIR` do coder.
            Será criado se não existir.
        env_file: `.env` a carregar (default: `adk/.env`).
        model: se informado, sobrescreve `ADK_LLM_MODEL` (ex.:
            `github_copilot/gpt-4` ou `gemini-2.5-flash`).
    """
    if not _ADK_DIR.is_dir():
        raise RuntimeError(f"Diretório ADK não encontrado: {_ADK_DIR}")

    # 1) sys.path: o código do projeto usa imports absolutos `shared`/`src`.
    adk_path = str(_ADK_DIR)
    if adk_path not in sys.path:
        sys.path.insert(0, adk_path)

    # 2) .env do adk/ (modelo, timeouts, credenciais).
    env_path = env_file or (_ADK_DIR / ".env")
    _load_dotenv(env_path)

    if model:
        os.environ["ADK_LLM_MODEL"] = model

    # 3) Workspace do coder — precisa estar setado antes do import do agente.
    workspace_dir.mkdir(parents=True, exist_ok=True)
    os.environ["WORKSPACE_OUTPUT_DIR"] = str(workspace_dir.resolve())

    # 4) Provider LiteLLM + fail-fast (espelha adk/app/main.py).
    _configure_litellm()


def _load_dotenv(env_path: Path) -> None:
    """Carrega o `.env` sem sobrescrever variáveis já definidas no ambiente."""
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except Exception:
        # Fallback mínimo: parsing linha-a-linha (KEY=VALUE), sem dependências.
        for linha in env_path.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            os.environ.setdefault(chave.strip(), valor.strip())


def _configure_litellm() -> None:
    """Registra o LiteLlm para `github_copilot/*` e aplica limites fail-fast."""
    try:
        import litellm
        from google.adk.models.lite_llm import LiteLlm
        from google.adk.models.registry import LLMRegistry

        LLMRegistry._register(r"github_copilot/.*", LiteLlm)
        LLMRegistry._register(r"github/.*", LiteLlm)

        litellm.drop_params = True
        litellm.request_timeout = float(os.environ.get("AI4ES_LLM_TIMEOUT", "120"))
        litellm.num_retries = int(os.environ.get("AI4ES_LLM_NUM_RETRIES", "1"))
    except Exception as exc:  # noqa: BLE001 — não fatal; run.py reporta na chamada
        print(f"[bootstrap] Aviso: falha ao configurar LiteLLM: {exc}", file=sys.stderr)
