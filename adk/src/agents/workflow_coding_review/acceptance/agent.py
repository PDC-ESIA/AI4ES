"""Autor de testes de aceite independentes e o gate que o põe no loop.

`AI4ES_ACEITE_INDEPENDENTE`: uma vez por task, depois que o coder entrega o
mínimo executável e antes da primeira execução do harness, um agente SEPARADO
escreve `tests/acceptance/test_aceite_<TASK>.py` a partir dos critérios. O mapa
critério→teste sai do nome das funções (`aceite_independente.extrair_mapa`) e é
gravado em `coder/tasks/`, fora do alcance do coder. O harness passa a decidir
esses critérios pelos testes (atendido/não atendido), e o validador reprova a
rodada quando algum não é atendido.

Produto web (`product_type` web_app) — SEMPRE: os critérios marcados com
`interface` vão para um segundo arquivo, `test_interface_<TASK>.py`, escrito
para o navegador (Playwright) e executado contra a aplicação no ar, partindo
da página inicial. Endpoint funcionando sem tela não atende critério de
interface.
"""

from __future__ import annotations

import ast
import json
import logging
import os
from typing import Any, AsyncGenerator, Optional

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from shared.agent_factory import (
    _bind_tool_to_workspace,
    lazy_agent_workspace,
    lazy_workspace_root,
)
from shared.execution.manifest import ManifestError, load_manifest
from shared.execution.verificador_executabilidade import verificar_executabilidade
from shared.pipeline_flags import aceite_independente
from shared.tools.coding_tools.aceite_independente import (
    PASTA_ACEITE,
    caminho_relativo,
    caminho_relativo_interface,
    comando_de_aceite,
    extrair_mapa,
    gravar_mapa,
    ler_mapa,
)
from shared.tools.coding_tools.jornada import (
    instalar_conftest,
    violacoes_do_modo_navegador,
)
from shared.tools.coding_tools.criterios_aceite import normalizar_criterios
from shared.tools.coding_tools.filesystem_coding import (
    DIRETORIOS_PROIBIDOS,
    tool_ler_arquivo,
)
from shared.tools.filesystem import tool_ler_workspace, tool_listar_workspace
from shared.workspace import get_agent_workspace

from . import prompt as acceptance_prompt

logger = logging.getLogger(__name__)

CHAVE_ACEITE_TASK = "aceite_task"
CHAVE_TENTATIVAS = "aceite_tentativas"
# Tentativas do autor por task: se nem assim houver mapa, a task segue no modo
# histórico (critérios `nao_avaliado`) em vez de travar o loop.
MAX_TENTATIVAS = 2
_MAX_ARQUIVOS_INVENTARIO = 120

_model = os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash")


# ── Ferramenta de gravação ─────────────────────────────────────────────────


def _task_do_state(state: Any, task_id: str) -> Optional[dict]:
    for task in (state.get("tasks") or {}).get("tasks") or []:
        if isinstance(task, dict) and task.get("id") == task_id:
            return task
    return None


def _workdir(coder_dir) -> str:
    try:
        return load_manifest(coder_dir / "run.json").workdir or "."
    except ManifestError:
        return "."


def _produto_web(state: Any) -> bool:
    macro = (state.get("tasks") or {}).get("macro_context") or {}
    return str(macro.get("product_type") or "").strip().lower() == "web_app"


def _sobe_servico(coder_dir) -> bool:
    try:
        manifest = load_manifest(coder_dir / "run.json")
    except ManifestError:
        return False
    return manifest.surface == "service" and bool(manifest.run and manifest.port)


def dividir_criterios(state: Any, task: dict, coder_dir) -> tuple[list[str], list[str]]:
    """(critérios do arquivo principal, critérios de interface pelo navegador).

    Em produto web que sobe como serviço, todo critério automatizável marcado
    com `interface` é comprovado pelo navegador — sempre. Fora disso (não é
    web, ou não há serviço para navegar) a lista de interface é vazia e todos
    vão para o arquivo principal, como antes.
    """
    criterios = [c for c in normalizar_criterios(task.get("acceptance_criteria")) if c.automatable]
    if _produto_web(state) and _sobe_servico(coder_dir):
        interface = [c.id for c in criterios if c.interface]
    else:
        interface = []
    return [c.id for c in criterios if c.id not in interface], interface


