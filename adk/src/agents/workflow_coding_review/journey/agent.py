"""Autor do teste de jornada do produto (`cr_journey_author`).

Invocado pelo TaskIterator depois da última task (`AI4ES_JORNADA`); o teste é
executado por `shared.tools.coding_tools.jornada.executar_jornada`.
"""

from __future__ import annotations

import ast
import json
import logging
import os
from pathlib import Path
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types

from shared.agent_factory import (
    _bind_tool_to_workspace,
    lazy_agent_workspace,
    lazy_workspace_root,
)
from shared.execution.manifest import ManifestError, load_manifest
from shared.tools.coding_tools.filesystem_coding import (
    DIRETORIOS_PROIBIDOS,
    tool_ler_arquivo,
)
from shared.tools.coding_tools.jornada import ARQUIVO_JORNADA, instalar_conftest
from shared.tools.filesystem import tool_ler_workspace, tool_listar_workspace
from shared.workspace import get_agent_workspace, get_workspace_root

from . import prompt as journey_prompt

logger = logging.getLogger(__name__)

CHAVE_CONTEXTO = "jornada_contexto"
_MAX_ARQUIVOS = 120
_PASTAS_DE_REQUISITOS = ("requirements/HUs", "requirements/Outros")

_model = os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash")


def _workdir(coder_dir: Path) -> str:
    try:
        return load_manifest(coder_dir / "run.json").workdir or "."
    except ManifestError:
        return "."


# Modos da jornada. Produto web é navegado pelo Playwright, só pela interface;
# os demais (API, CLI...) falam HTTP direto com o produto no ar.
MODO_NAVEGADOR = "navegador"
MODO_HTTP = "http"
_PRODUTOS_WEB = frozenset({"web_app"})

# No modo navegador, nada de atalhos que pulam a interface.
_MODULOS_PROIBIDOS = ("httpx", "requests", "urllib", "aiohttp", "fastapi", "starlette", "flask", "app")


def modo_da_jornada(product_type: Any) -> str:
    return MODO_NAVEGADOR if str(product_type or "").strip().lower() in _PRODUTOS_WEB else MODO_HTTP


def _modo_do_state(state: Any) -> str:
    try:
        return json.loads(state.get(CHAVE_CONTEXTO) or "{}").get("modo") or MODO_HTTP
    except (ValueError, AttributeError):
        return MODO_HTTP


def violacoes_do_modo_navegador(arvore: ast.AST) -> list[str]:
    """O que, num teste de jornada web, pula a interface do produto.

    Na sétima validação a jornada chamou os endpoints direto e passou, com um
    produto sem tela de upload, sem botão de seleção e sem tela de álbum.
    """
    erros: list[str] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes = [a.name for a in no.names]
        elif isinstance(no, ast.ImportFrom):
            nomes = [no.module or ""]
        else:
            nomes = []
        for nome in nomes:
            if nome.split(".")[0] in _MODULOS_PROIBIDOS:
                erros.append(f"import de `{nome}`: a jornada web usa só o navegador (`page`).")
        if isinstance(no, ast.Attribute) and no.attr == "request" and isinstance(no.value, ast.Name):
            erros.append(
                f"`{no.value.id}.request` faz HTTP direto, sem passar pela interface."
            )
        if (
            isinstance(no, ast.Call)
            and isinstance(no.func, ast.Attribute)
            and no.func.attr == "goto"
        ):
            alvo = no.args[0] if no.args else None
            if not (isinstance(alvo, ast.Constant) and alvo.value == "/"):
                erros.append(
                    "`page.goto(...)` só pode abrir a página inicial `\"/\"`; o resto se "
                    "alcança clicando em links e botões, como o usuário faria."
                )
    usa_page = any(
        isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
        and no.name.startswith("test_")
        and any(a.arg == "page" for a in no.args.args)
        for no in ast.walk(arvore)
    )
    if not usa_page:
        erros.append("Nenhum teste recebe a fixture `page` do Playwright.")
    return sorted(set(erros))


