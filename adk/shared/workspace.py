"""Gerenciamento centralizado do workspace de trabalho dos agentes.

Define a estrutura de diretórios, inicialização (com limpeza) e
resolução segura de caminhos por agente.

Suporta dois modos, escolhidos por quem chama (opt-in, não muda o padrão):

- **Legado (sem `session_id`)**: opera direto sobre a raiz de
  `WORKSPACE_OUTPUT_DIR`. `init_workspace()` limpa e recria essa raiz
  inteira — comportamento inalterado, preservado por compatibilidade.
- **Por sessão (com `session_id`)**: opera sob
  `WORKSPACE_OUTPUT_DIR/sessions/<session_id>/`, isolada das demais
  sessões. `init_workspace(session_id=...)` só limpa/recria a subpasta
  dessa sessão — nunca toca em `sessions/<outro_id>/`. Quem decide o
  `session_id` (tipicamente `ctx.session.id`) é responsabilidade de quem
  chama (ex.: o orchestrator), não deste módulo.

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

# Subpasta sob a raiz onde vivem os workspaces isolados por sessão.
_SESSIONS_SUBDIR = "sessions"

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
    "architect": "architecture",
    "test_planner": "test_plans",
    "coder_agent": "coder",
    "coder": "coder",
    "review_agent": "review",
    "reviewer": "review",
    "finalizer": "finalizer",
    # Workflow coding_review — artefatos consolidados em coder/
    "cr_context_engineer": "coder/tasks",
    "cr_coder": "coder/src",
    "cr_executor": "coder/execution",
    "cr_reviewer": "coder/review",
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

    logger.debug(f"[WORKSPACE] {_ENV_WORKSPACE}='{raw}' → resolvido para: {resolved}")
    return resolved


def get_session_root(session_id: str) -> Path:
    """Resolve a raiz isolada de uma sessão específica.

    Path: ``<workspace_root>/sessions/<session_id>/``. Sessões diferentes
    nunca compartilham diretório — isso é o que garante que inicializar ou
    limpar a sessão corrente jamais afeta artefatos de sessões anteriores.

    Args:
        session_id: identificador da sessão (ex.: ``ctx.session.id``).
            Quem decide esse valor é responsabilidade de quem chama (o
            orchestrator, tipicamente) — este módulo só resolve o path.

    Returns:
        Path: caminho absoluto resolvido (não cria o diretório).

    Raises:
        ValueError: se `session_id` for vazio.
    """
    if not session_id:
        raise ValueError("session_id não pode ser vazio.")
    return get_workspace_root() / _SESSIONS_SUBDIR / session_id


def init_workspace(session_id: str | None = None) -> Path:
    """Limpa e recria o workspace (somente a raiz + marker).

    As subpastas dos agentes são criadas sob demanda por
    ``get_agent_workspace()``, evitando a criação de diretórios
    que nunca serão utilizados na sessão corrente.

    Deve ser chamado no início de cada nova sessão/prompt para garantir
    um ambiente limpo.

    Args:
        session_id: quando informado, opera sob a raiz isolada dessa sessão
            (``get_session_root(session_id)``) em vez da raiz legada —
            limpa/recria só a subpasta dessa sessão, nunca a de outra.
            Quando omitido (padrão), preserva o comportamento legado:
            limpa/recria a raiz inteira de ``WORKSPACE_OUTPUT_DIR``.

    Safety checks:
    - Se o diretório já existe, só remove se contiver o marker
      `.ai4se_workspace` (previne rmtree acidental em diretórios errados).
    - Valida que o diretório pode ser criado (fail-fast em caso de
      permissões insuficientes ou path inválido).

    Returns:
        Path: Caminho absoluto da raiz do workspace recriado (raiz legada ou
        raiz da sessão, dependendo de `session_id`).

    Raises:
        PermissionError: Se não houver permissão para criar/limpar o diretório.
        RuntimeError: Se o diretório existente não for um workspace gerenciado
            (ausência do marker `.ai4se_workspace`).
    """
    root = get_session_root(session_id) if session_id else get_workspace_root()

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

    logger.info(
        f"[WORKSPACE] Workspace inicializado: {root} "
        f"(subpastas serão criadas sob demanda)"
    )
    return root


def get_agent_workspace(agent_name: str, session_id: str | None = None) -> Path:
    """Retorna o caminho absoluto da subpasta do agente no workspace.

    Cria o diretório sob demanda na primeira chamada (lazy init),
    evitando a criação de pastas que nunca serão utilizadas.

    Args:
        agent_name: Nome do agente (deve existir em AGENT_DIRS).
        session_id: quando informado, resolve a subpasta sob a raiz isolada
            dessa sessão (``get_session_root(session_id)``) em vez da raiz
            legada. Quando omitido (padrão), preserva o comportamento legado.

    Returns:
        Path absoluto da subpasta do agente (já existente no filesystem).

    Raises:
        ValueError: Se o agente não está mapeado em AGENT_DIRS.
    """
    if agent_name not in AGENT_DIRS:
        raise ValueError(
            f"Agente '{agent_name}' não possui subpasta mapeada. "
            f"Agentes válidos: {sorted(AGENT_DIRS.keys())}"
        )
    root = get_session_root(session_id) if session_id else get_workspace_root()
    agent_path = root / AGENT_DIRS[agent_name]
    agent_path.mkdir(parents=True, exist_ok=True)
    return agent_path
