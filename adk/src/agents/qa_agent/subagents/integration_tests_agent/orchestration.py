"""Tools da base multistack de testes de integração."""

from shared.testing import (
    INTEGRATION_TEST_PROFILES,
    inspect_request,
    normalize_integration_result,
    prepare_request,
)
from shared.testing.profile_orchestration import (
    load_artifacts,
    resolve_managed_project_root,
)

from .profile_generation import run_integration_profile_adapter


def inspecionar_projeto_integracao(
    workspace_projeto: str = "",
    arquivos_declarados_json: str = "[]",
    stack_declarada: str = "",
) -> dict:
    """Inspeciona o projeto usando somente perfis de integração registrados."""
    return inspect_request(
        INTEGRATION_TEST_PROFILES,
        workspace_project=workspace_projeto,
        declared_files_json=arquivos_declarados_json,
        declared_stack=stack_declarada,
    )


def preparar_testes_integracao(
    artefatos_json: str,
    workspace_projeto: str = "",
    stack_declarada: str = "",
) -> dict:
    """Seleciona e executa o adaptador de integração da stack.

    artefatos_json: JSON de um objeto ou lista de objetos. O código-fonte é
    lido automaticamente do projeto; cada objeto só precisa descrever o
    requisito/cenário a validar, com estes campos:
    - id_artefato (str, opcional): identificador do artefato (ex: "RF-01").
    - tipo (str, opcional): tipo do artefato (ex: "RF", "HU").
    - modulo (str, opcional): componente/módulo alvo.
    - conteudo (str): texto do requisito ou cenário de integração a validar
      (ex: "Reserva de estoque bem-sucedida realiza o checkout; estoque
      insuficiente rejeita o checkout com erro."). Aceita também os campos
      alternativos descricao, requisito, resumo, titulo, criterios_aceite ou
      criterios_verificaveis caso conteudo não seja usado.
    """
    prepared = prepare_request(
        INTEGRATION_TEST_PROFILES,
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
        adapter_result = run_integration_profile_adapter(
            profile["profile_id"], artifacts, project_root
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
                {"codigo": "ADAPTADOR_INTEGRACAO_INVALIDO", "mensagem": str(exc)}
            ],
        }
    normalized = normalize_integration_result(
        prepared["inspecao"], profile, adapter_result
    )
    normalized["adaptador"] = {
        "gerador": profile["generator"],
        "executor": profile["executor"],
    }
    return normalized
