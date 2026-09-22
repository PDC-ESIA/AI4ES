"""Perfis de integração limitados às famílias publicadas pelo Coder."""

from .test_profiles import StackTestProfile, TestProfileRegistry

_NODE_SUFFIXES = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")

INTEGRATION_TEST_PROFILES = TestProfileRegistry(
    "integracao",
    (
        StackTestProfile(
            profile_id="python-integration",
            test_type="integracao",
            stack="python",
            framework="pytest",
            source_suffixes=(".py",),
            marker_files=(
                "pyproject.toml",
                "pytest.ini",
                "requirements.txt",
                "setup.cfg",
            ),
            test_file_pattern="test_<componente>_integration.py",
            generator="pytest_integration_generator",
            executor="pytest_integration_runner",
            aliases=("fastapi", "python-fastapi", "python/fastapi"),
            implemented=True,
        ),
        StackTestProfile(
            profile_id="node-integration",
            test_type="integracao",
            stack="node",
            framework="project-declared",
            source_suffixes=_NODE_SUFFIXES,
            marker_files=("package.json",),
            test_file_pattern="<componente>.integration.test.ts",
            generator="node_integration_generator",
            executor="node_integration_runner",
            aliases=(
                "javascript",
                "typescript",
                "javascript-typescript",
                "express",
                "node-express",
                "node/express",
            ),
            implemented=True,
        ),
        StackTestProfile(
            profile_id="java-integration",
            test_type="integracao",
            stack="java",
            framework="junit",
            source_suffixes=(".java",),
            marker_files=("pom.xml", "build.gradle", "build.gradle.kts"),
            test_file_pattern="<Componente>IntegrationTest.java",
            generator="junit_integration_generator",
            executor="junit_integration_runner",
            aliases=("spring", "java-spring", "java/spring"),
            implemented=True,
        ),
        StackTestProfile(
            profile_id="go-integration",
            test_type="integracao",
            stack="go",
            framework="testing",
            source_suffixes=(".go",),
            marker_files=("go.mod",),
            test_file_pattern="<componente>_integration_test.go",
            generator="go_integration_generator",
            executor="go_integration_runner",
            aliases=("golang",),
            implemented=True,
        ),
    ),
)

__all__ = ["INTEGRATION_TEST_PROFILES"]