def _destino(coder_dir, arquivo_rel: str):
    destino = (coder_dir / _workdir(coder_dir) / arquivo_rel).resolve()
    if not str(destino).startswith(str(coder_dir.resolve())):
        return None
    return destino


def tool_salvar_teste_aceite(conteudo: str, tool_context: ToolContext) -> dict:
    """Salva o arquivo de testes de aceite da task atual.

    Args:
        conteudo: Código pytest completo do arquivo. Cada teste deve se chamar
            `test_CA_<NN>_<resumo>`, com o id do critério que comprova.

    Returns:
        dict com `sucesso`, o caminho gravado e os critérios cobertos, ou o erro
        a corrigir antes de salvar de novo.
    """
    state = tool_context.state
    task_id = state.get("task_id")
    task = _task_do_state(state, task_id) if isinstance(task_id, str) else None
    if task is None:
        return {"sucesso": False, "erro": "Task atual não encontrada no state."}

    coder_dir = get_agent_workspace("cr_coder")
    automatizaveis, de_interface = dividir_criterios(state, task, coder_dir)
    if not automatizaveis:
        return {
            "sucesso": False,
            "erro": (
                "Todos os critérios automatizáveis desta task são de interface "
                f"({', '.join(de_interface)}): use tool_salvar_teste_interface."
            ),
        }
    arquivo_rel = caminho_relativo(task_id)
    try:
        mapa = extrair_mapa(conteudo, automatizaveis, arquivo_rel)
    except SyntaxError as exc:
        return {"sucesso": False, "erro": f"O arquivo não compila: {exc}"}
    if not mapa:
        return {
            "sucesso": False,
            "erro": (
                "Nenhuma função `test_CA_<NN>_...` corresponde a um critério "
                f"automatizável desta task ({', '.join(automatizaveis) or 'nenhum'})."
            ),
        }

    destino = _destino(coder_dir, arquivo_rel)
    if destino is None:
        return {"sucesso": False, "erro": "workdir do run.json fora do workspace."}
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(conteudo, encoding="utf-8")
    gravar_mapa(
        get_agent_workspace("cr_context_engineer"), task_id, arquivo_rel, mapa, mesclar=True
    )

    faltando = sorted(set(automatizaveis) - set(mapa))
    logger.info("[ACEITE][%s] testes de aceite gravados: %s", task_id, sorted(mapa))
    return {
        "sucesso": True,
        "caminho": arquivo_rel,
        "criterios_cobertos": sorted(mapa),
        "criterios_sem_teste": faltando,
    }


def tool_executar_teste_aceite(tool_context: ToolContext) -> dict:
    """Roda o arquivo de testes de aceite já salvo contra o código atual.

    Use DEPOIS de `tool_salvar_teste_aceite`, para conferir que o TESTE está
    certo. Falhas porque o app ainda não cumpre o critério são esperadas;
    erros vindos do próprio teste (API errada, nome inexistente, fixture
    ausente) devem ser corrigidos e o arquivo salvo de novo.

    Returns:
        dict com `exit_code` (None quando não há como executar) e `saida`.
    """
    from shared.execution.verificacao_rapida import executar_arquivo_de_teste

    task_id = tool_context.state.get("task_id")
    if not isinstance(task_id, str):
        return {"exit_code": None, "saida": "Task atual não encontrada no state."}
    coder_dir = get_agent_workspace("cr_coder")
    if not (coder_dir / _workdir(coder_dir) / caminho_relativo(task_id)).is_file():
        return {"exit_code": None, "saida": "Salve o arquivo com tool_salvar_teste_aceite antes."}
    exit_code, saida = executar_arquivo_de_teste(
        coder_dir, tool_context.state.get("trilha"), caminho_relativo(task_id)
    )
    return {"exit_code": exit_code, "saida": saida}


