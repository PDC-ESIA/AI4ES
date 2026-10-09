"""Flags de comportamento do pipeline SDLC, lidas do ambiente (.env).

Todas desligadas por padrão: sem a variável, o orchestrator mantém o
comportamento histórico. Lidas a cada chamada (não no import) para que
testes e ajustes de .env com --reload tenham efeito imediato.

Contagem de tokens:
    AI4ES_TOKEN_USAGE_PERSIST       grava o acumulado no state ao fim de cada
                                    workflow e em <workspace>/token_usage.json
                                    a cada chamada LLM (sobrevive a queda).
    AI4ES_TOKEN_REPORT_ON_PAUSE     emite a tabela parcial quando a execução pausa.
    AI4ES_TOKEN_REPORT_DETAIL       acrescenta o consumo por agente à tabela.
    AI4ES_TOKEN_SESSION_TOTAL       acumula as execuções da sessão e mostra o
                                    total da sessão junto da execução atual.

Coder/reviewer:
    AI4ES_CODER_CONTEXTO_ENXUTO     o coder recebe só a task atual (no state) e
                                    implementa só ela; coder e executor deixam
                                    de reenviar o histórico acumulado do branch.
                                    Lida também no import dos agentes
                                    (``include_contents``): exige reiniciar.
    AI4ES_TRILHAS                   stack conhecida (ex.: python-web) roda com
                                    interpretador e versões fixados
                                    (shared/execution/trilhas.py).
    AI4ES_VERIFICACAO_RAPIDA        antes do harness, checa sintaxe/import/
                                    coleta (com trilha) ou faz revisão por LLM
                                    (sem trilha); falha volta direto ao coder.
    AI4ES_ACEITE_INDEPENDENTE       um agente separado escreve os testes de
                                    aceite de cada task (o coder não os edita),
                                    e eles decidem os critérios no harness e no
                                    veredito. Lida também no import do loop.
    AI4ES_ACEITE_COBERTURA_MIN      cobertura mínima de critérios para aceitar
                                    task com ressalvas (padrão 0.6).
    AI4ES_MAX_LLM_CALLS             teto de chamadas de LLM por pipeline
                                    (RunConfig.max_llm_calls do ADK). Padrão:
                                    500 (o do ADK); 2000 com as flags do
                                    coder/reviewer, que fazem mais chamadas.
    AI4ES_JORNADA                   depois da última task, um agente escreve o
                                    teste de jornada do produto (a partir das
                                    HUs); falha vira task de integração.
                                    Lida também no import do pipeline.
"""

from __future__ import annotations

import os

_TRUE = {"1", "true", "yes", "on", "sim"}


def flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUE


def token_usage_persist() -> bool:
    return flag("AI4ES_TOKEN_USAGE_PERSIST")


def token_report_on_pause() -> bool:
    return flag("AI4ES_TOKEN_REPORT_ON_PAUSE")


def token_report_detail() -> bool:
    return flag("AI4ES_TOKEN_REPORT_DETAIL")


def token_session_total() -> bool:
    return flag("AI4ES_TOKEN_SESSION_TOTAL")


def coder_contexto_enxuto() -> bool:
    return flag("AI4ES_CODER_CONTEXTO_ENXUTO")


def trilhas() -> bool:
    return flag("AI4ES_TRILHAS")


def verificacao_rapida() -> bool:
    return flag("AI4ES_VERIFICACAO_RAPIDA")


def aceite_independente() -> bool:
    return flag("AI4ES_ACEITE_INDEPENDENTE")


def aceite_cobertura_minima() -> float:
    try:
        return float(os.environ.get("AI4ES_ACEITE_COBERTURA_MIN", "") or 0.6)
    except ValueError:
        return 0.6


def jornada() -> bool:
    return flag("AI4ES_JORNADA")


def contrato_web() -> bool:
    return flag("AI4ES_CONTRATO_WEB")


def quadro_produto() -> bool:
    return flag("AI4ES_QUADRO_PRODUTO")


def max_llm_calls() -> int:
    """Teto de chamadas de LLM por execução de pipeline (ADK `RunConfig`).

    Na validação, o coder/reviewer com aceite independente, verificação rápida
    e rodadas de correção passou das 500 chamadas (padrão do ADK) no meio da
    5ª de 7 tasks e a execução abortou com LlmCallsLimitExceededError.
    """
    bruto = os.environ.get("AI4ES_MAX_LLM_CALLS", "").strip()
    if bruto:
        try:
            return int(bruto)
        except ValueError:
            pass
    novas = coder_contexto_enxuto() or aceite_independente() or jornada()
    return 2000 if novas else 500