def tool_salvar_teste_jornada(conteudo: str, tool_context: ToolContext) -> dict:
    """Salva o teste de jornada do produto.

    Args:
        conteudo: Código pytest completo, com uma função `test_jornada_<NN>_...`
            por jornada.

    Returns:
        dict com `sucesso` e as jornadas encontradas, ou o erro a corrigir.
    """
    try:
        arvore = ast.parse(conteudo)
    except SyntaxError as exc:
        return {"sucesso": False, "erro": f"O arquivo não compila: {exc}"}
    jornadas = [
        no.name
        for no in arvore.body
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name.startswith("test_")
    ]
    if not jornadas:
        return {"sucesso": False, "erro": "Nenhuma função de teste (`test_jornada_...`) no arquivo."}
    modo = _modo_do_state(tool_context.state)
    if modo == MODO_NAVEGADOR:
        violacoes = violacoes_do_modo_navegador(arvore)
        if violacoes:
            return {
                "sucesso": False,
                "erro": "Jornada de produto web precisa percorrer a INTERFACE: "
                + " ".join(violacoes),
            }

    coder_dir = get_agent_workspace("cr_coder")
    destino = (coder_dir / _workdir(coder_dir) / ARQUIVO_JORNADA).resolve()
    if not str(destino).startswith(str(coder_dir.resolve())):
        return {"sucesso": False, "erro": "workdir do run.json fora do workspace."}
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(conteudo, encoding="utf-8")
    if modo == MODO_NAVEGADOR:
        instalar_conftest(coder_dir / _workdir(coder_dir))
    logger.info("[JORNADA] teste de jornada gravado (%s): %s", modo, jornadas)
    return {"sucesso": True, "caminho": ARQUIVO_JORNADA, "modo": modo, "jornadas": jornadas}


def tool_executar_teste_jornada(tool_context: ToolContext) -> dict:
    """Roda a jornada já salva contra o produto no ar (build + run do run.json).

    Use DEPOIS de `tool_salvar_teste_jornada`, para conferir que o TESTE está
    certo. Falhas porque o produto não faz o que a história pede são o
    resultado esperado; erros vindos do próprio teste (tipo errado, API do
    cliente, nome inexistente) devem ser corrigidos e o arquivo salvo de novo.

    Returns:
        dict com `status` (passou | falhou | nao_executada), `motivo` e `saida`.
    """
    from shared.tools.coding_tools.jornada import executar_jornada

    resultado = executar_jornada(get_agent_workspace("cr_coder"), tool_context.state.get("trilha"))
    return {"status": resultado.status, "motivo": resultado.motivo, "saida": resultado.saida[-3500:]}


def _bind(tool):
    return _bind_tool_to_workspace(
        tool, lazy_agent_workspace("cr_coder"), lazy_workspace_root()
    )


def _instrucao(readonly_context) -> str:
    """Substitui só `{jornada_contexto?}`.

    Sem o templating do ADK de propósito: o prompt traz código Python com
    f-strings (`{url}`, `{ref}`), que o ADK tentaria resolver como variáveis de
    state — na validação isso derrubou o autor com `KeyError: url`.
    """
    contexto = readonly_context.state.get(CHAVE_CONTEXTO) or ""
    return journey_prompt.instruction.replace("{jornada_contexto?}", str(contexto))


author = LlmAgent(
    model=_model,
    name="cr_journey_author",
    description="Escreve o teste de jornada de ponta a ponta do produto a partir das HUs.",
    instruction=_instrucao,
    include_contents="none",
    generate_content_config=types.GenerateContentConfig(max_output_tokens=16384),
    tools=[
        _bind(FunctionTool(tool_ler_arquivo)),
        _bind(FunctionTool(tool_listar_workspace)),
        _bind(FunctionTool(tool_ler_workspace)),
        FunctionTool(tool_salvar_teste_jornada),
        FunctionTool(tool_executar_teste_jornada),
    ],
)


def _listar(raiz: Path, limite: int = _MAX_ARQUIVOS) -> list[str]:
    arquivos = []
    for caminho in sorted(raiz.rglob("*")):
        rel = caminho.relative_to(raiz)
        if caminho.is_file() and not any(p in DIRETORIOS_PROIBIDOS for p in rel.parts):
            arquivos.append(rel.as_posix())
        if len(arquivos) >= limite:
            break
    return arquivos


def montar_contexto_jornada(state: Any, tasks: list[dict]) -> str:
    """Produto, tasks resumidas, requisitos a ler e inventário do código."""
    raiz = get_workspace_root()
    requisitos = [
        f"{pasta}/{nome}"
        for pasta in _PASTAS_DE_REQUISITOS
        for nome in (_listar(raiz / pasta) if (raiz / pasta).is_dir() else [])
        if nome.endswith(".md")
    ]
    macro = (state.get("tasks") or {}).get("macro_context") or {}
    coder_dir = get_agent_workspace("cr_coder")
    return json.dumps(
        {
            "produto": {
                chave: macro.get(chave)
                for chave in ("summary", "product_type", "tech_stack")
                if chave in macro
            },
            "tasks": [
                {
                    "id": t.get("id"),
                    "description": t.get("description"),
                    "acceptance_criteria": t.get("acceptance_criteria"),
                }
                for t in tasks
            ],
            "arquivos_de_requisitos": requisitos,
            "arquivo_de_teste": ARQUIVO_JORNADA,
            "modo": modo_da_jornada(macro.get("product_type")),
            "workdir": _workdir(coder_dir),
            "arquivos_do_projeto": _listar(coder_dir),
        },
        ensure_ascii=False,
        indent=2,
    )