def tool_salvar_teste_interface(conteudo: str, tool_context: ToolContext) -> dict:
    """Salva os testes dos critérios de INTERFACE da task (produto web).

    Args:
        conteudo: Código pytest completo, só com Playwright: cada teste recebe
            a fixture `page`, abre `page.goto("/")` e chega à funcionalidade
            clicando e preenchendo. Nomes `test_CA_<NN>_<resumo>`.

    Returns:
        dict com `sucesso`, o caminho e os critérios cobertos, ou o erro a
        corrigir antes de salvar de novo.
    """
    state = tool_context.state
    task_id = state.get("task_id")
    task = _task_do_state(state, task_id) if isinstance(task_id, str) else None
    if task is None:
        return {"sucesso": False, "erro": "Task atual não encontrada no state."}
    coder_dir = get_agent_workspace("cr_coder")
    _, de_interface = dividir_criterios(state, task, coder_dir)
    if not de_interface:
        return {
            "sucesso": False,
            "erro": "Esta task não tem critério de interface: use tool_salvar_teste_aceite.",
        }
    try:
        arvore = ast.parse(conteudo)
    except SyntaxError as exc:
        return {"sucesso": False, "erro": f"O arquivo não compila: {exc}"}
    violacoes = violacoes_do_modo_navegador(arvore)
    if violacoes:
        return {
            "sucesso": False,
            "erro": "Critério de interface se comprova PELA INTERFACE: " + " ".join(violacoes),
        }
    arquivo_rel = caminho_relativo_interface(task_id)
    mapa = extrair_mapa(conteudo, de_interface, arquivo_rel)
    if not mapa:
        return {
            "sucesso": False,
            "erro": (
                "Nenhuma função `test_CA_<NN>_...` corresponde a um critério de "
                f"interface desta task ({', '.join(de_interface)})."
            ),
        }
    destino = _destino(coder_dir, arquivo_rel)
    if destino is None:
        return {"sucesso": False, "erro": "workdir do run.json fora do workspace."}
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(conteudo, encoding="utf-8")
    instalar_conftest(coder_dir / _workdir(coder_dir), PASTA_ACEITE)
    gravar_mapa(
        get_agent_workspace("cr_context_engineer"), task_id, arquivo_rel, mapa, mesclar=True
    )
    logger.info("[ACEITE][%s] testes de interface gravados: %s", task_id, sorted(mapa))
    return {
        "sucesso": True,
        "caminho": arquivo_rel,
        "criterios_cobertos": sorted(mapa),
        "criterios_sem_teste": sorted(set(de_interface) - set(mapa)),
    }


def tool_executar_teste_interface(tool_context: ToolContext) -> dict:
    """Roda os testes de interface já salvos contra a aplicação no ar.

    Constrói e sobe o produto como o `run.json` manda e abre o navegador. Use
    DEPOIS de `tool_salvar_teste_interface`. Falha porque a tela ainda não
    existe ou não faz o que o critério pede é esperada; erro do PRÓPRIO teste
    (API do Playwright errada, sintaxe de seletor) deve ser corrigido.

    Returns:
        dict com `status` (passou | falhou | nao_executada), `motivo` e `saida`.
    """
    from shared.tools.coding_tools.jornada import executar_jornada

    task_id = tool_context.state.get("task_id")
    if not isinstance(task_id, str):
        return {"status": "nao_executada", "motivo": "Task atual não encontrada no state."}
    resultado = executar_jornada(
        get_agent_workspace("cr_coder"),
        tool_context.state.get("trilha"),
        arquivo=caminho_relativo_interface(task_id),
    )
    return {"status": resultado.status, "motivo": resultado.motivo, "saida": resultado.saida[-3500:]}


# ── Agente autor ───────────────────────────────────────────────────────────


def _bind(tool):
    return _bind_tool_to_workspace(
        tool, lazy_agent_workspace("cr_coder"), lazy_workspace_root()
    )


def _instrucao(readonly_context) -> str:
    """Substitui só `{aceite_task?}` (sem o templating do ADK: chaves no texto
    do prompt, como em exemplos de código, não podem virar variável)."""
    contexto = readonly_context.state.get(CHAVE_ACEITE_TASK) or ""
    return acceptance_prompt.instruction.replace("{aceite_task?}", str(contexto))


author = LlmAgent(
    model=_model,
    name="cr_acceptance_author",
    description="Escreve testes de aceite independentes do coder a partir dos critérios.",
    instruction=_instrucao,
    include_contents="none",
    generate_content_config=types.GenerateContentConfig(max_output_tokens=16384),
    tools=[
        _bind(FunctionTool(tool_ler_arquivo)),
        _bind(FunctionTool(tool_listar_workspace)),
        _bind(FunctionTool(tool_ler_workspace)),
        FunctionTool(tool_salvar_teste_aceite),
        FunctionTool(tool_executar_teste_aceite),
        FunctionTool(tool_salvar_teste_interface),
        FunctionTool(tool_executar_teste_interface),
    ],
)


