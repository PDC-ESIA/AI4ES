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

import hashlib
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
from shared.tools.coding_tools.harness_schemas import CriterionOutcome
from shared.tools.coding_tools.harness_execucao import executar_harness_tool
from shared.workspace import get_agent_workspace
from src.agents.implementation_validator import root_agent as implementation_validator
from src.agents.implementation_validator.agent import _report_path_valido

from . import prompt as executor_prompt
from .acceptance_score import CHAVE_ACEITE
from .loop_policy import (
    CHAVE_HISTORICO,
    assinatura_erro,
    fingerprint_mudou,
    registrar_e_avaliar,
    registrar_rodada,
)
from .progress_score import (
    CHAVE_FONTE_EVIDENCIA,
    FONTE_QA_E2E,
    NotaProgresso,
    calcular_nota,
    evidencia_de_qa,
)
from .qa_criterios import (
    CHAVE_QA,
    CHAVE_QA_EVIDENCIAS,
    verificar_criterios_por_e2e,
)
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


def _criterios_reprovados_pelo_qa(state) -> list[dict]:
    """Critérios que o QA PROVOU não atendidos navegando a aplicação.

    Lê o registro que `_aplicar_qa_de_criterios` deixou no state, e não o report
    em disco: o report é do harness, e sobrescrevê-lo com evidência de outro
    produtor apagaria a fronteira que faz dele um sensor confiável.

    Só `nao_atendido` entra. `sem_teste_mapeado`, `teste_nao_executado` e
    `nao_automatizavel` significam "não comprovado", e ausência de evidência
    nunca é evidência de ausência — cobrá-los aqui recriaria a task que nunca
    aprova.
    """
    registro = state.get(CHAVE_QA_EVIDENCIAS)
    if not isinstance(registro, list):
        return []
    return [
        evidencia
        for evidencia in registro
        if isinstance(evidencia, dict)
        and evidencia.get("outcome") == CriterionOutcome.NAO_ATENDIDO.value
    ]


def _assinatura_da_rodada(exec_report: dict, reprovados_pelo_qa: list[dict]) -> str:
    """Assinatura de falha da rodada, incluindo o que o QA reprovou.

    A do harness sozinha não serve quando a execução foi tecnicamente verde e só
    o QA reprovou: ela seria IDÊNTICA em todas essas rodadas (nenhum estágio
    falho, mesma contagem de testes), e o gatilho de erro repetido encerraria a
    task já na segunda tentativa de fechar um critério — mesmo que o coder
    estivesse fechando um critério diferente a cada rodada.

    Somando os ids reprovados, a assinatura passa a distinguir "travado no mesmo
    critério" de "avançou para o próximo", que é exatamente a leitura que a
    política de continuidade precisa fazer.
    """
    base = assinatura_erro(exec_report)
    if not reprovados_pelo_qa:
        return base
    ids = sorted(
        str(c.get("criterion_id") or c.get("criterion", "")) for c in reprovados_pelo_qa
    )
    return hashlib.sha256("\n".join([base, *ids]).encode("utf-8")).hexdigest()


def _mensagem_de_criterios_reprovados(reprovados: list[dict]) -> str:
    """Devolve ao coder o que o QA constatou, com a evidência de cada critério.

    É a única via pela qual o achado do QA chega a quem pode agir sobre ele: o
    `ErrorReport` é montado a partir do report do harness, que não conhece a
    navegação. Sem esta mensagem, o loop bloquearia a aprovação sem nunca dizer
    ao coder o que precisa mudar.
    """
    itens = "\n".join(
        f"- {c.get('criterion_id') or '?'}: {c.get('criterion', '')}\n"
        f"  O que o QA observou: {c.get('observed', '(sem detalhe)')}"
        for c in reprovados
    )
    return (
        "EXECUÇÃO OK, MAS A ENTREGA NÃO ATENDE AOS CRITÉRIOS DE ACEITE.\n\n"
        "O build, a inicialização e a sua suíte passaram. Um agente de QA "
        "independente navegou a aplicação com um navegador real e comprovou que "
        f"{len(reprovados)} critério(s) NÃO são atendidos:\n\n"
        f"{itens}\n\n"
        "Estes não são testes seus: são a verificação do que o Work Item pediu, "
        "feita na interface. Corrija o COMPORTAMENTO da aplicação para que cada "
        "um passe a valer — não escreva testes novos para contorná-los, e não "
        "altere o que já funciona."
    )


