"""Categorias de falha do grading do BigCodeBench (módulo leve, sem dependências)."""

from __future__ import annotations

# Categorias de falha.
PASSED = "passed"
MISSING_DEPENDENCY = "missing_dependency"  # ModuleNotFoundError
IMPORT_ERROR = "import_error"  # ImportError (símbolo inexistente no módulo)
API_MISUSE = "api_misuse"  # AttributeError/TypeError ligados a API de biblioteca
LOGIC = "logic"  # AssertionError nos testes oficiais
RUNTIME_ERROR = "runtime_error"  # demais exceções em tempo de execução
SYNTAX = "syntax"
TIMEOUT = "timeout"
NO_SOLUTION = "no_solution"
GENERATION_ERROR = "generation_error"
SANDBOX_ERROR = "sandbox_error"  # falha de infraestrutura (Docker), não do modelo

# Agrupamento: o que a issue chama de "falhas por import/dependência" vs "lógica".
LIBRARY_FAILURES = (MISSING_DEPENDENCY, IMPORT_ERROR, API_MISUSE)
LOGIC_FAILURES = (LOGIC, RUNTIME_ERROR)
OTHER_FAILURES = (SYNTAX, TIMEOUT, NO_SOLUTION, GENERATION_ERROR, SANDBOX_ERROR)
NOT_RUN = "not_run"  # tarefa sem resultado (ex.: shard interrompido antes dela)

# Desfechos que não são do modelo (LLM/Docker) ou ainda inexistentes: não entram
# no checkpoint nem no pass@1 — ficam pendentes e são refeitos ao retomar o run.
PENDING_CATEGORIES = (GENERATION_ERROR, SANDBOX_ERROR, NOT_RUN)
