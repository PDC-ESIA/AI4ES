"""cr_feedforward — camada de provisionamento de contexto (issue #303, Frente 1).

`BaseAgent` determinístico, sem LLM. Vive no `SequentialAgent` do
`workflow_coding_review`, entre o `context_engineer` e o `LoopAgent[coder↔executor]`.

Responsabilidades (relatório §8.2):
1. Ler `state["tasks"]["macro_context"]["tech_stack"]` — sem LLM, sem alterar o
   context engineer (o campo já existe em `TasksOutput`/`MacroContext`).
2. Carregar `adk/knowledge/core/` (sempre) + `adk/knowledge/stacks/<stack>/`
   (quando a stack for reconhecida — ver `selecionar_stack`).
3. Concatenar tudo em um `context_pack` — acumula por padrão (*grow-and-refine*,
   §5.4 do relatório): sem truncagem por orçamento arbitrário de tokens. A única
   leitura estrutural é a quebra em itens (`## título`), que existe para deduplicar
   o que se repete entre `core/` e `stacks/<stack>/`.
4. Gravar em `state["context_pack"]` e persistir em `coder/context/context_pack.md`
   para auditoria (mesmo padrão do `ExecutionReport` em disco).

Consumido pelo `cr_coder` via `{context_pack?}` — mecanismo de templating do ADK
(`inject_session_state`), idêntico ao já usado por `{execution_result?}`: chave
ausente ou vazia vira string vazia, não quebra o prompt.
"""

from __future__ import annotations

