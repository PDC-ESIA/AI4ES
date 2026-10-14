"""Saída estruturada do reviewer: ReviewOutput validado e decisão em código.

O reviewer escreve a análise em markdown e encerra com um bloco ```json no
formato de `ReviewOutput`. Depois do LLM, em Python puro:

1. o último bloco ```json da resposta é validado contra `ReviewOutput`, com
   severidade, camada e status normalizados;
2. o status é DECIDIDO EM CÓDIGO: BLOQUEADO se houver qualquer issue
   `critical`, APROVADO caso contrário — a regra que antes vivia só no prompt.
   O gate de cobertura continua tendo precedência: sem cobertura comprovada,
   o status é BLOQUEADO qualquer que seja a análise;
3. o resultado é gravado em `verificacao_revisao.json`, que o manifesto lê
   antes do markdown;
4. se o status decidido diferir da linha "## Status:" do markdown, a linha é
   sobrescrita, para que markdown e JSON nunca se contradigam.

Sem bloco JSON válido nada disso acontece: nenhum JSON é gravado e o manifesto
cai para a leitura do markdown, exatamente como antes desta mudança.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from google.genai import types
from pydantic import ValidationError

from shared.tools.coding_tools.review_tools import (
    _review_ws,
    _salvar_relatorio,
    cobertura_comprovada,
)

from .schemas import ReviewOutput

logger = logging.getLogger(__name__)

JSON_FILENAME = "verificacao_revisao.json"
REPORT_FILENAME = "verificacao_revisao.md"

_BLOCO_JSON_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_STATUS_RE = re.compile(r"^#{0,6}\s*Status:\s*.*$", re.MULTILINE)
_SEVERIDADES = {
    "critical": "critical",
    "critico": "critical",
    "crítico": "critical",
    "critica": "critical",
    "crítica": "critical",
    "warning": "warning",
    "aviso": "warning",
    "info": "info",
}


def extrair_review_output(texto: str) -> Optional[ReviewOutput]:
    """Último bloco ```json do texto como ReviewOutput normalizado; None se inválido."""
    blocos = _BLOCO_JSON_RE.findall(texto or "")
    if not blocos:
        return None
    try:
        bruto = json.loads(blocos[-1])
        if not isinstance(bruto, dict):
            return None
        saida = ReviewOutput(**bruto)
    except (json.JSONDecodeError, ValidationError, TypeError):
        return None
    for issue in saida.issues:
        issue.severity = _SEVERIDADES.get(issue.severity.strip().lower(), issue.severity.strip().lower())
        issue.layer = issue.layer.strip().lower()
    saida.status = saida.status.strip().upper()
    saida.report_path = REPORT_FILENAME
    return saida


def decidir_status(saida: ReviewOutput, cobertura_ok: bool) -> str:
    """Gate de cobertura > qualquer issue critical > APROVADO."""
    if not cobertura_ok:
        return "BLOQUEADO"
    if any(issue.severity == "critical" for issue in saida.issues):
        return "BLOQUEADO"
    return "APROVADO"


def status_do_markdown(texto: str) -> Optional[str]:
    """Status escrito na primeira linha "Status:" do markdown, se houver."""
    linha = _STATUS_RE.search(texto or "")
    if not linha:
        return None
    for status in ("BLOQUEADO", "APROVADO"):
        if status in linha.group(0).upper():
            return status
    return None


def _sobrescrever_status(texto: str, status: str) -> str:
    """Troca TODAS as linhas de status por uma única, no topo."""
    corpo = _STATUS_RE.sub("", texto).strip()
    return f"## Status: {status}\n\n{corpo}"


def registrar_saida_estruturada(callback_context: Any) -> Optional[types.Content]:
    """Valida o JSON da resposta, decide o status em código e grava o .json.

    Returns:
        O Content com o markdown corrigido quando o status do markdown diferia
        do decidido; None nos demais casos (inclusive sem JSON válido).
    """
    state = callback_context.state
    texto = str(state.get("review_analysis") or "")
    saida = extrair_review_output(texto)
    if saida is None:
        logger.warning("reviewer: resposta sem bloco JSON válido; manifesto usará o markdown")
        return None

    status_llm = saida.status
    saida.status = decidir_status(saida, cobertura_comprovada(state))

    registro = {
        **saida.model_dump(),
        "status_llm": status_llm,
        "status_ajustado": saida.status != status_llm,
    }
    destino = Path(_review_ws()) / JSON_FILENAME
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")

    if status_do_markdown(texto) == saida.status:
        return None
    logger.warning(
        "reviewer: status do markdown (%s) difere do decidido em código (%s); markdown corrigido",
        status_do_markdown(texto),
        saida.status,
    )
    corrigido = _sobrescrever_status(texto, saida.status)
    state["review_analysis"] = corrigido
    _salvar_relatorio(corrigido)
    return types.Content(role="model", parts=[types.Part(text=corrigido)])
