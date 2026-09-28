"""Métricas de avaliação próprias do AI4ES, plugadas no `AgentEvaluator` do ADK.

Por que existem
---------------
A métrica nativa `tool_trajectory_avg_score` compara a trajetória exigindo igualdade de
**nome E argumentos** (`trajectory_evaluator.py::_are_tool_calls_exact_match` →
`actual.args == expected.args`, nos três `match_type`). Isso a torna aplicável só onde os
argumentos são determinísticos — um caminho de arquivo ecoado do prompt, um booleano
derivado de outra tool.

A maior parte dos contratos do Time 4 não é assim. O protocolo de bloqueio do
`cr_context_engineer` é uma sequência obrigatória de três tools
(`tool_gerar_doubt_artifact` → `tool_emitir_manifesto_bloqueado` →
`aguardar_resolucao_bloqueio`, esta última o `LongRunningFunctionTool` que pausa o
pipeline) cujos argumentos incluem descrição em texto livre escrita pelo LLM. O que
precisa ser garantido ali é **a sequência**, não o texto: um bloqueio parcial (doubt
escrito, manifesto não emitido) não pausa nada.

`ai4es_tool_sequence_in_order` mede exatamente isso: a sequência de **nomes** de tool,
ignorando argumentos.

Contrato com o ADK
------------------
Uma métrica custom é uma função com a assinatura que `_CustomMetricEvaluator` invoca
(`custom_metric_evaluator.py:60-71`)::

    f(eval_metric, actual_invocations, expected_invocations, conversation_scenario)
        -> EvaluationResult

Dois detalhes do runtime que mudam como a função deve ser escrita:

1. `_CustomMetricEvaluator` **zera o `threshold`** da cópia que entrega à função
   (`:60-61`). O limiar NÃO chega aqui — quem o aplica é o `AgentEvaluator`, refazendo
   `score >= threshold` sobre a **média das invocações** (`agent_evaluator.py:667-676`)
   com o valor do `test_config.json`. Portanto: a função devolve **score**; o gate mora
   no config.
2. Com `num_runs=N` a média é sobre N execuções. Limiar `1.0` significa "conformou em
   todas as execuções" — é assim que o gate **enxerga** o não-determinismo em vez de
   escondê-lo.

Limite conhecido (verificado na 1.33.0)
---------------------------------------
`Invocation` **não carrega o session state**, e os `InvocationEvent` guardam apenas
`author` + `content` — o `actions.state_delta` é descartado na conversão
(`evaluation_generator.py:315-317`). Nenhuma métrica, custom ou nativa, consegue avaliar
os handoffs por state do Time 4 (`state["tasks"]`, `state["validation"]`,
`state["task_iteration_summary"]`). É teto da ferramenta, não desta implementação.
"""

from __future__ import annotations

import logging
from typing import Optional, Sequence

from google.adk.evaluation.eval_case import (
    ConversationScenario,
    Invocation,
    get_all_tool_calls,
)
from google.adk.evaluation.eval_metrics import EvalMetric, EvalStatus
from google.adk.evaluation.evaluator import EvaluationResult, PerInvocationResult

# Nomes públicos — os mesmos que vão no `criteria` do test_config.json.
_LOG = logging.getLogger(__name__)

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


def nomes_das_tools(invocation: Optional[Invocation]) -> list[str]:
    """Sequência de nomes de tool de uma invocação, na ordem em que ocorreram.

    Lê também o `final_response`, onde o ADK deixa a chamada de um
    `LongRunningFunctionTool` (ver `docs/adr/0001-avaliacao-de-agentes-com-agentevaluator.md`).
    """
    if invocation is None:
        return []

    nomes = [
        chamada.name for chamada in get_all_tool_calls(invocation.intermediate_data)
    ]
    for parte in getattr(invocation.final_response, "parts", None) or []:
        chamada = getattr(parte, "function_call", None)
        if chamada is not None and getattr(chamada, "name", None):
            nomes.append(chamada.name)
    return nomes


def nomes_das_tools_declaradas(
    invocation: Optional[Invocation],
) -> dict[str, list[str]]:
    """Tools que cada agente **declarou ao modelo**, por nome, a partir do `LlmRequest`.

    Vem de `Invocation.app_details`, preenchido pelo `_RequestIntercepterPlugin` do ADK.
    Verificado em 07/09 que funciona com `LiteLlm`/`github_copilot`, não só com Gemini.

    `AgentDetails.tool_declarations` é `list[Any]` e em runtime carrega objetos
    `genai_types.Tool` — o nome não está no `Tool`, e sim em cada
    `Tool.function_declarations[].name`. Do lado **esperado** aceitamos strings
    simples, para que o eval set possa declarar só a lista de nomes.
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

    É o `IN_ORDER` do ADK, só que sobre nomes. Sequência esperada vazia casa com
    qualquer coisa — mesma convenção de `_are_tool_calls_in_order_match`.
    """
    iterador = iter(obtidos)
    return all(any(obtido == esperado for obtido in iterador) for esperado in esperados)


