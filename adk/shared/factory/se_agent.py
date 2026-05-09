"""
Factory para criação de agentes de Engenharia de Software.

Estende a base factory injetando tools específicas do domínio SE
(filesystem, git) organizadas em presets reutilizáveis.

Cada agente SE opera dentro de uma subpasta dedicada no workspace,
definida pelo parâmetro agent_subdir. As tools recebem base_dir/cwd
automaticamente via functools.partial.
"""

from functools import partial
from types import ModuleType
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from shared.factory.base import create_base_agent
from shared.factory.workspace import (
    AGENT_DIRS,
    get_workspace_root,
)
from shared.tools import (
    tool_criar_arquivo,
    tool_git_add,
    tool_git_checkout,
    tool_preparar_commit,
    tool_confirmar_commit,
    tool_ler_arquivo,
    tool_ler_diff,
    tool_salvar_relatorio,
    tool_substituir_trecho,
    tool_ler_workspace,
    tool_listar_workspace,
)


# -------------------------------------------------------------------
# TOOLS COM WORKSPACE BINDING
# -------------------------------------------------------------------

# Classificação das tools por tipo de parâmetro de workspace
_FILESYSTEM_TOOLS = {
    "tool_criar_arquivo": tool_criar_arquivo,
    "tool_ler_arquivo": tool_ler_arquivo,
    "tool_substituir_trecho": tool_substituir_trecho,
    "tool_salvar_relatorio": tool_salvar_relatorio,
}

_WORKSPACE_READ_TOOLS = {
    "tool_ler_workspace": tool_ler_workspace,
    "tool_listar_workspace": tool_listar_workspace,
}

_GIT_TOOLS = {
    "tool_git_add": tool_git_add,
    "tool_preparar_commit": tool_preparar_commit,
    "tool_confirmar_commit": tool_confirmar_commit,
    "tool_git_checkout": tool_git_checkout,
    "tool_ler_diff": tool_ler_diff,
}

# Configurações especiais por tool
_TOOL_CONFIG = {
    "tool_confirmar_commit": {"require_confirmation": True},
}


def _build_bound_tools(
    tool_names: list[str],
    agent_workspace: str,
    workspace_root: str,
) -> list[FunctionTool]:
    """Constrói FunctionTools com base_dir/cwd injetados via partial.

    Args:
        tool_names: Nomes das tools a construir.
        agent_workspace: Caminho absoluto da subpasta do agente.
        workspace_root: Caminho absoluto da raiz do workspace.

    Returns:
        Lista de FunctionTools com workspace binding.
    """
    tools = []

    for name in tool_names:
        extra_kwargs = _TOOL_CONFIG.get(name, {})

        if name in _FILESYSTEM_TOOLS:
            bound_fn = partial(_FILESYSTEM_TOOLS[name], base_dir=agent_workspace)
            # Preservar metadata da função original para o ADK
            bound_fn.__name__ = _FILESYSTEM_TOOLS[name].__name__
            bound_fn.__doc__ = _FILESYSTEM_TOOLS[name].__doc__
            tools.append(FunctionTool(bound_fn, **extra_kwargs))

        elif name in _WORKSPACE_READ_TOOLS:
            bound_fn = partial(_WORKSPACE_READ_TOOLS[name], base_dir=workspace_root)
            bound_fn.__name__ = _WORKSPACE_READ_TOOLS[name].__name__
            bound_fn.__doc__ = _WORKSPACE_READ_TOOLS[name].__doc__
            tools.append(FunctionTool(bound_fn, **extra_kwargs))

        elif name in _GIT_TOOLS:
            bound_fn = partial(_GIT_TOOLS[name], cwd=agent_workspace)
            bound_fn.__name__ = _GIT_TOOLS[name].__name__
            bound_fn.__doc__ = _GIT_TOOLS[name].__doc__
            tools.append(FunctionTool(bound_fn, **extra_kwargs))

    return tools


# -------------------------------------------------------------------
# PRESETS (nomes das tools por perfil)
# -------------------------------------------------------------------

