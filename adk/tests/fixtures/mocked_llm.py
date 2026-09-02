"""Mocks de LLM reutilizáveis entre as camadas de teste.

Objetivo: permitir testar agentes ADK/LangChain sem depender de uma chamada
real de modelo (custo, latência, não-determinismo), mantendo uma interface
mínima compatível com o que os agentes deste projeto esperam (`.invoke`,
`.ainvoke`, respostas com `.content`/function_call).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class MockResponse:
    """Resposta sintética de um LLM, no formato mínimo usado pelos agentes.

    Attributes:
        content: texto da resposta (pode ser vazio se só houver function_call).
        function_call: nome + args da tool que o "modelo" decidiu chamar,
            ou None se a resposta for texto puro.
        raw: payload original (dict) para inspeção nos testes, se necessário.
    """

    content: str = ""
    function_call: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class MockLLM:
    """LLM síncrono determinístico: devolve respostas pré-programadas em sequência.

    Uso::

        llm = MockLLM(responses=[
            MockResponse(function_call={"name": "tool_criar_arquivo", "args": {...}}),
            MockResponse(content="Concluído."),
        ])
        r1 = llm.invoke("prompt qualquer")  # -> primeira resposta
        r2 = llm.invoke("prompt qualquer")  # -> segunda resposta

    Se a lista de respostas se esgotar, repete a última (evita StopIteration
    em loops de agente que chamam o LLM mais vezes do que o previsto).
    """

    def __init__(self, responses: list[MockResponse] | None = None) -> None:
        self.responses = responses or [MockResponse(content="ok")]
        self.calls: list[Any] = []
        self._idx = 0

    def invoke(self, prompt: Any, **kwargs: Any) -> MockResponse:
        """Registra a chamada e devolve a próxima resposta programada."""
        self.calls.append({"prompt": prompt, "kwargs": kwargs})
        resposta = self.responses[min(self._idx, len(self.responses) - 1)]
        self._idx += 1
        return resposta

    def reset(self) -> None:
        """Zera o histórico de chamadas e volta ao início da lista de respostas."""
        self.calls.clear()
        self._idx = 0


class AsyncMockLLM(MockLLM):
    """Variante assíncrona de `MockLLM`, para agentes que usam `ainvoke`."""

    async def ainvoke(self, prompt: Any, **kwargs: Any) -> MockResponse:
        """Versão assíncrona de `invoke` — mesma semântica de sequência de respostas."""
        return self.invoke(prompt, **kwargs)


def make_scripted_llm(
    script: list[Callable[[Any], MockResponse] | MockResponse],
) -> MockLLM:
    """Cria um `MockLLM` cujo comportamento por chamada é definido por `script`.

    Cada item do script é uma `MockResponse` fixa OU uma função que recebe o
    prompt recebido e devolve uma `MockResponse` — útil quando a resposta
    depende do conteúdo do prompt (ex.: simular decisão condicional de um
    LLM-judge sem precisar de um modelo real).
    """
    llm = MockLLM(responses=[MockResponse()])
    resolved: list[MockResponse] = []

    def _invoke(prompt: Any, **kwargs: Any) -> MockResponse:
        idx = min(len(llm.calls), len(script) - 1)
        item = script[idx]
        resposta = item(prompt) if callable(item) else item
        llm.calls.append({"prompt": prompt, "kwargs": kwargs})
        resolved.append(resposta)
        return resposta

    llm.invoke = _invoke  # type: ignore[assignment]
    return llm
