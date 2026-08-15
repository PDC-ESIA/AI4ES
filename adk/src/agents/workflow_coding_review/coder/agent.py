"""Coder do workflow coding_review.

- Prompt sem seções de Git/HITL.
- Tools de filesystem bound a workspace_output/coder/src/ (consolidado).
- Instância dedicada para evitar conflito de parent no pipeline.
"""

import json
import logging
import os
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types

from shared.agent_factory import _bind_tool_to_workspace
from shared.workspace import get_agent_workspace, get_workspace_root
from shared.tools.coding_tools.filesystem_coding import (
    listar_arquivos,
    tool_criar_arquivo,
    tool_ler_arquivo,
    tool_substituir_trecho,
)
from shared.tools.filesystem import (
    tool_ler_workspace,
    tool_listar_workspace,
)

from . import prompt as coder_prompt

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

_WORKSPACE_ROOT = str(get_workspace_root())
_CODER_WS = str(get_agent_workspace("cr_coder"))


def _bind(tool):
    return _bind_tool_to_workspace(tool, _CODER_WS, _WORKSPACE_ROOT)


_INSTRUCTION_TEMPLATE = coder_prompt.build_instruction(_CODER_WS)

# Tetos do contexto injetado. O prompt do coder é system instruction: ele é
# reenviado em TODA requisição do turno (uma por tool call), então cada char
# aqui é multiplicado pelo nº de chamadas. Injetamos o que evita idas ao disco,
# não o workspace inteiro.
_MAX_ARQUIVOS_LISTADOS = 200

# Orçamentos RESERVADOS por bloco. Nunca um teto único sobre o texto montado: a
# task atual é o último bloco e seria a primeira vítima de um corte monolítico —
# o coder implementaria sem jamais ver os próprios critérios de aceite. Cada
# bloco é truncado no seu próprio limite, e a task atual jamais é descartada.
_MAX_MACRO_CHARS = 1_500
_MAX_TASK_ATUAL_CHARS = 6_000
_MAX_PLANO_CHARS = 5_000

# Visão geral das tasks: insumo do PLAN.md, que é um manifesto GLOBAL (arquivos
# → responsabilidade → task(s)/interface(s), consolidando outputs repetidos
# entre tasks). Ela só existe enquanto o plano não existe — depois disso é o
# próprio PLAN.md que governa a construção, como manda a ETAPA 0.
_MAX_TASKS_COMPACTAS_CHARS = 5_000
_MAX_DESCRICAO_COMPACTA = 240
# Teto POR LINHA: torna a visão geral limitada por construção (n_tasks × teto),
# em vez de depender de um corte no fim que poderia estourar com um único
# contrato gigante.
_MAX_LINHA_COMPACTA = 400
_ARQUIVO_PLANO = "PLAN.md"

_SEM_CONTRATO = (
    "(contrato da task indisponível — leia-o com "
    '`tool_ler_workspace("coder/tasks/<TASK-ID>.json")`)'
)


def _truncar(texto: str, teto: int) -> str:
    if len(texto) <= teto:
        return texto
    return texto[:teto] + f"\n...[truncado: {len(texto) - teto} caracteres omitidos]"


def _ler_json(caminho: Path) -> object | None:
    """Lê um JSON do workspace, devolvendo None em qualquer falha.

    Contrato ausente/ilegível não pode derrubar o turno do coder: ele degrada
    para a instrução de ler do disco, que continua disponível.
    """
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — contrato ilegível é contrato ausente
        return None


def _do_state(state, task_id: str | None) -> tuple[dict | None, dict | None]:
    """(macro_context, task) a partir de `state["tasks"]` — a fonte canônica.

    `state["tasks"]` é escrito pelo ADK a partir do `output_key` do
    context_engineer e validado pelo `output_schema` TasksOutput: existe sempre
    que aquele agente terminou, e é a mesma fonte que o TaskIterator usa para
    iterar. Os arquivos em `coder/tasks/` são redundância — dependem de o LLM
    ter chamado `tool_salvar_task_cr` para cada task, e o nome do arquivo é
    informado separadamente do conteúdo.
    """
    envelope = state.get("tasks") if hasattr(state, "get") else None
    if not isinstance(envelope, dict):
        return None, None

    macro = envelope.get("macro_context")
    macro = macro if isinstance(macro, dict) else None

    task = None
    tasks = envelope.get("tasks")
    if task_id and isinstance(tasks, list):
        task = next(
            (
                item
                for item in tasks
                if isinstance(item, dict) and item.get("id") == task_id
            ),
            None,
        )
    return macro, task


def _bloco_json(titulo: str, dado: object) -> str:
    return f"## {titulo}\n```json\n" + json.dumps(dado, ensure_ascii=False, indent=2) + "\n```"


