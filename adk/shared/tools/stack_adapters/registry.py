"""Registro de adapters + resolução de stack em camadas (Tiers 1/2/3).

Não há lista central de markers que o resolver possua: cada adapter declara os
próprios `tech_stack_keywords` e `file_markers`, e o resolver apenas itera sobre
os adapters REGISTRADOS. Adicionar uma stack (Fatia D) passa a tocar zero
arquivos deste módulo — só se acrescenta um adapter a `_ADAPTERS`.

Camadas:
- Tier 1 — declarado (fonte de verdade): `tech_stack` do context_engineer.
- Tier 2 — manifesto: presença de arquivo no `coder_dir`, quando o Tier 1 não
  casa. Substitui o antigo "default silencioso para Python": uma task sem o
  campo cai aqui e resolve para Python porque ACHOU `requirements.txt`, não por
  suposição.
- Tier 3 — falha explícita: sem declaração nem manifesto reconhecido, nenhum
  adapter. Quem chama emite `STACK_NAO_IDENTIFICADA` — nunca um default para
  Python (rodar pytest contra stack desconhecida produz evidência-lixo).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .base import StackAdapter
from .node_adapter import NodeAdapter
from .python_adapter import PythonAdapter

# Adapters registrados. A ordem define a precedência de desempate (o primeiro que
# reivindicar vence): Python primeiro (manifestos requirements.txt/pyproject.toml),
# depois Node (package.json). Adicionar uma stack é só acrescentar um adapter aqui.
_ADAPTERS: tuple[StackAdapter, ...] = (PythonAdapter(), NodeAdapter())


def adapters_registrados() -> tuple[StackAdapter, ...]:
    """Os adapters atualmente registrados (para testes/introspecção)."""
    return _ADAPTERS


@dataclass(frozen=True)
class ResolucaoStack:
    """Resultado da resolução de stack.

    `adapter` é None apenas no Tier 3 (falha). `origem` registra QUAL camada
    resolveu ("tech_stack_declarado" | "manifesto" | None) e `detalhe` o que
    casou — ambos viram evidência no StageResult do Estágio 1.
    """

    adapter: Optional[StackAdapter]
    origem: Optional[str]
    detalhe: str


def resolver_stack(
    tech_stack: Optional[Iterable[str]], coder_dir: Path
) -> ResolucaoStack:
    """Resolve o adapter de stack em camadas (1 → 2 → 3).

    Não decide o que fazer com uma falha — devolve `adapter=None` e deixa o
    chamador (Estágio 1) emitir `STACK_NAO_IDENTIFICADA`.
    """
    stack = list(tech_stack or [])

    # Tier 1 — declarado (fonte de verdade).
    for adapter in _ADAPTERS:
        kw = adapter.keyword_casada(stack)
        if kw:
            return ResolucaoStack(
                adapter=adapter,
                origem="tech_stack_declarado",
                detalhe=f"keyword '{kw}' casou a tech_stack declarada",
            )

    # Tier 2 — manifesto no workspace.
    coder_dir = Path(coder_dir)
    for adapter in _ADAPTERS:
        marker = adapter.manifesto_encontrado(coder_dir)
        if marker:
            return ResolucaoStack(
                adapter=adapter,
                origem="manifesto",
                detalhe=f"manifesto '{marker}' encontrado no workspace do coder",
            )

    # Tier 3 — falha explícita.
    return ResolucaoStack(
        adapter=None,
        origem=None,
        detalhe="nenhum adapter reivindicou a stack (nem declaração nem manifesto)",
    )
