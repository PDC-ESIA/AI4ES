"""Testes do gate determinístico entre pipeline_controller e parallel_branch.

Cobre a regressão real (2026-08-23): pipeline_controller recusou avançar
("PIPELINE_ERROR") porque a análise técnica só tinha a Seção 1, mas
parallel_branch rodou mesmo assim — só não produziu artefatos quebrados
porque cada especialista, por conta própria, percebeu o problema e recusou
o trabalho. `gate_parallel_branch` fecha essa lacuna com uma checagem de
código antes de o ParallelAgent rodar.

Não usa o runtime ADK: `validate_analysis_sections` é a mesma função pura
que pipeline_controller já chama via Agente IO; o `CallbackContext` é
substituído por um duplo mínimo, igual ao padrão de test_design_manifest.py.
"""

from pathlib import Path

from google.genai import types

from src.agents.workflow_design_pipeline.gate import (
    _analysis_completeness,
    gate_parallel_branch,
)

_REQUIRED_SECTIONS = [
    (1, "Compreensão do lote"),
    (2, "Decisão(ões) de arquitetura e trade-offs"),
    (3, "Tipo de diagrama por HU"),
    (4, "Componentes por HU com origens"),
    (5, "Bloqueios identificados"),
    (6, "Tabela de cobertura por HU"),
    (7, "Gap Analysis"),
    (8, "Plano de Prototipação"),
]


def _complete_analysis_text() -> str:
    blocks = [f"{n}. {title}\nConteúdo da seção {n}." for n, title in _REQUIRED_SECTIONS]
    return "\n<<<FIM_SECAO>>>\n".join(blocks) + "\n<<<FIM_SECAO>>>\n"


def _incomplete_analysis_text() -> str:
    """Reproduz o incidente real: só a Seção 1 está presente."""
    return "1. Compreensão do lote\nConteúdo da seção 1.\n<<<FIM_SECAO>>>\n"


def _write_analysis(tmp_path: Path, content: str, filename: str = "analise_tecnica_HU-001.md") -> Path:
    design_root = tmp_path / "workspace_output" / "design"
    analysis_dir = design_root / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    (analysis_dir / filename).write_text(content, encoding="utf-8")
    return design_root


class _FakeCtx:
    """Duplo mínimo de CallbackContext: gate_parallel_branch não usa .state."""


# ──────────────────────────────────────────────────────────────────────────────
# _analysis_completeness — checagem pura
# ──────────────────────────────────────────────────────────────────────────────


def test_incompleto_sem_pasta_analysis(tmp_path):
    design_root = tmp_path / "workspace_output" / "design"
    ok, motivo = _analysis_completeness(design_root)
    assert ok is False
    assert "analysis" in motivo


def test_incompleto_sem_nenhum_arquivo(tmp_path):
    design_root = tmp_path / "workspace_output" / "design"
    (design_root / "analysis").mkdir(parents=True)
    ok, motivo = _analysis_completeness(design_root)
    assert ok is False
    assert "nenhum arquivo" in motivo


def test_incompleto_quando_faltam_secoes(tmp_path):
    """Regressão do incidente real: só a Seção 1 presente."""
    design_root = _write_analysis(tmp_path, _incomplete_analysis_text())
    ok, motivo = _analysis_completeness(design_root)
    assert ok is False
    assert "analise_tecnica_HU-001.md" in motivo
    assert "[2, 3, 4, 5, 6, 7, 8]" in motivo


def test_completo_quando_todas_as_secoes_presentes(tmp_path):
    design_root = _write_analysis(tmp_path, _complete_analysis_text())
    ok, motivo = _analysis_completeness(design_root)
    assert ok is True
    assert motivo == ""


# ──────────────────────────────────────────────────────────────────────────────
# gate_parallel_branch — before_agent_callback
# ──────────────────────────────────────────────────────────────────────────────


def test_gate_bloqueia_quando_analise_incompleta(tmp_path, monkeypatch):
    _write_analysis(tmp_path, _incomplete_analysis_text())
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace_output"))

    result = gate_parallel_branch(_FakeCtx())

    assert isinstance(result, types.Content)
    text = result.parts[0].text
    assert "PIPELINE_ERROR" in text
    assert "incompleto" in text


def test_gate_libera_quando_analise_completa(tmp_path, monkeypatch):
    _write_analysis(tmp_path, _complete_analysis_text())
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace_output"))

    result = gate_parallel_branch(_FakeCtx())

    assert result is None


def test_gate_falha_fechada_quando_checagem_lanca_excecao(tmp_path, monkeypatch):
    """O gate protege contra estado inválido/desconhecido — nunca libera às
    cegas se a própria checagem não puder ser executada."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace_output"))

    def _boom(*_args, **_kwargs):
        raise RuntimeError("disco indisponível")

    import src.agents.workflow_design_pipeline.gate as gate_module
    monkeypatch.setattr(gate_module, "validate_analysis_sections", _boom)
    _write_analysis(tmp_path, _complete_analysis_text())

    result = gate_parallel_branch(_FakeCtx())

    assert isinstance(result, types.Content)
    assert "PIPELINE_ERROR" in result.parts[0].text


def test_parallel_branch_tem_before_agent_callback_do_gate():
    from src.agents.workflow_design_pipeline.agent import parallel_branch
    from src.agents.workflow_design_pipeline.gate import gate_parallel_branch

    assert parallel_branch.before_agent_callback is gate_parallel_branch
