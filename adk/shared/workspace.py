"""Gerenciamento centralizado do workspace de trabalho dos agentes.

Define a estrutura de diretórios, inicialização e resolução segura de
caminhos por agente.

Workspace por sessão: cada sessão ADK tem sua própria pasta em
``<WORKSPACE_OUTPUT_DIR>/<yyyyMMdd-HHmm>-<session_id>/`` — o timestamp é o da
criação; execuções seguintes da mesma sessão reaproveitam a pasta existente. A sessão corrente é carregada num
``ContextVar`` (ver ``session_workspace``), definido pelo
``SessionWorkspacePlugin`` no início de cada run — sessões concorrentes no
mesmo processo não se enxergam. Sem sessão definida (scripts, benchmarks,
testes), a raiz é o próprio ``WORKSPACE_OUTPUT_DIR``.

O workspace de uma sessão NUNCA é apagado automaticamente: só via
``delete_session_workspace()``, por pedido explícito do usuário.

Portado de feat/me2/coding_squad (Time 4) — adaptado para os 14 agentes
+ 5 workflows da nossa consolidação.

Variável de ambiente: WORKSPACE_OUTPUT_DIR (default: ./workspace_output)
- Suporta caminhos absolutos, relativos e com ~ (expandido para home).
"""

import logging
import os
import re
import shutil
import threading
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import datetime
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

_ENV_WORKSPACE = "WORKSPACE_OUTPUT_DIR"
_DEFAULT_WORKSPACE = "./workspace_output"

# Arquivo marker que identifica um diretório como workspace gerenciado.
# Previne rmtree acidental em diretórios que não são workspace.
_WORKSPACE_MARKER = ".ai4se_workspace"

# Session id vira nome de pasta: só caracteres seguros (sem "/", sem "..").
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

# Prefixo do nome da pasta da sessão: yyyyMMdd-HHmm (hora local da criação).
_SESSION_DIR_TIMESTAMP = "%Y%m%d-%H%M"
_SESSION_DIR_GLOB = "[0-9]" * 8 + "-" + "[0-9]" * 4 + "-"

# Pasta escolhida por (base, session_id): o timestamp é fixado na primeira
# resolução, para todas as chamadas seguintes caírem na mesma pasta mesmo
# antes de ela existir em disco.
_session_dirs: dict[tuple[Path, str], Path] = {}
_session_dirs_lock = threading.Lock()

_current_session_id: ContextVar[str | None] = ContextVar(
    "ai4se_workspace_session_id", default=None
)

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
    "mermaid_specialist": "design",
    "markdown_specialist": "design",
    "validator": "design",
    "io_agent": "design",
    # Time 3 — QA / Testes
    "qa_agent": "tests",
    "action_planner": "tests/planning",
    "code_fix_agent": "tests/fixes",
    "receive_requirements": "tests/inputs",
    "integration_tests_agent": "tests/integration_tests",
    "unit_test_generator": "tests/unit",
    "e2e_test_generator": "tests/e2e",
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
    "implementation_validator": "coder/validation",
    # Orquestração
    "orchestrator": "orchestrator",
    "pipeline": "pipeline",
}


