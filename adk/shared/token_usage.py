"""Contabilização de tokens (entrada/saída) por workflow do orchestrator.

O orchestrator roda cada pipeline num ``Runner`` próprio, e vários sub-agentes
são chamados via ``AgentTool`` — cujos eventos não sobem até o orchestrator.
Por isso a contagem é feita por um plugin (``after_model_callback``), que o
ADK propaga para os Runners aninhados, e não pelos eventos do stream.

A atribuição ao workflow usa um ``ContextVar``: o orchestrator chama
``bind_stage`` antes de cada pipeline, e as tasks criadas pelo Runner herdam o
valor. O acumulado é serializável (``to_dict``/``from_dict``) para sobreviver à
pausa HITL entre invocações.

Chamadas LLM que não passam pelo ADK precisam registrar explicitamente:
``record_litellm_response`` após ``litellm.completion`` e
``instrument_genai_client`` no cliente Gemini do mem0. Threads criadas à mão
devem propagar o contexto (``contextvars.copy_context().run``).

Além do total por workflow, o acumulador guarda o consumo por agente
(entrada/saída/chamadas). A entrada servida do cache do provider (``cached``)
é um subconjunto da entrada, contada à parte porque custa uma fração do preço;
só aparece na serialização quando há cache, para não mudar o formato antigo. Opcionalmente (``persist_path``) grava um snapshot
JSON a cada chamada — ver ``shared.pipeline_flags``.
"""

from __future__ import annotations

import json
import os
import threading
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from google.adk.plugins.base_plugin import BasePlugin

# nome do pipeline no orchestrator -> rótulo exibido no relatório
STAGE_LABELS: dict[str, str] = {
    "requirements_pipeline": "requisitos",
    "design_pipeline": "design",
    "coding_review_pipeline": "coder_reviewer",
    "qa_pipeline": "qa",
}

_REPORT_ORDER = ("requisitos", "design", "coder_reviewer", "qa")

# Agentes de chamadas feitas fora do ADK (sem callback_context).
AGENT_LITELLM = "litellm_direto"
AGENT_MEM0 = "mem0"

_DETAIL_TOP_N = 10


def _empty() -> dict[str, int]:
    return {"input": 0, "output": 0}


def _add_cached(bucket: dict[str, int], cached_tokens: int) -> None:
    if cached_tokens:
        bucket["cached"] = bucket.get("cached", 0) + cached_tokens


def _with_cached(bucket: dict[str, int]) -> dict[str, int]:
    """Cópia serializável: ``cached`` só entra quando houve cache."""
    out = dict(bucket)
    if not out.get("cached"):
        out.pop("cached", None)
    return out


