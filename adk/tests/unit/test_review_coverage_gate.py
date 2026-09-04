"""Testes do gate determinístico de cobertura aplicado pelo reviewer."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def _summary(*, completa: bool = False) -> dict:
    approved = ["TASK-001", "TASK-002"] if completa else ["TASK-001"]
    return {
        "input_valid": True,
        "input_errors": [],
        "expected_task_ids": ["TASK-001", "TASK-002"],
        "processed_task_ids": ["TASK-001", "TASK-002"],
        "approved_task_ids": approved,
        "task_results": {
            "TASK-001": {
                "status": "aprovado",
                "blocking_reason": None,
                "report_path": None,
                "motivo_terminacao": "aprovado",
            },
            "TASK-002": {
                "status": "aprovado" if completa else "reprovado",
                "blocking_reason": None if completa else "falhou",
                "report_path": None,
                "motivo_terminacao": (
                    "aprovado" if completa else "reprovado_apos_loop"
                ),
            },
        },
        "cobertura_completa": completa,
    }


@pytest.fixture
def review_tools_module(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.tools.coding_tools import review_tools

    return importlib.reload(review_tools)


def test_cobertura_exige_summary_completo_e_consistente(review_tools_module):
    rt = review_tools_module
    assert rt.cobertura_comprovada(
        {"task_iteration_summary": _summary(completa=True)}
    ) is True

    invalidos = [
        None,
        "summary",
        {"cobertura_completa": True},
        {**_summary(completa=True), "expected_task_ids": 123},
        {**_summary(completa=True), "task_results": []},
        {**_summary(completa=True), "approved_task_ids": ["TASK-001"]},
        {**_summary(completa=False), "cobertura_completa": True},
    ]
    for summary in invalidos:
        assert rt.cobertura_comprovada(
            {"task_iteration_summary": summary}
        ) is False


def test_task_aceita_com_ressalvas_comprova_cobertura(review_tools_module):
    summary = _summary(completa=False)
    summary.update(
        {
            "approved_task_ids": ["TASK-001"],
            "accepted_task_ids": ["TASK-002"],
            "cobertura_completa": True,
            "qualidade_completa": False,
        }
    )
    summary["task_results"]["TASK-002"].update(
        {
            "status": "aceito_com_ressalvas",
            "motivo_terminacao": "aceito_com_ressalvas_plato_nota",
            "nota_final": 0.8,
            "conceito": "B",
        }
    )

    assert review_tools_module.cobertura_comprovada(
        {"task_iteration_summary": summary}
    ) is True

    original = "## Status: APROVADO\n\n## Resumo\nEntrega funcional com ressalvas."

    class Ctx:
        state = {"review_analysis": original, "task_iteration_summary": summary}

    assert review_tools_module._persist_review(Ctx()) is None
    assert Ctx.state["review_analysis"] == original


def test_gate_remove_status_conflitante_preserva_corpo_e_e_idempotente(
    review_tools_module,
):
    rt = review_tools_module
    analysis = (
        "## Status: APROVADO\n\n"
        "## Issues\nFalha X.\n\n"
        "## Status: OUTRO\n\n"
        "## Resumo\nTexto original."
    )

    primeira = rt.aplicar_gate_de_cobertura(analysis, _summary())
    segunda = rt.aplicar_gate_de_cobertura(primeira, _summary())

    assert primeira == segunda
    assert primeira.count("## Status:") == 1
    assert primeira.startswith("## Status: BLOQUEADO")
    assert primeira.count("<!-- task-coverage-gate:start -->") == 1
    assert "TASK-002: reprovado" in primeira
    assert "## Issues\nFalha X." in primeira
    assert "## Resumo\nTexto original." in primeira


@pytest.mark.parametrize(
    "summary",
    [
        None,
        "inválido",
        {"cobertura_completa": False, "expected_task_ids": 123},
        {
            **_summary(),
            "input_errors": 123,
        },
        {
            **_summary(),
            "approved_task_ids": [["TASK-001"]],
        },
    ],
)
def test_gate_summary_malformado_bloqueia_sem_excecao(
    review_tools_module, summary
):
    texto = review_tools_module.aplicar_gate_de_cobertura(
        "## Status: APROVADO\n\n## Resumo\nTexto", summary
    )
    assert texto.startswith("## Status: BLOQUEADO")
    assert "resumo de iteração está ausente ou inválido" in texto


def test_callback_com_analise_vazia_lista_pendencias_e_retorna_content(
    review_tools_module,
):
    rt = review_tools_module

    class Ctx:
        state = {
            "review_analysis": "   \n",
            "task_iteration_summary": _summary(),
        }

    content = rt._persist_review(Ctx())
    assert content is not None
    texto = content.parts[0].text
    assert texto.startswith("## Status: BLOQUEADO")
    assert "TASK-002: reprovado" in texto
    assert Ctx.state["review_analysis"] == texto

    report = Path(rt._REVIEW_WS) / "verificacao_revisao.md"
    assert report.read_text(encoding="utf-8") == texto


def test_callback_cobertura_completa_preserva_texto_e_nao_retorna_content(
    review_tools_module,
):
    rt = review_tools_module
    original = "## Status: APROVADO\n\n## Resumo\nTudo certo."

    class Ctx:
        state = {
            "review_analysis": original,
            "task_iteration_summary": _summary(completa=True),
        }

    assert rt._persist_review(Ctx()) is None
    assert Ctx.state["review_analysis"] == original
    report = Path(rt._REVIEW_WS) / "verificacao_revisao.md"
    assert report.read_text(encoding="utf-8") == original


def test_runner_propaga_bloqueio_como_ultimo_evento(review_tools_module):
    rt = review_tools_module
    import src.agents.workflow_coding_review.reviewer.agent as reviewer
    from google.adk.models.llm_response import LlmResponse
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types

    reviewer = importlib.reload(reviewer)

    def stub(callback_context, llm_request):
        callback_context.state["task_iteration_summary"] = _summary()
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="## Status: APROVADO\n\n## Resumo\nTexto")],
            )
        )

    original_callback = reviewer._analyzer.before_model_callback
    reviewer._analyzer.before_model_callback = stub
    try:
        runner = Runner(
            agent=reviewer._analyzer,
            app_name="workflow_coding_review",
            session_service=InMemorySessionService(),
            auto_create_session=True,
        )
        events = list(
            runner.run(
                user_id="gate-user",
                session_id="gate-session",
                new_message=types.Content(
                    role="user", parts=[types.Part(text="revisar")]
                ),
            )
        )
    finally:
        reviewer._analyzer.before_model_callback = original_callback

    textos = [
        part.text
        for event in events
        if event.content
        for part in event.content.parts
        if part.text
    ]
    report = Path(rt._REVIEW_WS) / "verificacao_revisao.md"
    assert textos[-1].startswith("## Status: BLOQUEADO")
    assert textos[-1] == report.read_text(encoding="utf-8")
