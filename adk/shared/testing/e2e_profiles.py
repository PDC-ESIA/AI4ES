"""Perfis E2E limitados às famílias publicadas pelo Coder."""

from .test_profiles import StackTestProfile, TestProfileRegistry

_NODE_SUFFIXES = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")


def _profile(
    profile_id: str,
    stack: str,
    source_suffixes: tuple[str, ...],
    marker_files: tuple[str, ...],
    aliases: tuple[str, ...] = (),
) -> StackTestProfile:
    return StackTestProfile(
        profile_id=profile_id,
        test_type="e2e",
        stack=stack,
        framework="playwright-typescript",
        source_suffixes=source_suffixes,
        marker_files=marker_files,
        test_file_pattern="<fluxo>.spec.ts",
        generator="playwright_typescript_generator",
        executor="playwright_runner",
        aliases=aliases,
        implemented=True,
    )


E2E_TEST_PROFILES = TestProfileRegistry(
    "e2e",
    (
        _profile(
            "python-e2e",
            "python",
            (".py",),
            ("pyproject.toml", "requirements.txt"),
            ("fastapi", "python-fastapi", "python/fastapi"),
        ),
        _profile(
            "node-e2e",
            "node",
            _NODE_SUFFIXES,
            ("package.json",),
            (
                "javascript",
                "typescript",
                "javascript-typescript",
                "express",
                "node-express",
                "node/express",
            ),
        ),
        _profile(
            "java-e2e",
            "java",
            (".java",),
            ("pom.xml", "build.gradle", "build.gradle.kts"),
            ("spring", "java-spring", "java/spring"),
        ),
        _profile(
            "go-e2e",
            "go",
            (".go",),
            ("go.mod",),
            ("golang",),
        ),
    ),
)

__all__ = ["E2E_TEST_PROFILES"]
