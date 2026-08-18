"""Subagente receive_requirements — recebe artefatos de requisito e gera testes pytest.

Re-exporta os símbolos públicos e os usados por testes/consumidores externos
(workflow_qa, tests/unit) para preservar os caminhos de import existentes
após a divisão do antigo arquivo único em módulos por responsabilidade.
"""

from .agent import agent
from .io import _doubt_dir, _tests_dir
from .orchestration import receber_requisitos
from .sanitizer import _validar_e_sanitizar_codigo

__all__ = [
    "agent",
    "receber_requisitos",
    "_tests_dir",
    "_doubt_dir",
    "_validar_e_sanitizar_codigo",
]
