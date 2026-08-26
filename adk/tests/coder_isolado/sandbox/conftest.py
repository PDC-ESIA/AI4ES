"""conftest.py — Camada 4 (sandbox e2e, escopo coder_isolado).

`workspace_fixture` e `_requer_llm_real` vêm do ancestral
`tests/coder_isolado/conftest.py` (mesma decisão documentada lá: fixtures
compartilhadas entre `evals/` e `sandbox/` vivem no conftest do ancestral
comum, não em `tests/fixtures/` — pytest já descobre fixtures de qualquer
conftest.py entre a raiz e o teste sem precisar de import, o que
`tests/fixtures/` (um pacote Python comum, não escaneado pelo pytest)
exigiria de qualquer forma). Este arquivo só acrescenta o que é específico
do e2e: semear os artefatos mínimos que `cr_context_engineer` exige para
não abortar em Doubt Artifact.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest


@pytest.fixture
def seed_requirements_e_design() -> Callable[[Path, str, str], None]:
    """Factory: escreve o RF e a análise técnica mínimos que o pipeline exige.

    `cr_context_engineer` aborta com Doubt Artifact sem: pelo menos 1
    `requirements/RFs/RF-*.md` (via `tool_ler_requirements`) e pelo menos 1
    `design/analise_tecnica_*.md` (via `tool_ler_design`). Uso::

        def test_x(workspace_fixture, seed_requirements_e_design):
            seed_requirements_e_design(workspace_fixture, texto_rf, texto_design)
    """

    def _seed(workspace: Path, texto_rf: str, texto_design: str) -> None:
        rf_dir = workspace / "requirements" / "RFs"
        rf_dir.mkdir(parents=True, exist_ok=True)
        (rf_dir / "RF-001.md").write_text(texto_rf, encoding="utf-8")

        design_dir = workspace / "design"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "analise_tecnica_RF-001.md").write_text(texto_design, encoding="utf-8")

    return _seed
