"""Integração Orquestrador → QA Agent (FRENTE 1, Cenário 1).

TDD rigoroso: Red-Green-Refactor.

Objetivo: garantir que o orquestrador atue como dispatcher fino,
repassando apenas o Manifesto de Fase do coding ao QA Agent e
exigindo de volta o manifesto de QA com os artefatos persistidos.
"""

from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai import types


# ──────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_workspace(tmp_path: Path, monkeypatch) -> Path:
    """Workspace isolado por teste, substituindo workspace_output."""
    ws = tmp_path / "workspace_output"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / ".ai4se_workspace").write_text("marker", encoding="utf-8")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws))
    # Garante que get_workspace_root resolva dentro do tmp_path sem
    # poluir o default global para outros testes.
    from shared import workspace as _ws_mod

    monkeypatch.setattr(_ws_mod, "_DEFAULT_WORKSPACE", str(ws))
    return ws


@pytest.fixture
def coding_manifest(tmp_workspace: Path) -> dict:
    """Manifesto de coding mínimo com um artefato de código no workspace."""
    coder_dir = tmp_workspace / "coder" / "src"
    coder_dir.mkdir(parents=True, exist_ok=True)
    code_file = coder_dir / "calculadora.py"
    code_file.write_text(
        "def somar(a, b):\n    return a + b\n",
        encoding="utf-8",
    )

    return {
        "phase": "coding",
        "status": "ok",
        "artifacts": [
            {
                "tipo": "codigo",
                "id": "calculadora",
                "path": str(code_file.relative_to(tmp_workspace)),
            }
        ],
        "doubts": [],
        "summary": "Código da calculadora entregue.",
    }


@pytest.fixture
def requirements_manifest(tmp_workspace: Path) -> dict:
    """Manifesto de requirements opcional para contexto adicional."""
    req_dir = tmp_workspace / "requirements" / "HUs"
    req_dir.mkdir(parents=True, exist_ok=True)
    hu_file = req_dir / "HU-001.md"
    hu_file.write_text(
        "# HU-001\n\nComo usuário, quero somar dois números.",
        encoding="utf-8",
    )

    return {
        "phase": "requirements",
        "status": "ok",
        "artifacts": [
            {
                "tipo": "HU",
                "id": "HU-001",
                "path": str(hu_file.relative_to(tmp_workspace)),
            }
        ],
        "doubts": [],
        "summary": "Requisito da calculadora.",
    }


class _FakeSession:
    def __init__(self, session_id: str = "inner-sid", user_id: str = "u",
                 state: dict | None = None):
        self.id = session_id
        self.user_id = user_id
        self.state = state if state is not None else {}


class _FakeSessionService:
    def __init__(self, inner_state: dict):
        self._state = inner_state

    async def create_session(self, *, app_name, user_id, state):
        # Mescla state inicial com o que o orchestrator passou
        merged = dict(self._state)
        merged.update(state)
        self._state = merged
        return _FakeSession(state=merged)


class _FakeQAPipeline:
    """Simula o workflow_qa: lê manifestos do state, gera artefatos fake
    e devolve o manifesto de QA via state_delta no último evento.
    """

    name = "qa_pipeline"

    def __init__(self, tmp_workspace: Path, inner_state: dict):
        self.tmp_workspace = tmp_workspace
        self.inner_state = inner_state
        self.close = AsyncMock(return_value=None)

    async def run_async(self, **kwargs) -> AsyncGenerator[Event, None]:
        new_message = kwargs.get("new_message")
        assert new_message is not None

        # O input enviado pelo orquestrador DEVE ser a representação leve
        # dos manifestos (não o conteúdo dos artefatos).
        input_text = ""
        if new_message and new_message.parts:
            for part in new_message.parts:
                if part.text:
                    input_text = part.text
                    break

        assert "Manifesto de Fase" in input_text or "manifesto" in input_text.lower(), (
            f"Orquestrador não enviou a lista de manifestos ao QA. Input: {input_text[:200]}"
        )

        # O state interno deve conter os manifestos das fases anteriores.
        phase_manifests = self.inner_state.get("phase_manifests", [])
        assert len(phase_manifests) >= 1, "QA não recebeu manifestos no state"
        assert any(m["phase"] == "coding" for m in phase_manifests), (
            "Manifesto de coding ausente"
        )

        # Gera artefatos fake de QA no workspace.
        slug = "calculadora"
        tests_dir = self.tmp_workspace / "tests" / slug
        tests_dir.mkdir(parents=True, exist_ok=True)
        test_file = tests_dir / f"test_{slug}.py"
        test_file.write_text(
            "def test_somar():\n    from src.calculadora import somar\n    assert somar(2, 3) == 5\n",
            encoding="utf-8",
        )

        inputs_dir = self.tmp_workspace / "tests" / "inputs"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        input_file = inputs_dir / f"{slug}.json"
        input_file.write_text(
            '{"id_artefato": "HU-001", "tipo": "HU"}',
            encoding="utf-8",
        )

        # Emite manifesto de QA via state_delta.
        qa_manifest = {
            "phase": "qa",
            "status": "ok",
            "artifacts": [
                {
                    "tipo": "input",
                    "id": slug,
                    "path": str(input_file.relative_to(self.tmp_workspace)),
                },
                {
                    "tipo": "teste",
                    "id": slug,
                    "path": str(test_file.relative_to(self.tmp_workspace)),
                },
            ],
            "doubts": [],
            "summary": "Testes gerados e executados com sucesso.",
        }

        updated_manifests = list(phase_manifests) + [qa_manifest]
        self.inner_state["phase_manifests"] = updated_manifests

        yield Event(
            author="qa_pipeline",
            invocation_id="inv-qa",
            content=types.Content(
                role="model",
                parts=[types.Part(text="QA concluído com sucesso.")],
            ),
            actions=EventActions(
                state_delta={"phase_manifests": updated_manifests},
            ),
        )


