"""Tools multistack de geração e execução de testes E2E."""

import json

from google.adk.tools.tool_context import ToolContext
from shared.testing import (
    E2E_TEST_PROFILES,
    inspect_request,
    normalize_e2e_result,
    prepare_request,
)
from shared.testing.profile_orchestration import (
    block_prepared_result,
    load_artifacts,
    resolve_managed_project_root,
)

from .profile_adapter import run_e2e_profile_adapter
from .tools.extrair_contrato_textual import extrair_contrato_textual_e2e


def _plano_validado_da_sessao(tool_context: ToolContext | None) -> str:
    """Recupera o plano canônico salvo pelo output_key do Action Planner."""
    if tool_context is None:
        return ""
    state = getattr(tool_context, "state", None)
    if state is None:
        return ""
    value = state.get("last_action_plan", "")
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return value if isinstance(value, str) else ""


def _artefatos_com_handoff(artefatos_json: str, plano_acao: str) -> str:
    """Preserva o requisito canônico mesmo quando o modelo envia um resumo."""
    try:
        artifacts = load_artifacts(artefatos_json)
    except ValueError:
        return artefatos_json
    try:
        plan = json.loads(plano_acao)
    except (json.JSONDecodeError, TypeError):
        return artefatos_json
    handoff = plan.get("handoff_context", {}) if isinstance(plan, dict) else {}
    original = handoff.get("entrada_original") if isinstance(handoff, dict) else None
    if original in (None, "", [], {}):
        return artefatos_json
    content = (
        original
        if isinstance(original, str)
        else json.dumps(original, ensure_ascii=False)
    )
    if any(
        item.get("conteudo") == content or item.get("content") == content
        for item in artifacts
    ):
        return artefatos_json
    artifacts.append(
        {
            "id_artefato": "E2E-001" if not artifacts else "E2E-HANDOFF-001",
            "tipo": "RF",
            "conteudo": content,
        }
    )
    return json.dumps(artifacts, ensure_ascii=False)


def _contrato_canonico_do_handoff(plano_acao: str) -> dict:
    """Extrai fatos E2E do pedido original, sem depender do resumo do modelo."""
    try:
        plan = json.loads(plano_acao)
    except json.JSONDecodeError, TypeError:
        return {}
    handoff = plan.get("handoff_context", {}) if isinstance(plan, dict) else {}
    original = handoff.get("entrada_original") if isinstance(handoff, dict) else None
    return extrair_contrato_textual_e2e(original)


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
    plano_efetivo = _plano_validado_da_sessao(tool_context) or plano_acao
    artefatos_efetivos = _artefatos_com_handoff(
        artefatos_json,
        plano_efetivo,
    )
    contrato_canonico = _contrato_canonico_do_handoff(plano_efetivo)
    tipo_sistema_efetivo = contrato_canonico.get("tipo_sistema") or tipo_sistema
    base_url_efetiva = contrato_canonico.get("base_url") or base_url
    rotas_efetivas = (
        json.dumps(contrato_canonico["rotas_ou_telas"], ensure_ascii=False)
        if contrato_canonico.get("rotas_ou_telas")
        else rotas_ou_telas_json
    )
    dados_efetivos = (
        json.dumps(contrato_canonico["dados_teste"], ensure_ascii=False)
        if contrato_canonico.get("dados_teste")
        else dados_teste_json
    )
    prepared = prepare_request(
        E2E_TEST_PROFILES,
        artifacts_json=artefatos_efetivos,
        workspace_project=workspace_projeto,
        declared_stack=stack_declarada,
    )
    if prepared["status"] != "pronto":
        return prepared
    try:
        artifacts = load_artifacts(artefatos_efetivos)
        project_root = resolve_managed_project_root(workspace_projeto)
        profile = prepared["perfil"]
        adapter_result = run_e2e_profile_adapter(
            profile["profile_id"],
            artifacts,
            project_root,
            plano_acao=plano_efetivo,
            codigo_fonte_json=codigo_fonte_json,
            tipo_sistema=tipo_sistema_efetivo,
            base_url=base_url_efetiva,
            rotas_ou_telas_json=rotas_efetivas,
            perfis_usuario_json=perfis_usuario_json,
            dados_teste_json=dados_efetivos,
            contratos_api_json=contratos_api_json,
            contratos_negativos_json=contratos_negativos_json,
            ambiente_execucao_json=ambiente_execucao_json,
            restricoes_json=restricoes_json,
            tool_context=tool_context,
        )
    except (KeyError, ValueError) as exc:
        return block_prepared_result(prepared, "ADAPTADOR_E2E_INVALIDO", str(exc))
    normalized = normalize_e2e_result(
        prepared["inspecao"], profile, adapter_result, artifacts
    )
    normalized["adaptador"] = {
        "gerador": profile["generator"],
        "executor": profile["executor"],
    }
    return normalized