_PRESET_CODER_NAMES = [
    "tool_criar_arquivo",
    "tool_ler_arquivo",
    "tool_substituir_trecho",
    "tool_ler_workspace",
    "tool_listar_workspace",
    "tool_git_add",
    "tool_preparar_commit",
    "tool_confirmar_commit",
    "tool_git_checkout",
]

_PRESET_REVIEWER_NAMES = [
    "tool_ler_diff",
    "tool_salvar_relatorio",
]

_PRESET_FULL_NAMES = _PRESET_CODER_NAMES + _PRESET_REVIEWER_NAMES

TOOL_PRESET_NAMES: dict[str, list[str]] = {
    "coder": _PRESET_CODER_NAMES,
    "reviewer": _PRESET_REVIEWER_NAMES,
    "full": _PRESET_FULL_NAMES,
}


# -------------------------------------------------------------------
# INSTRUÇÃO DE WORKSPACE (injetada no prompt do agente)
# -------------------------------------------------------------------

_WORKSPACE_INSTRUCTION = """

# DIRETÓRIO DE TRABALHO
- Seu diretório de trabalho exclusivo é: {agent_workspace}
- Todos os arquivos que você criar ou modificar DEVEM estar dentro deste diretório.
- Ao usar tools de arquivo de escrita, informe APENAS caminhos relativos (ex: "main.py", "src/utils.py").
- NÃO use caminhos absolutos. NÃO use ".." para navegar para fora do seu diretório.
"""


# -------------------------------------------------------------------
# FACTORY
# -------------------------------------------------------------------

def create_se_agent(
    name: str,
    prompt_module: ModuleType,
    output_key: str | None = None,
    output_schema: Any = None,
    preset: str = "full",
    extra_tools: list | None = None,
    model: str | None = None,
    agent_subdir: str | None = None,
) -> LlmAgent:
    """Cria um agente de Engenharia de Software com tools do domínio SE.

    As tools de filesystem recebem base_dir e as de git recebem cwd,
    ambos apontando para a subpasta do agente no workspace. As tools de
    read workspace recebem base_dir apontando para a raiz do workspace.

    Args:
        name: Nome único do agente (ex: 'coder_agent').
        prompt_module: Módulo Python contendo 'description' e 'instruction'.
        output_key: Chave no session state para a saída do agente.
        output_schema: Schema Pydantic para validação da saída (opcional).
        preset: Conjunto de tools a injetar: 'coder', 'reviewer' ou 'full'.
        extra_tools: Tools adicionais além do preset (opcional).
        model: Override do modelo LLM (opcional, default via env var).
        agent_subdir: Subpasta no workspace para este agente.
            Se None, tenta resolver via AGENT_DIRS usando o name.

    Returns:
        LlmAgent configurado com tools de engenharia de software
        e workspace binding.

    Raises:
        ValueError: Se o preset não existir ou o agent_subdir não puder ser resolvido.
    """
    if preset not in TOOL_PRESET_NAMES:
        raise ValueError(
            f"Preset '{preset}' não encontrado. "
            f"Opções válidas: {list(TOOL_PRESET_NAMES.keys())}"
        )

    # Resolver subpasta do agente no workspace
    subdir = agent_subdir or AGENT_DIRS.get(name)
    if subdir is None:
        raise ValueError(
            f"Não foi possível resolver a subpasta do agente '{name}'. "
            f"Informe agent_subdir ou adicione '{name}' ao AGENT_DIRS."
        )

    workspace_root = str(get_workspace_root())
    agent_workspace = str(get_workspace_root() / subdir)

    # Construir tools com workspace binding
    tool_names = TOOL_PRESET_NAMES[preset]
    tools = _build_bound_tools(tool_names, agent_workspace, workspace_root)

    if extra_tools:
        tools.extend(extra_tools)

    # Injetar instrução de workspace no prompt
    workspace_instruction = _WORKSPACE_INSTRUCTION.format(
        agent_workspace=agent_workspace,
    )

    # Criar módulo de prompt modificado com a instrução de workspace
    class _AugmentedPrompt:
        description = prompt_module.description
        instruction = prompt_module.instruction + workspace_instruction

    return create_base_agent(
        name=name,
        prompt_module=_AugmentedPrompt,
        output_key=output_key,
        output_schema=output_schema,
        tools=tools,
        model=model,
    )