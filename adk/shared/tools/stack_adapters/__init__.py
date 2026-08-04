"""Adapters de stack do harness de execução.

Cada adapter encapsula o que é específico de uma stack (reivindicação por
keyword/manifesto + execução de testes no container). O harness genérico só
conhece a interface (`StackAdapter`) e a resolução em camadas (`resolver_stack`).
"""

from .base import ExecNoContainer, FileMarker, ResultadoTestes, StackAdapter
from .python_adapter import PythonAdapter
from .registry import ResolucaoStack, adapters_registrados, resolver_stack

__all__ = [
    "ExecNoContainer",
    "FileMarker",
    "ResultadoTestes",
    "StackAdapter",
    "PythonAdapter",
    "ResolucaoStack",
    "adapters_registrados",
    "resolver_stack",
]
