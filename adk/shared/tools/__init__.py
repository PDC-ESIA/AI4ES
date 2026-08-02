from .git import tool_git_add, tool_git_commit, tool_git_checkout, tool_ler_diff, tool_preparar_commit, tool_confirmar_commit
from .filesystem import (
    tool_criar_arquivo,
    tool_salvar_relatorio,
    tool_ler_arquivo,
    tool_substituir_trecho,
    tool_salvar_artefato_requisito,
    tool_ler_workspace,
    tool_listar_workspace,
    ler_artefatos_gerados,
)
# NOTE: `gerar_doubt_artifact` é reexportado de `doubt_generator_analista` para manter compatibilidade.
from .hitl_tool import aguardar_aprovacao_humana
from .planner_tools import (
    create_hitl_checkpoint,
    describe_tools,
    generate_compliance_report,
    list_available_tools,
    plan_validator,
    register_human_validation,
)
from .doubt_handler import registrar_duvida, listar_duvidas_pendentes
from .slicer_tool import run_slicer, ler_chunk, extract_text
from .doubt_generator_analista import gerar_doubt_artifact
from .search_tool import run_search
from .glossary_tool import check_glossary, add_to_glossary
from .clarification import tool_ask_clarification_adk
from .doubt_inbox import coletar_doubts_pendentes, responder_doubt

__all__ = [
    "tool_git_add",
    "tool_git_commit",
    "tool_git_checkout",
    "tool_ler_diff",
    "tool_preparar_commit",
    "tool_confirmar_commit",
    "tool_criar_arquivo",
    "tool_salvar_relatorio",
    "tool_ler_arquivo",
    "tool_substituir_trecho",
    "tool_salvar_artefato_requisito",
    "tool_ler_workspace",
    "tool_listar_workspace",
    "registrar_duvida",
    "listar_duvidas_pendentes",
    "run_slicer",
    "ler_chunk",
    "extract_text",
    "gerar_doubt_artifact",
    "run_search",
    "check_glossary",
    "add_to_glossary",
    "ler_artefatos_gerados",
    "tool_ask_clarification_adk",
    "coletar_doubts_pendentes",
    "responder_doubt",
    "aguardar_aprovacao_humana",
    "create_hitl_checkpoint",
    "describe_tools",
    "generate_compliance_report",
    # "gerar_doubt_artifact",  # já listado acima
    "list_available_tools",
    "plan_validator",
    "register_human_validation",
]



