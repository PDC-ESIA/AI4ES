"""Factory composta para os agentes de Engenharia de Software.

Mantém defensive prompting + tool_ask_clarification (versão original desta branch).
Adiciona binding opcional ao workspace centralizado (porte Time 4):
- Quando agent_subdir é informado, tools de filesystem recebem base_dir
  injetado via closure e tools de git recebem cwd injetado.
- Quando agent_subdir é None (default), comportamento atual preservado.
"""

import inspect
import os
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from shared.tools.clarification import tool_ask_clarification_adk

# Lazy import workspace para evitar import circular se workspace eventualmente
# importar shared.tools (não o faz hoje, mas defensivo)
from shared.workspace import get_agent_workspace, get_workspace_root, AGENT_DIRS

_DEFAULT_MODEL = "gemini-2.5-flash"

_SE_AGENT_POLICY = """

---
CRITICAL POLICY (DEFENSIVE PROMPTING):
Você é um agente de Engenharia de Software. Se você encontrar ambiguidades, falta de requisitos,
código ausente, ou qualquer impeditivo irrecuperável, você NÃO deve inventar ou alucinar informações.
Você DEVE usar a ferramenta 'tool_ask_clarification' para registrar a dúvida e interromper a execução,
devolvendo o controle ao usuário.
"""

# Tools que aceitam base_dir (filesystem — escopo do agente)
_FILESYSTEM_TOOL_NAMES = {
    "tool_criar_arquivo",
    "tool_ler_arquivo",
    "tool_substituir_trecho",
    "tool_salvar_relatorio",
    "tool_salvar_artefato_requisito",
    "gerar_doubt_artifact",
    "tool_ask_clarification",
    # Time 2 (Design) — shared/tools/design_filesystem.py
    "save_artifact",
    "append_artifact",
    "append_architect_section",
    "patch_section",
    "promote_artifact",
    "clear_design_folder",
    "list_design_files",
    "check_active_blocks",
    "read_file",
    "read_analysis_sections",
    "read_multiple_files",
}

# Tools de workspace read (aceitam base_dir como workspace_root)
_WORKSPACE_READ_TOOL_NAMES = {
    "tool_ler_workspace",
    "tool_listar_workspace",
}

# Tools que aceitam cwd (git)
_GIT_TOOL_NAMES = {
    "tool_git_add",
    "tool_git_commit",
    "tool_git_checkout",
    "tool_ler_diff",
    "tool_preparar_commit",
    "tool_confirmar_commit",
    "trava_seguranca_git_commit",
}


def _make_bound_closure(fn: Any, param_name: str, bound_value: str) -> Any:
    """Cria closure que injeta param_name=bound_value sem expor ao LLM.

    Ao contrário de functools.partial, a closure resultante NÃO inclui o
    parâmetro injetado na signature/schema — o LLM nunca vê o param e
    não pode sobrescrevê-lo com null.
    """
    sig = inspect.signature(fn)
    visible_params = [p for p in sig.parameters.values() if p.name != param_name]
    visible_names = [p.name for p in visible_params]
    new_sig = sig.replace(parameters=visible_params)
    new_annotations = {
        name: p.annotation
        for name, p in sig.parameters.items()
        if name != param_name and p.annotation != inspect.Parameter.empty
    }
    if sig.return_annotation != inspect.Signature.empty:
        new_annotations["return"] = sig.return_annotation

    def wrapper(*args, **kwargs):
        # Mapeia args posicionais para os nomes dos params visíveis
        for i, val in enumerate(args):
            if i < len(visible_names):
                kwargs[visible_names[i]] = val
        kwargs[param_name] = bound_value
        return fn(**kwargs)

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    wrapper.__signature__ = new_sig
    wrapper.__annotations__ = new_annotations
    return wrapper


def _bind_tool_to_workspace(
    tool: Any,
    agent_workspace: str,
    workspace_root: str,
) -> Any:
    """Cria nova FunctionTool com closure que injeta base_dir ou cwd.

    Identifica o tipo de tool pelo nome da função subjacente:
    - Filesystem tools: recebem base_dir=agent_workspace
    - Workspace read tools: recebem base_dir=workspace_root
    - Git tools: recebem cwd=agent_workspace
    - Outras tools: retornadas sem binding.

    Usa closures (não functools.partial) para que o parâmetro injetado
    fique INVISÍVEL no schema exposto ao LLM — evitando que o modelo
    passe null e sobrescreva o binding.
    """
    # Extrai a função subjacente (suporta tanto FunctionTool quanto callable direto)
    if isinstance(tool, FunctionTool):
        underlying = tool.func if hasattr(tool, "func") else tool
        # tenta encontrar o nome real
        fn = getattr(underlying, "__wrapped__", underlying)
        if hasattr(fn, "__name__"):
            fn_name = fn.__name__
        else:
            return tool  # não conseguimos identificar
    elif callable(tool):
        underlying = tool
        fn = tool
        fn_name = getattr(fn, "__name__", "")
    else:
        return tool

    if fn_name in _FILESYSTEM_TOOL_NAMES:
        bound = _make_bound_closure(underlying, "base_dir", agent_workspace)
        return FunctionTool(bound)
    if fn_name in _WORKSPACE_READ_TOOL_NAMES:
        bound = _make_bound_closure(underlying, "base_dir", workspace_root)
        return FunctionTool(bound)
    if fn_name in _GIT_TOOL_NAMES:
        bound = _make_bound_closure(underlying, "cwd", agent_workspace)
        return FunctionTool(bound)

    return tool  # tool desconhecida, retorna intacta (ex.: tool_ask_clarification_adk)


def create_se_agent(
    name: str,
    description: str,
    instruction: str,
    tools: list | None = None,
    agent_subdir: str | None = None,
    **kwargs,
) -> LlmAgent:
    """Cria um LlmAgent com base comum (defensive prompting + tool_ask_clarification).

    Args:
        name: Nome do agente.
        description: Descrição curta.
        instruction: Instrução completa (será apended com _SE_AGENT_POLICY).
        tools: Lista de tools (FunctionTool ou callable). Default: lista vazia.
        agent_subdir: Subpasta do agente no workspace (opcional). Se informado,
            tools de filesystem/git/workspace_read são bound via closure
            ao workspace centralizado. Pode ser:
            - Nome do agente em AGENT_DIRS (ex.: "context_engineer")
            - Caminho relativo direto (ex.: "tasks") — usado como subpasta
        **kwargs: Repassados ao LlmAgent (ex.: output_key, output_schema).

    Returns:
        LlmAgent configurado.
    """
    model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)

    base_tools = [tool_ask_clarification_adk]
    if tools:
        base_tools.extend(tools)

    # Workspace binding (opt-in)
    if agent_subdir is not None:
        workspace_root = str(get_workspace_root())
        # Resolve agent_subdir: nome em AGENT_DIRS OU caminho relativo direto
        if agent_subdir in AGENT_DIRS:
            agent_workspace = str(get_agent_workspace(agent_subdir))
        else:
            from pathlib import Path
            agent_workspace = str(Path(workspace_root) / agent_subdir)

        base_tools = [
            _bind_tool_to_workspace(t, agent_workspace, workspace_root)
            for t in base_tools
        ]

    full_instruction = instruction + _SE_AGENT_POLICY

    return LlmAgent(
        model=model,
        name=name,
        description=description,
        instruction=full_instruction,
        tools=base_tools,
        **kwargs,
    )
