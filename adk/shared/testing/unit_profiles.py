"""Perfis unitários limitados às stacks publicadas pelo Coder."""

from __future__ import annotations

from .test_profiles import TestProfile, TestProfileRegistry, UnitTestProfile


_NODE_SUFFIXES = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")

_PROFILES = (
    TestProfile(
        profile_id="python-pytest",
        test_type="unitario",
        stack="python",
        framework="pytest",
        source_suffixes=(".py",),
        marker_files=("pyproject.toml", "pytest.ini", "requirements.txt", "setup.cfg"),
        test_file_pattern="test_<componente>.py",
        coverage_format="coverage.py-json",
        executor="pytest_runner",
        implemented=True,
    ),
    TestProfile(
        profile_id="node-vitest",
        test_type="unitario",
        stack="javascript-typescript",
        framework="vitest",
        source_suffixes=_NODE_SUFFIXES,
        marker_files=("package.json", "vitest.config.js", "vitest.config.ts"),
        test_file_pattern="<componente>.test.ts",
        coverage_format="lcov",
        executor="vitest_runner",
        implemented=True,
    ),
    TestProfile(
        profile_id="node-jest",
        test_type="unitario",
        stack="javascript-typescript",
        framework="jest",
        source_suffixes=_NODE_SUFFIXES,
        marker_files=("package.json", "jest.config.js", "jest.config.ts"),
        test_file_pattern="<componente>.test.ts",
        coverage_format="lcov",
        executor="jest_runner",
        implemented=True,
    ),
    TestProfile(
        profile_id="node-node-test",
        test_type="unitario",
        stack="javascript-typescript",
        framework="node:test",
        source_suffixes=_NODE_SUFFIXES,
        marker_files=("package.json",),
        test_file_pattern="<componente>.test.js",
        coverage_format="node-v8",
        executor="node_test_runner",
        implemented=True,
    ),
    TestProfile(
        profile_id="node-mocha",
        test_type="unitario",
        stack="javascript-typescript",
        framework="mocha",
        source_suffixes=_NODE_SUFFIXES,
        marker_files=("package.json", ".mocharc.json", ".mocharc.js"),
        test_file_pattern="<componente>.test.js",
        coverage_format=None,
        executor="mocha_runner",
        implemented=True,
    ),
    TestProfile(
        profile_id="node-unconfigured",
        test_type="unitario",
        stack="javascript-typescript",
        framework="unconfigured",
        source_suffixes=_NODE_SUFFIXES,
        marker_files=("package.json",),
        test_file_pattern="<componente>.test.ts",
        coverage_format=None,
        executor=None,
        implemented=False,
    ),
    TestProfile(
        profile_id="java-junit",
        test_type="unitario",
        stack="java",
        framework="junit",
        source_suffixes=(".java",),
        marker_files=("pom.xml", "build.gradle", "build.gradle.kts"),
        test_file_pattern="<Componente>Test.java",
        coverage_format="jacoco-xml",
        executor="junit_runner",
        implemented=True,
    ),
    TestProfile(
        profile_id="go-testing",
        test_type="unitario",
        stack="go",
        framework="testing",
        source_suffixes=(".go",),
        marker_files=("go.mod",),
        test_file_pattern="<componente>_test.go",
        coverage_format="go-coverprofile",
        executor="go_test_runner",
        implemented=True,
    ),
)

UNIT_TEST_PROFILES = TestProfileRegistry("unitario", _PROFILES)

_ALIASES = {
    "python": "python-pytest",
    "fastapi": "python-pytest",
    "python-fastapi": "python-pytest",
    "python/fastapi": "python-pytest",
    "pytest": "python-pytest",
    "python-pytest": "python-pytest",
    "javascript": "node-unconfigured",
    "typescript": "node-unconfigured",
    "javascript-typescript": "node-unconfigured",
    "node": "node-unconfigured",
    "nodejs": "node-unconfigured",
    "node-express": "node-unconfigured",
    "node/express": "node-unconfigured",
    "express": "node-unconfigured",
    "vitest": "node-vitest",
    "node-vitest": "node-vitest",
    "jest": "node-jest",
    "node-jest": "node-jest",
    "node-test": "node-node-test",
    "node:test": "node-node-test",
    "node-node-test": "node-node-test",
    "mocha": "node-mocha",
    "node-mocha": "node-mocha",
    "java": "java-junit",
    "spring": "java-junit",
    "java-spring": "java-junit",
    "java/spring": "java-junit",
    "junit": "java-junit",
    "java-junit": "java-junit",
    "go": "go-testing",
    "golang": "go-testing",
    "go-testing": "go-testing",
}


def get_unit_test_profile(profile_id: str) -> UnitTestProfile:
    """Retorna um perfil pelo identificador canônico."""
    try:
        return UNIT_TEST_PROFILES[profile_id]
    except KeyError:
        raise ValueError(f"Perfil unitário desconhecido: '{profile_id}'.") from None


def resolve_unit_test_profile(value: str) -> UnitTestProfile | None:
    """Resolve linguagem, framework ou ID para um perfil conhecido."""
    normalized = (value or "").strip().casefold().replace("_", "-")
    profile_id = _ALIASES.get(normalized)
    return UNIT_TEST_PROFILES.get(profile_id) if profile_id else None


def list_unit_test_profiles() -> list[dict]:
    """Lista serializável usada por tools e documentação do agente."""
    return [profile.to_dict() for profile in _PROFILES]


__all__ = [
    "UNIT_TEST_PROFILES",
    "UnitTestProfile",
    "get_unit_test_profile",
    "list_unit_test_profiles",
    "resolve_unit_test_profile",
]