def _bloco_plano() -> str | None:
    """Conteúdo do PLAN.md, truncado — None quando ele ainda não existe.

    Depois de escrito, o plano é "a fonte da verdade" pela ETAPA 0. Com
    `include_contents="none"`, porém, o coder da task seguinte não teria como
    vê-lo: não está no histórico e a árvore de arquivos só diz que ele existe.
    Injetá-lo é o que sustenta o papel que o prompt lhe atribui.
    """
    caminho = get_agent_workspace("cr_coder") / _ARQUIVO_PLANO
    try:
        conteudo = caminho.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 — plano ilegível é plano ausente
        return None
    return f"## {_ARQUIVO_PLANO} (sua fonte da verdade)\n" + _truncar(
        conteudo, _MAX_PLANO_CHARS
    )


def _todas_as_tasks(state, tasks_dir: Path) -> list[dict]:
    """Todas as tasks do épico: state (canônico) e, se ausente, o disco."""
    envelope = state.get("tasks") if hasattr(state, "get") else None
    if isinstance(envelope, dict) and isinstance(envelope.get("tasks"), list):
        return [item for item in envelope["tasks"] if isinstance(item, dict)]
    if not tasks_dir.exists():
        return []
    lidas = []
    for caminho in sorted(tasks_dir.glob("TASK-*.json")):
        dado = _ler_json(caminho)
        if isinstance(dado, dict):
            lidas.append(dado)
    return lidas


def _linha_compacta(task: dict, task_id_atual: str | None, com_descricao: bool) -> str:
    """Uma task em uma entrada de lista, limitada por `_MAX_LINHA_COMPACTA`."""
    identificador = task.get("id")
    marcador = " (task atual)" if identificador == task_id_atual else ""
    cabecalho = f"- **{identificador}**{marcador}"

    if com_descricao:
        descricao = str(task.get("description") or "").strip()
        if descricao:
            if len(descricao) > _MAX_DESCRICAO_COMPACTA:
                descricao = descricao[:_MAX_DESCRICAO_COMPACTA] + "…"
            cabecalho += f": {descricao}"

    partes = [cabecalho]
    contrato = task.get("contract")
    contrato = contrato if isinstance(contrato, dict) else {}
    if contrato.get("outputs"):
        partes.append("  - outputs: " + ", ".join(str(o) for o in contrato["outputs"]))
    if contrato.get("interfaces"):
        partes.append("  - interfaces: " + ", ".join(str(i) for i in contrato["interfaces"]))

    linha = "\n".join(partes)
    if len(linha) > _MAX_LINHA_COMPACTA:
        linha = linha[:_MAX_LINHA_COMPACTA] + "…"
    return linha


def _visao_geral_das_tasks(tasks: list[dict], task_id_atual: str | None) -> str:
    """Projeção compacta de TODAS as tasks — o insumo que o PLAN.md exige.

    Degrada por CAMPO antes de descartar task: primeiro com descrição, depois
    sem, e só em último caso reduz a lista a ids. Descartar tasks em silêncio
    seria pior do que abreviar — o prompt promete a visão do conjunto, e um
    manifesto global feito sobre um subconjunto invisível é pior que um
    manifesto feito sobre ids.
    """
    if not tasks:
        return ""
    for com_descricao in (True, False):
        linhas = [_linha_compacta(t, task_id_atual, com_descricao) for t in tasks]
        if sum(len(linha) + 1 for linha in linhas) <= _MAX_TASKS_COMPACTAS_CHARS:
            return "\n".join(linhas)

    identificadores = ", ".join(str(t.get("id")) for t in tasks)
    return _truncar(
        "- tasks do épico (somente ids — épico grande demais para detalhar aqui; "
        "use `tool_ler_workspace(\"coder/tasks/<ID>.json\")` para o detalhe): "
        + identificadores,
        _MAX_TASKS_COMPACTAS_CHARS,
    )


