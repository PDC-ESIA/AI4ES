"""memory_feedforward — PoC de camada de memória entre execuções (mem0).

`BaseAgent` determinístico, sem LLM. Vive no `SequentialAgent` do
`workflow_coding_review`, entre o `context_engineer` e o `LoopAgent[coder,
executor]` — mesma posição que `cr_feedforward` ocupava no design anterior
(issue #303), mas consultando o mem0 em vez de ler `.md` estático: aqui a
"lição" vem de execuções passadas do próprio pipeline, não de um arquivo
curado à mão.

Responsabilidades:
1. Ler `state["tasks"]["macro_context"]["tech_stack"]` — sem LLM, sem alterar
   o context engineer (o campo já existe em `TasksOutput`/`MacroContext`).
2. Derivar uma chave de stack estável (`_stack_key`) a partir do
   `tech_stack` — é o `agent_id` usado tanto na busca aqui quanto na escrita
   feita pelo `reviewer` (ver `reviewer/agent.py`).
3. Consultar `mem0` (`AsyncMemory.search`) por lições associadas a essa
   stack e montar `state["memory_context"]` — texto simples, uma lição por
   linha.
4. Nunca derrubar o pipeline: qualquer falha do mem0 (rede, chave ausente,
   índice vazio) é engolida com log, e o coder segue sem `memory_context`
   (mesmo comportamento de degradação do `cr_feedforward` original).

Consumido pelo coder via `{{memory_context?}}` — mesmo mecanismo de
templating do ADK (`inject_session_state`) já usado por `{{execution_result?}}`.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions

from shared.coding_review_lesson_memory.config import get_memory, memoria_habilitada

logger = logging.getLogger(__name__)

# Nº máximo de lições trazidas de volta por run — evita inflar o prompt do
# coder indefinidamente conforme a memória cresce ao longo de muitas execuções.
_TOP_K = 5


def stack_key(tech_stack: list[str]) -> str:
    """Normaliza `tech_stack` numa chave estável para o `agent_id` do mem0.

    `tech_stack` é texto livre gerado por LLM (`["Python", "FastAPI"]`,
    `["FastAPI 0.111"]`, `["Python/FastAPI/SQLAlchemy"]`, ...). O mem0 escopa
    memória por `agent_id` exato — sem uma chave estável, a mesma stack
    gerada de formas diferentes por runs distintas nunca bateria na busca.
    Para o PoC, a normalização é propositalmente simples (primeiro termo,
    caixa baixa); refinar isso é trabalho de pós-PoC, não deste esboço.
    """
    termos = [t for t in tech_stack if isinstance(t, str) and t.strip()]
    if not termos:
        return "stack-desconhecida"
    return termos[0].strip().casefold()


def _formatar_memory_context(resultados: list[dict]) -> str:
    """Uma lição por linha, a partir do retorno de `AsyncMemory.search`."""
    linhas = [r.get("memory", "") for r in resultados if r.get("memory")]
    return "\n".join(f"- {linha}" for linha in linhas)


class _MemoryProvisioner(BaseAgent):
    """Consulta o mem0 e injeta `state["memory_context"]` antes do loop."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        tasks = state.get("tasks") or {}
        macro_context = tasks.get("macro_context") if isinstance(tasks, dict) else None
        tech_stack = (macro_context or {}).get("tech_stack") or []
        chave = stack_key(tech_stack)

        memory_context = ""
        if memoria_habilitada():
            try:
                memoria = get_memory()
                termos_busca = [
                    t for t in tech_stack if isinstance(t, str) and t.strip()
                ]
                resultado = await memoria.search(
                    query=" ".join(termos_busca) or chave,
                    filters={"agent_id": chave},
                    top_k=_TOP_K,
                )
                memory_context = _formatar_memory_context(resultado.get("results", []))
            except Exception:
                # Mesma filosofia do cr_feedforward original: nada que venha do
                # mem0 justifica abortar o pipeline de codificação inteiro. Pior
                # caso aceitável é o coder rodar sem memory_context.
                logger.exception(
                    "memory_feedforward: falha ao consultar o mem0 (stack=%r) — "
                    "o coder segue sem memory_context (degradação, não interrupção)",
                    chave,
                )

        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(
                state_delta={
                    "memory_context": memory_context,
                    "memory_stack_key": chave,
                }
            ),
        )


agent = _MemoryProvisioner(
    name="memory_feedforward_agent",
    description=(
        "PoC: consulta o mem0 por lições de execuções passadas para a mesma "
        "stack e grava em state['memory_context'], antes do loop coder↔executor."
    ),
)
