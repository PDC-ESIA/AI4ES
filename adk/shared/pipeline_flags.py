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
