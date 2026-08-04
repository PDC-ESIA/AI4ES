"""Context Engineer dedicado ao workflow coding_review.

Instância ajustada do context_engineer original (src/agents/context_engineer/):
- Lê artefatos de requisitos e design diretamente do workspace (via manifests).
- Verifica artefatos mínimos obrigatórios; injeta contexto das fases anteriores
  no prompt via before_agent_callback + InstructionProvider.
- Enriquece cada task com rastreabilidade explicita (requirement_id,
  design_refs) e critérios de aceitação.
- Persiste tasks em workspace_output/coder/tasks/ via after_agent_callback
  (resolve GAP-00: LlmAgent não pode usar output_schema + tools ao mesmo tempo).
- Evita conflito de parent com o sdlc_pipeline (instância dedicada).
"""

import json
import logging
import os
from typing import TYPE_CHECKING, Any

from google.adk.agents import LlmAgent

from shared.tools.coding_tools.context_engineer_tools import tool_salvar_task_cr
from shared.workspace import get_workspace_root
from src.agents.context_engineer import prompt as ce_prompt, schemas as ce_schemas

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
else:
    CallbackContext = Any

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)


# ---------------------------------------------------------------------------
# before_agent_callback: injeta manifests das fases anteriores
# ---------------------------------------------------------------------------

def _read_manifest(phase_dir: str) -> str:
    """Lê manifest.json de uma fase anterior do disco. Best-effort."""
    try:
        path = get_workspace_root() / phase_dir / "manifest.json"
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.debug("[cr_context_engineer] manifest %s inacessível: %s", phase_dir, exc)
    return ""


def _inject_previous_manifests(callback_context: CallbackContext) -> None:
    """Lê os manifests de requisitos e design do disco e injeta no state.

    Substitui tool_ler_requirements_adk e tool_ler_design_adk sem passar
    tools ao LlmAgent (resolve GAP-00). O InstructionProvider (_instruction_provider)
    inclui o conteúdo no prompt em runtime.
    Retorna None para não interromper a execução do agente.
    """
    req_manifest = _read_manifest("requirements")
    design_manifest = _read_manifest("design")

    callback_context.state["_req_manifest"] = (
        req_manifest or "(manifesto de requisitos não disponível)"
    )
    callback_context.state["_design_manifest"] = (
        design_manifest or "(manifesto de design não disponível)"
    )
    return None


# ---------------------------------------------------------------------------
# after_agent_callback: persiste tasks geradas pelo LLM no disco
# ---------------------------------------------------------------------------

def _persist_tasks(callback_context: CallbackContext) -> None:
    """Persiste as tasks produzidas pelo LLM em workspace_output/coder/tasks/.

    O LLM grava o resultado estruturado em state["tasks"] via output_key.
    Este callback lê esse valor e chama tool_salvar_task_cr para cada task,
    eliminando a necessidade de o LLM chamar uma tool (resolve GAP-00).
    Retorna None para não substituir a saída do agente.
    """
    tasks_raw = callback_context.state.get("tasks")
    if not tasks_raw:
        logger.warning("[cr_context_engineer] state['tasks'] vazio — nenhuma task persistida")
        return None

    if isinstance(tasks_raw, str):
        try:
            tasks_data = json.loads(tasks_raw)
        except json.JSONDecodeError as exc:
            logger.warning("[cr_context_engineer] falha ao parsear tasks JSON: %s", exc)
            return None
    else:
        tasks_data = tasks_raw

    tasks_list = tasks_data.get("tasks", []) if isinstance(tasks_data, dict) else []
    if not tasks_list:
        logger.warning("[cr_context_engineer] lista de tasks vazia no output")
        return None

    for task in tasks_list:
        task_id = task.get("id", "TASK-???")
        result = tool_salvar_task_cr(
            task_id=task_id,
            task_json=json.dumps(task, ensure_ascii=False),
        )
        if not result.get("sucesso"):
            logger.warning(
                "[cr_context_engineer] falha ao salvar task %s: %s",
                task_id, result.get("erro"),
            )

    return None


# ---------------------------------------------------------------------------
# InstructionProvider: instrução base + manifests das fases anteriores
# ---------------------------------------------------------------------------

_BASE_INSTRUCTION = ce_prompt.instruction.replace(
    "Você receberá os requisitos atômicos do agente anterior via state[\"requirements\"].\n"
    "Cada requisito contém: id, description e acceptance_criteria.\n\n"
    "Se a entrada estiver vazia ou ausente, retorne um erro claro e encerre.",
    "Você receberá os requisitos como parte da mensagem de entrada (contexto das\n"
    "fases anteriores do pipeline). Extraia os requisitos atômicos do texto recebido.\n"
    "Cada requisito contém: id, description e acceptance_criteria.\n\n"
    "Se a entrada estiver vazia ou não contiver requisitos identificáveis, retorne\n"
    "um erro claro e encerre.",
)


def _instruction_provider(ctx: Any) -> str:
    """InstructionProvider: injeta manifests das fases anteriores em runtime."""
    req_manifest = ctx.state.get("_req_manifest", "(manifesto de requisitos não disponível)")
    design_manifest = ctx.state.get("_design_manifest", "(manifesto de design não disponível)")

    manifests_section = (
        "\n\n# CONTEXTO DAS FASES ANTERIORES\n"
        "Use os manifests das fases de Requisitos e Design para enriquecer o contexto\n"
        "das tasks geradas (rastreabilidade, critérios de aceite, artefatos produzidos):\n\n"
        "## Manifesto de Requisitos\n"
        f"{req_manifest}\n\n"
        "## Manifesto de Design\n"
        f"{design_manifest}\n"
    )
    return _BASE_INSTRUCTION + manifests_section


# ---------------------------------------------------------------------------
# Agente
# ---------------------------------------------------------------------------

agent = LlmAgent(
    model=_model,
    name="cr_context_engineer",
    description=ce_prompt.description,
    instruction=_instruction_provider,
    output_key="tasks",
    output_schema=ce_schemas.TasksOutput,
    # Sem tools: output_schema e tools são mutuamente exclusivos (GAP-00).
    # Persistência via after_agent_callback; leitura de manifests via before_agent_callback.
)
agent.before_agent_callback = _inject_previous_manifests
agent.after_agent_callback = _persist_tasks
