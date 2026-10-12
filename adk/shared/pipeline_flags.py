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