async def _aplicar_qa_de_criterios(callback_context, exec_report: dict) -> dict:
    """Substitui a evidência de critérios do harness pela do QA, quando houver.

    Roda ANTES do cálculo da nota, e é o que faz o QA entrar no loop de verdade:
    o degrau `CRITERIOS_ATENDIDOS` lê `criteria_evidence`, então trocar a fonte
    dessa lista muda a nota da rodada — e, por ela, a decisão de continuidade.

    A substituição é TOTAL, não uma fusão: as duas fontes respondem à mesma
    pergunta por vias diferentes, e misturá-las produziria dois resultados para o
    mesmo critério sem uma regra defensável de desempate. Quando o QA rodou, a
    palavra dele vale — ele navegou a aplicação; o harness só olhou o resultado
    dos testes que o próprio coder escreveu e vinculou.

    Quando o QA não roda (portão fechado, app que não subiu, runtime ausente), a
    evidência do harness permanece intocada e o fluxo se comporta exatamente como
    antes desta PoC. Degradar para o comportamento anterior é deliberado: uma
    medida auxiliar indisponível não pode piorar a leitura da rodada.

    Returns:
        O `exec_report` a usar no cálculo — o mesmo objeto quando o QA não rodou.
    """
    state = callback_context.state
    task_id = state.get("task_id") or ""
    if not task_id:
        return exec_report

    # O QA promete não levantar, mas a promessa depende de infraestrutura que
    # não controlamos: `sandbox.exec` deixa passar `OSError`/`FileNotFoundError`,
    # e escrever o spec toca o disco. Sem esta rede, uma falha de infra do QA
    # derrubaria a rodada INTEIRA — inclusive `montar_error_report`, que roda
    # depois e é o que dá feedback ao coder. Uma medida auxiliar nunca pode
    # custar o turno de quem ela deveria ajudar.
    try:
        resultado = await verificar_criterios_por_e2e(task_id, exec_report)
    except Exception:  # noqa: BLE001 — QA quebrado degrada, não interrompe
        logger.exception(
            "[QA] Verificação por navegação falhou na task %s; a rodada segue "
            "com a evidência do harness.",
            task_id,
        )
        state[CHAVE_QA] = {"executado": False, "motivo": "erro na verificação"}
        return exec_report

    state[CHAVE_QA] = resultado.como_dict()

    # Só substitui quando o QA DECIDIU algo. Uma lista só de recusas e de
    # "não verificável" não é melhor que a do harness — e apagaria os
    # `atendido` que o harness tinha, sumindo com eles da cobertura publicada ao
    # reviewer sem nada melhor a pôr no lugar.
    decididos = [
        e
        for e in resultado.evidencias
        if e.outcome in (CriterionOutcome.ATENDIDO, CriterionOutcome.NAO_ATENDIDO)
    ]
    if not decididos:
        # `CallbackContext.state` é `google.adk.sessions.state.State`, que
        # implementa get/set/update, mas não `pop`/deleção. Além de funcionar
        # tanto no ADK quanto nos dicts dos testes, gravar a lista vazia no
        # delta remove deterministicamente qualquer evidência da rodada
        # anterior sem deixar valor obsoleto persistido na sessão/frontend.
        state[CHAVE_QA_EVIDENCIAS] = []
        logger.info(
            "[QA] Task %s sem verificação por navegação nesta rodada: %s",
            task_id,
            resultado.motivo or "nenhum critério pôde ser decidido",
        )
        return exec_report

    evidencias = [e.model_dump(mode="json") for e in resultado.evidencias]
    # Registrado no state porque `montar_error_report` relê o report do DISCO,
    # que é do harness e não conhece a navegação. É daqui que sai o que o coder
    # recebe sobre os critérios.
    state[CHAVE_QA_EVIDENCIAS] = evidencias

    return {
        **exec_report,
        CHAVE_FONTE_EVIDENCIA: FONTE_QA_E2E,
        "criteria_evidence": evidencias,
    }


