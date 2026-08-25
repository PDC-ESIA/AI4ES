"""Executor dedicado ao workflow coding_review.

- Compõe harness + AgentTool(validador) + exit_loop.
- O loop encerra por APROVAÇÃO (veredito do validador) ou por FALTA DE PROGRESSO
  (política em `loop_policy.py`, issue #394). O status técnico de execução do
  harness, sozinho, nunca encerra. Ambos os encerramentos são sinalizados por
  código via `escalate`; o `exit_loop` do prompt é uma via redundante no caminho
  de aprovação.

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
workflow; por isso compomos o harness direto, sem reinjetar paths. NÃO resolvemos
esses caminhos no import de propósito: get_agent_workspace CRIA o diretório sem o
marker `.ai4se_workspace`, e isso faria `init_workspace()` recusar limpar o
workspace. Resolvê-los em tempo de chamada (após init_workspace) evita esse
efeito colateral.

Vive no LoopAgent [coder → executor]; o validador é AgentTool interna do
executor. O reviewer permanece fora do loop.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, exit_loop
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from shared.execution.verificador_executabilidade import verificar_executabilidade
from shared.tools.coding_tools.harness_execucao import executar_harness_tool
from shared.workspace import get_agent_workspace
from src.agents.implementation_validator import root_agent as implementation_validator
from src.agents.implementation_validator.agent import _report_path_valido

from . import prompt as executor_prompt
from .loop_policy import (
    assinatura_erro,
    fingerprint_mudou,
    registrar_e_avaliar,
    registrar_rodada,
)
from .progress_score import NotaProgresso, calcular_nota
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
    precisa ser `<task_id>.report.json` dentro do workspace do executor.
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


_CABECALHO_RECUSA = (
    "IMPLEMENTAÇÃO INCOMPLETA — o harness NÃO foi executado (não há o que "
    "validar ainda)."
)


def _mensagem_de_recusa(bloqueios, arquivos) -> str:
    """Relatório determinístico devolvido ao coder no lugar do ErrorReport.

    É um pedido para CONTINUAR implementando, não um encerramento: quem decide
    encerrar por falta de progresso é a política (`loop_policy.py`), a partir do
    histórico de notas — não deste texto.
    """
    inventario = "\n".join(f"- {a}" for a in arquivos) or "- (workspace vazio)"
    return (
        f"{_CABECALHO_RECUSA}\n\n"
        "Faltando:\n"
        + "\n".join(f"- {bloqueio}" for bloqueio in bloqueios)
        + "\n\nArquivos hoje no seu workspace:\n"
        + inventario
        + "\n\nComplete a implementação AGORA, no mesmo turno: crie os arquivos "
        "que faltam com `tool_criar_arquivo`, um por vez, e NÃO responda com "
        "texto até terminar. Texto sem chamada de ferramenta encerra o seu "
        "turno e gasta uma iteração do loop sem produzir nada."
    )


def recusar_execucao_incompleta(callback_context) -> Optional[types.Content]:
    """`before_agent_callback` do `cr_executor_agent` — gate estrutural.

    Recusa a rodada quando o artefato ainda não tem o mínimo para ser executado,
    ANTES de gastar as chamadas de LLM do executor e do validador e a execução
    do sandbox. Numa run real, ~13 das 37 execuções do harness aconteceram sobre
    um workspace com um arquivo novo ou nenhum.

    A checagem cobre apenas condições que o harness TAMBÉM reprovaria no estágio
    1 — sem `run.json`, manifesto incoerente, nenhum código. Como falso positivo
    é impossível nesse conjunto, a RECUSA em si não tem teto de tentativas: o
    gate nunca cede enquanto faltar o mínimo, e nunca trava uma implementação
    legítima.

    O que passou a ter limite (issue #394) é o LOOP, não o gate: recusas
    consecutivas entram na política de progresso como nota 0.0, e o platô acaba
    encerrando a task. São coisas diferentes — o gate continua recusando
    corretamente para sempre; o que se reconhece é que um coder incapaz de
    produzir o mínimo executável depois de várias rodadas está travado, e
    insistir só queima orçamento.

    ATENÇÃO — `state["execution_result"]` é escrito AQUI, na mão: quando um
    `before_agent_callback` devolve Content, o ADK marca `end_invocation=True` e
    retorna antes do `_run_async_impl`, que é onde o `output_key` seria gravado
    (`llm_agent.py::__maybe_save_output_to_state`). Sem esta escrita, o coder
    receberia de volta o ErrorReport da rodada ANTERIOR e não saberia o que
    falta.

    Returns:
        None para deixar o executor rodar; o Content da recusa caso contrário.
    """
    state = callback_context.state
    resultado = verificar_executabilidade(get_agent_workspace("cr_coder"))
    if resultado.executavel:
        return None

    logger.warning(
        "[EXECUTABILIDADE] Execução recusada para %s: %s",
        state.get("task_id"),
        "; ".join(resultado.bloqueios),
    )

    # A rodada recusada TAMBÉM entra na política de progresso (issue #394).
    # Quando este callback devolve Content, o ADK marca `end_invocation` e nenhum
    # `after_agent_callback` roda — então, se a avaliação não acontecesse aqui,
    # um coder que trava justamente neste ponto (nunca produz manifesto válido
    # ou código) não geraria rodada nenhuma no histórico, nenhum gatilho o
    # enxergaria, e ele só pararia no teto de segurança.
    #
    # Nota 0.0 sem detalhamento: o degrau `MINIMO_PARA_RODAR` não foi vencido e
    # nada a jusante chegou a ser tentado. Sem ExecutionReport não há assinatura
    # de erro, então o gatilho de erro repetido não se aplica a este caminho.
    decisao = registrar_e_avaliar(
        state,
        nota_total=0.0,
        nota_detalhe=None,
        arquivos_mudaram=fingerprint_mudou(state),
    )

    mensagem = _mensagem_de_recusa(resultado.bloqueios, resultado.arquivos)
    state["execution_result"] = mensagem

    if decisao.parar:
        # `escalate` setado aqui chega ao LoopAgent: o evento do
        # before_agent_callback é emitido com `actions=callback_context
        # ._event_actions` ANTES de `end_invocation` cortar o turno.
        callback_context.actions.escalate = True
        logger.warning(
            "[EXECUTABILIDADE] Loop encerrado por %s após recusas consecutivas "
            "na task %s.",
            decisao.motivo,
            state.get("task_id"),
        )

    return types.Content(role="model", parts=[types.Part(text=mensagem)])


def _resumo_da_parada(motivo: Optional[str], nota: NotaProgresso) -> str:
    """Texto do turno quando a política encerra o loop por travamento.

    Destinado ao reviewer a jusante, não ao coder: quando este texto é
    produzido, o loop já vai encerrar e não haverá nova rodada de correção.
    """
    detalhe = ", ".join(
        f"{degrau}={score:.2f}" for degrau, score in sorted(nota.como_dict().items())
    )
    return (
        f"LOOP ENCERRADO POR FALTA DE PROGRESSO ({motivo}).\n"
        f"Nota de progresso final: {nota.total:.3f}.\n"
        f"Degraus: {detalhe}.\n"
        "Este encerramento NÃO é aprovação — o veredito permanece 'reprovado'."
    )


def aplicar_politica_de_progresso(callback_context) -> Optional[types.Content]:
    """PRIMEIRO `after_agent_callback` do executor — a política da issue #394.

    Calcula a nota da rodada e decide, POR CÓDIGO, se o loop continua. Substitui
    o "protocolo anti-estagnação" do prompt, que dependia de o LLM do executor
    perceber o travamento e declarar por conta própria.

    A ordem na lista de callbacks é carga estrutural, não estilo: o ADK para no
    PRIMEIRO callback que devolve `Content` não-vazio, e `montar_error_report`
    devolve `Content` em toda rodada reprovada — o caso comum. Se este callback
    viesse depois, nunca rodaria justamente nas rodadas que importam.

    Returns:
        `Content` apenas quando a política decide PARAR por travamento —
        substituindo o turno, para que o coder não receba um relatório
        "conserte isto" numa rodada que não vai existir. Nos demais casos
        devolve `None`, deixando `montar_error_report` seguir normalmente.
    """
    state = callback_context.state
    validation = state.get("validation")
    if not validation:
        # Mesma degradação de `montar_error_report`: sem veredito não há como
        # medir a rodada, e inventar uma nota seria pior que não registrar.
        logger.warning(
            "cr_executor: state['validation'] ausente; rodada não entra no "
            "histórico de progresso."
        )
        return None

    exec_report = _carregar_execution_report(callback_context)
    nota = calcular_nota(exec_report)

    if validation.get("status") == "aprovado":
        # A rodada aprovada TAMBÉM entra no histórico: sem isso, a nota final da
        # task seria a da penúltima rodada (reprovada) — e o critério de aceite
        # pede a nota final registrada.
        registrar_rodada(state, nota.total, nota.como_dict())
        # Encerramento determinístico. O prompt continua pedindo `exit_loop` ao
        # LLM no caminho de aprovação; as duas vias são independentes e
        # redundantes de propósito, como o teto do LoopAgent.
        callback_context.actions.escalate = True
        logger.info(
            "[PROGRESSO] Task %s aprovada com nota %.3f (histórico=%s).",
            state.get("task_id"),
            nota.total,
            state.get("progress_score_history"),
        )
        # `None` preserva o texto de confirmação que o executor já produz.
        return None

    decisao = registrar_e_avaliar(
        state,
        nota_total=nota.total,
        nota_detalhe=nota.como_dict(),
        arquivos_mudaram=fingerprint_mudou(state),
        assinatura_erro_atual=assinatura_erro(exec_report, validation),
    )
    if not decisao.parar:
        return None

    callback_context.actions.escalate = True
    resumo = _resumo_da_parada(decisao.motivo, nota)
    state["execution_result"] = resumo
    return types.Content(role="model", parts=[types.Part(text=resumo)])


def montar_error_report(callback_context) -> Optional[types.Content]:
    """`after_agent_callback` do `cr_executor_agent`.

    Monta o ErrorReport determinístico e o devolve no lugar da saída do turno.

    Retorna `None` (preservando a saída original do executor) quando:
    - `state['validation']` está ausente — o mecanismo de propagação não
      disparou; degrada para a prosa do LLM em vez de emitir relatório vazio;
    - o veredito real é 'aprovado' — não há erro a relatar.

    Não precisa mais tratar o encerramento por travamento: quando a política
    decide parar, ela devolve `Content` e o ADK interrompe a cadeia de callbacks
    antes de chegar aqui (ver `aplicar_politica_de_progresso`).
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


# A instrução (fluxo + salvaguarda) vem do prompt local: os nomes de tool e o
# fluxo já valem para o workflow, sem ajustes de workspace/contexto.
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
        FunctionTool(exit_loop),
    ],
)
agent.before_agent_callback = recusar_execucao_incompleta
# A ORDEM é carga estrutural: o ADK executa os callbacks em sequência e PARA no
# primeiro que devolver `Content` não-vazio. `montar_error_report` devolve
# `Content` em toda rodada reprovada — o caso comum —, então a política precisa
# vir antes, ou nunca rodaria justamente nas rodadas que ela existe para julgar.
agent.after_agent_callback = [aplicar_politica_de_progresso, montar_error_report]
