"""Infraestrutura compartilhada para geração de testes multistack."""

from .coder_stack import load_coder_stack, resolve_coder_stack
from .e2e_profiles import E2E_TEST_PROFILES
from .integration_profiles import INTEGRATION_TEST_PROFILES
from .integration_adapters import (
    build_integration_command,
    detect_node_integration_framework,
    execute_integration_adapter,
)
from .profile_inspector import inspect_test_project
from .profile_orchestration import inspect_request, prepare_request
from .project_inspector import inspect_unit_test_project
from .result_normalization import (
    normalize_e2e_result,
    normalize_integration_execution,
    normalize_integration_result,
    parse_integration_counts,
)
from .test_profiles import StackTestProfile, TestProfileRegistry
from .unit_profiles import (
    UNIT_TEST_PROFILES,
    UnitTestProfile,
    get_unit_test_profile,
    list_unit_test_profiles,
    resolve_unit_test_profile,
)
from .unit_runner import executar_teste_unitario

__all__ = [
    "E2E_TEST_PROFILES",
    "INTEGRATION_TEST_PROFILES",
    "StackTestProfile",
    "TestProfileRegistry",
    "UNIT_TEST_PROFILES",
    "UnitTestProfile",
    "build_integration_command",
    "detect_node_integration_framework",
    "execute_integration_adapter",
    "get_unit_test_profile",
    "executar_teste_unitario",
    "inspect_request",
    "inspect_test_project",
    "inspect_unit_test_project",
    "list_unit_test_profiles",
    "load_coder_stack",
    "normalize_e2e_result",
    "normalize_integration_execution",
    "normalize_integration_result",
    "parse_integration_counts",
    "resolve_unit_test_profile",
    "resolve_coder_stack",
    "prepare_request",
]
