"""Entrada e saída comuns dos agentes de integração e E2E por perfis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shared.workspace import get_agent_workspace, get_workspace_root

from .coder_stack import load_coder_stack
from .profile_inspector import inspect_test_project
from .test_profiles import TestProfileRegistry


def resolve_managed_project_root(workspace_project: str) -> Path:
    """Resolve o projeto sem permitir fuga do workspace gerenciado."""
    workspace_root = get_workspace_root().resolve()
    if workspace_project and workspace_project.strip():
        received = Path(workspace_project.strip()).expanduser()
        candidate = received if received.is_absolute() else workspace_root / received
        candidate = candidate.resolve()
    else:
        candidate = get_agent_workspace("cr_coder").resolve()
    if candidate != workspace_root and not candidate.is_relative_to(workspace_root):
        raise ValueError(
            "workspace_projeto deve permanecer dentro do workspace gerenciado."
        )
    return candidate


def parse_declared_files(value: str) -> list[str]:
    """Normaliza uma lista JSON de nomes ou descritores de arquivo."""
    try:
        raw = json.loads(value or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(f"arquivos_declarados_json inválido: {exc}") from exc
    if not isinstance(raw, list):
        raise ValueError("arquivos_declarados_json deve ser uma lista JSON.")
    names: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
        elif isinstance(item, dict):
            name = item.get("path") or item.get("nome") or item.get("filename")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
    return names


def load_artifacts(value: str) -> list[dict[str, Any]]:
    """Carrega um artefato ou uma lista de artefatos sem alterar seu conteúdo."""
    try:
        raw = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"artefatos_json inválido: {exc}") from exc
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
        raise ValueError("artefatos_json deve conter um objeto ou lista de objetos.")
    return raw


def artifact_file_names(artifacts: list[dict[str, Any]]) -> list[str]:
    """Extrai somente nomes de arquivos usados como evidência de inspeção."""
    names: list[str] = []
    for artifact in artifacts:
        support_files = artifact.get("arquivos_apoio", [])
        if not isinstance(support_files, list):
            continue
        for item in support_files:
            if isinstance(item, str) and item.strip():
                names.append(item.strip())
            elif isinstance(item, dict):
                name = item.get("path") or item.get("nome") or item.get("filename")
                if isinstance(name, str) and name.strip():
                    names.append(name.strip())
    return names


def blocked_test_result(
    test_type: str, code: str, message: str, *, inspection: dict | None = None
) -> dict:
    """Cria o envelope estável compartilhado pelos dois agentes."""
    blockers = inspection.get("bloqueios", []) if inspection else []
    if not blockers:
        blockers = [{"codigo": code, "mensagem": message}]
    return {
        "status": "bloqueado",
        "tipo_teste": test_type,
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
        "bloqueios": blockers,
    }


def inspect_request(
    registry: TestProfileRegistry,
    workspace_project: str = "",
    declared_files_json: str = "[]",
    declared_stack: str = "",
) -> dict:
    """Prepara uma inspeção usando apenas o catálogo fornecido."""
    try:
        project_root = resolve_managed_project_root(workspace_project)
        declared_files = parse_declared_files(declared_files_json)
    except ValueError as exc:
        return {
            "status": "bloqueado",
            "tipo_teste": registry.test_type,
            "projeto": None,
            "perfil": None,
            "confianca": 0.0,
            "evidencias": [],
            "arquivos_fonte": [],
            "bloqueios": [
                {"codigo": "ENTRADA_INSPECAO_INVALIDA", "mensagem": str(exc)}
            ],
        }
    effective_stack = declared_stack or load_coder_stack()
    return inspect_test_project(
        project_root,
        registry,
        declared_files=declared_files,
        declared_stack=effective_stack,
    )


def prepare_request(
    registry: TestProfileRegistry,
    artifacts_json: str,
    workspace_project: str = "",
    declared_stack: str = "",
) -> dict:
    """Valida a entrada e seleciona o perfil antes de qualquer geração."""
    try:
        artifacts = load_artifacts(artifacts_json)
        project_root = resolve_managed_project_root(workspace_project)
    except ValueError as exc:
        return blocked_test_result(
            registry.test_type,
            "ENTRADA_TESTE_INVALIDA",
            str(exc),
        )
    effective_stack = declared_stack or load_coder_stack()
    inspection = inspect_test_project(
        project_root,
        registry,
        declared_files=artifact_file_names(artifacts),
        declared_stack=effective_stack,
    )
    if inspection["status"] != "suportado":
        return blocked_test_result(
            registry.test_type,
            "PERFIL_INDISPONIVEL",
            f"Nenhum perfil de {registry.test_type} está disponível.",
            inspection=inspection,
        )
    return {
        "status": "pronto",
        "tipo_teste": registry.test_type,
        "inspecao": inspection,
        "perfil": inspection["perfil"],
        "resumo": {
            "total": len(artifacts),
            "sucessos": 0,
            "bloqueados": 0,
            "falhas": 0,
            "executados": 0,
        },
        "arquivos_gerados": [],
        "detalhes": [],
        "bloqueios": [],
    }
