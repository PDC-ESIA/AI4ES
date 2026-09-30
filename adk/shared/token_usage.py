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
"""

from __future__ import annotations

from contextvars import ContextVar
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


class TokenUsage:
    """Acumulador de tokens de entrada/saída por workflow."""

    def __init__(self, stages: Optional[dict[str, dict[str, int]]] = None):
        self.stages: dict[str, dict[str, int]] = {
            k: {"input": int(v.get("input", 0)), "output": int(v.get("output", 0))}
            for k, v in (stages or {}).items()
        }

    def add(self, stage: str, input_tokens: int, output_tokens: int) -> None:
        bucket = self.stages.setdefault(stage, {"input": 0, "output": 0})
        bucket["input"] += input_tokens
        bucket["output"] += output_tokens

    @property
    def total_input(self) -> int:
        return sum(s["input"] for s in self.stages.values())

    @property
    def total_output(self) -> int:
        return sum(s["output"] for s in self.stages.values())

    def to_dict(self) -> dict[str, dict[str, int]]:
        return {k: dict(v) for k, v in self.stages.items()}

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]]) -> "TokenUsage":
        return cls(data or {})

    def format_report(self, note: Optional[str] = None) -> str:
        """Tabela markdown; ``note`` sinaliza relatório parcial (execução falhou)."""

        def row(label: str, inp: int, out: int) -> str:
            return f"| {label} | {inp:,} | {out:,} | {inp + out:,} |"

        labels = [s for s in _REPORT_ORDER] + sorted(
            s for s in self.stages if s not in _REPORT_ORDER
        )
        title = "**Consumo de tokens da execução**"
        if note:
            title = f"**Consumo de tokens da execução (parcial)**\n\n{note}"
        lines = [
            title,
            "",
            "| Workflow | Entrada | Saída | Total |",
            "|---|---:|---:|---:|",
            row("Total", self.total_input, self.total_output),
        ]
        for label in labels:
            s = self.stages.get(label, {"input": 0, "output": 0})
            lines.append(row(label, s["input"], s["output"]))
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


def record_usage(input_tokens: int, output_tokens: int) -> None:
    """Soma tokens no workflow corrente; no-op fora de uma execução do orchestrator."""
    bound = _current.get()
    if bound is None:
        return
    usage, stage = bound
    usage.add(stage, input_tokens or 0, output_tokens or 0)


def record_litellm_response(response: Any) -> None:
    """Contabiliza uma resposta de ``litellm.completion`` chamado fora do ADK."""
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return
    get = usage.get if isinstance(usage, dict) else (lambda k: getattr(usage, k, 0))
    record_usage(get("prompt_tokens") or 0, get("completion_tokens") or 0)


def instrument_genai_client(client: Any) -> None:
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
                (meta.candidates_token_count or 0)
                + (getattr(meta, "thoughts_token_count", None) or 0),
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
            (meta.candidates_token_count or 0)
            + (getattr(meta, "thoughts_token_count", None) or 0),
        )
        return None


token_usage_plugin = TokenUsagePlugin()
