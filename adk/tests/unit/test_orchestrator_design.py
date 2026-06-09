"""Testes da inclusão do design_pipeline na sequência do orchestrator."""


def test_orchestrator_includes_design_pipeline_in_order():
    from src.agents.orchestrator.agent import _PipelineOrchestrator

    nomes = [p.name for p in _PipelineOrchestrator._pipelines]

    assert nomes == [
        "requirements_pipeline",
        "design_pipeline",
        "coding_review_pipeline",
        "qa_pipeline",
    ], f"Sequência inesperada: {nomes}"