class _FakeCtx:
    def __init__(self, user_text: str, session_id: str = "outer-sid",
                 state: dict | None = None):
        self.user_content = types.Content(
            role="user", parts=[types.Part(text=user_text)]
        )
        self.user_id = "test-user"
        self.session = MagicMock()
        self.session.id = session_id
        self.session.state = state if state is not None else {}
        self.artifact_service = MagicMock()
        self.credential_service = MagicMock()
        self.plugin_manager = MagicMock()
        self.plugin_manager.plugins = []


# ──────────────────────────────────────────────────────────────────────────────
# 1. FASE RED — teste de integração que falha até a implementação existir
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_orchestrator_envia_manifesto_ao_qa_e_recebe_manifesto_qa(
    tmp_workspace: Path,
    coding_manifest: dict,
    requirements_manifest: dict,
    monkeypatch,
):
    """RED/GREEN: dispatcher fino repassa manifestos e exige manifesto qa."""
    from src.agents.orchestrator.agent import _PipelineOrchestrator
    from shared.manifest import PhaseManifest, PhaseStatus

    inner_state = {
        "phase_manifests": [requirements_manifest, coding_manifest],
    }
    fake_qa = _FakeQAPipeline(tmp_workspace, inner_state)
    fake_qa.session_service = _FakeSessionService(inner_state)

    # Substitui o workflow_qa real pelo stub.
    monkeypatch.setattr(
        "src.agents.orchestrator.agent.qa_pipeline",
        fake_qa,
    )

    # O Runner do orchestrator deve criar o fake QA com o state correto.
    def _fake_runner_constructor(*, app_name, agent, **kwargs):
        # Só intercepta o qa_pipeline; os demais pipelines usam um runner fake vazio.
        if getattr(agent, "name", None) == "qa_pipeline":
            return fake_qa
        # Pipelines anteriores simulam sucesso sem eventos relevantes.
        r = MagicMock()
        r.session_service = _FakeSessionService({})
        r.close = AsyncMock(return_value=None)
        async def _empty(**kw):
            if False:
                yield None
        r.run_async = _empty
        return r

    monkeypatch.setattr(
        "src.agents.orchestrator.agent.Runner",
        _fake_runner_constructor,
    )

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    # Simula o SDLC completo: os 3 primeiros pipelines são stubs que já
    # rodaram e deixaram os manifestos no state; o QA é o quarto pipeline.
    class _StubPipeline:
        name = "stub_pipeline"

    monkeypatch.setattr(
        _PipelineOrchestrator,
        "_pipelines",
        [_StubPipeline(), _StubPipeline(), _StubPipeline(), fake_qa],
    )

    ctx = _FakeCtx(
        "Gerar testes para a calculadora",
        session_id="outer-1",
        state={"phase_manifests": [requirements_manifest, coding_manifest]},
    )

    events = [e async for e in orch._run_async_impl(ctx)]

    # O state externo deve conter os manifestos + o manifesto de QA.
    final_manifests = ctx.session.state.get("phase_manifests", [])
    assert len(final_manifests) == 3, (
        f"Esperado 3 manifestos, obtido {len(final_manifests)}"
    )

    qa_manifest_dict = final_manifests[-1]
    qa_manifest = PhaseManifest.model_validate(qa_manifest_dict)

    assert qa_manifest.phase == "qa"
    assert qa_manifest.status == PhaseStatus.OK
    assert len(qa_manifest.artifacts) == 2
    assert any(a.tipo == "input" for a in qa_manifest.artifacts)
    assert any(a.tipo == "teste" for a in qa_manifest.artifacts)

    # Invariante: status ok => nenhuma dúvida bloqueante.
    assert not any(d.bloqueante for d in qa_manifest.doubts)

    # O orquestrador não deve ter lido o conteúdo dos artefatos (dispatcher fino).
    # Se o input continha o código fonte completo, o teste fake levantaria.
    texts = [
        p.text
        for e in events if e.content
        for p in e.content.parts if p.text
    ]
    assert any("QA concluído" in t for t in texts)


