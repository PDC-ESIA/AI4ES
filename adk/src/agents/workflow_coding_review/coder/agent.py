"""Coder do workflow coding_review.

- Prompt sem seções de Git/HITL.
- Tools de filesystem bound a workspace_output/coder/src/ (consolidado).
- Instância dedicada para evitar conflito de parent no pipeline.
- Memória incremental: o prompt é montado em runtime por um InstructionProvider
  que prefixa as lições destiladas de runs anteriores (issue #303).
"""

import logging
import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

from shared.agent_factory import _bind_tool_to_workspace
from shared.memory import (
    MemoryStore,
    error_codes_do_report,
    carregar_report,
    memoria_habilitada,
    recuperar,
    render_bloco,
)
from shared.workspace import get_agent_workspace, get_workspace_root
from shared.tools.coding_tools.filesystem_coding import (
    tool_criar_arquivo,
    tool_ler_arquivo,
    tool_substituir_trecho,
)
from shared.tools.filesystem import (
    tool_ler_workspace,
    tool_listar_workspace,
)

from . import prompt as coder_prompt

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

_WORKSPACE_ROOT = str(get_workspace_root())
_CODER_WS = str(get_agent_workspace("cr_coder"))


def _bind(tool):
    return _bind_tool_to_workspace(tool, _CODER_WS, _WORKSPACE_ROOT)


_INSTRUCTION = coder_prompt.build_instruction(_CODER_WS)


def _consulta_de_recuperacao(state) -> tuple[str, list[str], str]:
    """Monta a consulta de recuperação a partir do que a run já sabe.

    Devolve `(consulta, error_codes, tech_stack)`. A consulta é o texto usado
    no ranking por cosseno; os `error_codes` e a `tech_stack` são o pré-filtro
    determinístico (ver `shared/memory/retrieve.py`).

    Na **1ª iteração** ainda não há `report_path`, então não há `error_code` e a
    seleção é puramente semântica sobre o objetivo da task. A partir da **2ª**
    (modo correção) o executor já gravou o relatório, e aí a memória passa a ser
    filtrada pelo erro concreto que acabou de acontecer — que é quando ela vale
    mais.
    """
    tasks = state.get("tasks") if hasattr(state, "get") else None
    consulta = str(tasks or "")[:2000]

    report = carregar_report(state.get("report_path") if hasattr(state, "get") else None)
    codigos = error_codes_do_report(report)

    # O escopo vem do mesmo par de fontes que o `memory_writer` usa para
    # gravá-lo — disco primeiro, estado da sessão como reserva. Manter as duas
    # pontas simétricas é o que garante que o item gravado com escopo X seja
    # recuperável numa run que resolve o escopo pela outra fonte.
    from src.agents.workflow_coding_review.memory_writer.agent import (
        _tech_stack_e_objetivo,
    )

    stack, resumo = _tech_stack_e_objetivo(state)
    if not consulta:
        consulta = resumo

    if codigos:
        consulta = f"{consulta}\nErros da iteração anterior: {', '.join(codigos)}"

    return consulta.strip(), codigos, stack


def _run_id(ctx) -> str:
    """Identificador da run, na MESMA chave que o `memory_writer` grava.

    O `memory_writer` usa o id da sessão em `MemoryProvenance.run_id`; usar o
    mesmo aqui é o que faz "item criado na run R" e "item injetado na run R"
    serem cruzáveis por join — que é o ponto do `used_in_runs`.

    O `invocation_id` é reserva para contexto sem sessão (testes).
    """
    sessao = getattr(ctx, "session", None)
    return str(getattr(sessao, "id", "") or getattr(ctx, "invocation_id", "") or "")


def _instruction_provider(ctx) -> str:
    """Prefixa a instrução do coder com a memória de runs anteriores.

    Mesmo padrão do `cr_review_analyzer` (`reviewer/agent.py`), que já injeta os
    achados de análise estática em runtime — a instrução base continua sendo a
    de `coder_prompt.build_instruction()`, sem edição.

    Chamado uma vez por TURNO do coder (várias vezes por run, uma por iteração
    do loop e por chamada de tool). A injeção se repete a cada turno, como deve;
    o REGISTRO de uso é idempotente por run — `registrar_uso` guarda o run_id e
    não o reinsere, então não é preciso deduplicar por invocação aqui.

    Nunca levanta: se a memória falhar, o coder recebe exatamente o prompt de
    `develop`.
    """
    if not memoria_habilitada():
        return _INSTRUCTION

    try:
        state = getattr(ctx, "state", None)
        consulta, codigos, stack = _consulta_de_recuperacao(state) if state else ("", [], "")

        itens = recuperar(consulta, error_codes=codigos, tech_stack=stack)
        if not itens:
            return _INSTRUCTION

        # Registro de uso — o dado que, cruzado com o desfecho da run, permite
        # mais adiante rankear por utilidade medida em vez de por similaridade.
        if MemoryStore().registrar_uso([i.id for i in itens], _run_id(ctx)):
            logger.info(
                "[MEMORY] %d item(ns) injetado(s) no prompt do coder: %s",
                len(itens),
                [i.title[:40] for i in itens],
            )
        return render_bloco(itens) + "\n\n" + _INSTRUCTION
    except Exception:
        logger.exception("[MEMORY] Injeção falhou; seguindo com o prompt base.")
        return _INSTRUCTION


agent = LlmAgent(
    model=_model,
    name="cr_coder_agent",
    description="Implementa código funcional a partir de requisitos, sem git.",
    instruction=_instruction_provider,
    output_key="implementation",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=16384,
    ),
    tools=[
        _bind(FunctionTool(tool_criar_arquivo)),
        _bind(FunctionTool(tool_ler_arquivo)),
        _bind(FunctionTool(tool_substituir_trecho)),
        _bind(FunctionTool(tool_ler_workspace)),
        _bind(FunctionTool(tool_listar_workspace)),
    ],
)
