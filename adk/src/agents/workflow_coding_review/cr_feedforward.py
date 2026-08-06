"""cr_feedforward — camada de provisionamento de contexto (issue #303, Frente 1).

`BaseAgent` determinístico, sem LLM. Vive no `SequentialAgent` do
`workflow_coding_review`, entre o `context_engineer` e o `LoopAgent[coder↔executor]`.

Responsabilidades (relatório §8.2):
1. Ler `state["tasks"]["macro_context"]["tech_stack"]` — sem LLM, sem alterar o
   context engineer (o campo já existe em `TasksOutput`/`MacroContext`).
2. Carregar `adk/knowledge/core/` (sempre) + `adk/knowledge/stacks/<stack>/`
   (quando a stack for reconhecida — ver `selecionar_stack`).
3. Concatenar tudo em um `context_pack` — acumula por padrão (D7, grow-and-refine):
   sem parsing, sem truncagem por orçamento arbitrário de tokens.
4. Gravar em `state["context_pack"]` e persistir em `coder/context/context_pack.md`
   para auditoria (mesmo padrão do `ExecutionReport` em disco).

Consumido pelo `cr_coder` via `{context_pack?}` — mecanismo de templating do ADK
(`inject_session_state`), idêntico ao já usado por `{execution_result?}`: chave
ausente ou vazia vira string vazia, não quebra o prompt.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions

from shared.workspace import get_agent_workspace

logger = logging.getLogger(__name__)

# Seleção de stack: palavra-chave (case-insensitive) → pasta em knowledge/stacks/.
# Adicionar uma stack nova é uma linha aqui + o diretório correspondente — sem
# mudar o resto do componente. `tech_stack` é list[str] (ex: ["Python", "FastAPI",
# "SQLAlchemy"]); o match é por termo presente na lista, não pela lista inteira,
# pra tolerar ordem/variação de nome.
_STACK_KEYWORDS: dict[str, str] = {
    "fastapi": "python-fastapi",
}


def _dir_knowledge() -> Path:
    """Raiz da KB de feedforward — fora do workspace_output/, versionada no git.

    Mesmo idioma de `harness_execucao.py::_dir_historico` (override por env var +
    `parents[3]` a partir do próprio arquivo para chegar em `adk/`).
    """
    override = os.environ.get("AI4ES_KNOWLEDGE_DIR")
    if override:
        return Path(override)
    # .../adk/src/agents/workflow_coding_review/cr_feedforward.py → parents[3] == adk/
    return Path(__file__).resolve().parents[3] / "knowledge"


def selecionar_stack(tech_stack: list[str]) -> str | None:
    """Mapeia `tech_stack` (lista) para uma pasta de `knowledge/stacks/`.

    Sem correspondência conhecida, devolve `None` — o pack carrega só `core/`,
    nunca quebra por stack não reconhecida.
    """
    stack_lower = {s.lower() for s in tech_stack if isinstance(s, str)}
    for termo, pasta in _STACK_KEYWORDS.items():
        if termo in stack_lower:
            return pasta
    return None


def _ler_md(diretorio: Path) -> list[tuple[str, str]]:
    """Lê todo `.md` de primeiro nível em `diretorio`, ordenado por nome.

    Devolve pares (nome_do_arquivo, conteúdo). Diretório ausente ou arquivo vazio
    são ignorados silenciosamente — a KB é opcional por natureza (sempre há o
    fallback de rodar sem `context_pack`).
    """
    if not diretorio.is_dir():
        return []
    pares = []
    for arquivo in sorted(diretorio.glob("*.md")):
        conteudo = arquivo.read_text(encoding="utf-8").strip()
        if conteudo:
            pares.append((arquivo.name, conteudo))
    return pares


def build_context_pack(tech_stack: list[str], knowledge_root: Path | None = None) -> str:
    """Monta o `context_pack` determinístico a partir da KB em disco.

    Função pura, testável sem ADK: recebe a stack e (opcionalmente) a raiz da KB,
    devolve o texto pronto para injeção. `core/` sempre entra; `stacks/<stack>/`
    entra se `selecionar_stack` reconhecer a stack. String vazia se a KB não tiver
    nada a oferecer (diretório ausente, ou stack desconhecida e core/ vazio).
    """
    raiz = knowledge_root if knowledge_root is not None else _dir_knowledge()
    secoes: list[str] = []

    core = _ler_md(raiz / "core")
    if core:
        secoes.append(
            "# Conhecimento — core (vale para qualquer stack)\n\n"
            + "\n\n".join(f"## {nome}\n\n{conteudo}" for nome, conteudo in core)
        )

    stack = selecionar_stack(tech_stack)
    if stack:
        stack_md = _ler_md(raiz / "stacks" / stack)
        if stack_md:
            secoes.append(
                f"# Conhecimento — stack `{stack}`\n\n"
                + "\n\n".join(f"## {nome}\n\n{conteudo}" for nome, conteudo in stack_md)
            )

    return "\n\n---\n\n".join(secoes)


def _linha_auditoria(tech_stack: list[str], stack: str | None) -> str:
    """Comentário HTML com o que o cr_feedforward recebeu/decidiu nesta run.

    Só entra na CÓPIA EM DISCO (auditoria) — não em `state["context_pack"]`, pra
    não poluir o prompt do coder com metadado que não ajuda a codificar. Existe
    porque `tech_stack` não é persistido em nenhum outro lugar do workspace: sem
    isso, não dá pra conferir depois do fato por que uma stack foi (ou não) selecionada.
    """
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return (
        f"<!-- cr_feedforward | gerado em {agora} UTC | "
        f"tech_stack recebido: {tech_stack!r} | "
        f"stack selecionada: {stack!r} -->\n\n"
    )


class _ContextProvisioner(BaseAgent):
    """Monta e injeta o `context_pack` antes do loop coder↔executor."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        tasks = state.get("tasks") or {}
        macro_context = tasks.get("macro_context") or {}
        tech_stack = macro_context.get("tech_stack") or []

        pack = build_context_pack(tech_stack)
        state_delta: dict = {"context_pack": pack}

        if pack:
            try:
                destino = (
                    get_agent_workspace("cr_coder").parent / "context" / "context_pack.md"
                )
                destino.parent.mkdir(parents=True, exist_ok=True)
                stack = selecionar_stack(tech_stack)
                destino.write_text(_linha_auditoria(tech_stack, stack) + pack, encoding="utf-8")
                state_delta["context_pack_path"] = str(destino)
            except OSError:
                logger.exception(
                    "cr_feedforward: falha ao persistir context_pack.md "
                    "(state['context_pack'] segue disponível mesmo assim)"
                )

        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(state_delta=state_delta),
        )


agent = _ContextProvisioner(
    name="cr_feedforward_agent",
    description=(
        "Monta o context_pack (conhecimento core + stack, de adk/knowledge/) e "
        "grava em state['context_pack'], antes do loop coder↔executor."
    ),
)