def get_workspace_base() -> Path:
    """Resolve o diretório base dos workspaces via variável de ambiente.

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

    return resolved.resolve()


def _validate_session_id(session_id: str) -> str:
    if not isinstance(session_id, str) or not _SESSION_ID_RE.match(session_id):
        raise ValueError(
            f"[WORKSPACE] session_id inválido para nome de pasta: {session_id!r}"
        )
    return session_id


def get_session_id() -> str | None:
    """Session id cujo workspace está ativo no contexto corrente (ou None)."""
    return _current_session_id.get()


def set_session_id(session_id: str | None) -> Token:
    """Ativa o workspace da sessão no contexto corrente.

    Devolve o token para ``reset_session_id``. Prefira ``session_workspace``
    quando o escopo couber num ``with``.
    """
    if session_id is not None:
        _validate_session_id(session_id)
    return _current_session_id.set(session_id)


def reset_session_id(token: Token) -> None:
    _current_session_id.reset(token)


@contextmanager
def session_workspace(session_id: str) -> Iterator[Path]:
    """Context manager: ativa (e cria) o workspace da sessão no bloco."""
    token = set_session_id(session_id)
    try:
        yield init_workspace()
    finally:
        reset_session_id(token)


def _find_session_dir(base: Path, session_id: str) -> Path | None:
    """Pasta já existente da sessão (``<timestamp>-<session_id>``), se houver."""
    # session_id validado só tem [A-Za-z0-9._-]: nenhum metacaractere de glob.
    matches = sorted(
        d for d in base.glob(_SESSION_DIR_GLOB + session_id) if d.is_dir()
    )
    return matches[0] if matches else None


def get_session_workspace(session_id: str) -> Path:
    """Caminho do workspace de uma sessão (não cria).

    Reaproveita a pasta existente ``<timestamp>-<session_id>``; se não houver,
    fixa um nome novo com o timestamp atual.
    """
    _validate_session_id(session_id)
    base = get_workspace_base()
    key = (base, session_id)
    with _session_dirs_lock:
        cached = _session_dirs.get(key)
        if cached is not None:
            return cached
        found = _find_session_dir(base, session_id)
        if found is None:
            stamp = datetime.now().strftime(_SESSION_DIR_TIMESTAMP)
            found = base / f"{stamp}-{session_id}"
        _session_dirs[key] = found
        return found


def get_workspace_root() -> Path:
    """Raiz do workspace ativo.

    ``<WORKSPACE_OUTPUT_DIR>/<yyyyMMdd-HHmm>-<session_id>`` quando há sessão
    no contexto; senão o próprio ``WORKSPACE_OUTPUT_DIR``. Não cria o diretório.
    """
    session_id = _current_session_id.get()
    if session_id is not None:
        root = get_session_workspace(session_id)
    else:
        root = get_workspace_base()
    logger.debug(f"[WORKSPACE] raiz ativa (session={session_id}): {root}")
    return root


def init_workspace() -> Path:
    """Garante que o workspace ativo existe (cria raiz + marker se faltar).

    Não apaga nada: um workspace já existente (ex.: nova prompt na mesma
    sessão) é reaproveitado como está. As subpastas dos agentes são criadas
    sob demanda por ``get_agent_workspace()``.

    Returns:
        Path: Caminho absoluto da raiz do workspace.

    Raises:
        PermissionError: Se não houver permissão para criar o diretório.
    """
    root = get_workspace_root()

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

    # Marker identifica o diretório como workspace gerenciado — pré-requisito
    # para delete_session_workspace() aceitar removê-lo.
    marker = root / _WORKSPACE_MARKER
    if not marker.exists():
        marker.write_text(
            "Diretório gerenciado pelo sistema AI4SE. Não remova este arquivo.\n",
            encoding="utf-8",
        )
        logger.info(f"[WORKSPACE] Workspace criado: {root}")
    return root


def delete_session_workspace(session_id: str) -> bool:
    """Apaga o workspace de uma sessão. Só deve ser chamado a pedido do usuário.

    Returns:
        True se removido; False se não existia.

    Raises:
        RuntimeError: Se o diretório existe mas não tem o marker
            ``.ai4se_workspace`` (previne rmtree em diretório errado).
    """
    root = get_session_workspace(session_id)
    if not root.exists():
        return False
    if not (root / _WORKSPACE_MARKER).exists():
        raise RuntimeError(
            f"[WORKSPACE] Recusa em apagar '{root}': diretório não contém "
            f"o marker '{_WORKSPACE_MARKER}'."
        )
    shutil.rmtree(root)
    with _session_dirs_lock:
        _session_dirs.pop((get_workspace_base(), session_id), None)
    logger.info(f"[WORKSPACE] Workspace da sessão removido: {root}")
    return True


def get_agent_workspace(agent_name: str) -> Path:
    """Retorna o caminho absoluto da subpasta do agente no workspace.

    Cria o diretório sob demanda na primeira chamada (lazy init),
    evitando a criação de pastas que nunca serão utilizadas.

    Args:
        agent_name: Nome do agente (deve existir em AGENT_DIRS).

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
    agent_path = get_workspace_root() / AGENT_DIRS[agent_name]
    agent_path.mkdir(parents=True, exist_ok=True)
    return agent_path
