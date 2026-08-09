"""Executor dedicado ao workflow coding_review — independente do pacote executor/.

Módulo autônomo (instrução e schemas próprios, em `prompt.py` e
`schemas.py` deste package): não deriva de `executor/prompt.py` nem importa
`executor/schemas.py`.
- Compõe harness + AgentTool(validador). Sem `exit_loop`: a terminação do loop
  saiu do executor e virou responsabilidade do `cr_convergence_checker`
  (early-stopping determinístico), que roda logo após este agente.
- O executor apenas roda o harness, obtém o veredito do validador e o registra.
  O status técnico de execução do harness, sozinho, nunca decide nada.

## Relatório de erro ao coder (determinístico)

Quando o veredito é 'reprovado', o `after_agent_callback` deste agente monta um
`ErrorReport` e o devolve como saída do turno — substituindo a prosa do LLM. O
relatório é montado a partir de duas fontes que JÁ existem, sem nenhuma síntese
do LLM:
- `state['validation']` — o ValidationVerdict real, escrito pelo callback do
  `implementation_validator` (política determinística: Camada 1 + agregação);
- o ExecutionReport em disco (`state['report_path']`, gravado pelo harness) —
  de onde saem os estágios em falha com sua EVIDÊNCIA BRUTA (logs, tracebacks).

O ErrorReport diz o QUE falhou e mostra o material bruto do POR QUÊ. Ele NÃO
prescreve correção: diagnosticar causa raiz, escolher arquivos e decidir a
mudança é trabalho do coder — não do executor.

Binding ao workspace do workflow: o harness já resolve, em tempo de CHAMADA, os
seus base_dirs default — coder/src (get_agent_workspace("cr_coder"), entrada do
coder), coder/execution ("cr_executor", saída da execução) e coder/tasks
("cr_context_engineer", a Task). Esses são exatamente os diretórios deste
workflow; por isso compomos o harness direto, como o consolidado, sem reinjetar
paths. NÃO resolvemos esses caminhos no import de propósito: get_agent_workspace
CRIA o diretório sem o marker `.ai4se_workspace`, e isso faria `init_workspace()`
recusar limpar o workspace. Resolvê-los em tempo de chamada (após init_workspace)
evita esse efeito colateral.

Vive no LoopAgent [coder → executor → convergence_checker]; o validador é
AgentTool interna do executor. O cr_reviewer permanece fora do loop.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from shared.tools.coding_tools.harness_execucao import executar_harness_tool
from src.agents.implementation_validator import root_agent as implementation_validator
from src.agents.implementation_validator.agent import _report_path_valido

from . import prompt as executor_prompt
from .schemas import ErrorReport, FailedCriterion, FailedStage

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

# Estágios apenas PULADOS são consequência em cascata do que falhou antes
# ("Abortado: ..."), não trazem evidência útil — só falha/erro entram no report.
_STATUS_COM_EVIDENCIA = ("falha", "erro")


def _como_content(report: ErrorReport) -> types.Content:
    """Serializa o ErrorReport como saída final do turno do executor.

    Retornar um Content do `after_agent_callback` substitui a resposta do agente
    — é assim que o coder passa a receber o relatório determinístico no lugar da
    prosa que o LLM escreveu.
    """
    return types.Content(
        role="model",
        parts=[types.Part(text=json.dumps(report.model_dump(), ensure_ascii=False))],
    )


def _carregar_execution_report(callback_context) -> dict:
    """Lê o ExecutionReport do disco a partir do `report_path` do state.

    O caminho é validado com o mesmo helper estrito do validador (Spec C):
    precisa ser `<task_id>.report.json` dentro do workspace do cr_executor.
    Em qualquer falha devolve {} — o ErrorReport ainda sai, só sem a seção de
    estágios (o veredito, que é o essencial, nunca depende do disco).
    """
    caminho = callback_context.state.get("report_path")
    task_id = callback_context.state.get("task_id")
    if not caminho:
        return {}
    if not _report_path_valido(caminho, task_id or ""):
        logger.warning(
            "cr_executor: report_path recusado pela validação de workspace (%s); "
            "ErrorReport seguirá sem a evidência de estágios.",
            caminho,
        )
        return {}
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except Exception:
        logger.warning("cr_executor: falha ao ler o ExecutionReport em %s", caminho)
        return {}


def montar_error_report(callback_context) -> Optional[types.Content]:
    """`after_agent_callback` do `cr_executor_agent`.

    Monta o ErrorReport determinístico e o devolve no lugar da saída do turno.

    Retorna `None` (preservando a saída original do executor) quando:
    - `state['validation']` está ausente — o mecanismo de propagação não
      disparou; degrada para a prosa do LLM em vez de emitir relatório vazio;
    - o veredito real é 'aprovado' — não há erro a relatar.
    """
    validation = callback_context.state.get("validation")
    if not validation:
        logger.warning(
            "cr_executor: state['validation'] ausente; mantendo a saída do LLM "
            "(sem ErrorReport determinístico nesta iteração)."
        )
        return None

    if validation.get("status") != "reprovado":
        return None

    exec_report = _carregar_execution_report(callback_context)

    criterios = [
        FailedCriterion(
            criterion=cv.get("criterion", ""),
            status=cv.get("status", ""),
            reasoning=cv.get("reasoning", ""),
            evidence_ref=cv.get("evidence_ref"),
        )
        for cv in validation.get("criteria_verdicts", [])
        if cv.get("status") != "atendido"
    ]

    estagios = [
        FailedStage(
            stage=s.get("stage", ""),
            status=s.get("status", ""),
            error_code=s.get("error_code"),
            summary=s.get("summary", ""),
            evidence=s.get("evidence") or {},
        )
        for s in exec_report.get("stages", [])
        if s.get("status") in _STATUS_COM_EVIDENCIA
    ]

    try:
        report = ErrorReport(
            work_item_id=validation.get("work_item_id")
            or exec_report.get("work_item_id", "desconhecido"),
            iteration=exec_report.get("iteration"),
            verdict_status=validation.get("status", "reprovado"),
            blocking_reason=validation.get("blocking_reason"),
            failed_criteria=criterios,
            failed_stages=estagios,
            report_path=callback_context.state.get("report_path"),
        )
    except Exception:
        logger.exception("cr_executor: falha ao montar o ErrorReport")
        return None

    callback_context.state["error_report"] = report.model_dump()
    return _como_content(report)


# Instrução e schemas são PRÓPRIOS deste package (prompt.py / schemas.py): o
# executor não deriva mais do pacote executor/. Sem exit_loop — a terminação do
# loop é do convergence_checker.
agent = LlmAgent(
    model=_model,
    name="cr_executor_agent",
    description=executor_prompt.description,
    instruction=executor_prompt.instruction,
    output_key="execution_result",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=8192,
    ),
    tools=[
        FunctionTool(executar_harness_tool),
        AgentTool(agent=implementation_validator),
    ],
)
agent.after_agent_callback = montar_error_report
