"""Bootstrap do benchmark BigCodeBench — reutiliza o do HumanEval.

`prepare_environment` fixa `sys.path`, `.env`, provider LiteLLM e o workspace do
coder ANTES de qualquer import do agente. O módulo do humaneval resolve a raiz do
repositório pela posição do arquivo (`parents[3]`), que é idêntica aqui.
"""

from __future__ import annotations

from benchmarks.coding_review.humaneval.bootstrap import (
    adk_dir,
    prepare_environment,
    repo_root,
)

__all__ = ["adk_dir", "prepare_environment", "repo_root"]
