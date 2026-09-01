"""Inspeção genérica orientada por perfis para integração e E2E."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from .test_profiles import StackTestProfile, TestProfileRegistry

_IGNORED_DIRS = {
    ".build",
    ".git",
    ".gradle",
    ".idea",
    ".pytest_cache",
    ".venv",
    "bin",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "obj",
    "pods",
    "target",
    "vendor",
}


def _blocked(
    registry: TestProfileRegistry,
    project_root: Path,
    code: str,
    message: str,
    *,
    evidence: list[str] | None = None,
) -> dict:
    return {
        "status": "bloqueado",
        "tipo_teste": registry.test_type,
        "projeto": str(project_root),
        "perfil": None,
        "confianca": 0.0,
        "evidencias": evidence or [],
        "arquivos_fonte": [],
        "bloqueios": [{"codigo": code, "mensagem": message}],
    }


def _project_files(project_root: Path) -> list[Path]:
    if not project_root.is_dir():
        return []
    files: list[Path] = []
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(project_root).parts[:-1]
        if any(part.casefold() in _IGNORED_DIRS for part in relative_parts):
            continue
        files.append(path)
        if len(files) >= 5_000:
            break
    return files


def _profile_score(
    profile: StackTestProfile,
    project_root: Path,
    files: list[Path],
    declared_files: list[str],
) -> tuple[int, list[str], list[str]]:
    evidence: list[str] = []
    sources: list[str] = []
    score = 0

    all_names = [path.relative_to(project_root).as_posix() for path in files]
    all_names.extend(name.replace("\\", "/") for name in declared_files)
    for marker in profile.marker_files:
        matches = [
            name
            for name in all_names
            if fnmatch(name, marker) or fnmatch(Path(name).name, marker)
        ]
        if matches:
            score += 4
            evidence.append(f"marcador:{marker}")

    suffixes = {suffix.casefold() for suffix in profile.source_suffixes}
    for name in all_names:
        if Path(name).suffix.casefold() in suffixes:
            sources.append(name)
    if sources:
        score += 1
        evidence.append(f"fontes:{len(set(sources))}")
    return score, evidence, sorted(set(sources))


def inspect_test_project(
    project_root: Path,
    registry: TestProfileRegistry,
    *,
    declared_files: list[str] | None = None,
    declared_stack: str = "",
) -> dict:
    """Seleciona um perfil registrado sem embutir conhecimento de stack."""
    root = project_root.expanduser().resolve()
    declared = declared_files or []
    if not root.is_dir():
        return _blocked(
            registry,
            root,
            "PROJETO_INEXISTENTE",
            "O workspace do projeto não existe ou não é um diretório.",
        )
    if len(registry) == 0:
        code = f"CATALOGO_{registry.test_type.upper()}_VAZIO"
        return _blocked(
            registry,
            root,
            code,
            (
                f"A base de testes de {registry.test_type} está pronta, mas ainda "
                "não possui perfis de stack registrados."
            ),
        )

    files = _project_files(root)
    candidates: list[tuple[int, StackTestProfile, list[str], list[str]]] = []
    declared_matches = registry.resolve(declared_stack)
    if declared_stack and not declared_matches:
        return _blocked(
            registry,
            root,
            "STACK_DECLARADA_NAO_REGISTRADA",
            f"A stack declarada '{declared_stack}' não possui perfil registrado.",
        )

    allowed = set(declared_matches) if declared_matches else set(registry.values())
    for profile in allowed:
        score, evidence, sources = _profile_score(profile, root, files, declared)
        if profile in declared_matches:
            score += 10
            evidence.insert(0, f"stack_declarada:{declared_stack}")
        if score:
            candidates.append((score, profile, evidence, sources))

    if not candidates:
        return _blocked(
            registry,
            root,
            "PERFIL_NAO_IDENTIFICADO",
            "Nenhum perfil registrado corresponde às evidências do projeto.",
        )
    candidates.sort(key=lambda item: (-item[0], item[1].profile_id))
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        tied = [
            item[1].profile_id for item in candidates if item[0] == candidates[0][0]
        ]
        return _blocked(
            registry,
            root,
            "PERFIL_AMBIGUO",
            "Mais de um perfil possui a mesma confiança: " + ", ".join(tied),
        )

    score, profile, evidence, sources = candidates[0]
    if not profile.implemented or not profile.generator or not profile.executor:
        result = _blocked(
            registry,
            root,
            "PERFIL_NAO_IMPLEMENTADO",
            f"O perfil '{profile.profile_id}' foi declarado, mas seu adaptador está incompleto.",
            evidence=evidence,
        )
        result["perfil"] = profile.to_dict()
        result["arquivos_fonte"] = sources
        return result

    return {
        "status": "suportado",
        "tipo_teste": registry.test_type,
        "projeto": str(root),
        "perfil": profile.to_dict(),
        "confianca": min(1.0, score / 15),
        "evidencias": evidence,
        "arquivos_fonte": sources,
        "bloqueios": [],
    }
