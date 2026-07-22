"""Gerenciamento do sandbox Daytona compartilhado pela sessão.

Espelha o padrão de shared/workspace.py, mas o "workspace" passa a ser
um sandbox remoto Daytona em vez de uma pasta local. Reaproveita
AGENT_DIRS como fonte única de verdade para as subpastas por agente —
a estrutura lógica de pastas não muda, só onde ela fisicamente existe.

Regra de sessão: UM sandbox por sessão inteira, compartilhado entre os
14 agentes (mesma decisão de design do workspace local: cross-agent
read via tool_ler_workspace exige uma raiz comum visível a todos).

Variável de ambiente: DAYTONA_SANDBOX_ID — guarda o ID do sandbox ativo
da sessão corrente, permitindo que agentes diferentes (chamadas de tool
separadas) reconectem ao mesmo sandbox em vez de criar um novo.
"""

import logging
import os

from daytona import Daytona, DaytonaConfig, Sandbox

from shared.workspace import AGENT_DIRS

logger = logging.getLogger(__name__)

_ENV_SANDBOX_ID = "DAYTONA_SANDBOX_ID"

_daytona_client: Daytona | None = None


def _get_client() -> Daytona:
    """Cliente Daytona (singleton simples, reaproveitado entre chamadas)."""
    global _daytona_client
    if _daytona_client is None:
        config = DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"])
        _daytona_client = Daytona(config)
    return _daytona_client


def get_or_create_sandbox() -> Sandbox:
    """Retorna o sandbox da sessão corrente, criando um novo se necessário.

    Espelha a lógica de get_workspace_root(): primeira chamada da sessão
    cria o recurso, chamadas subsequentes (de outros agentes/tools)
    reconectam ao mesmo recurso via ID salvo em variável de ambiente.

    Returns:
        Sandbox ativo (novo ou reconectado).
    """
    client = _get_client()
    sandbox_id = os.environ.get(_ENV_SANDBOX_ID)

    if sandbox_id:
        try:
            sandbox = client.get(sandbox_id)
            logger.debug(f"[SANDBOX] Reconectado ao sandbox existente: {sandbox_id}")
            return sandbox
        except Exception:
            logger.warning(
                f"[SANDBOX] Sandbox '{sandbox_id}' não encontrado/expirado, "
                f"criando um novo."
            )

    sandbox = client.create()
    os.environ[_ENV_SANDBOX_ID] = sandbox.id
    logger.info(f"[SANDBOX] Novo sandbox criado para a sessão: {sandbox.id}")
    return sandbox


def get_agent_sandbox_path(agent_name: str) -> str:
    """Caminho relativo (dentro do sandbox) da subpasta do agente.

    Equivalente sandbox-aware de get_agent_workspace() — mesma lógica de
    AGENT_DIRS, mas devolve string relativa (para uso com sandbox.fs),
    não um Path local absoluto.

    Args:
        agent_name: Nome do agente (deve existir em AGENT_DIRS).

    Returns:
        Caminho relativo dentro do sandbox, ex: "coder", "design/diagrams".

    Raises:
        ValueError: Se o agente não está mapeado em AGENT_DIRS.
    """
    if agent_name not in AGENT_DIRS:
        raise ValueError(
            f"Agente '{agent_name}' não possui subpasta mapeada. "
            f"Agentes válidos: {sorted(AGENT_DIRS.keys())}"
        )
    return f"workspace/{AGENT_DIRS[agent_name]}"