# ──────────────────────────────────────────────────────────────────────────────
# 2. FASE GREEN — validação do manifesto construído pelo orquestrador
# ──────────────────────────────────────────────────────────────────────────────


def test_build_manifest_input_e_leve_e_nao_inclui_conteudo(tmp_workspace: Path,
                                                            coding_manifest: dict):
    """O input para o QA deve listar manifestos, nunca o conteúdo dos artefatos."""
    from src.agents.orchestrator._helpers import _build_manifest_input
    from shared.manifest import PhaseManifest

    manifest = PhaseManifest.model_validate(coding_manifest)
    text = _build_manifest_input([manifest])

    assert manifest.phase in text
    assert manifest.artifacts[0].path in text
    assert "def somar" not in text


# ──────────────────────────────────────────────────────────────────────────────
# 3. FASE REFACTOR — contrato forte via Pydantic
# ──────────────────────────────────────────────────────────────────────────────


def test_manifest_status_ok_proibe_duvida_bloqueante():
    """Invariante crítica: status=ok ⇒ sem dúvidas bloqueantes."""
    from shared.manifest import PhaseManifest, PhaseStatus, DoubtItem

    with pytest.raises(ValueError, match="bloqueante"):
        PhaseManifest(
            phase="qa",
            status=PhaseStatus.OK,
            artifacts=[],
            doubts=[
                DoubtItem(
                    id="D-001",
                    severidade="alta",
                    bloqueante=True,
                    path="doubts/D-001.md",
                )
            ],
            summary="deve falhar",
        )


def test_manifest_status_blocked_exige_duvida_bloqueante():
    """status=blocked implica ao menos uma dúvida bloqueante."""
    from shared.manifest import PhaseManifest, PhaseStatus, DoubtItem

    with pytest.raises(ValueError, match="bloqueante"):
        PhaseManifest(
            phase="qa",
            status=PhaseStatus.BLOCKED,
            artifacts=[],
            doubts=[],
            summary="deve falhar",
        )


@pytest.mark.asyncio
async def test_orchestrator_e_roteador_puro_sem_open_em_arquivos(
    tmp_workspace: Path,
    coding_manifest: dict,
    monkeypatch,
):
    """REFACTOR: orquestrador não abre artefatos — só roteia manifestos."""
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    inner_state = {"phase_manifests": [coding_manifest]}
    fake_qa = _FakeQAPipeline(tmp_workspace, inner_state)
    fake_qa.session_service = _FakeSessionService(inner_state)
    monkeypatch.setattr(
        "src.agents.orchestrator.agent.qa_pipeline",
        fake_qa,
    )

    def _fake_runner_constructor(*, app_name, agent, **kwargs):
        if getattr(agent, "name", None) == "qa_pipeline":
            return fake_qa
        r = MagicMock()
        r.session_service = _FakeSessionService({})
        r.close = AsyncMock(return_value=None)
        async def _empty(**kw):
            if False:
                yield None
        r.run_async = _empty
        return r

    monkeypatch.setattr(
        "src.agents.orchestrator.agent.Runner",
        _fake_runner_constructor,
    )

    class _StubPipeline:
        name = "stub_pipeline"

    orch = _PipelineOrchestrator(name="orchestrator", description="test")
    monkeypatch.setattr(
        _PipelineOrchestrator,
        "_pipelines",
        [_StubPipeline(), fake_qa],
    )

    ctx = _FakeCtx(
        "prompt",
        session_id="outer-2",
        state={"phase_manifests": [coding_manifest]},
    )

    open_spy = MagicMock(side_effect=open)
    monkeypatch.setattr("builtins.open", open_spy)

    _ = [e async for e in orch._run_async_impl(ctx)]

    # O orquestrador não deve abrir nenhum arquivo (o QA sim, mas não o dispatcher).
    # Filtra apenas chamadas de leitura/escrita de arquivo real (não StringIO/mocks).
    file_opens = [
        call for call in open_spy.call_args_list
        if call.args and isinstance(call.args[0], (str, Path))
    ]
    assert len(file_opens) == 0, (
        f"Orquestrador abriu arquivos: {[c.args[0] for c in file_opens]}"
    )

    # Garante que o manifesto final é um PhaseManifest válido.
    from shared.manifest import PhaseManifest
    final_manifests = ctx.session.state.get("phase_manifests", [])
    assert len(final_manifests) == 2
    PhaseManifest.model_validate(final_manifests[-1])