async def aplicar_politica_de_progresso(callback_context) -> Optional[types.Content]:
    """PRIMEIRO `after_agent_callback` do executor — a política da issue #394.

    Calcula a nota da rodada e decide, POR CÓDIGO, se o loop continua. Substitui
    o "protocolo anti-estagnação" do prompt, que dependia de o LLM do executor
    perceber o travamento e declarar por conta própria.

    É `async` porque a verificação de critérios por navegação (PoC do QA no loop)
    invoca um agente — o ADK aguarda callbacks que devolvem awaitable, então a
    assinatura muda sem que nada no wiring precise mudar junto.

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
    exec_report = await _aplicar_qa_de_criterios(callback_context, exec_report)
    nota = calcular_nota(exec_report)

    # A cobertura vai para o state a CADA rodada, e não só no fechamento da
    # task: uma task que termina por platô ou bloqueio nunca tem "rodada de
    # fechamento", e é justamente nela que a medida importa para auditoria. O
    # valor é sobrescrito a cada rodada e quem consome lê o último — sempre o da
    # evidência mais recente.
    #
    # A NOTA de aceite não é mais composta por fora (ver `acceptance_score`): ela
    # entra na nota única como o degrau `CRITERIOS_ATENDIDOS`. O que se publica
    # aqui é o recorte auditável dessa dimensão.
    # A procedência acompanha o que é PUBLICADO, e não só o que pontua. Sem
    # isso, `nota_aceite` e `cobertura_criterios` chegariam ao reviewer e ao
    # manifesto como se fossem verificação independente quando são, na verdade, o
    # resultado dos testes que o próprio coder escreveu — a mesma autoavaliação
    # que a trava do degrau recusa. `nota` vai a `None` nesse caso: "ninguém
    # verificou" é diferente de "verifiquei e deu isto".
    veio_do_qa = evidencia_de_qa(exec_report)
    aceite_publicado = nota.aceite.como_dict()
    aceite_publicado["fonte"] = (
        FONTE_QA_E2E if veio_do_qa else "harness_testes_do_coder"
    )
    if not veio_do_qa:
        aceite_publicado["nota"] = None
        aceite_publicado["cobertura"] = 0.0
    state[CHAVE_ACEITE] = aceite_publicado

    # O veredito responde "a execução foi bem-sucedida?" e NADA além disso (ver
    # `montar_veredito`). Sem esta trava, uma entrega que constrói, sobe e passa
    # nos próprios testes seria aprovada mesmo com o QA tendo PROVADO, navegando,
    # que ela não faz o que os critérios pedem — e o agente de QA não teria
    # influência nenhuma sobre o que é entregue, justamente o problema que
    # trazê-lo para dentro do loop deveria resolver.
    #
    # Só falha PROVADA bloqueia. Critério que ninguém conseguiu verificar
    # continua sem bloquear nada: é a mesma assimetria que mantém o teto da nota
    # em 1.0 quando não há evidência (ver `progress_score`), e é o que impede
    # esta trava de recriar a task que nunca aprova.
    reprovados_pelo_qa = _criterios_reprovados_pelo_qa(state)

    if validation.get("status") == "aprovado" and not reprovados_pelo_qa:
        # A rodada aprovada TAMBÉM entra no histórico: sem isso, a nota final da
        # task seria a da penúltima rodada (reprovada) — e o critério de aceite
        # pede a nota final registrada.
        registrar_rodada(state, nota.total, nota.como_dict())

        # Encerramento determinístico. O prompt continua pedindo `exit_loop` ao
        # LLM no caminho de aprovação; as duas vias são independentes e
        # redundantes de propósito, como o teto do LoopAgent.
        callback_context.actions.escalate = True
        logger.info(
            "[PROGRESSO] Task %s aprovada com nota %.3f (histórico=%s); "
            "aceite=%s cobertura=%.0f%%.",
            state.get("task_id"),
            nota.total,
            state.get(CHAVE_HISTORICO),
            nota.aceite.nota,
            nota.aceite.cobertura * 100,
        )
        # `None` preserva o texto de confirmação que o executor já produz.
        return None

    # A partir daqui a rodada é tratada como NÃO concluída — inclusive quando o
    # veredito técnico foi 'aprovado' e só o QA reprovou. Ela passa pela política
    # de continuidade como qualquer outra, e isso é obrigatório: um caminho que
    # devolvesse Content sem chamar `registrar_e_avaliar` não registraria
    # assinatura, não avaliaria platô e deixaria a task rodar até o teto do
    # LoopAgent — gastando um build e uma suíte de navegação por rodada. Seria a
    # volta do loop sem freio que a issue #394 existe para eliminar.
    decisao = registrar_e_avaliar(
        state,
        nota_total=nota.total,
        nota_detalhe=nota.como_dict(),
        arquivos_mudaram=fingerprint_mudou(state),
        assinatura_erro_atual=_assinatura_da_rodada(exec_report, reprovados_pelo_qa),
    )
    if decisao.parar:
        callback_context.actions.escalate = True
        resumo = _resumo_da_parada(decisao.motivo, nota)
        state["execution_result"] = resumo
        return types.Content(role="model", parts=[types.Part(text=resumo)])

    if reprovados_pelo_qa:
        # Execução tecnicamente OK: o `ErrorReport` a jusante não teria o que
        # relatar (ele nasce de estágios em falha), então o achado do QA precisa
        # sair por aqui ou não chega a quem pode agir sobre ele.
        mensagem = _mensagem_de_criterios_reprovados(reprovados_pelo_qa)
        state["execution_result"] = mensagem
        logger.info(
            "[QA] Task %s tecnicamente aprovada, mas o QA reprovou %d "
            "critério(s) navegando: %s. A task volta ao coder.",
            state.get("task_id"),
            len(reprovados_pelo_qa),
            ", ".join(c.get("criterion_id") or "?" for c in reprovados_pelo_qa),
        )
        return types.Content(role="model", parts=[types.Part(text=mensagem)])

    return None


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