def _contrato_da_task(state) -> str:
    """Serializa o contexto macro + a task da vez para dentro do prompt.

    A task é resolvida por `state["task_id"]`, escopado por código pelo
    TaskIterator — o coder não escolhe em qual task está trabalhando.

    Cada peça é resolvida independentemente: primeiro o state (canônico),
    depois o arquivo em disco. Sem esse fallback, uma persistência que falhou
    deixaria o coder implementando sem descrição nem critérios de aceite — e,
    com `include_contents="none"`, sem o histórico que antes o salvava. Ele não
    travaria: inventaria, e a task queimaria o orçamento inteiro do loop sendo
    reprovada contra critérios que nunca viu.

    Os diretórios são resolvidos em tempo de CHAMADA (não no import): antes de
    `init_workspace()`, `get_agent_workspace` criaria a raiz sem o marker
    `.ai4se_workspace` e faria a limpeza do workspace ser recusada.
    """
    task_id = state.get("task_id") if hasattr(state, "get") else None
    macro, task = _do_state(state, task_id)

    tasks_dir = get_agent_workspace("cr_context_engineer")
    if macro is None:
        macro = _ler_json(tasks_dir / "_macro_context.json")
        macro = macro if isinstance(macro, dict) else None
    if task is None and task_id:
        task = _ler_json(tasks_dir / f"{task_id}.json")
        task = task if isinstance(task, dict) else None

    partes: list[str] = []
    if macro is not None:
        partes.append(
            _truncar(_bloco_json("Contexto macro", macro), _MAX_MACRO_CHARS)
        )

    # Exatamente UMA visão global, conforme a fase:
    #  - antes do PLAN.md, o coder está PLANEJANDO e precisa do conjunto das
    #    tasks (injetar só a atual produziria um manifesto que enxerga uma
    #    fração do escopo, e um esqueleto que as demais tasks não habitam);
    #  - depois, o plano é a fonte da verdade — e precisa estar VISÍVEL, já que
    #    sem histórico o coder da próxima task não teria como lê-lo.
    plano = _bloco_plano()
    if plano is not None:
        partes.append(plano)
    else:
        todas = _todas_as_tasks(state, tasks_dir)
        if todas:
            partes.append(
                "## Visão geral das tasks (insumo do PLAN.md)\n"
                "Conjunto completo do épico, em forma compacta. O PLAN.md é um "
                "manifesto GLOBAL: planeje olhando todas elas, não só a task "
                "atual.\n\n" + _visao_geral_das_tasks(todas, task_id)
            )

    # A task atual é o último bloco (posição de maior atenção) e tem orçamento
    # próprio: nenhum bloco anterior pode empurrá-la para fora.
    if task is not None:
        partes.append(
            _truncar(
                _bloco_json(f"Task atual — {task_id}", task), _MAX_TASK_ATUAL_CHARS
            )
        )
    elif task_id:
        logger.warning(
            "[CODER] Contrato da task %s não encontrado nem em state['tasks'] "
            "nem em %s — o coder vai implementar sem critérios de aceite.",
            task_id,
            tasks_dir,
        )
        partes.append(f"## Task atual — {task_id}\n{_SEM_CONTRATO}")

    if not partes:
        return _SEM_CONTRATO
    return "\n\n".join(partes)


def _arvore_de_arquivos() -> str:
    """Lista, em bullets, os arquivos que já existem em `coder/src/`.

    Substitui a redescoberta por tool (que custava uma requisição inteira por
    chamada) e evita que o coder recrie — e assim SOBRESCREVA — arquivo que ele
    mesmo escreveu numa iteração anterior e não vê mais no histórico.

    Resolve o diretório em tempo de CHAMADA (como `_contrato_da_task`), e não
    pela constante de import: o módulo é importado no boot do servidor, muito
    antes de `init_workspace()` recriar o workspace da run.
    """
    vazio = "- (nenhum arquivo ainda — este é o primeiro turno neste workspace)"
    return listar_arquivos(
        get_agent_workspace("cr_coder"),
        teto=_MAX_ARQUIVOS_LISTADOS,
        vazio=vazio,
        inexistente=vazio,
    )


def _instruction_provider(ctx) -> str:
    """InstructionProvider: injeta contrato, árvore e resultado da execução.

    ATENÇÃO — `execution_result` é injetado AQUI, na mão. O ADK só resolve
    templates de state (`{chave?}`) quando a instrução é uma `str`; com um
    InstructionProvider ele devolve `bypass_state_injection=True`
    (llm_agent.py::canonical_instruction) e o placeholder chegaria LITERAL ao
    modelo. O coder então veria o bloco vazio, se julgaria em "primeira
    execução" e recriaria o projeto do zero a cada iteração, sobrescrevendo as
    correções — falha silenciosa. Replicamos a semântica do `?`: chave ausente
    vira string vazia.
    """
    state = getattr(ctx, "state", None)
    if state is None:
        state = {}
    execution_result = state.get("execution_result") or ""
    return (
        _INSTRUCTION_TEMPLATE
        .replace("__CONTRATO_DA_TASK__", _contrato_da_task(state))
        .replace("__ARVORE_DE_ARQUIVOS__", _arvore_de_arquivos())
        .replace("__EXECUTION_RESULT__", str(execution_result))
    )

agent = LlmAgent(
    model=_model,
    name="cr_coder_agent",
    description="Implementa código funcional a partir de requisitos, sem git.",
    instruction=_instruction_provider,
    # Sem histórico de conversa: o coder recebe o resultado da iteração anterior
    # pelo template `{execution_result?}` (state), não pelo diálogo, e o código
    # que já escreveu está em disco. Reenviar a transcrição de todas as
    # iterações anteriores da task só inflava o contexto — media ~7k tokens de
    # crescimento por iteração. O ADK preserva o turno corrente e a última
    # resposta do executor, que é o ErrorReport de que ele precisa.
    include_contents="none",
    output_key="implementation",
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=16384,
    ),
    tools=[
        _bind(FunctionTool(tool_criar_arquivo)),
        _bind(FunctionTool(tool_ler_arquivo)),
        _bind(FunctionTool(tool_substituir_trecho)),
        _bind(FunctionTool(tool_ler_workspace)),
        _bind(FunctionTool(tool_listar_workspace)),
    ],
)
