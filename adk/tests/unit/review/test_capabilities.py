"""Testes da camada de capacidades de análise estática.

Cobertura:
- Finding: validação de campos e severidade
- run_capabilities: isolamento de falhas, ordenação, registry vazio
- RuffCapability: detecção de problemas reais (integração)
- BanditCapability: detecção de problemas de segurança reais (integração)
"""

from pathlib import Path

import pytest

from shared.review import Finding, run_capabilities
from shared.review.capability import BanditCapability, RuffCapability


# ---------------------------------------------------------------------------
# Finding — modelo
# ---------------------------------------------------------------------------

def test_finding_campos_minimos():
    """Finding aceita campos opcionais ausentes."""
    f = Finding(
        origem="ruff",
        regra="E501",
        severidade="warning",
        arquivo="app/main.py",
        mensagem="line too long",
    )
    assert f.linha is None
    assert f.sugestao is None


def test_finding_severidade_invalida_rejeitada():
    """Finding rejeita severidade fora do Literal permitido."""
    with pytest.raises(Exception):
        Finding(
            origem="x",
            regra="X1",
            severidade="high",  # inválido — só critical/warning/info
            arquivo="f.py",
            mensagem="msg",
        )


# ---------------------------------------------------------------------------
# run_capabilities — comportamento
# ---------------------------------------------------------------------------

def test_run_capabilities_registry_vazio(tmp_path):
    """Registry vazio retorna lista vazia sem erro."""
    assert run_capabilities(tmp_path, registry=[]) == []


def test_run_capabilities_isolamento_falha(tmp_path):
    """Capacidade que lança exceção não interrompe as demais."""

    class _FaultyCap:
        name = "faulty"

        def run(self, target_dir: Path) -> list[Finding]:
            raise RuntimeError("ferramenta quebrada")

    class _GoodCap:
        name = "good"

        def run(self, target_dir: Path) -> list[Finding]:
            return [Finding(
                origem="good",
                regra="G1",
                severidade="info",
                arquivo="f.py",
                mensagem="ok",
            )]

    results = run_capabilities(tmp_path, registry=[_FaultyCap(), _GoodCap()])
    assert len(results) == 1
    assert results[0].origem == "good"


def test_run_capabilities_ordenacao_por_severidade(tmp_path):
    """Resultados ordenados: critical → warning → info."""

    class _Cap:
        name = "test"

        def run(self, target_dir: Path) -> list[Finding]:
            return [
                Finding(origem="test", regra="I1", severidade="info", arquivo="f.py", mensagem="i"),
                Finding(origem="test", regra="C1", severidade="critical", arquivo="f.py", mensagem="c"),
                Finding(origem="test", regra="W1", severidade="warning", arquivo="f.py", mensagem="w"),
            ]

    results = run_capabilities(tmp_path, registry=[_Cap()])
    assert [f.severidade for f in results] == ["critical", "warning", "info"]


def test_run_capabilities_multiplas_caps_agrupadas(tmp_path):
    """Findings de múltiplas capacidades são combinados e ordenados."""

    class _CapA:
        name = "a"

        def run(self, target_dir: Path) -> list[Finding]:
            return [Finding(origem="a", regra="A1", severidade="warning", arquivo="f.py", mensagem="w")]

    class _CapB:
        name = "b"

        def run(self, target_dir: Path) -> list[Finding]:
            return [Finding(origem="b", regra="B1", severidade="critical", arquivo="f.py", mensagem="c")]

    results = run_capabilities(tmp_path, registry=[_CapA(), _CapB()])
    assert len(results) == 2
    assert results[0].severidade == "critical"
    assert results[1].severidade == "warning"


# ---------------------------------------------------------------------------
# Integração — ferramentas reais
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_ruff_detecta_import_nao_usado(tmp_path):
    """RuffCapability detecta import não usado (F401) em código real."""
    (tmp_path / "bad.py").write_text("import os\n\nx = 1\n")
    findings = RuffCapability().run(tmp_path)
    assert any(f.regra.startswith("F") for f in findings), (
        f"Esperava finding F* do ruff, obteve: {[f.regra for f in findings]}"
    )


@pytest.mark.integration
def test_bandit_detecta_senha_hardcoded(tmp_path):
    """BanditCapability detecta senha hardcoded (B105/B106) em código real."""
    (tmp_path / "insecure.py").write_text('password = "hardcoded_secret_123"\n')
    findings = BanditCapability().run(tmp_path)
    assert len(findings) > 0, "Bandit deveria detectar senha hardcoded"


@pytest.mark.integration
def test_run_capabilities_com_registry_padrao(tmp_path):
    """run_capabilities com REGISTRY padrão processa diretório real sem erro."""
    (tmp_path / "app.py").write_text("import sys\npassword = '12345'\n")
    findings = run_capabilities(tmp_path)
    assert isinstance(findings, list)
    assert len(findings) > 0, "Esperava ao menos 1 finding de ruff ou bandit"