# ── Gate no loop ───────────────────────────────────────────────────────────


def _inventario(coder_dir) -> list[str]:
    arquivos = []
    for caminho in sorted(coder_dir.rglob("*")):
        rel = caminho.relative_to(coder_dir)
        if caminho.is_file() and not any(p in DIRETORIOS_PROIBIDOS for p in rel.parts):
            arquivos.append(rel.as_posix())
        if len(arquivos) >= _MAX_ARQUIVOS_INVENTARIO:
            break
    return arquivos


def montar_aceite_task(state: Any, task: dict, coder_dir) -> str:
    macro = (state.get("tasks") or {}).get("macro_context") or {}
    principal, de_interface = dividir_criterios(state, task, coder_dir)
    extra = (
        {
            "criterios_arquivo_principal": principal,
            "interface": {
                "criterios": de_interface,
                "arquivo": caminho_relativo_interface(task["id"]),
                "modo": "navegador (Playwright), sempre — produto web",
            },
        }
        if de_interface
        else {}
    )
    return json.dumps(
        {
            "task": {
                chave: task.get(chave)
                for chave in ("id", "description", "acceptance_criteria", "contract", "business_rules")
                if chave in task
            },
            "tech_stack": macro.get("tech_stack"),
            "product_type": macro.get("product_type"),
            "arquivo_de_testes": caminho_relativo(task["id"]),
            "workdir": _workdir(coder_dir),
            "arquivos_do_projeto": _inventario(coder_dir),
            **extra,
        },
        ensure_ascii=False,
        indent=2,
    )


class AceiteIndependenteGate(BaseAgent):
    """Invoca o autor uma vez por task, quando há o que testar e ainda não há mapa."""

    @staticmethod
    def _mapa_completo(state: Any, task_id: str, mapa: dict) -> bool:
        """Em produto web, o mapa só está completo com o arquivo de interface."""
        task = _task_do_state(state, task_id)
        if task is None:
            return True
        _, de_interface = dividir_criterios(state, task, get_agent_workspace("cr_coder"))
        return not de_interface or caminho_relativo_interface(task_id) in mapa["arquivos"]

    def _motivo_para_pular(self, state: Any) -> Optional[str]:
        task_id = state.get("task_id")
        if not aceite_independente() or not isinstance(task_id, str):
            return "desligado"
        mapa = ler_mapa(get_agent_workspace("cr_context_engineer"), task_id)
        if mapa and self._mapa_completo(state, task_id, mapa):
            return "mapa já existe"
        if (state.get(CHAVE_TENTATIVAS) or {}).get(task_id, 0) >= MAX_TENTATIVAS:
            return "tentativas esgotadas"
        coder_dir = get_agent_workspace("cr_coder")
        if not verificar_executabilidade(coder_dir).executavel:
            return "artefato ainda não executável"
        try:
            manifest = load_manifest(coder_dir / "run.json")
        except ManifestError:
            return "manifesto inválido"
        if comando_de_aceite(manifest.test, "x") is None:
            return "stack sem pytest"
        task = _task_do_state(state, task_id)
        if task is None or not any(
            c.automatable for c in normalizar_criterios(task.get("acceptance_criteria"))
        ):
            return "sem critério automatizável"
        return None

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        motivo = self._motivo_para_pular(state)
        if motivo is not None:
            logger.debug("[ACEITE] autor não invocado: %s", motivo)
            return

        task_id = state["task_id"]
        coder_dir = get_agent_workspace("cr_coder")
        texto = montar_aceite_task(state, _task_do_state(state, task_id), coder_dir)
        tentativas = dict(state.get(CHAVE_TENTATIVAS) or {})
        tentativas[task_id] = tentativas.get(task_id, 0) + 1
        state[CHAVE_ACEITE_TASK] = texto
        state[CHAVE_TENTATIVAS] = tentativas
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=EventActions(
                state_delta={CHAVE_ACEITE_TASK: texto, CHAVE_TENTATIVAS: tentativas}
            ),
        )

        logger.info("[ACEITE][%s] invocando o autor (tentativa %d).", task_id, tentativas[task_id])
        async for evento in self.sub_agents[0].run_async(ctx):
            yield evento


gate = AceiteIndependenteGate(
    name="acceptance_gate",
    description=(
        "Uma vez por task, invoca o autor de testes de aceite independentes "
        "antes da primeira execução do harness."
    ),
    sub_agents=[author],
)
