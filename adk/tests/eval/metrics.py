"""Métricas próprias do AI4ES, plugadas no `AgentEvaluator` do ADK por `custom_metrics`.

Cada função tem a assinatura que o `_CustomMetricEvaluator` do ADK invoca e devolve só o
score por invocação (1.0 conforme, 0.0 não conforme). O limiar não chega aqui: fica no
`test_config.json` e o `AgentEvaluator` o aplica sobre a média das invocações, então
limiar 1.0 exige conformidade em todas as execuções.

Por que estas métricas existem e o que o framework não deixa ver (session state, chamadas
de `LongRunningFunctionTool`): `docs/adr/0001-avaliacao-de-agentes-com-agentevaluator.md`.
"""

from __future__ import annotations

import logging
from typing import Optional, Sequence

from google.adk.evaluation.eval_case import (
    ConversationScenario,
    Invocation,
    get_all_tool_calls_with_responses,
)
from google.adk.evaluation.eval_metrics import EvalMetric, EvalStatus
from google.adk.evaluation.evaluator import EvaluationResult, PerInvocationResult
from google.genai import types as genai_types

_LOG = logging.getLogger(__name__)

# Nomes públicos — os mesmos que vão no `criteria` do test_config.json.
METRICA_SEQUENCIA_EM_ORDEM = "ai4es_tool_sequence_in_order"
METRICA_CONTRATO_DE_TOOLS = "ai4es_contrato_de_tools"
METRICA_RESPOSTA_CONTEM = "ai4es_resposta_contem"

