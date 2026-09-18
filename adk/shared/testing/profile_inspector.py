"""Inspeção determinística comum aos três níveis de teste."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable

from .test_profiles import TestProfile, TestProfileRegistry
from .unit_profiles import (
    UNIT_TEST_PROFILES,
    get_unit_test_profile,
    resolve_unit_test_profile,
)

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
    ".vscode",
    "__pycache__",
}
_MAX_FILES = 5_000
_MAX_CONFIG_BYTES = 1_000_000


def _blocked_result(
    test_type: str,
    project_root: Path,
    code: str,
    message: str,
    *,
    evidence: list[str] | None = None,
    sources: list[str] | None = None,
) -> dict:
    return {
        "status": "bloqueado",
        "tipo_teste": test_type,
        "projeto": str(project_root),
        "perfil": None,
        "confianca": 0.0,
        "evidencias": evidence or [],
        "arquivos_fonte": sources or [],
        "bloqueios": [{"codigo": code, "mensagem": message}],
    }


def _project_files(project_root: Path) -> list[Path]:
    if not project_root.is_dir():
        return []
    files: list[Path] = []
    for current_root, directories, filenames in os.walk(project_root):
        directories[:] = [
            name for name in directories if name.casefold() not in _IGNORED_DIRS
        ]
        for filename in filenames:
            path = Path(current_root) / filename
            if path.is_symlink() or not path.is_file():
                continue
            files.append(path)
            if len(files) >= _MAX_FILES:
                return files
    return files


def _profile_score(
    profile: TestProfile,
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
    if registry.test_type == "unitario":
        return inspect_unit_test_project(
            project_root,
            declared_files=declared_files or (),
            declared_stack=declared_stack,
        )
    root = project_root.expanduser().resolve()
    declared = declared_files or []
    if not root.is_dir():
        return _blocked_result(
            registry.test_type,
            root,
            "PROJETO_INEXISTENTE",
            "O workspace do projeto não existe ou não é um diretório.",
        )
    if len(registry) == 0:
        code = f"CATALOGO_{registry.test_type.upper()}_VAZIO"
        return _blocked_result(
            registry.test_type,
            root,
            code,
            (
                f"A base de testes de {registry.test_type} está pronta, mas ainda "
                "não possui perfis de stack registrados."
            ),
        )

    files = _project_files(root)
    candidates: list[tuple[int, TestProfile, list[str], list[str]]] = []
    declared_matches = registry.resolve(declared_stack)
    if declared_stack and not declared_matches:
        return _blocked_result(
            registry.test_type,
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
        return _blocked_result(
            registry.test_type,
            root,
            "PERFIL_NAO_IDENTIFICADO",
            "Nenhum perfil registrado corresponde às evidências do projeto.",
        )
    candidates.sort(key=lambda item: (-item[0], item[1].profile_id))
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        tied = [
            item[1].profile_id for item in candidates if item[0] == candidates[0][0]
        ]
        return _blocked_result(
            registry.test_type,
            root,
            "PERFIL_AMBIGUO",
            "Mais de um perfil possui a mesma confiança: " + ", ".join(tied),
        )

    score, profile, evidence, sources = candidates[0]
    if not profile.implemented or not profile.generator or not profile.executor:
        result = _blocked_result(
            registry.test_type,
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


def _read_small_text(path: Path) -> str:
    try:
        if path.stat().st_size > _MAX_CONFIG_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _node_unit_profile(
    package_files: list[Path], names: set[str]
) -> tuple[str, list[str]]:
    for prefix, profile_id in (
        ("vitest.config.", "node-vitest"),
        ("jest.config.", "node-jest"),
        (".mocharc.", "node-mocha"),
    ):
        if any(name.startswith(prefix) for name in names):
            return profile_id, [f"config:{profile_id}"]

    for package_file in package_files:
        try:
            package = json.loads(_read_small_text(package_file))
        except json.JSONDecodeError, TypeError:
            continue
        dependencies: dict[str, object] = {}
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            value = package.get(key, {}) if isinstance(package, dict) else {}
            if isinstance(value, dict):
                dependencies.update(
                    {str(name).casefold(): version for name, version in value.items()}
                )
        scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
        script_text = (
            " ".join(str(value) for value in scripts.values()).casefold()
            if isinstance(scripts, dict)
            else ""
        )
        for marker, profile_id in (
            ("vitest", "node-vitest"),
            ("jest", "node-jest"),
            ("mocha", "node-mocha"),
        ):
            if marker in dependencies or marker in script_text:
                return profile_id, [f"package.json:{marker}"]
        if "node --test" in script_text or "node --experimental-test" in script_text:
            return "node-node-test", ["package.json:node-test"]
    return "node-unconfigured", ["package.json:framework-ausente"]


def _unit_candidates(
    files: list[Path], declared_files: Iterable[str]
) -> dict[str, dict]:
    names = {path.name.casefold() for path in files}
    declared_names = {
        Path(str(name).replace("\\", "/")).name.casefold()
        for name in declared_files
        if str(name).strip()
    }
    all_names = names | declared_names
    suffix_counts: dict[str, int] = defaultdict(int)
    for path in files:
        suffix_counts[path.suffix.casefold()] += 1
    for name in declared_names:
        suffix_counts[Path(name).suffix.casefold()] += 1
    candidates: dict[str, dict] = {}

    def add(profile_id: str, score: int, evidence: list[str]) -> None:
        current = candidates.setdefault(profile_id, {"score": 0, "evidence": []})
        current["score"] += score
        current["evidence"].extend(evidence)

    python_markers = {
        "pyproject.toml",
        "pytest.ini",
        "requirements.txt",
        "setup.cfg",
        "setup.py",
    }
    python_hits = sorted(all_names & python_markers)
    python_sources = suffix_counts.get(".py", 0)
    if python_hits or python_sources:
        add(
            "python-pytest",
            (8 if python_hits else 0) + min(python_sources, 5),
            [f"marker:{name}" for name in python_hits]
            + ([f"source:.py({python_sources})"] if python_sources else []),
        )

    node_suffixes = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")
    node_sources = sum(suffix_counts.get(suffix, 0) for suffix in node_suffixes)
    package_files = [path for path in files if path.name.casefold() == "package.json"]
    if "package.json" in all_names or node_sources:
        profile_id, evidence = _node_unit_profile(package_files, all_names)
        add(
            profile_id,
            (8 if "package.json" in all_names else 0) + min(node_sources, 5),
            evidence + ([f"source:node({node_sources})"] if node_sources else []),
        )

    java_markers = {"pom.xml", "build.gradle", "build.gradle.kts"}
    java_sources = suffix_counts.get(".java", 0)
    if java_sources:
        java_hits = sorted(all_names & java_markers)
        add(
            "java-junit",
            (8 if java_hits else 0) + min(java_sources, 5),
            [f"marker:{name}" for name in java_hits]
            + [f"source:.java({java_sources})"],
        )

    go_sources = suffix_counts.get(".go", 0)
    if "go.mod" in all_names or go_sources:
        add(
            "go-testing",
            (8 if "go.mod" in all_names else 0) + min(go_sources, 5),
            (["marker:go.mod"] if "go.mod" in all_names else [])
            + ([f"source:.go({go_sources})"] if go_sources else []),
        )
    return candidates


def inspect_unit_test_project(
    project_root: Path,
    *,
    declared_files: Iterable[str] = (),
    declared_stack: str = "",
) -> dict:
    """Seleciona um perfil unitário usando o mesmo núcleo de inspeção."""
    root = project_root.expanduser().resolve()
    files = _project_files(root)
    candidates = _unit_candidates(files, declared_files)
    suffixes = {
        suffix
        for profile in UNIT_TEST_PROFILES.values()
        for suffix in profile.source_suffixes
    }
    relative_sources = [
        path.relative_to(root).as_posix()
        for path in files
        if path.suffix.casefold() in suffixes
    ]

    if declared_stack.strip():
        profile = resolve_unit_test_profile(declared_stack)
        if profile is None:
            return _blocked_result(
                "unitario",
                root,
                "STACK_DECLARADA_DESCONHECIDA",
                f"A stack declarada '{declared_stack}' não pertence ao catálogo do Coder.",
                evidence=[f"stack_declarada:{declared_stack}"],
                sources=relative_sources,
            )
        if profile.profile_id == "node-unconfigured":
            configured = [
                (profile_id, data)
                for profile_id, data in candidates.items()
                if profile_id.startswith("node-") and profile_id != "node-unconfigured"
            ]
            if configured:
                profile = get_unit_test_profile(
                    max(configured, key=lambda item: (item[1]["score"], item[0]))[0]
                )
        blockers = (
            []
            if profile.implemented
            else [
                {
                    "codigo": "PERFIL_NAO_IMPLEMENTADO",
                    "mensagem": "A família Node foi declarada, mas o Coder não publicou qual runner de teste utiliza.",
                }
            ]
        )
        return {
            "status": "suportado" if profile.implemented else "bloqueado",
            "tipo_teste": "unitario",
            "projeto": str(root),
            "perfil": profile.to_dict(),
            "confianca": 1.0,
            "evidencias": [f"stack_declarada:{declared_stack}"],
            "arquivos_fonte": relative_sources,
            "bloqueios": blockers,
        }

    if not candidates:
        return _blocked_result(
            "unitario",
            root,
            "STACK_NAO_IDENTIFICADA",
            "Nenhuma das stacks publicadas pelo Coder foi identificada.",
            sources=relative_sources,
        )
    ordered = sorted(candidates.items(), key=lambda item: (-item[1]["score"], item[0]))
    best_id, best = ordered[0]
    if len(ordered) > 1 and ordered[1][1]["score"] == best["score"]:
        tied = [
            profile_id for profile_id, data in ordered if data["score"] == best["score"]
        ]
        return _blocked_result(
            "unitario",
            root,
            "STACK_AMBIGUA",
            f"Mais de um perfil possui a mesma evidência: {', '.join(tied)}.",
            evidence=sorted(
                {
                    item
                    for profile_id in tied
                    for item in candidates[profile_id]["evidence"]
                }
            ),
            sources=relative_sources,
        )
    profile = get_unit_test_profile(best_id)
    if not profile.implemented:
        result = _blocked_result(
            "unitario",
            root,
            "PERFIL_NAO_IMPLEMENTADO",
            "O projeto Node não declara qual runner unitário utiliza.",
            evidence=sorted(set(best["evidence"])),
            sources=relative_sources,
        )
        result["perfil"] = profile.to_dict()
        return result
    return {
        "status": "suportado",
        "tipo_teste": "unitario",
        "projeto": str(root),
        "perfil": profile.to_dict(),
        "confianca": min(0.99, round(0.5 + (best["score"] / 20), 2)),
        "evidencias": sorted(set(best["evidence"])),
        "arquivos_fonte": relative_sources,
        "bloqueios": [],
    }


__all__ = ["inspect_test_project", "inspect_unit_test_project"]