import logging
import os
import re
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
# mudar o resto do componente. O match é por SUBSTRING sobre a `tech_stack` inteira
# concatenada (ver `selecionar_stack`), pra tolerar ordem, versão e string composta.
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

    Casa por SUBSTRING, não por igualdade de elemento: `tech_stack` é texto livre
    gerado por LLM e chega em formatos variados — `["Python", "FastAPI"]`, mas
    também `["FastAPI 0.111"]` ou `["Python/FastAPI/SQLAlchemy"]`. Igualdade exata
    falharia nos dois últimos.

    Sem correspondência conhecida devolve `None` — o pack carrega só `core/`, nunca
    quebra por stack não reconhecida. O aviso em log fica a cargo de
    `build_context_pack`, para não repetir a mensagem a cada consulta.
    """
    termos = " ".join(s for s in tech_stack if isinstance(s, str)).casefold()
    for termo, pasta in _STACK_KEYWORDS.items():
        if termo in termos:
            return pasta
    return None


# Ordem de leitura dentro de cada escopo (`core/` e `stacks/<stack>/`): regra
# acionável primeiro, referência depois. Arquivo fora desta lista entra no fim, em
# ordem alfabética — acrescentar um `.md` novo na KB não exige tocar aqui.
_ORDEM_ARQUIVOS: tuple[str, ...] = (
    "consistency-rules.md",
    "pitfalls.md",
    "lessons.md",
    "deps.md",
    "conventions.md",
)


def _ordem(nome: str) -> tuple[int, str]:
    """Chave de ordenação de arquivo da KB — conhecidos primeiro, na ordem acima."""
    if nome in _ORDEM_ARQUIVOS:
        return (_ORDEM_ARQUIVOS.index(nome), "")
    return (len(_ORDEM_ARQUIVOS), nome)


def _ler_md(diretorio: Path) -> list[tuple[str, str]]:
    """Lê todo `.md` de primeiro nível em `diretorio`, na ordem de `_ORDEM_ARQUIVOS`.

    Devolve pares (nome_do_arquivo, conteúdo). Diretório ausente ou arquivo vazio
    são ignorados silenciosamente — a KB é opcional por natureza (sempre há o
    fallback de rodar sem `context_pack`).

    Arquivo ilegível (não-UTF-8, permissão, I/O) é PULADO com aviso, nunca propaga:
    a KB é editada à mão e um `.md` salvo em latin-1 não pode derrubar o pipeline
    de codificação inteiro. O resto da KB continua valendo.
    """
    if not diretorio.is_dir():
        return []
    pares = []
    for arquivo in sorted(diretorio.glob("*.md"), key=lambda p: _ordem(p.name)):
        try:
            conteudo = arquivo.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError):
            logger.warning(
                "cr_feedforward: %s ilegível, fora do context_pack (esperado UTF-8)",
                arquivo,
                exc_info=True,
            )
            continue
        if conteudo:
            pares.append((arquivo.name, conteudo))
    return pares


def _secoes(conteudo: str) -> list[tuple[str, str]]:
    """Quebra um `.md` da KB nos seus itens — os blocos iniciados por `## `.

    Devolve pares (título, bloco completo). O `# título` do arquivo e qualquer
    preâmbulo antes do primeiro `##` são descartados: quem identifica a origem no
    pack é o cabeçalho de escopo, e repetir o nome do arquivo só gastaria tokens.

    Existe para viabilizar o dedup por item: sem quebrar em seções, a mesma regra
    presente em `core/` e em `stacks/<stack>/` chegaria duplicada ao coder.
    """
    pares = []
    for bloco in re.split(r"^(?=## )", conteudo, flags=re.MULTILINE):
        bloco = bloco.strip()
        if not bloco.startswith("## "):
            continue
        titulo = bloco.splitlines()[0][3:].strip()
        pares.append((titulo, bloco))
    return pares


def _montar_escopo(diretorio: Path, cabecalho: str, vistos: set[str]) -> str | None:
    """Monta um escopo do pack (core ou stack), pulando itens já incluídos.

    `vistos` é mutado — é o estado compartilhado do dedup entre os escopos. Como
    `core/` é montado primeiro, uma regra genérica repetida no arquivo da stack é
    descartada, e não o contrário: o item promovido a `core/` é o canônico.
    """
    itens = []
    for _, conteudo in _ler_md(diretorio):
        for titulo, bloco in _secoes(conteudo):
            chave = titulo.casefold()
            if chave in vistos:
                continue
            vistos.add(chave)
            itens.append(bloco)
    if not itens:
        return None
    return cabecalho + "\n\n" + "\n\n".join(itens)


def build_context_pack(
    tech_stack: list[str],
    knowledge_root: Path | None = None,
    arm: str | None = None,
) -> str:
    """Monta o `context_pack` determinístico a partir da KB em disco.

    Função pura, testável sem ADK: recebe a stack e (opcionalmente) a raiz da KB,
    devolve o texto pronto para injeção. `core/` sempre entra; `stacks/<stack>/`
    entra se `selecionar_stack` reconhecer a stack. String vazia se a KB não tiver
    nada a oferecer (diretório ausente, ou stack desconhecida e core/ vazio).

    `arm` seleciona o braço do protocolo de validação (relatório §11.2) — só para
    o experimento A/B/C, nunca setado em produção (default é sempre `"C"`, o
    comportamento real desta camada). Lido de `AI4ES_FEEDFORWARD_ARM` se não
    passado explicitamente:

    - **"A"** — baseline: sem KB nenhuma, devolve `""` direto, nem lê disco.
    - **"B"** — long-context: ignora `selecionar_stack`, despeja `core/` +
      **todas** as pastas de `stacks/`, sem filtrar por stack. É o braço que
      testa se selecionar por stack (C) vale o esforço frente a despejar tudo.
    - **"C"** (default) — o comportamento desta camada: `core/` + só a stack
      reconhecida.
    """
    modo = (arm or os.environ.get("AI4ES_FEEDFORWARD_ARM") or "C").upper()
    if modo == "A":
        return ""

    raiz = knowledge_root if knowledge_root is not None else _dir_knowledge()
    vistos: set[str] = set()
    escopos: list[str] = []

    core = _montar_escopo(
        raiz / "core", "# Conhecimento — core (vale para qualquer stack)", vistos
    )
    if core:
        escopos.append(core)

    if modo == "B":
        stacks_dir = raiz / "stacks"
        pastas = sorted(p for p in stacks_dir.iterdir() if p.is_dir()) if stacks_dir.is_dir() else []
        for pasta in pastas:
            stack_md = _montar_escopo(
                pasta, f"# Conhecimento — stack `{pasta.name}`", vistos
            )
            if stack_md:
                escopos.append(stack_md)
    else:
        stack = selecionar_stack(tech_stack)
        if stack:
            stack_md = _montar_escopo(
                raiz / "stacks" / stack, f"# Conhecimento — stack `{stack}`", vistos
            )
            if stack_md:
                escopos.append(stack_md)
        else:
            # Não é ruído: desde que o `ERROS COMUNS` saiu do prompt do cr_coder, cair
            # em core/ significa o coder ficar sem deps.md/pitfalls.md — perda de
            # conhecimento que antes era garantida pela instrução. Precisa ser visível.
            logger.warning(
                "cr_feedforward: stack não reconhecida em %r — context_pack sai só com "
                "core/ (sem deps.md/pitfalls.md). Stacks disponíveis: %s",
                tech_stack,
                sorted(set(_STACK_KEYWORDS.values())),
            )

    return "\n\n---\n\n".join(escopos)


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

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        tasks = state.get("tasks") or {}
        macro_context = tasks.get("macro_context") if isinstance(tasks, dict) else None
        tech_stack = (macro_context or {}).get("tech_stack") or []

        # Rede de segurança: este agente é um elo de um SequentialAgent, então
        # qualquer exceção aqui aborta o pipeline de codificação inteiro. Nada que
        # venha da KB — que é editada à mão — justifica isso: o pior caso aceitável
        # é o coder rodar sem context_pack, que é o comportamento anterior a esta
        # camada.
        try:
            pack = build_context_pack(tech_stack)
        except Exception:
            logger.exception(
                "cr_feedforward: falha ao montar o context_pack — o coder segue "
                "sem conhecimento de apoio (degradação, não interrupção)"
            )
            pack = ""

        state_delta: dict = {"context_pack": pack}

        if pack:
            try:
                # AGENT_DIRS["cr_feedforward"] == "coder/context"; get_agent_workspace
                # cria a pasta sob demanda. Derivar o destino do workspace do coder
                # (`.parent / "context"`) funcionava, mas quebraria em silêncio se o
                # mapeamento do coder mudasse.
                destino = get_agent_workspace("cr_feedforward") / "context_pack.md"
                stack = selecionar_stack(tech_stack)
                destino.write_text(
                    _linha_auditoria(tech_stack, stack) + pack, encoding="utf-8"
                )
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