class TokenUsage:
    """Acumulador de tokens de entrada/saída por workflow e por agente."""

    def __init__(
        self,
        stages: Optional[dict[str, dict[str, int]]] = None,
        agents: Optional[dict[str, dict[str, dict[str, int]]]] = None,
    ):
        self.stages: dict[str, dict[str, int]] = {
            k: _with_cached(
                {
                    "input": int(v.get("input", 0)),
                    "output": int(v.get("output", 0)),
                    "cached": int(v.get("cached", 0)),
                }
            )
            for k, v in (stages or {}).items()
        }
        self.agents: dict[str, dict[str, dict[str, int]]] = {
            stage: {
                name: _with_cached(
                    {
                        "input": int(v.get("input", 0)),
                        "output": int(v.get("output", 0)),
                        "calls": int(v.get("calls", 0)),
                        "cached": int(v.get("cached", 0)),
                    }
                )
                for name, v in by_agent.items()
            }
            for stage, by_agent in (agents or {}).items()
        }
        # Snapshot JSON opcional, gravado a cada add() (ver orchestrator).
        self.persist_path: Optional[Path] = None
        self.persist_meta: dict[str, Any] = {}
        self._lock = threading.Lock()

    def add(
        self,
        stage: str,
        input_tokens: int,
        output_tokens: int,
        agent: Optional[str] = None,
        cached_tokens: int = 0,
    ) -> None:
        with self._lock:
            bucket = self.stages.setdefault(stage, _empty())
            bucket["input"] += input_tokens
            bucket["output"] += output_tokens
            _add_cached(bucket, cached_tokens)
            if agent:
                a = self.agents.setdefault(stage, {}).setdefault(
                    agent, {"input": 0, "output": 0, "calls": 0}
                )
                a["input"] += input_tokens
                a["output"] += output_tokens
                a["calls"] += 1
                _add_cached(a, cached_tokens)
        if self.persist_path is not None:
            self.write_snapshot()

    def merge(self, other: "TokenUsage") -> "TokenUsage":
        """Soma ``other`` neste acumulador (por workflow e por agente)."""
        for stage, v in other.stages.items():
            b = self.stages.setdefault(stage, _empty())
            b["input"] += v["input"]
            b["output"] += v["output"]
            _add_cached(b, v.get("cached", 0))
        for stage, by_agent in other.agents.items():
            for name, v in by_agent.items():
                a = self.agents.setdefault(stage, {}).setdefault(
                    name, {"input": 0, "output": 0, "calls": 0}
                )
                for k in ("input", "output", "calls"):
                    a[k] += v[k]
                _add_cached(a, v.get("cached", 0))
        return self

    @property
    def total_input(self) -> int:
        return sum(s["input"] for s in self.stages.values())

    @property
    def total_output(self) -> int:
        return sum(s["output"] for s in self.stages.values())

    @property
    def total_cached(self) -> int:
        return sum(s.get("cached", 0) for s in self.stages.values())

    def to_dict(self) -> dict[str, dict[str, int]]:
        return {k: _with_cached(v) for k, v in self.stages.items()}

    def agents_dict(self) -> dict[str, dict[str, dict[str, int]]]:
        return {
            s: {n: _with_cached(v) for n, v in a.items()}
            for s, a in self.agents.items()
        }

    @classmethod
    def from_dict(
        cls,
        data: Optional[dict[str, Any]],
        agents: Optional[dict[str, Any]] = None,
    ) -> "TokenUsage":
        return cls(data or {}, agents or {})

    # ── Persistência opcional ─────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        return {
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            **self.persist_meta,
            "current_run": {
                "total": _with_cached(
                    {
                        "input": self.total_input,
                        "output": self.total_output,
                        "cached": self.total_cached,
                    }
                ),
                "workflows": self.to_dict(),
                "agents": self.agents_dict(),
            },
        }

    def write_snapshot(self) -> None:
        """Grava o snapshot de forma atômica; falha de I/O nunca derruba a execução."""
        path = self.persist_path
        if path is None:
            return
        try:
            with self._lock:
                data = json.dumps(self.snapshot(), ensure_ascii=False, indent=2)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}")
            tmp.write_text(data, encoding="utf-8")
            os.replace(tmp, path)
        except OSError:
            pass

    # ── Relatório ─────────────────────────────────────────────────────────

    def _labels(self) -> list[str]:
        return list(_REPORT_ORDER) + sorted(
            s for s in self.stages if s not in _REPORT_ORDER
        )

    def _table(self) -> list[str]:
        def row(label: str, inp: int, out: int) -> str:
            return f"| {label} | {inp:,} | {out:,} | {inp + out:,} |"

        lines = [
            "| Workflow | Entrada | Saída | Total |",
            "|---|---:|---:|---:|",
            row("Total", self.total_input, self.total_output),
        ]
        for label in self._labels():
            s = self.stages.get(label, _empty())
            lines.append(row(label, s["input"], s["output"]))
        return lines

    def _agent_table(self, top_n: int = _DETAIL_TOP_N) -> list[str]:
        rows = [
            (stage, name, v)
            for stage, by_agent in self.agents.items()
            for name, v in by_agent.items()
        ]
        if not rows:
            return []
        rows.sort(key=lambda r: r[2]["input"] + r[2]["output"], reverse=True)
        lines = [
            f"**Consumo por agente** (top {min(top_n, len(rows))} de {len(rows)})",
            "",
            "| Workflow | Agente | Chamadas | Entrada | Saída | Total |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for stage, name, v in rows[:top_n]:
            lines.append(
                f"| {stage} | {name} | {v['calls']:,} | {v['input']:,} | "
                f"{v['output']:,} | {v['input'] + v['output']:,} |"
            )
        return lines

    def format_report(
        self,
        note: Optional[str] = None,
        *,
        detail: bool = False,
        session_total: Optional["TokenUsage"] = None,
        session_runs: int = 0,
    ) -> str:
        """Tabela markdown.

        ``note`` sinaliza relatório parcial (falha/pausa/parada); ``detail``
        acrescenta o consumo por agente; ``session_total`` acrescenta o
        acumulado de todas as execuções da sessão.
        """
        title = "**Consumo de tokens da execução**"
        if note:
            title = f"**Consumo de tokens da execução (parcial)**\n\n{note}"
        lines = [title, "", *self._table()]
        if detail:
            agent_lines = self._agent_table()
            if agent_lines:
                lines += ["", *agent_lines]
        if session_total is not None:
            lines += [
                "",
                f"**Total da sessão** ({session_runs} execução(ões))",
                "",
                *session_total._table(),
            ]
        return "\n".join(lines)


# (acumulador, workflow corrente) — definido pelo orchestrator.
_current: ContextVar[Optional[tuple[TokenUsage, str]]] = ContextVar(
    "token_usage_current", default=None
)


def bind_stage(usage: TokenUsage, pipeline_name: str) -> None:
    """Direciona os tokens das próximas chamadas LLM para o workflow dado."""
    _current.set((usage, STAGE_LABELS.get(pipeline_name, pipeline_name)))


def current_stage() -> Optional[str]:
    """Rótulo do workflow corrente, ou None fora de uma execução."""
    bound = _current.get()
    return bound[1] if bound else None


def _output_tokens(meta: Any) -> int:
    """Tokens de saída (resposta + raciocínio) de um ``usage_metadata``.

    A semântica de ``candidates_token_count`` varia: no Gemini exclui o
    raciocínio (reportado à parte em ``thoughts_token_count``); via LiteLlm
    ele recebe o ``completion_tokens`` da OpenAI, que JÁ inclui o raciocínio,
    e ``thoughts_token_count`` repete esse valor. Por isso deriva a saída de
    ``total - prompt``, igual nos dois casos; só soma os campos quando o
    total não vem preenchido.
    """
    prompt = getattr(meta, "prompt_token_count", None) or 0
    total = getattr(meta, "total_token_count", None) or 0
    tool_prompt = getattr(meta, "tool_use_prompt_token_count", None) or 0
    if total:
        return max(total - prompt - tool_prompt, 0)
    return (getattr(meta, "candidates_token_count", None) or 0) + (
        getattr(meta, "thoughts_token_count", None) or 0
    )


def record_usage(
    input_tokens: int,
    output_tokens: int,
    agent: Optional[str] = None,
    cached_tokens: int = 0,
) -> None:
    """Soma tokens no workflow corrente; no-op fora de uma execução do orchestrator."""
    bound = _current.get()
    if bound is None:
        return
    usage, stage = bound
    usage.add(
        stage,
        input_tokens or 0,
        output_tokens or 0,
        agent=agent,
        cached_tokens=cached_tokens or 0,
    )


def record_litellm_response(response: Any, agent: str = AGENT_LITELLM) -> None:
    """Contabiliza uma resposta de ``litellm.completion`` chamado fora do ADK."""
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return
    get = usage.get if isinstance(usage, dict) else (lambda k: getattr(usage, k, 0))
    details = get("prompt_tokens_details")
    if isinstance(details, dict):
        cached = details.get("cached_tokens") or 0
    else:
        cached = getattr(details, "cached_tokens", 0) or 0
    record_usage(
        get("prompt_tokens") or 0,
        get("completion_tokens") or 0,
        agent=agent,
        cached_tokens=cached if isinstance(cached, int) else 0,
    )


def instrument_genai_client(client: Any, agent: str = AGENT_MEM0) -> None:
    """Envolve ``client.models.generate_content`` (google-genai) para contabilizar.

    Usado no cliente Gemini que o mem0 cria internamente — chamadas que não
    passam pelo ADK. Embeddings (``embed_content``) não são contados: a API do
    Gemini não devolve contagem de tokens para eles.
    """
    models = getattr(client, "models", None)
    original = getattr(models, "generate_content", None)
    if original is None or getattr(original, "_token_usage_wrapped", False):
        return

    def generate_content(*args, **kwargs):
        response = original(*args, **kwargs)
        meta = getattr(response, "usage_metadata", None)
        if meta is not None:
            record_usage(
                meta.prompt_token_count or 0,
                _output_tokens(meta),
                agent=agent,
                cached_tokens=getattr(meta, "cached_content_token_count", 0) or 0,
            )
        return response

    generate_content._token_usage_wrapped = True
    models.generate_content = generate_content


class TokenUsagePlugin(BasePlugin):
    """Soma ``usage_metadata`` de cada resposta final do LLM no workflow atual."""

    def __init__(self, name: str = "token_usage"):
        super().__init__(name=name)

    async def after_model_callback(self, *, callback_context, llm_response):
        meta = getattr(llm_response, "usage_metadata", None)
        # Chunks parciais de streaming repetem o uso; conta só a resposta final.
        if meta is None or getattr(llm_response, "partial", False):
            return None
        record_usage(
            meta.prompt_token_count or 0,
            _output_tokens(meta),
            agent=getattr(callback_context, "agent_name", None),
            cached_tokens=getattr(meta, "cached_content_token_count", 0) or 0,
        )
        return None


token_usage_plugin = TokenUsagePlugin()
