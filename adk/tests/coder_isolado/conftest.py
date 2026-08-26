"""conftest.py — coder_isolado (escopo: só workflow_coding_review).

Fixtures usadas pelos testes de escopo coding_review movidos para cá na
reorganização por escopo de agente (ver `tests/README.md`). Implementações
herdadas do antigo conftest da Camada 2 (hoje `tests/integration/conftest.py`,
bem menor) — não duplicadas "por via das dúvidas": cada uma aqui é usada
por pelo menos um teste dentro de `tests/coder_isolado/`
(`trace_collector` por `trajetoria/test_trajetoria_harness_exemplo.py` e por
`trajetoria/test_trajetoria_convergencia_loop.py`).

Nenhum teste remanescente em `tests/integration/` usa estas fixtures (o
harness era exercitado só pelos arquivos que migraram para cá), por isso
foram removidas de lá em vez de mantidas + duplicadas.

Os fixtures `docker_mock`/`mock_response` (stubs de Docker/HTTP herdados do
harness pré-issue #370) foram removidos daqui: desde que
`trajetoria/test_trajetoria_harness_exemplo.py` passou a exercitar o harness
pós-#370 via manifesto `run.json` com `surface="command"` (perfil que não
sobe serviço nem faz healthcheck HTTP — ver `shared/execution/profile.py`),
nenhum teste da suíte os consome mais.

`workspace_fixture` e `_requer_llm_real` (adicionadas para as Camadas 3/4,
`evals/` e `sandbox/`) seguem a mesma lógica: `tests/integration/` também
define um `workspace_fixture` equivalente, mas é um galho IRMÃO desta
pasta na árvore de testes — o pytest só descobre fixtures subindo de um
teste até a raiz (`conftest.py` ancestrais), nunca atravessando para um
galho lateral. Importar de lá exigiria um `from tests.integration.conftest
import workspace_fixture` explícito em cada um dos 2 conftest.py filhos
(`evals/`, `sandbox/`) — mais indireção do que centralizar aqui, no
ancestral comum das duas pastas que realmente precisam dela. Por isso a
implementação é copiada (não importada) para este arquivo; a de
`tests/integration/conftest.py` permanece intacta e não utilizada lá.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shared.preflight import PreflightResult, ensure_llm_ready
from tests.fixtures.trace_helpers import TraceCollector


# ---------------------------------------------------------------------------
# Workspace isolado (compartilhado por evals/ e sandbox/)
# ---------------------------------------------------------------------------

@pytest.fixture
def workspace_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Workspace isolado por teste, substituindo `workspace_output` global.

    Cópia de `tests/integration/conftest.py::workspace_fixture` (ver
    docstring do módulo para o porquê de não ser importada de lá). Cria a
    raiz do workspace com o marker esperado por `shared.workspace` e aponta
    `WORKSPACE_OUTPUT_DIR` para dentro do `tmp_path` do teste.
    """
    from shared import workspace as _workspace_mod

    ws = tmp_path / "workspace_output"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / ".ai4se_workspace").write_text("marker", encoding="utf-8")

    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws))
    monkeypatch.setattr(_workspace_mod, "_DEFAULT_WORKSPACE", str(ws))
    return ws


# ---------------------------------------------------------------------------
# Gate de credencial real de LLM (Camadas 3/4 — evals/, sandbox/)
# ---------------------------------------------------------------------------

@pytest.fixture
async def _requer_llm_real() -> None:
    """Skip automático se não houver credencial real de LLM disponível.

    Requisitada EXPLICITAMENTE (não autouse) pelos testes que precisam de
    LLM real — basta listá-la como parâmetro do teste; o `pytest.skip`
    roda no setup da fixture, antes do corpo do teste executar. Ao
    contrário do `_stub_llm_preflight` autouse em `tests/conftest.py` (que
    só neutraliza `ensure_llm_ready` referenciado a partir de
    `src.agents.orchestrator.agent`), esta fixture importa
    `shared.preflight.ensure_llm_ready` diretamente — não é interceptada
    por aquele stub, o health-check aqui é real.

    Para provider não-Copilot, `ensure_llm_ready` é no-op (sempre ok=True):
    não valida de fato uma credencial Gemini ausente/inválida, por exemplo.
    """
    resultado: PreflightResult = await ensure_llm_ready()
    if not resultado.ok:
        pytest.skip(f"LLM real indisponível: {resultado.message}")


# ---------------------------------------------------------------------------
# Coleta de trace estruturado
# ---------------------------------------------------------------------------

@pytest.fixture
def trace_collector(tmp_path: Path, request: pytest.FixtureRequest):
    """`TraceCollector` com dump automático em JSON ao final do teste.

    O JSON (canonical + raw layer) é escrito em
    ``tmp_path/traces/<nome_do_teste>.json`` mesmo se o teste falhar,
    facilitando debug de trajetórias inesperadas. Para inspecionar
    manualmente: rode com ``pytest --basetemp=.pytest_traces`` e o
    arquivo fica preservado após a execução.
    """
    collector = TraceCollector()
    yield collector

    destino = tmp_path / "traces" / f"{request.node.name}.json"
    collector.dump(destino)
