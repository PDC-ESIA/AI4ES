"""
Gerenciamento centralizado do workspace de trabalho dos agentes SE.

Define a estrutura de diretórios, inicialização (com limpeza) e
resolução segura de caminhos por agente.

Regra: o sistema atende UMA prompt por vez. A cada nova sessão/prompt,
o workspace é limpo e recriado com subpastas vazias.
"""

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

_ENV_WORKSPACE = "WORKSPACE_OUTPUT_DIR"
_DEFAULT_WORKSPACE = "./workspace_output"

# Mapeamento agente → subpasta dentro do workspace
AGENT_DIRS: dict[str, str] = {
    "requirements_agent": "requirements",
    "context_engineer": "tasks",
    "coder_agent": "coder",
    "review_agent": "review",
    "pipeline": "pipeline",
}


def get_workspace_root() -> Path:
    """Resolve o diretório raiz do workspace via variável de ambiente."""
    return Path(os.environ.get(_ENV_WORKSPACE, _DEFAULT_WORKSPACE)).resolve()


def init_workspace() -> Path:
    """Limpa e recria o workspace com todas as subpastas dos agentes.

    Deve ser chamado no início de cada nova sessão/prompt para garantir
    um ambiente limpo.

    Returns:
        Path: Caminho absoluto da raiz do workspace recriado.
    """
    root = get_workspace_root()

    if root.exists():
        shutil.rmtree(root)
        logger.info(f"[WORKSPACE] Workspace anterior removido: {root}")

    root.mkdir(parents=True, exist_ok=True)

    for agent_name, subdir in AGENT_DIRS.items():
        agent_path = root / subdir
        agent_path.mkdir(parents=True, exist_ok=True)

    logger.info(
        f"[WORKSPACE] Workspace inicializado: {root} "
        f"({len(AGENT_DIRS)} subpastas criadas)"
    )
    return root


def get_agent_workspace(agent_name: str) -> Path:
    """Retorna o caminho absoluto da subpasta do agente no workspace.

    Args:
        agent_name: Nome do agente (deve existir em AGENT_DIRS).

    Returns:
        Path absoluto da subpasta do agente.

    Raises:
        ValueError: Se o agente não está mapeado em AGENT_DIRS.
    """
    if agent_name not in AGENT_DIRS:
        raise ValueError(
            f"Agente '{agent_name}' não possui subpasta mapeada. "
            f"Agentes válidos: {list(AGENT_DIRS.keys())}"
        )
    return get_workspace_root() / AGENT_DIRS[agent_name]


def resolve_agent_path(agent_name: str, relative_path: str) -> Path:
    """Resolve um caminho relativo dentro da subpasta do agente.

    Garante que o caminho final está DENTRO da subpasta do agente,
    rejeitando path traversal e caminhos absolutos.

    Args:
        agent_name: Nome do agente.
        relative_path: Caminho relativo ao diretório do agente.

    Returns:
        Path absoluto resolvido e seguro.

    Raises:
        ValueError: Se o caminho tenta escapar da subpasta do agente.
    """
    agent_dir = get_agent_workspace(agent_name)

    rel = Path(relative_path)

    if rel.is_absolute():
        raise ValueError(
            f"Caminho absoluto não permitido: '{relative_path}'. "
            f"Use caminhos relativos ao diretório do agente."
        )

    if ".." in rel.parts:
        raise ValueError(
            f"Path traversal não permitido: '{relative_path}'. "
            f"Não use '..' no caminho."
        )

    resolved = (agent_dir / rel).resolve()

    # Verificação final: o caminho resolvido deve estar dentro do agent_dir
    if not str(resolved).startswith(str(agent_dir)):
        raise ValueError(
            f"Caminho '{relative_path}' escapa da subpasta do agente. "
            f"Caminho resolvido: {resolved}, esperado dentro de: {agent_dir}"
        )

    return resolved
