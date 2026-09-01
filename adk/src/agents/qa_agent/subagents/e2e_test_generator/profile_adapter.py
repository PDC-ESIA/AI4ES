"""Adaptador Playwright compartilhado pelos perfis E2E das stacks do Coder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google.adk.tools.tool_context import ToolContext
from shared.testing import E2E_TEST_PROFILES

from .tools.gerar_testes_e2e import gerar_testes_e2e


def run_e2e_profile_adapter(
    profile_id: str,
    artifacts: list[dict[str, Any]],
    project_root: Path,
    *,
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
) -> dict[str, Any]:
    """Executa o Playwright com perfil e comando fechados pelo catálogo."""
    profile = E2E_TEST_PROFILES.get(profile_id)
    if profile is None or not profile.implemented:
        return {
            "status": "bloqueado",
            "tipo_teste": "e2e",
            "perfil": profile_id,
            "bloqueios": [
                {
                    "codigo": "ADAPTADOR_E2E_INDISPONIVEL",
                    "mensagem": f"O perfil E2E '{profile_id}' não está ativo.",
                }
            ],
        }

    requested_environment: dict[str, Any] = {}
    if ambiente_execucao_json.strip():
        decoded_environment = json.loads(ambiente_execucao_json)
        if not isinstance(decoded_environment, dict):
            raise ValueError("ambiente_execucao_json deve ser um objeto JSON.")
        for field in ("timeout_segundos", "timeout_teste_ms"):
            if field in decoded_environment:
                requested_environment[field] = decoded_environment[field]
    requested_environment.update(
        {
            "tipo": "local",
            "browser": "chromium",
            "auto_instalar_runtime": False,
        }
    )
    environment = json.dumps(requested_environment)
    envelope = {
        "origem": "agente",
        "requisitos": artifacts,
        "workspace_projeto": str(project_root.resolve()),
        "politica_execucao": {
            "autonomo": True,
            "permitir_hitl": False,
            "max_tentativas": 2,
        },
        "metadados": {
            "perfil_stack": profile_id,
            "framework_perfil": profile.framework,
        },
    }
    return gerar_testes_e2e(
        requisitos=json.dumps(envelope, ensure_ascii=False),
        plano_acao=plano_acao,
        codigo_fonte=codigo_fonte_json,
        tipo_sistema=tipo_sistema,
        framework_alvo="playwright",
        base_url=base_url,
        rotas_ou_telas=rotas_ou_telas_json,
        perfis_usuario=perfis_usuario_json,
        dados_teste=dados_teste_json,
        contratos_api=contratos_api_json,
        contratos_negativos=contratos_negativos_json,
        ambiente_execucao=environment,
        comando_execucao="npx playwright test",
        restricoes=restricoes_json,
        tool_context=tool_context,
    )


__all__ = ["run_e2e_profile_adapter"]
