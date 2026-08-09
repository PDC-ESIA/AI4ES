"""Context Engineer dedicado ao workflow coding_review.

Instância ajustada do context_engineer original (src/agents/context_engineer/):
- Lê artefatos de requisitos e design diretamente do workspace.
- Verifica artefatos mínimos obrigatórios e gera Doubt Artifact se ausentes.
- Enriquece cada task com rastreabilidade explicita (requirement_id,
  design_refs) e critérios de aceitação.
- Persiste tasks em workspace_output/coder/tasks/ (consolidado sob coder/).
- Evita conflito de parent com o sdlc_pipeline (instância dedicada).

GAP-00 (schema + tools são mutuamente exclusivos no ADK): `output_schema` ativa
o modo gramática/constrained decoding, que DESABILITA o function calling. Como
este agente PRECISA de tools (ler requisitos/design, salvar task), ele roda SEM
`output_schema` — caso contrário o modelo devolve prosa em vez do JSON e a
validação do ADK (`__maybe_save_output_to_state`) falha com `json_invalid`.
O contrato estruturado (`TasksOutput`) é reconstruído deterministicamente pelo
`after_agent_callback` `_persistir_tasks_output`, que grava o resultado validado
em `state["tasks"]`.
"""

import json
import logging
import os
import re
from pathlib import Path

from google.adk.agents import LlmAgent

from shared.tools.coding_tools.context_engineer_tools import (
    tool_salvar_task_cr_adk,
    tool_ler_requirements_adk,
    tool_ler_design_adk,
    tool_gerar_doubt_artifact_adk,
)
from shared.workspace import get_agent_workspace
from src.agents.context_engineer import prompt as ce_prompt, schemas as ce_schemas

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

# Chave onde o ADK grava o texto BRUTO do LLM (via output_key). O callback lê
# daqui e escreve o TasksOutput validado em state["tasks"].
_RAW_STATE_KEY = "tasks_raw"

# Extrai o maior span `{...}` de um texto — tolera cercas markdown e prosa ao
# redor do JSON emitido pelo LLM.
_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)

# macro_context degradado usado apenas quando o LLM não emitiu um JSON
# parseável: mantém state["tasks"] estruturado sem inventar uma stack.
_MACRO_FALLBACK = {
    "summary": "a definir",
    "tech_stack": ["a definir"],
    "global_rules": ["Seguir padrões do projeto"],
}


def _extrair_json_obj(texto: str) -> dict | None:
    """Extrai o primeiro objeto JSON de `texto` (tolera markdown/prosa ao redor)."""
    if not texto:
        return None
    m = _JSON_OBJ_RE.search(texto)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _ler_tasks_do_disco() -> list[dict]:
    """Lê as tasks persistidas por tool_salvar_task_cr em coder/tasks/.

    Fonte autoritativa das tasks: os arquivos são gravados deterministicamente
    pela tool, independentemente do que o LLM ecoe no texto final.
    """
    try:
        pasta = get_agent_workspace("cr_context_engineer")
    except Exception:  # workspace não resolúvel — degrada para lista vazia
        return []
    if not pasta.exists():
        return []
    tasks: list[dict] = []
    for arq in sorted(pasta.glob("TASK-*.json")):
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("[CR CONTEXT ENGINEER] Task ilegível ignorada: %s", arq)
            continue
        if isinstance(dados, dict):
            tasks.append(dados)
    return tasks


def _persistir_tasks_output(callback_context):
    """Reconstrói o TasksOutput e grava em state["tasks"] (enforcement GAP-00).

    Determinístico, independente do que o LLM escreva:
    - tasks: fonte autoritativa é o disco (persistido por tool_salvar_task_cr);
      cai para as tasks do JSON do LLM apenas se o disco estiver vazio.
    - macro_context: só existe na resposta do LLM — extraído do JSON emitido;
      se ausente/ilegível, usa um macro_context degradado ('a definir').
    - Se a validação do TasksOutput falhar, grava a melhor estrutura possível
      (nunca deixa state["tasks"] com o texto cru inválido).
    """
    raw = callback_context.state.get(_RAW_STATE_KEY, "") or ""
    parsed = _extrair_json_obj(raw) or {}

    tasks_disco = _ler_tasks_do_disco()
    tasks_brutas = tasks_disco or parsed.get("tasks") or []
    macro_bruto = parsed.get("macro_context") or dict(_MACRO_FALLBACK)

    try:
        saida = ce_schemas.TasksOutput(
            macro_context=macro_bruto,
            tasks=tasks_brutas,
        )
        callback_context.state["tasks"] = saida.model_dump()
        logger.info(
            "[CR CONTEXT ENGINEER] TasksOutput consolidado: %d task(s) "
            "(fonte: %s).",
            len(saida.tasks),
            "disco" if tasks_disco else "resposta do LLM",
        )
    except Exception as e:  # validação falhou — grava melhor esforço
        logger.warning(
            "[CR CONTEXT ENGINEER] Falha ao validar TasksOutput (%s); "
            "gravando estrutura de melhor esforço em state['tasks'].",
            e,
        )
        callback_context.state["tasks"] = {
            "macro_context": macro_bruto,
            "tasks": tasks_brutas,
        }
    return None


agent = LlmAgent(
    model=_model,
    name="cr_context_engineer",
    description=ce_prompt.description,
    instruction=ce_prompt.instruction,
    # SEM output_schema — GAP-00: schema + tools são mutuamente exclusivos.
    # O texto bruto do LLM cai em state["tasks_raw"]; o callback reconstrói o
    # TasksOutput validado em state["tasks"].
    output_key=_RAW_STATE_KEY,
    tools=[
        tool_salvar_task_cr_adk,
        tool_ler_requirements_adk,
        tool_ler_design_adk,
        tool_gerar_doubt_artifact_adk,
    ],
)
agent.after_agent_callback = _persistir_tasks_output
