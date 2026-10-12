"""C1 — pipeline_controller faz as checagens determinísticas sem passar pelo io_agent."""

from src.agents.workflow_design_pipeline.agent import pipeline_controller


def _nomes(agent):
    return [getattr(t, "name", None) or getattr(t, "__name__", "") for t in agent.tools]


def test_controller_tem_checagens_diretas():
    nomes = _nomes(pipeline_controller)
    for esperado in ("clear_design_folder", "list_design_files",
                     "validate_analysis_sections", "check_active_blocks"):
        assert esperado in nomes, nomes
    # estrutura preservada: io_agent, design_architect e a pausa HITL continuam
    assert {"io_agent", "design_architect", "aguardar_resolucao_doubt"} <= set(nomes)


def test_controller_sem_etapa_redundante():
    assert "VERIFICAÇÃO PRÉ-SEQUÊNCIA" not in pipeline_controller.instruction


def test_checagem_direta_usa_pasta_de_design_da_sessao(tmp_path, monkeypatch):
    from shared.tools import design_filesystem as df
    root = tmp_path / "design"
    monkeypatch.setattr(df, "ADK_DIR", tmp_path)
    monkeypatch.setattr(df, "DESIGN_DIR", root)
    monkeypatch.setattr(df, "LOCKS_DIR", root / ".locks")
    monkeypatch.setattr(
        "shared.agent_factory.get_agent_workspace", lambda name: root
    )
    (root / "doubts").mkdir(parents=True)
    (root / "doubts" / "Doubt_Artifact_HU-001_2026-10-03.md").write_text(
        "**Status:** Bloqueado", encoding="utf-8")
    tool = next(t for t in pipeline_controller.tools
                if getattr(t, "name", "") == "check_active_blocks")
    r = tool.func(caller="pipeline_controller")
    assert r["has_blocks"] is True


def test_requisitos_bloqueado_com_hus_nao_para_o_design():
    """Requisitos 'blocked' com HUs publicadas: o design segue (só para sem HUs)."""
    inst = pipeline_controller.instruction
    assert "fase de requisitos bloqueada e sem\n         HUs publicadas" in inst
    assert "aguardando resolução do lado de Requisitos" not in inst
