"""Tools determinísticas do subagente de testes unitários."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shared.testing import UNIT_TEST_PROFILES, inspect_unit_test_project
from shared.testing.coder_stack import load_coder_stack
from shared.tools.pytest_runner import executar_pytest_tool
from shared.workspace import get_agent_workspace, get_workspace_root
from src.agents.qa_agent.subagents.receive_requirements.orchestration import (
    receber_requisitos,
)

from .profile_generation import gerar_testes_do_perfil

_NON_PYTHON_PROFILES = {
    profile_id
    for profile_id, profile in UNIT_TEST_PROFILES.items()
    if profile_id != "python-pytest" and profile.implemented
}


def _blocked(code: str, message: str, *, inspection: dict | None = None) -> dict:
    return {
        "status": "bloqueado",
        "tipo_teste": "unitario",
        "inspecao": inspection,
        "perfil": inspection.get("perfil") if inspection else None,
        "resumo": {
            "total": 0,
            "sucessos": 0,
            "bloqueados": 1,
            "falhas": 0,
            "executados": 0,
        },
        "arquivos_gerados": [],
        "detalhes": [],
        "bloqueios": [{"codigo": code, "mensagem": message}],
    }


def _resolve_project_root(workspace_projeto: str) -> Path:
    workspace_root = get_workspace_root().resolve()
    if workspace_projeto and workspace_projeto.strip():
        received = Path(workspace_projeto.strip()).expanduser()
        candidate = received if received.is_absolute() else workspace_root / received
        candidate = candidate.resolve()
    else:
        candidate = get_agent_workspace("cr_coder").resolve()

    if candidate != workspace_root and not candidate.is_relative_to(workspace_root):
        raise ValueError(
            "workspace_projeto deve permanecer dentro do workspace gerenciado."
        )
    return candidate


def _parse_declared_files(arquivos_declarados_json: str) -> list[str]:
    try:
        raw = json.loads(arquivos_declarados_json or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(f"arquivos_declarados_json inválido: {exc}") from exc
    if not isinstance(raw, list):
        raise ValueError("arquivos_declarados_json deve ser uma lista JSON.")

    names: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
        elif isinstance(item, dict):
            value = item.get("path") or item.get("nome") or item.get("filename")
            if isinstance(value, str) and value.strip():
                names.append(value.strip())
    return names


def _load_artifacts(artefatos_json: str) -> list[dict[str, Any]]:
    try:
        raw = json.loads(artefatos_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"artefatos_json inválido: {exc}") from exc
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
        raise ValueError("artefatos_json deve conter um objeto ou lista de objetos.")
    return raw


def _artifact_file_names(artifacts: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for artifact in artifacts:
        support_files = artifact.get("arquivos_apoio", [])
        if isinstance(support_files, list):
            for item in support_files:
                if isinstance(item, str) and item.strip():
                    names.append(item.strip())
                elif isinstance(item, dict):
                    value = item.get("path") or item.get("nome") or item.get("filename")
                    if isinstance(value, str) and value.strip():
                        names.append(value.strip())

        parts = artifact.get("parts")
        if not isinstance(parts, list):
            content = artifact.get("content")
            parts = content.get("parts") if isinstance(content, dict) else None
        if isinstance(parts, list):
            for part in parts:
                inline = part.get("inlineData") if isinstance(part, dict) else None
                if isinstance(inline, dict):
                    value = inline.get("displayName") or inline.get("name")
                    if isinstance(value, str) and value.strip():
                        names.append(value.strip())
    return names


def inspecionar_projeto_unitario(
    workspace_projeto: str = "",
    arquivos_declarados_json: str = "[]",
    stack_declarada: str = "",
) -> dict:
    """Identifica deterministicamente o perfil de teste unitário do projeto."""
    try:
        project_root = _resolve_project_root(workspace_projeto)
        declared_files = _parse_declared_files(arquivos_declarados_json)
    except ValueError as exc:
        return {
            "status": "bloqueado",
            "tipo_teste": "unitario",
            "projeto": None,
            "perfil": None,
            "confianca": 0.0,
            "evidencias": [],
            "arquivos_fonte": [],
            "bloqueios": [
                {"codigo": "ENTRADA_INSPECAO_INVALIDA", "mensagem": str(exc)}
            ],
        }
    effective_stack = stack_declarada or load_coder_stack()
    return inspect_unit_test_project(
        project_root,
        declared_files=declared_files,
        declared_stack=effective_stack,
    )


def gerar_testes_unitarios(
    artefatos_json: str,
    workspace_projeto: str = "",
    stack_declarada: str = "",
) -> dict:
    """Inspeciona, gera e executa testes unitários no perfil suportado."""
    try:
        artifacts = _load_artifacts(artefatos_json)
        project_root = _resolve_project_root(workspace_projeto)
    except ValueError as exc:
        return _blocked("ENTRADA_UNITARIA_INVALIDA", str(exc))

    effective_stack = stack_declarada or load_coder_stack()
    inspection = inspect_unit_test_project(
        project_root,
        declared_files=_artifact_file_names(artifacts),
        declared_stack=effective_stack,
    )
    if inspection["status"] != "suportado":
        blockers = inspection.get("bloqueios") or []
        result = _blocked(
            blockers[0]["codigo"] if blockers else "PERFIL_INDISPONIVEL",
            blockers[0]["mensagem"]
            if blockers
            else "O perfil unitário não está disponível.",
            inspection=inspection,
        )
        result["bloqueios"] = blockers
        return result

    profile = inspection.get("perfil") or {}
    profile_id = profile.get("profile_id")
    if profile_id == "python-pytest":
        generation = receber_requisitos(artefatos_json)
    elif profile_id in _NON_PYTHON_PROFILES:
        generation = gerar_testes_do_perfil(profile_id, artifacts, project_root)
    else:
        return _blocked(
            "EXECUTOR_UNITARIO_INDISPONIVEL",
            f"O executor do perfil '{profile_id or 'desconhecido'}' ainda não foi implementado.",
            inspection=inspection,
        )

    normalized_details: list[dict] = []
    generated_files: list[str] = []
    execution_failures = 0
    execution_successes = 0
    blocked_count = 0
    generation_failures = 0 if generation.get("status") == "concluido" else 1

    for detail in generation.get("detalhes", []):
        normalized = dict(detail)
        execution = detail.get("resultado_execucao")
        if detail.get("status") == "sucesso":
            generated_path = detail.get("arquivo_gerado")
            if isinstance(generated_path, str) and generated_path:
                generated_files.append(generated_path)
            if profile_id == "python-pytest" and detail.get("fluxo") == "A":
                if generated_path:
                    execution = executar_pytest_tool(generated_path)
                else:
                    execution = {
                        "status": "falha",
                        "erros": [
                            {
                                "codigo": "ARQUIVO_GERADO_AUSENTE",
                                "mensagem": "O gerador não retornou arquivo_gerado para o Fluxo A.",
                            }
                        ],
                    }
            if execution:
                if execution.get("status") == "sucesso":
                    execution_successes += 1
                elif execution.get("status") == "bloqueado":
                    blocked_count += 1
                else:
                    execution_failures += 1
        elif detail.get("status") == "bloqueado":
            blocked_count += 1
        else:
            generation_failures += 1
        normalized["resultado_execucao"] = execution
        normalized_details.append(normalized)

    generated_successes = sum(
        1 for detail in normalized_details if detail.get("status") == "sucesso"
    )
    successful_skeletons = sum(
        1
        for detail in normalized_details
        if detail.get("status") == "sucesso"
        and detail.get("fluxo") == "B"
        and detail.get("resultado_execucao") is None
    )
    effective_successes = execution_successes + successful_skeletons
    failure_count = generation_failures + execution_failures
    if effective_successes and (blocked_count or failure_count):
        status = "parcial"
    elif blocked_count and not effective_successes:
        status = "bloqueado"
    elif failure_count:
        status = "falha"
    elif generated_successes:
        status = "sucesso"
    else:
        status = "falha"

    return {
        "status": status,
        "tipo_teste": "unitario",
        "inspecao": inspection,
        "perfil": profile,
        "resumo": {
            "total": len(normalized_details),
            "sucessos": effective_successes,
            "bloqueados": blocked_count,
            "falhas": failure_count,
            "executados": execution_successes + execution_failures,
        },
        "arquivos_gerados": generated_files,
        "detalhes": normalized_details,
        "bloqueios": [
            {
                "codigo": "ARTEFATO_BLOQUEADO",
                "mensagem": detail.get("mensagem")
                or detail.get("motivo")
                or "Artefato bloqueado.",
            }
            for detail in normalized_details
            if detail.get("status") == "bloqueado"
        ],
    }