# Caminhos de import usados no bloco `custom_metrics` do test_config.json.
CAMINHOS_DAS_FUNCOES = {
    METRICA_SEQUENCIA_EM_ORDEM: "tests.eval.metrics.tool_sequence_in_order",
    METRICA_CONTRATO_DE_TOOLS: "tests.eval.metrics.contrato_de_tools",
    METRICA_RESPOSTA_CONTEM: "tests.eval.metrics.resposta_contem",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _falhou(resposta: Optional[genai_types.FunctionResponse]) -> bool:
    """O retorno da tool sinaliza erro: `sucesso: False`, ou texto que começa com "Erro".

    O ADK embrulha retorno que não é dict em `{"result": ...}`. Chamada sem retorno
    registrado não conta como erro.
    """
    conteudo = getattr(resposta, "response", None)
    if not isinstance(conteudo, dict):
        return False
    if conteudo.get("sucesso") is False:
        return True
    texto = conteudo.get("result")
    return isinstance(texto, str) and texto.startswith("Erro")


def _chamadas(invocation: Optional[Invocation]) -> list[tuple[str, bool]]:
    """(nome, falhou) de cada chamada de tool de uma invocação, na ordem em que ocorreram.

    Lê também o `final_response`, onde o ADK deixa a chamada de um
    `LongRunningFunctionTool` (ver o ADR 0001); essa chamada não tem retorno.
    """
    if invocation is None:
        return []

    chamadas = [
        (chamada.name, _falhou(resposta))
        for chamada, resposta in get_all_tool_calls_with_responses(
            invocation.intermediate_data
        )
    ]
    for parte in getattr(invocation.final_response, "parts", None) or []:
        chamada = getattr(parte, "function_call", None)
        if chamada is not None and getattr(chamada, "name", None):
            chamadas.append((chamada.name, False))
    return chamadas


def nomes_das_tools(invocation: Optional[Invocation]) -> list[str]:
    """Nomes das chamadas de tool que não devolveram erro, na ordem em que ocorreram."""
    return [nome for nome, falhou in _chamadas(invocation) if not falhou]


def nomes_das_tools_declaradas(
    invocation: Optional[Invocation],
) -> dict[str, list[str]]:
    """Tools que cada agente declarou ao modelo, por nome, a partir de `app_details`.

    Do lado obtido vêm objetos `genai_types.Tool` (o nome está em cada
    `function_declarations[].name`); do lado esperado, o eval set declara só strings.
    """
    if invocation is None:
        return {}

    por_agente: dict[str, list[str]] = {}
    app_details = getattr(invocation, "app_details", None)
    for nome_agente, detalhe in (
        getattr(app_details, "agent_details", None) or {}
    ).items():
        nomes: list[str] = []
        for declaracao in getattr(detalhe, "tool_declarations", None) or []:
            if isinstance(declaracao, str):  # lado esperado, escrito no eval set
                nomes.append(declaracao)
                continue
            funcoes = getattr(declaracao, "function_declarations", None) or []
            for funcao in funcoes:
                if getattr(funcao, "name", None):
                    nomes.append(funcao.name)
            if not funcoes and getattr(declaracao, "name", None):
                nomes.append(declaracao.name)
        por_agente[nome_agente] = sorted(nomes)
    return por_agente


def _e_subsequencia(esperados: Sequence[str], obtidos: Sequence[str]) -> bool:
    """True se `esperados` aparece em `obtidos` na mesma ordem, tolerando extras.

    Sequência esperada vazia casa com qualquer coisa, como no `IN_ORDER` do ADK.
    """
    iterador = iter(obtidos)
    return all(any(obtido == esperado for obtido in iterador) for esperado in esperados)


def _texto_da_resposta(invocation: Optional[Invocation]) -> str:
    """Concatena as partes textuais da resposta final de uma invocação."""
    if invocation is None:
        return ""
    partes = getattr(invocation.final_response, "parts", None) or []
    return "\n".join(p.text for p in partes if getattr(p, "text", None))


def _por_invocacao(
    obtida: Invocation, esperada: Invocation, score: float
) -> PerInvocationResult:
    """Resultado de uma invocação: PASSED só com score 1.0."""
    return PerInvocationResult(
        actual_invocation=obtida,
        expected_invocation=esperada,
        score=score,
        eval_status=EvalStatus.PASSED if score == 1.0 else EvalStatus.FAILED,
    )


def _consolidar(resultados: list[PerInvocationResult]) -> EvaluationResult:
    """Média dos scores por invocação: PASSED só com média 1.0."""
    if not resultados:
        return EvaluationResult()

    media = sum(r.score for r in resultados) / len(resultados)
    return EvaluationResult(
        overall_score=media,
        overall_eval_status=EvalStatus.PASSED if media == 1.0 else EvalStatus.FAILED,
        per_invocation_results=resultados,
    )


# ---------------------------------------------------------------------------
# As métricas
# ---------------------------------------------------------------------------


def tool_sequence_in_order(
    eval_metric: EvalMetric,
    actual_invocations: list[Invocation],
    expected_invocations: Optional[list[Invocation]] = None,
    conversation_scenario: Optional[ConversationScenario] = None,
) -> EvaluationResult:
    """As tools esperadas ocorrem, nesta ordem e sem devolver erro, tolerando chamadas extras.

    Compara só nomes: a métrica nativa exige argumentos idênticos, e os argumentos dos
    agentes do pipeline são texto livre do LLM.
    """
    del eval_metric, conversation_scenario  # o limiar vem do test_config
    if expected_invocations is None:
        raise ValueError(
            "ai4es_tool_sequence_in_order precisa de invocações esperadas — declare "
            "`intermediate_data.tool_uses` no eval case."
        )

    resultados: list[PerInvocationResult] = []
    for obtida, esperada in zip(actual_invocations, expected_invocations):
        nomes_obtidos = nomes_das_tools(obtida)
        nomes_esperados = nomes_das_tools(esperada)

        conforme = _e_subsequencia(nomes_esperados, nomes_obtidos)
        if not conforme:
            # O AgentEvaluator só reporta "Expected 1.0, but got 0.0"; sem isto, toda
            # falha de sequência exigiria outra rodada para saber o que o agente fez.
            _LOG.warning(
                "[ai4es_tool_sequence_in_order] sequência divergente\n"
                "  esperado: %s\n"
                "  obtido  : %s",
                nomes_esperados,
                [
                    f"{nome} (erro)" if falhou else nome
                    for nome, falhou in _chamadas(obtida)
                ],
            )
        resultados.append(_por_invocacao(obtida, esperada, 1.0 if conforme else 0.0))

    return _consolidar(resultados)


def contrato_de_tools(
    eval_metric: EvalMetric,
    actual_invocations: list[Invocation],
    expected_invocations: Optional[list[Invocation]] = None,
    conversation_scenario: Optional[ConversationScenario] = None,
) -> EvaluationResult:
    """O agente ofereceu ao modelo exatamente as tools esperadas, nem mais nem menos.

    O esperado vai no eval set como lista de nomes em
    `app_details.agent_details.<agente>.tool_declarations`. Só os agentes declarados no
    esperado são conferidos.
    """
    del eval_metric, conversation_scenario
    if expected_invocations is None:
        raise ValueError("ai4es_contrato_de_tools precisa de invocações esperadas.")

    resultados: list[PerInvocationResult] = []
    for obtida, esperada in zip(actual_invocations, expected_invocations):
        declarado = nomes_das_tools_declaradas(obtida)
        exigido = nomes_das_tools_declaradas(esperada)

        conforme = bool(exigido) and all(
            declarado.get(agente) == nomes for agente, nomes in exigido.items()
        )
        resultados.append(_por_invocacao(obtida, esperada, 1.0 if conforme else 0.0))

    return _consolidar(resultados)


def resposta_contem(
    eval_metric: EvalMetric,
    actual_invocations: list[Invocation],
    expected_invocations: Optional[list[Invocation]] = None,
    conversation_scenario: Optional[ConversationScenario] = None,
) -> EvaluationResult:
    """Cada linha não vazia da resposta esperada aparece na resposta obtida.

    Para quando só parte da resposta é determinística: o ROUGE-1 do
    `response_match_score` pune uma referência curta contra uma resposta longa. O score
    é a fração de marcadores presentes; no eval set, um marcador por linha.
    """
    del eval_metric, conversation_scenario
    if expected_invocations is None:
        raise ValueError("ai4es_resposta_contem precisa de invocações esperadas.")

    resultados: list[PerInvocationResult] = []
    for obtida, esperada in zip(actual_invocations, expected_invocations):
        marcadores = [
            linha.strip()
            for linha in _texto_da_resposta(esperada).splitlines()
            if linha.strip()
        ]
        texto_obtido = _texto_da_resposta(obtida)

        if not marcadores:
            raise ValueError(
                "ai4es_resposta_contem: o final_response esperado está vazio — "
                "declare um marcador por linha."
            )
        presentes = sum(1 for m in marcadores if m in texto_obtido)
        resultados.append(_por_invocacao(obtida, esperada, presentes / len(marcadores)))

    return _consolidar(resultados)


# ---------------------------------------------------------------------------
# Registro no MetricEvaluatorRegistry do ADK
# ---------------------------------------------------------------------------


def registrar_metricas_ai4es() -> list[str]:
    """Registra as métricas próprias no registry default do ADK e devolve os nomes.

    O import do registry fica aqui dentro porque arrasta `pandas` e `rouge_score`: no
    topo, este módulo seria inimportável sem o grupo `eval`, e o conftest precisa dele
    para pular a suíte com a mensagem certa.
    """
    from google.adk.evaluation.custom_metric_evaluator import _CustomMetricEvaluator
    from google.adk.evaluation.eval_metrics import (
        Interval,
        MetricInfo,
        MetricValueInfo,
    )
    from google.adk.evaluation.metric_evaluator_registry import (
        DEFAULT_METRIC_EVALUATOR_REGISTRY,
    )

    descricoes = {
        METRICA_SEQUENCIA_EM_ORDEM: (
            "Tools esperadas ocorrem na ordem esperada e sem erro no retorno, "
            "ignorando argumentos e tolerando chamadas extras. 1.0 quando conforme, "
            "0.0 caso contrário."
        ),
        METRICA_CONTRATO_DE_TOOLS: (
            "As tools declaradas ao modelo são exatamente as esperadas, por agente. "
            "Olha o que foi oferecido, não o que foi chamado. 1.0 quando conforme."
        ),
        METRICA_RESPOSTA_CONTEM: (
            "Cada linha não-vazia da resposta esperada aparece na resposta obtida. "
            "Score é a fração de marcadores presentes."
        ),
    }

    for nome, descricao in descricoes.items():
        DEFAULT_METRIC_EVALUATOR_REGISTRY.register_evaluator(
            metric_info=MetricInfo(
                metric_name=nome,
                description=descricao,
                metric_value_info=MetricValueInfo(
                    interval=Interval(min_value=0.0, max_value=1.0)
                ),
            ),
            evaluator=_CustomMetricEvaluator,
        )

    return list(descricoes)
