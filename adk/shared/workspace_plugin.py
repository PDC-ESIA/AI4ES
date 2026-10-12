"""Plugin ADK que ativa o workspace da sessão em cada run.

Registrado no nível do app (``extra_plugins`` em ``app/main.py``), roda no
``before_run_callback`` de toda invocação: define o session id corrente no
``ContextVar`` de ``shared.workspace`` e garante que a pasta
``<WORKSPACE_OUTPUT_DIR>/<yyyyMMdd-HHmm>-<session_id>/`` existe. Todas as tools resolvem
caminhos via ``get_workspace_root()`` no momento da chamada, então passam a
escrever na pasta da sessão.

Runners aninhados (o orchestrator repassa ``ctx.plugin_manager.plugins`` aos
sub-pipelines, que usam sessões internas próprias) herdam o session id da
sessão EXTERNA: o plugin só define o valor quando ainda não há um ativo.
"""

from __future__ import annotations

from contextvars import Token
from typing import TYPE_CHECKING, Optional

from google.adk.plugins import BasePlugin

from shared.workspace import (
    get_session_id,
    init_workspace,
    reset_session_id,
    set_session_id,
)

if TYPE_CHECKING:
    from google.adk.agents.invocation_context import InvocationContext
    from google.genai import types


class SessionWorkspacePlugin(BasePlugin):
    def __init__(self, name: str = "session_workspace") -> None:
        super().__init__(name=name)
        self._tokens: dict[str, Token] = {}

    async def before_run_callback(
        self, *, invocation_context: "InvocationContext"
    ) -> Optional["types.Content"]:
        if get_session_id() is None:
            token = set_session_id(invocation_context.session.id)
            self._tokens[invocation_context.invocation_id] = token
        init_workspace()
        return None

    async def after_run_callback(
        self, *, invocation_context: "InvocationContext"
    ) -> None:
        token = self._tokens.pop(invocation_context.invocation_id, None)
        if token is not None:
            try:
                reset_session_id(token)
            except ValueError:
                # Token criado em outro Context (generator fechado em outra
                # task): o Context original morre com a task, nada a desfazer.
                pass


session_workspace_plugin = SessionWorkspacePlugin()