def _avaliar(
    actual_invocations: list[Invocation],
    expected_invocations: Optional[list[Invocation]],
) -> EvaluationResult:
    """Motor comum: 1.0 por invocação conforme, 0.0 caso contrário."""
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
            # O AgentEvaluator só reporta "Expected 1.0, but got 0.0", e a saída
            # detalhada dele exige pandas+tabulate. Sem isto, toda falha de sequência
            # obriga uma segunda rodada só para descobrir o que o agente fez.
            _LOG.warning(
                "[ai4es_tool_sequence_in_order] sequência divergente\n"
                "  esperado: %s\n"
                "  obtido  : %s",
                nomes_esperados,
                nomes_obtidos,
            )
        resultados.append(
            PerInvocationResult(
                actual_invocation=obtida,
                expected_invocation=esperada,
                score=1.0 if conforme else 0.0,
                eval_status=EvalStatus.PASSED if conforme else EvalStatus.FAILED,
            )
        )

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
    """As tools esperadas ocorrem, nesta ordem, tolerando chamadas extras.

    Use quando o contrato é "estes passos obrigatórios acontecem, nesta ordem", e o
    agente pode legitimamente chamar outras tools no meio — o caso do protocolo de
    bloqueio do `cr_context_engineer`.
    """
    del eval_metric, conversation_scenario  # o limiar vem do test_config
    return _avaliar(actual_invocations, expected_invocations)


def contrato_de_tools(
    eval_metric: EvalMetric,
    actual_invocations: list[Invocation],
    expected_invocations: Optional[list[Invocation]] = None,
    conversation_scenario: Optional[ConversationScenario] = None,
) -> EvaluationResult:
    """O agente declarou ao modelo exatamente as tools esperadas — nem a mais, nem a menos.

    Não olha o que foi *chamado* (isso é `ai4es_tool_sequence_in_order`), e sim o que foi
    **oferecido** ao modelo. Pega uma classe de defeito que nenhum teste atual alcança:
    uma tool removida, renomeada ou acrescentada em `agent.py` muda o espaço de ações do
    agente em silêncio, e a suíte unitária continua verde porque a tool em si funciona.

    O esperado é declarado no eval set como uma lista de **nomes**, dentro de
    `app_details.agent_details.<agente>.tool_declarations` da invocação esperada::

        "app_details": {"agent_details": {"implementation_validator": {
            "name": "implementation_validator",
            "tool_declarations": ["tool_ler_arquivo", "tool_ask_clarification"]}}}

    Só são conferidos os agentes declarados no esperado — um eval set não precisa
    enumerar a árvore inteira.
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
        resultados.append(
            PerInvocationResult(
                actual_invocation=obtida,
                expected_invocation=esperada,
                score=1.0 if conforme else 0.0,
                eval_status=EvalStatus.PASSED if conforme else EvalStatus.FAILED,
            )
        )

    if not resultados:
        return EvaluationResult()

    media = sum(r.score for r in resultados) / len(resultados)
    return EvaluationResult(
        overall_score=media,
        overall_eval_status=EvalStatus.PASSED if media == 1.0 else EvalStatus.FAILED,
        per_invocation_results=resultados,
    )


def _texto_da_resposta(invocation: Optional[Invocation]) -> str:
    """Concatena as partes textuais da resposta final de uma invocação."""
    if invocation is None:
        return ""
    partes = getattr(invocation.final_response, "parts", None) or []
    return "\n".join(p.text for p in partes if getattr(p, "text", None))


def resposta_contem(
    eval_metric: EvalMetric,
    actual_invocations: list[Invocation],
    expected_invocations: Optional[list[Invocation]] = None,
    conversation_scenario: Optional[ConversationScenario] = None,
) -> EvaluationResult:
    """Cada linha não-vazia da resposta esperada tem de aparecer na resposta obtida.

    Alternativa ao `response_match_score` para quando **parte** da resposta é
    determinística e o resto é prosa do LLM. O ROUGE-1 do ADK pontua por *f-measure*
    (`final_response_match_v1.py:59`), então uma referência curta contra uma resposta
    longa é punida pela precisão — mesmo que o trecho determinístico esteja lá, intacto.

    O caso concreto é o gate de cobertura do reviewer: `aplicar_gate_de_cobertura`
    garante `## Status: BLOQUEADO` e o bloco `<!-- task-coverage-gate:start -->` em
    Python puro, mas preserva o corpo da análise escrito pelo LLM.

    Convenção do eval set: escreva no `final_response` esperado **uma linha por
    marcador exigido**. O score é a fração de marcadores presentes.
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
        score = presentes / len(marcadores)
        resultados.append(
            PerInvocationResult(
                actual_invocation=obtida,
                expected_invocation=esperada,
                score=score,
                eval_status=EvalStatus.PASSED if score == 1.0 else EvalStatus.FAILED,
            )
        )

    if not resultados:
        return EvaluationResult()

    media = sum(r.score for r in resultados) / len(resultados)
    return EvaluationResult(
        overall_score=media,
        overall_eval_status=EvalStatus.PASSED if media == 1.0 else EvalStatus.FAILED,
        per_invocation_results=resultados,
    )


# ---------------------------------------------------------------------------
# Registro no MetricEvaluatorRegistry do ADK
# ---------------------------------------------------------------------------


def registrar_metricas_ai4es() -> list[str]:
    """Registra as métricas próprias no registry default do ADK.

    O import do registry é feito aqui dentro, e não no topo do módulo, porque ele
    arrasta `pandas` e `rouge_score` (cadeia `metric_evaluator_registry` →
    `vertex_ai_eval_facade` / `final_response_match_v1`). Deixar no topo faria este
    módulo ser inimportável sem os extras, e o `conftest` precisa importá-lo para dar
    a mensagem de erro amigável.

    Returns:
        Os nomes registrados, na ordem.
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
            "Tools esperadas ocorrem na ordem esperada, ignorando argumentos e "
            "tolerando chamadas extras. 1.0 quando conforme, 0.0 caso contrário."
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
