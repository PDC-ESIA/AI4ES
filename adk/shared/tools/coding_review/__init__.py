"""Tools exclusivas do fluxo de codificação (workflow_coding_review + coder/context_engineer/reviewer standalone).

Ver docs/Time_4_Codificacao/Catalogo_de_tools_do_fluxo.md para o inventário
completo de qual agente usa qual tool.
"""

from .filesystem_coding import (
    tool_criar_arquivo,
    tool_salvar_relatorio,
    tool_ler_arquivo,
    tool_substituir_trecho,
)
from .git import (
    tool_git_add,
    tool_git_commit,
    tool_git_checkout,
    tool_ler_diff,
    tool_preparar_commit,
    tool_confirmar_commit,
)
from .context_engineer_task import tool_salvar_task, tool_salvar_task_adk

__all__ = [
    "tool_criar_arquivo",
    "tool_salvar_relatorio",
    "tool_ler_arquivo",
    "tool_substituir_trecho",
    "tool_git_add",
    "tool_git_commit",
    "tool_git_checkout",
    "tool_ler_diff",
    "tool_preparar_commit",
    "tool_confirmar_commit",
    "tool_salvar_task",
    "tool_salvar_task_adk",
]
