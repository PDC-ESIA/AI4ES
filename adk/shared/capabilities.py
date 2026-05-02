"""Registry de capabilities reutilizáveis entre agentes."""

from google.adk.tools import FunctionTool

from shared.tools import (
    tool_criar_arquivo,
    tool_git_add,
    tool_git_checkout,
    tool_git_commit,
    tool_ler_arquivo,
    tool_ler_diff,
    tool_salvar_relatorio,
    tool_substituir_trecho,
)

# Cada capability mapeia para uma lista de FunctionTools pré-configuradas.
CAPABILITIES: dict[str, list[FunctionTool]] = {
    "filesystem": [
        FunctionTool(tool_criar_arquivo),
        FunctionTool(tool_ler_arquivo),
        FunctionTool(tool_substituir_trecho),
    ],
    "git": [
        FunctionTool(tool_git_add),
        FunctionTool(tool_git_commit, require_confirmation=True),
        FunctionTool(tool_git_checkout),
    ],
    "reporting": [
        FunctionTool(tool_ler_diff),
        FunctionTool(tool_salvar_relatorio),
    ],
}


def resolve_tools(capabilities: list[str], extra_tools: list | None = None) -> list:
    """Resolve uma lista de nomes de capabilities + tools extras em uma lista final de tools."""
    tools = []
    for cap in capabilities:
        if cap not in CAPABILITIES:
            raise ValueError(f"Capability '{cap}' não registrada. Disponíveis: {list(CAPABILITIES.keys())}")
        tools.extend(CAPABILITIES[cap])
    if extra_tools:
        tools.extend(extra_tools)
    return tools
