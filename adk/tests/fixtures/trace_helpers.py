"""Utilitários de trace para a Camada 2 (trajetória).

Um "trace" aqui é a sequência de eventos emitidos por um agente/pipeline
ADK durante uma execução (chamadas de tool, decisões, mensagens). Modelamos
cada trace em duas camadas, inspirado no padrão canonical/raw usado por
observabilidade (Langfuse, OpenTelemetry):

- **raw layer**: o evento tal como foi observado (objeto ADK `Event`, dict
  de resposta de LLM, etc.) — preservado para debug e replay.
- **canonical layer**: uma projeção normalizada e estável do evento
  (`agente`, `acao`, `status`, `timestamp`, `metadata`), independente da
  forma exata do SDK de origem. É sobre a camada canônica que as asserções
  de trajetória devem ser feitas, para não quebrar a cada upgrade do ADK.

Ver README da suite para o racional (MASEval / trajectory evaluation).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TraceEvent:
    """Um evento único e normalizado dentro de um trace.

    Attributes:
        agente: nome do agente/pipeline que emitiu o evento.
        acao: rótulo da ação (ex.: "function_call:tool_criar_arquivo",
            "texto_final", "pausa_hitl").
        status: estado da ação ("ok", "erro", "pendente").
        timestamp: ordem/instante lógico do evento dentro do trace
            (inteiro sequencial é suficiente para asserts de ordem).
        metadata: dados adicionais relevantes para a asserção (args da
            tool, texto emitido, checkpoint_id etc.).
        raw: payload original do evento, preservado sem normalização.
    """

    agente: str
    acao: str
    status: str = "ok"
    timestamp: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    raw: Any = None

    def to_canonical(self) -> dict[str, Any]:
        """Projeta o evento para a camada canônica (serializável em JSON)."""
        return {
            "agente": self.agente,
            "acao": self.acao,
            "status": self.status,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class TraceCollector:
    """Coleta eventos de uma execução e os organiza em raw + canonical layer.

    Uso típico dentro de um teste de trajetória::

        collector = TraceCollector()
        collector.record(agente="qa_pipeline", acao="function_call:tool_x", raw=event)
        ...
        collector.assert_order(["requirements", "design", "coding_review", "qa"])
        collector.dump(tmp_path / "trace.json")
    """

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    def record(
        self,
        *,
        agente: str,
        acao: str,
        status: str = "ok",
        metadata: dict[str, Any] | None = None,
        raw: Any = None,
    ) -> TraceEvent:
        """Registra um novo evento no trace, atribuindo o próximo timestamp lógico."""
        evento = TraceEvent(
            agente=agente,
            acao=acao,
            status=status,
            timestamp=len(self._events),
            metadata=metadata or {},
            raw=raw,
        )
        self._events.append(evento)
        return evento

    @property
    def events(self) -> list[TraceEvent]:
        """Lista imutável (cópia) dos eventos coletados até agora."""
        return list(self._events)

    def agentes_na_ordem(self) -> list[str]:
        """Sequência de agentes na ordem em que emitiram eventos (sem repetição consecutiva)."""
        ordem: list[str] = []
        for evento in self._events:
            if not ordem or ordem[-1] != evento.agente:
                ordem.append(evento.agente)
        return ordem

    def assert_order(self, esperado: list[str]) -> None:
        """Verifica se a sequência de agentes (sem repetição consecutiva) bate com `esperado`."""
        assert_trace_order(self.agentes_na_ordem(), esperado)

    def to_dict(self) -> dict[str, Any]:
        """Estrutura completa do trace: camada canônica + camada raw."""
        return {
            "canonical": [e.to_canonical() for e in self._events],
            "raw": [_safe_repr(e.raw) for e in self._events],
        }

    def dump(self, path: Path) -> Path:
        """Persiste o trace estruturado (canonical + raw) como JSON em `path`."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return path


def _safe_repr(raw: Any) -> Any:
    """Converte o payload raw para algo serializável, sem levantar exceção."""
    if raw is None or isinstance(raw, (str, int, float, bool, dict, list)):
        return raw
    return repr(raw)


def normalize_trace(eventos_brutos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normaliza uma lista de eventos brutos (dicts heterogêneos) para a camada canônica.

    Aceita dicts com chaves variadas (compatíveis com `Event` do ADK ou logs
    do Langfuse) e produz a mesma forma estável usada por `TraceEvent.to_canonical`.
    """
    canonicos: list[dict[str, Any]] = []
    for i, evento in enumerate(eventos_brutos):
        canonicos.append(
            {
                "agente": evento.get("agente") or evento.get("author") or "desconhecido",
                "acao": evento.get("acao") or evento.get("action") or "desconhecida",
                "status": evento.get("status", "ok"),
                "timestamp": evento.get("timestamp", i),
                "metadata": evento.get("metadata", {}),
            }
        )
    return canonicos


def assert_trace_order(observado: list[str], esperado: list[str]) -> None:
    """Verifica que `esperado` aparece como subsequência (na ordem) dentro de `observado`.

    Não exige igualdade estrita: permite que outros agentes apareçam entre os
    esperados (ex.: pipelines auxiliares), mas a ordem relativa deve ser respeitada.
    """
    idx = 0
    for agente in observado:
        if idx < len(esperado) and agente == esperado[idx]:
            idx += 1
    assert idx == len(esperado), (
        f"Ordem de trajetória inesperada.\n"
        f"Esperado (subsequência): {esperado}\n"
        f"Observado: {observado}"
    )
