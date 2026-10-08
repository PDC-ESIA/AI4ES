"""Coder do workflow coding_review.

- Prompt sem seções de Git/HITL.
- Tools de filesystem bound a workspace_output/coder/src/ (consolidado).
- Instância dedicada para evitar conflito de parent no pipeline.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

from shared.agent_factory import (
    _bind_tool_to_workspace,
    lazy_agent_workspace,
    lazy_workspace_root,
)
from shared.execution.trilhas import secao_prompt
from shared.pipeline_flags import aceite_independente, coder_contexto_enxuto, jornada
from shared.workspace import get_agent_workspace
from shared.tools.coding_tools.filesystem_coding import (
    tool_criar_arquivo,
    tool_ler_arquivo,
    tool_remover_arquivo,
    tool_substituir_trecho,
)
from shared.tools.filesystem import (
    tool_ler_workspace,
    tool_listar_workspace,
)

from . import prompt as coder_prompt
from .workspace_guard import (
    anunciar_arquivos_herdados,
    auditar_remocao,
    avisar_fora_do_escopo,
    bloquear_sobrescrita_herdada,
    proteger_testes_de_aceite,
)

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

# Workspace resolvido a cada chamada/invocação: a raiz depende da sessão.
def _bind(tool):
    return _bind_tool_to_workspace(
        tool, lazy_agent_workspace("cr_coder"), lazy_workspace_root()
    )


def render_instruction(*, enxuto: bool = False) -> str:
    """Instrução (template, sem injeção de state) para o workspace da sessão."""
    return coder_prompt.build_instruction(
        str(get_agent_workspace("cr_coder")), enxuto=enxuto
    )


async def _INSTRUCTION(readonly_context) -> str:
    """InstructionProvider: modo enxuto só com a flag E a task no state.

    Sem `current_task` (benchmarks e TACO chamam o coder direto, fora do
    TaskIterator) a instrução é a histórica, mesmo com a flag ligada.
    """
    from google.adk.utils.instructions_utils import inject_session_state

    state = readonly_context.state
    enxuto = coder_contexto_enxuto() and bool(state.get("current_task"))
    # A trilha só existe no state quando o TaskIterator a escolheu
    # (`AI4ES_TRILHAS`); fora dele a seção é vazia.
    # Produto web: SEMPRE que o macro_context disser web_app (independe de flag).
    macro = (state.get("tasks") or {}).get("macro_context") if isinstance(state.get("tasks"), dict) else None
    produto = (macro or {}).get("product_type") if isinstance(macro, dict) else None
    instrucao = (
        secao_prompt(state.get("trilha"))
        + coder_prompt.secao_produto_web(produto)
        + render_instruction(enxuto=enxuto)
    )
    return await inject_session_state(instrucao, readonly_context)


agent = LlmAgent(
    model=_model,
    name="cr_coder_agent",
    description="Implementa código funcional a partir de requisitos, sem git.",
    instruction=_INSTRUCTION,
    output_key="implementation",
    # Contexto enxuto: só o turno corrente (aberto pelo TaskIterator ou pelo
    # executor); a task vem do state. Com uma única mensagem de usuário
    # (benchmarks, TACO) o conteúdo visto é o mesmo do 'default'.
    include_contents="none" if coder_contexto_enxuto() else "default",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=16384,
    ),
    tools=[
        _bind(FunctionTool(tool_criar_arquivo)),
        _bind(FunctionTool(tool_ler_arquivo)),
        _bind(FunctionTool(tool_substituir_trecho)),
        _bind(FunctionTool(tool_remover_arquivo)),
        _bind(FunctionTool(tool_ler_workspace)),
        _bind(FunctionTool(tool_listar_workspace)),
    ],
    # As frentes da proteção inter-task (ver `workspace_guard`): `anunciar_`
    # avisa que o projeto já existe antes da primeira escrita da task;
    # `bloquear_` recusa a sobrescrita se o aviso não bastar; `auditar_`
    # registra remoções e libera o caminho removido da baseline.
    # Com AI4ES_ACEITE_INDEPENDENTE (lida no import), os testes de aceite em
    # tests/acceptance/ ficam protegidos de escrita pelo coder.
    before_tool_callback=(
        [bloquear_sobrescrita_herdada, proteger_testes_de_aceite]
        if aceite_independente() or jornada()
        else bloquear_sobrescrita_herdada
    ),
    # `avisar_fora_do_escopo` só atua no modo contexto enxuto (current_task).
    after_tool_callback=[
        anunciar_arquivos_herdados,
        auditar_remocao,
        avisar_fora_do_escopo,
    ],
)
