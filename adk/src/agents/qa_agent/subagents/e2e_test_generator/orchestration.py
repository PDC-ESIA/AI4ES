"""Tools multistack de geração e execução de testes E2E."""

from google.adk.tools.tool_context import ToolContext
from shared.testing import (
    E2E_TEST_PROFILES,
    inspect_request,
    normalize_e2e_result,
    prepare_request,
)
from shared.testing.profile_orchestration import (
    load_artifacts,
    resolve_managed_project_root,
)

from .profile_adapter import run_e2e_profile_adapter


def inspecionar_projeto_e2e(
    workspace_projeto: str = "",
    arquivos_declarados_json: str = "[]",
    stack_declarada: str = "",
) -> dict:
    """Inspeciona o projeto usando somente perfis E2E registrados."""
    return inspect_request(
        E2E_TEST_PROFILES,
        workspace_project=workspace_projeto,
        declared_files_json=arquivos_declarados_json,
        declared_stack=stack_declarada,
    )


def preparar_testes_e2e(
    artefatos_json: str,
    workspace_projeto: str = "",
    stack_declarada: str = "",
    plano_acao: str = "",
    codigo_fonte_json: str = "",
    tipo_sistema: str = "",
    base_url: str = "",
    rotas_ou_telas_json: str = "",
    perfis_usuario_json: str = "",
    dados_teste_json: str = "",
    contratos_api_json: str = "",
    contratos_negativos_json: str = "",
    ambiente_execucao_json: str = "",
    restricoes_json: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """Seleciona e executa o adaptador Playwright do perfil E2E."""
    prepared = prepare_request(
        E2E_TEST_PROFILES,
        artifacts_json=artefatos_json,
        workspace_project=workspace_projeto,
        declared_stack=stack_declarada,
    )
    if prepared["status"] != "pronto":
        return prepared
    try:
        artifacts = load_artifacts(artefatos_json)
        project_root = resolve_managed_project_root(workspace_projeto)
        profile = prepared["perfil"]
        adapter_result = run_e2e_profile_adapter(
            profile["profile_id"],
            artifacts,
            project_root,
            plano_acao=plano_acao,
            codigo_fonte_json=codigo_fonte_json,
            tipo_sistema=tipo_sistema,
            base_url=base_url,
            rotas_ou_telas_json=rotas_ou_telas_json,
            perfis_usuario_json=perfis_usuario_json,
            dados_teste_json=dados_teste_json,
            contratos_api_json=contratos_api_json,
            contratos_negativos_json=contratos_negativos_json,
            ambiente_execucao_json=ambiente_execucao_json,
            restricoes_json=restricoes_json,
            tool_context=tool_context,
        )
    except (KeyError, ValueError) as exc:
        total = int(prepared.get("resumo", {}).get("total", 0) or 0)
        return {
            **prepared,
            "status": "bloqueado",
            "resumo": {
                "total": total,
                "sucessos": 0,
                "bloqueados": max(1, total),
                "falhas": 0,
                "executados": 0,
            },
            "bloqueios": [
                {"codigo": "ADAPTADOR_E2E_INVALIDO", "mensagem": str(exc)}
            ],
        }
    normalized = normalize_e2e_result(
        prepared["inspecao"], profile, adapter_result, artifacts
    )
    normalized["adaptador"] = {
        "gerador": profile["generator"],
        "executor": profile["executor"],
    }
    return normalized
