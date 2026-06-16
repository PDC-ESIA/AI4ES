"""Gerenciamento centralizado do workspace de trabalho dos agentes.

Define a estrutura de diretórios, inicialização (com limpeza) e
resolução segura de caminhos por agente.

Regra: o sistema atende UMA prompt por vez. A cada nova sessão/prompt,
o workspace é limpo e recriado com subpastas vazias.

Portado de feat/me2/coding_squad (Time 4) — adaptado para os 14 agentes
+ 5 workflows da nossa consolidação.

Variável de ambiente: WORKSPACE_OUTPUT_DIR (default: ./workspace_output)
- Suporta caminhos absolutos, relativos e com ~ (expandido para home).
"""

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

_ENV_WORKSPACE = "WORKSPACE_OUTPUT_DIR"
_DEFAULT_WORKSPACE = "./workspace_output"

# Arquivo marker que identifica um diretório como workspace gerenciado.
# Previne rmtree acidental em diretórios que não são workspace.
_WORKSPACE_MARKER = ".ai4se_workspace"

# Mapeamento agente → subpasta dentro do workspace.
# Cobre os 14 agentes individuais + 5 workflows + o orchestrator.
# Subpastas são logicamente agrupadas por Time.
AGENT_DIRS: dict[str, str] = {
    # Time 1 — Requisitos
    "requirements_agent": "requirements",
    "requirements": "requirements",
    "glossario_agent": "requirements/glossario",
    # Time 2 — Design
    "design_architect": "design",
    "design_orchestrator": "design",
    "mermaid_specialist": "design/diagrams",
    "markdown_specialist": "design/reports",
    "validator": "design/validation",
    "io_agent": "design/staging",
    # Time 3 — QA / Testes
    "qa_agent": "tests",
    "action_planner": "tests/planning",
    "code_fix_agent": "tests/fixes",
    "receive_requirements": "tests/inputs",
    # Time 4 — Codificação
    "context_engineer": "tasks",
    "cicd_agent": "pipeline",
    "architect": "architecture",
    "test_planner": "test_plans",
    "coder_agent": "coder",
    "coder": "coder",
    "review_agent": "review",
    "reviewer": "review",
    "finalizer": "finalizer",
    # Orquestração
    "orchestrator": "orchestrator",
    "pipeline": "pipeline",
}


def get_workspace_root() -> Path:
    """Resolve o diretório raiz do workspace via variável de ambiente.

    - Caminhos com ``~`` são expandidos para o home do usuário.
    - Caminhos absolutos (ex: ``/opt/workspace``) são usados diretamente.
    - Caminhos relativos (ex: ``workspace_output``) são resolvidos a partir
      do diretório de trabalho corrente (``cwd``).

    Returns:
        Path: caminho absoluto resolvido (não cria o diretório).
    """
    raw = os.environ.get(_ENV_WORKSPACE, _DEFAULT_WORKSPACE)
    path = Path(raw).expanduser()

    if path.is_absolute():
        resolved = path
    else:
        resolved = Path.cwd() / path

    resolved = resolved.resolve()

    logger.debug(
        f"[WORKSPACE] {_ENV_WORKSPACE}='{raw}' → resolvido para: {resolved}"
    )
    return resolved


def init_workspace() -> Path:
    """Limpa e recria o workspace com todas as subpastas dos agentes.

    Deve ser chamado no início de cada nova sessão/prompt para garantir
    um ambiente limpo.

    Safety checks:
    - Se o diretório já existe, só remove se contiver o marker
      `.ai4se_workspace` (previne rmtree acidental em diretórios errados).
    - Valida que o diretório pode ser criado (fail-fast em caso de
      permissões insuficientes ou path inválido).

    Returns:
        Path: Caminho absoluto da raiz do workspace recriado.

    Raises:
        PermissionError: Se não houver permissão para criar/limpar o diretório.
        RuntimeError: Se o diretório existente não for um workspace gerenciado
            (ausência do marker `.ai4se_workspace`).
    """
    root = get_workspace_root()

    if root.exists():
        marker = root / _WORKSPACE_MARKER
        if not marker.exists():
            raise RuntimeError(
                f"[WORKSPACE] Recusa em limpar '{root}': diretório existe mas "
                f"não contém o marker '{_WORKSPACE_MARKER}'. "
                f"Se este é o diretório correto, crie o marker manualmente ou "
                f"remova o diretório antes de executar."
            )
        shutil.rmtree(root)
        logger.info(f"[WORKSPACE] Workspace anterior removido: {root}")

    try:
        root.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise PermissionError(
            f"[WORKSPACE] Sem permissão para criar workspace em '{root}'. "
            f"Verifique a variável {_ENV_WORKSPACE} e as permissões do diretório."
        ) from exc
    except OSError as exc:
        raise OSError(
            f"[WORKSPACE] Falha ao criar workspace em '{root}': {exc}"
        ) from exc

    # Cria marker para identificar este diretório como workspace gerenciado.
    (root / _WORKSPACE_MARKER).write_text(
        "Diretório gerenciado pelo sistema AI4SE. Não remova este arquivo.\n",
        encoding="utf-8",
    )

    # Cria todas as subpastas únicas (dedup via set)
    subdirs_unicos = set(AGENT_DIRS.values())
    for subdir in subdirs_unicos:
        agent_path = root / subdir
        agent_path.mkdir(parents=True, exist_ok=True)

    logger.info(
        f"[WORKSPACE] Workspace inicializado: {root} "
        f"({len(subdirs_unicos)} subpastas criadas)"
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
            f"Agentes válidos: {sorted(AGENT_DIRS.keys())}"
        )
    return get_workspace_root() / AGENT_DIRS[agent_name]
