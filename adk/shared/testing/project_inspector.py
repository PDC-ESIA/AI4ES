"""Inspeção determinística das stacks publicadas pelo Coder."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .unit_profiles import (
    UNIT_TEST_PROFILES,
    get_unit_test_profile,
    resolve_unit_test_profile,
)

_IGNORED_DIRS = {
    ".git",
    ".idea",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
}
_MAX_FILES = 4_000
_MAX_CONFIG_BYTES = 1_000_000
_SOURCE_SUFFIXES = {
    suffix
    for profile in UNIT_TEST_PROFILES.values()
    for suffix in profile.source_suffixes
}


def _walk_project_files(project_root: Path) -> list[Path]:
    files: list[Path] = []
    if not project_root.is_dir():
        return files
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


def _read_small_text(path: Path) -> str:
    try:
        if path.stat().st_size > _MAX_CONFIG_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _node_profile(package_files: list[Path], names: set[str]) -> tuple[str, list[str]]:
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


def _candidate_profiles(
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
        profile_id, evidence = _node_profile(package_files, all_names)
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


def _blocked(
    root: Path,
    relative_sources: list[str],
    code: str,
    message: str,
    *,
    evidence: list[str] | None = None,
) -> dict:
    return {
        "status": "bloqueado",
        "tipo_teste": "unitario",
        "projeto": str(root),
        "perfil": None,
        "confianca": 0.0,
        "evidencias": evidence or [],
        "arquivos_fonte": relative_sources,
        "bloqueios": [{"codigo": code, "mensagem": message}],
    }


def inspect_unit_test_project(
    project_root: Path,
    *,
    declared_files: Iterable[str] = (),
    declared_stack: str = "",
) -> dict:
    """Seleciona um perfil conhecido sem interpretação por LLM."""
    root = project_root.resolve()
    files = _walk_project_files(root)
    candidates = _candidate_profiles(files, declared_files)
    relative_sources = [
        path.relative_to(root).as_posix()
        for path in files
        if path.suffix.casefold() in _SOURCE_SUFFIXES
    ]

    if declared_stack.strip():
        profile = resolve_unit_test_profile(declared_stack)
        if profile is None:
            return _blocked(
                root,
                relative_sources,
                "STACK_DECLARADA_DESCONHECIDA",
                f"A stack declarada '{declared_stack}' não pertence ao catálogo do Coder.",
                evidence=[f"stack_declarada:{declared_stack}"],
            )
        if profile.profile_id == "node-unconfigured":
            configured = [
                (profile_id, data)
                for profile_id, data in candidates.items()
                if profile_id.startswith("node-") and profile_id != "node-unconfigured"
            ]
            if configured:
                detected_id, _ = max(
                    configured,
                    key=lambda item: (item[1]["score"], item[0]),
                )
                profile = get_unit_test_profile(detected_id)

        blockers = (
            []
            if profile.implemented
            else [
                {
                    "codigo": "PERFIL_NAO_IMPLEMENTADO",
                    "mensagem": (
                        "A família Node foi declarada, mas o Coder não publicou "
                        "qual runner de teste utiliza."
                    ),
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
        return _blocked(
            root,
            relative_sources,
            "STACK_NAO_IDENTIFICADA",
            "Nenhuma das stacks publicadas pelo Coder foi identificada.",
        )

    ordered = sorted(candidates.items(), key=lambda item: (-item[1]["score"], item[0]))
    best_id, best = ordered[0]
    if len(ordered) > 1 and ordered[1][1]["score"] == best["score"]:
        tied = [
            profile_id for profile_id, data in ordered if data["score"] == best["score"]
        ]
        return _blocked(
            root,
            relative_sources,
            "STACK_AMBIGUA",
            f"Mais de um perfil possui a mesma evidência: {', '.join(tied)}.",
            evidence=sorted(
                {
                    item
                    for profile_id in tied
                    for item in candidates[profile_id]["evidence"]
                }
            ),
        )

    profile = get_unit_test_profile(best_id)
    if not profile.implemented:
        result = _blocked(
            root,
            relative_sources,
            "PERFIL_NAO_IMPLEMENTADO",
            "O projeto Node não declara qual runner unitário utiliza.",
            evidence=sorted(set(best["evidence"])),
        )
        result["perfil"] = profile.to_dict()
        return result

    confidence = min(0.99, round(0.5 + (best["score"] / 20), 2))
    return {
        "status": "suportado",
        "tipo_teste": "unitario",
        "projeto": str(root),
        "perfil": profile.to_dict(),
        "confianca": confidence,
        "evidencias": sorted(set(best["evidence"])),
        "arquivos_fonte": relative_sources,
        "bloqueios": [],
    }
