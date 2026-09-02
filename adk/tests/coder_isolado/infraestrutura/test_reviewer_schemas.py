"""Tests para o reviewer do workflow coding_review — schemas Pydantic (ReviewIssue/ReviewOutput)."""

import pytest
from pydantic import ValidationError

from src.agents.workflow_coding_review.reviewer.schemas import ReviewIssue, ReviewOutput


def test_review_issue_minimal():
    """ReviewIssue com campos obrigatórios."""
    issue = ReviewIssue(
        severity="critical",
        description="Função X não trata exceção Y",
        layer="corretude",
    )
    assert issue.severity == "critical"
    assert issue.description == "Função X não trata exceção Y"
    assert issue.layer == "corretude"
    assert issue.file is None


def test_review_issue_com_arquivo():
    issue = ReviewIssue(
        severity="warning",
        description="Falta docstring",
        file="src/utils.py",
        layer="arquitetura",
    )
    assert issue.file == "src/utils.py"


def test_review_issue_severity_aceita_strings_livres():
    """severity é string livre — o prompt valida critical/warning/info, não o schema."""
    issue = ReviewIssue(severity="info", description="X", layer="testes")
    assert issue.severity == "info"


def test_review_issue_campos_obrigatorios():
    """severity, description e layer são obrigatórios."""
    with pytest.raises(ValidationError):
        ReviewIssue(severity="critical")  # falta description e layer


def test_review_output_aprovado_sem_issues():
    output = ReviewOutput(status="APROVADO")
    assert output.status == "APROVADO"
    assert output.issues == []
    assert output.report_path is None


def test_review_output_bloqueado_com_issues():
    output = ReviewOutput(
        status="BLOQUEADO",
        issues=[
            ReviewIssue(severity="critical", description="X", layer="corretude"),
            ReviewIssue(severity="warning", description="Y", layer="testes"),
        ],
        report_path="verificacao_revisao.md",
    )
    assert output.status == "BLOQUEADO"
    assert len(output.issues) == 2
    assert output.report_path == "verificacao_revisao.md"


def test_review_output_serializa_para_json():
    """Confirma round-trip via Pydantic — útil para output_schema do ADK."""
    original = ReviewOutput(
        status="APROVADO",
        issues=[ReviewIssue(severity="info", description="Z", layer="arquitetura")],
    )
    data = original.model_dump()
    reconstructed = ReviewOutput(**data)
    assert reconstructed.status == "APROVADO"
    assert len(reconstructed.issues) == 1
    assert reconstructed.issues[0].description == "Z"
