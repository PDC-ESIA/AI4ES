"""Workflow de Requisitos (Time 1).

Orquestrador que delega ao requirements_agent — responsável por transformar
descrições em linguagem natural (PRDs, visões de projeto) em artefatos
estruturados (HUs, RFs, RNFs, UCs, RNs e Glossário).
"""

import os
from typing import TYPE_CHECKING, Any

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from shared.workspace import init_workspace
from src.agents.requirements.agent import agent as requirements_agent
from src.agents.requirements.manifest import emit_requirements_manifest

if TYPE_CHECKING:
    from google.adk.agents.callback_context import CallbackContext
else:
    CallbackContext = Any


def _reset_workspace(callback_context: CallbackContext) -> None:
    """before_agent_callback — limpa e recria o workspace antes de cada run.

    Garante ambiente isolado para cada nova invocação do pipeline,
    replicando o comportamento do orquestrador (_handle_fresh_run).
    """
    try:
        init_workspace()
    except Exception as exc:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).warning(
            "[WORKSPACE] Falha ao resetar workspace: %s", exc
        )

_DEFAULT_MODEL = "gemini-2.5-flash"

_INSTRUCTION = """
Você é o pipeline de Engenharia de Requisitos.

PAPEL:
Receber descrições em linguagem natural, PRDs ou documentos-matriz e
transformá-los em artefatos técnicos de requisitos estruturados, atômicos
e verificáveis, com glossário consolidado.

FLUXO OBRIGATÓRIO:

1. ELICITAÇÃO E ANÁLISE
   Encaminhe o documento de entrada ao requirements_agent.
   O agente fará: elicitação → análise crítica → classificação →
   especificação → glossário (sub-agente interno) → validação SMART.

2. ARTEFATOS ESPERADOS NO RETORNO (schema AnalystOutput)
   - user_stories (HUs)
   - functional_requirements (RFs)
   - non_functional_requirements (RNFs)
   - use_cases (UCs)
   - business_rules (RNs)
   - glossary (Glossário)
   - status: "concluido" ou "bloqueado"

3. BLOQUEIO POR AMBIGUIDADE
   Se o requirements_agent retornar status "bloqueado" e tiver gerado
   um Doubt_Artifact, encerre o pipeline e devolva ao solicitante:
   - o motivo do bloqueio
   - o caminho do Doubt_Artifact gerado
   - o que falta para destravar

REGRAS:
- Idioma: Português brasileiro.
- Nunca invente requisitos. Use somente o que está no documento-matriz.
- Persista os artefatos via tool_salvar_artefato_requisito (já integrado
  ao requirements_agent).

ENTREGA FINAL AO SOLICITANTE:
- Resumo executivo (campo `summary` do AnalystOutput).
- Lista de artefatos gerados (com IDs e caminhos persistidos).
- Lista de termos adicionados ao glossário.
- Doubt_Artifacts gerados (se houver), com caminho.
"""

agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="requirements_pipeline",
    description=(
        "Pipeline completo de Engenharia de Requisitos: transforma documentos "
        "de entrada em HUs, RFs, RNFs, UCs, RNs e Glossário estruturados."
    ),
    instruction=_INSTRUCTION,
    tools=[
        AgentTool(agent=requirements_agent),
    ],
)
agent.before_agent_callback = _reset_workspace
agent.after_agent_callback = emit_requirements_manifest
