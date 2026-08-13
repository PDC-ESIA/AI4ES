"""Tests para workflow_coding_review/context_engineer/ — descoberta + schemas + tools."""
 
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
 
import pytest
 
 
# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
 
def _paths_json(paths: list) -> str:
    """Monta paths_json no formato de lista simples de strings."""
    return json.dumps(paths)
 
 
# -------------------------------------------------------------------
# Descoberta e schema do agente
# -------------------------------------------------------------------
 
def test_context_engineer_agent_importavel():
    from src.agents.workflow_coding_review.context_engineer.agent import agent
    assert agent is not None
    assert agent.name == "cr_context_engineer"
 
 
def test_context_engineer_tem_tools_esperadas():
    from src.agents.workflow_coding_review.context_engineer.agent import agent
    from google.adk.tools import LongRunningFunctionTool
    tool_names = {getattr(getattr(t, "func", t), "__name__", "") for t in agent.tools}
    assert {
        "tool_salvar_task_cr",
        "tool_ler_requirements",
        "tool_ler_design",
        "tool_gerar_doubt_artifact",
        "tool_emitir_manifesto_bloqueado",
        "aguardar_resolucao_bloqueio",
    } <= tool_names
    hitl_tools = [
        t for t in agent.tools
        if isinstance(t, LongRunningFunctionTool)
    ]
    assert len(hitl_tools) == 1, (
        "Esperado exatamente 1 LongRunningFunctionTool. "
        f"Encontrado: {len(hitl_tools)}"
    )
 
 
def test_context_engineer_sem_output_schema():
    """GAP-00: output_schema deve estar ausente para não desabilitar tools."""
    from src.agents.workflow_coding_review.context_engineer.agent import agent
    assert agent.output_schema is None
 
 
# -------------------------------------------------------------------
# Schemas
# -------------------------------------------------------------------
 
def test_schemas_macro_context_minimal():
    from src.agents.workflow_coding_review.context_engineer.schemas import MacroContext
    mc = MacroContext(
        summary="Sistema de autenticação JWT",
        tech_stack=["Python", "FastAPI"],
        global_rules=["RESTful"],
    )
    assert mc.summary.startswith("Sistema")
    assert len(mc.tech_stack) == 2
 
 
def test_schemas_task_com_contract():
    from src.agents.workflow_coding_review.context_engineer.schemas import Task, Contract
    task = Task(
        id="TASK-001",
        type="backend",
        complexity="medium",
        description="Criar endpoint POST /auth/login",
        acceptance_criteria=["Retorna 200 com JWT", "Retorna 401 com credenciais inválidas"],
        contract=Contract(inputs=[], outputs=["src/auth.py"]),
        requirement_id="RF-001",
        design_refs=["design/analise_tecnica_HU-001.md"],
    )
    assert task.id == "TASK-001"
    assert task.business_rules == []
    assert task.contract.outputs == ["src/auth.py"]
 
 
def test_schemas_task_design_refs_vazio_valido():
    """design_refs pode ser lista vazia para RFs sem HU associada."""
    from src.agents.workflow_coding_review.context_engineer.schemas import Task, Contract
    task = Task(
        id="TASK-007",
        type="infra",
        complexity="low",
        description="Armazenar imagens em disco local",
        acceptance_criteria=["Sistema armazena imagens em disco"],
        contract=Contract(),
        requirement_id="RF-007",
        design_refs=[],
    )
    assert task.design_refs == []
 
 
def test_schemas_contract_interfaces_objeto_aceito():
    from src.agents.workflow_coding_review.context_engineer.schemas import Contract
    contract = Contract(
        interfaces={
            "create_ensaio": {
                "method": "POST",
                "params": {"titulo": "str", "cliente": "str"},
            }
        }
    )
    assert isinstance(contract.interfaces, list)
    assert any("create_ensaio" in item for item in contract.interfaces)
 
 
def test_schemas_tasks_output_completo():
    from src.agents.workflow_coding_review.context_engineer.schemas import (
        TasksOutput, MacroContext, Task, Contract
    )
    output = TasksOutput(
        macro_context=MacroContext(
            summary="X",
            tech_stack=["Python"],
            global_rules=["Y"],
        ),
        tasks=[
            Task(
                id="TASK-001",
                type="test",
                complexity="low",
                description="Z",
                acceptance_criteria=["A"],
                contract=Contract(),
                requirement_id="RF-001",
                design_refs=["design/analise_tecnica_HU-001.md"],
            )
        ],
    )
    assert len(output.tasks) == 1
    assert output.macro_context.summary == "X"
 
 
# -------------------------------------------------------------------
# tool_salvar_task_cr
# -------------------------------------------------------------------
 
def test_tool_salvar_task_cr_persiste_json(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.tools.coding_tools.context_engineer_tools import tool_salvar_task_cr
    task_json = json.dumps({"id": "TASK-001", "type": "backend", "description": "Criar endpoint"})
    result = tool_salvar_task_cr("TASK-001", task_json)
    assert result["sucesso"] is True
    arquivo = tmp_path / "ws" / "coder" / "tasks" / "TASK-001.json"
    assert arquivo.is_file()
 
 
def test_tool_salvar_task_cr_id_invalido_rejeita(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.tools.coding_tools.context_engineer_tools import tool_salvar_task_cr
    result = tool_salvar_task_cr("INVALID-001", json.dumps({"x": 1}))
    assert result["sucesso"] is False
    assert "TASK-" in result["erro"]
 
 
# -------------------------------------------------------------------
# tool_ler_requirements — via paths do manifesto
# -------------------------------------------------------------------
 
def test_tool_ler_requirements_com_paths_validos(tmp_path, monkeypatch):
    """Lê artefatos corretamente quando paths são fornecidos como lista de strings."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta_hus = tmp_path / "ws" / "requirements" / "HUs"
    pasta_rfs = tmp_path / "ws" / "requirements" / "RFs"
    pasta_hus.mkdir(parents=True)
    pasta_rfs.mkdir(parents=True)
    (pasta_hus / "HU-001.md").write_text("# HU-001", encoding="utf-8")
    (pasta_rfs / "RF-001.md").write_text("# RF-001", encoding="utf-8")
 
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_requirements
    paths = _paths_json([
        "requirements/HUs/HU-001.md",
        "requirements/RFs/RF-001.md",
    ])
    result = tool_ler_requirements(paths)
    assert result["sucesso"] is True
    assert result["artefatos_minimos_presentes"] is True
    assert result["tem_hu"] is True
    assert result["total_lidos"] == 2
 
 
def test_tool_ler_requirements_sem_rf_bloqueia(tmp_path, monkeypatch):
    """Retorna artefatos_minimos_presentes=False quando não há RF."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta_hus = tmp_path / "ws" / "requirements" / "HUs"
    pasta_hus.mkdir(parents=True)
    (pasta_hus / "HU-001.md").write_text("# HU-001", encoding="utf-8")
 
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_requirements
    paths = _paths_json(["requirements/HUs/HU-001.md"])
    result = tool_ler_requirements(paths)
    assert result["sucesso"] is True
    assert result["artefatos_minimos_presentes"] is False
    assert any("RF" in msg for msg in result["artefatos_minimos_ausentes"])
 
 
def test_tool_ler_requirements_sem_paths_bloqueia(tmp_path, monkeypatch):
    """Retorna erro quando paths_json está vazio."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_requirements
    result = tool_ler_requirements("[]")
    assert result["sucesso"] is False
    assert "Nenhum path" in result["erro"]
 
 
def test_tool_ler_requirements_path_traversal_rejeitado(tmp_path, monkeypatch):
    """Paths com .. são rejeitados."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_requirements
    paths = _paths_json(["../../etc/passwd"])
    result = tool_ler_requirements(paths)
    assert result["sucesso"] is True
    assert result["erros_leitura"] is not None
    assert any(".." in e or "inválido" in e for e in result["erros_leitura"])
 
 
def test_tool_ler_requirements_so_rf_valido(tmp_path, monkeypatch):
    """Aceita cenário com apenas RF — HU ausente não bloqueia sozinha."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta_rfs = tmp_path / "ws" / "requirements" / "RFs"
    pasta_rfs.mkdir(parents=True)
    (pasta_rfs / "RF-001.md").write_text("# RF-001", encoding="utf-8")
 
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_requirements
    paths = _paths_json(["requirements/RFs/RF-001.md"])
    result = tool_ler_requirements(paths)
    assert result["sucesso"] is True
    assert result["artefatos_minimos_presentes"] is True
    assert result["tem_hu"] is False
 
 
# -------------------------------------------------------------------
# tool_ler_design — fallback direto no workspace
# -------------------------------------------------------------------
 
def test_tool_ler_design_com_analise(tmp_path, monkeypatch):
    """Detecta analise_tecnica presente no workspace."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta = tmp_path / "ws" / "design"
    pasta.mkdir(parents=True)
    (pasta / "analise_tecnica_HU-001.md").write_text("# Análise", encoding="utf-8")
 
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_design
    result = tool_ler_design()
    assert result["sucesso"] is True
    assert result["artefatos_minimos_presentes"] is True
    assert result["fallback"] is True
    assert result["inconsistencia_detectada"] is False
 
 
def test_tool_ler_design_detecta_inconsistencia(tmp_path, monkeypatch):
    """Detecta inconsistência quando tem_hu=False mas existe analise_tecnica_HU."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta = tmp_path / "ws" / "design"
    pasta.mkdir(parents=True)
    (pasta / "analise_tecnica_HU-001.md").write_text("# Análise", encoding="utf-8")
 
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_design
    result = tool_ler_design(tem_hu=False)
    assert result["sucesso"] is True
    assert result["inconsistencia_detectada"] is True
 
 
def test_tool_ler_design_sem_inconsistencia_quando_tem_hu(tmp_path, monkeypatch):
    """Não detecta inconsistência quando tem_hu=True."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta = tmp_path / "ws" / "design"
    pasta.mkdir(parents=True)
    (pasta / "analise_tecnica_HU-001.md").write_text("# Análise", encoding="utf-8")
 
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_design
    result = tool_ler_design(tem_hu=True)
    assert result["sucesso"] is True
    assert result["inconsistencia_detectada"] is False
 
 
def test_tool_ler_design_sem_analise(tmp_path, monkeypatch):
    """Detecta ausência de analise_tecnica no workspace."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta = tmp_path / "ws" / "design" / "diagrams"
    pasta.mkdir(parents=True)
    (pasta / "diagrama_HU-001.mmd").write_text("graph TD", encoding="utf-8")
 
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_design
    result = tool_ler_design()
    assert result["sucesso"] is True
    assert result["artefatos_minimos_presentes"] is False
    assert result["inconsistencia_detectada"] is False
 
 
def test_tool_ler_design_pasta_inexistente(tmp_path, monkeypatch):
    """Retorna erro se pasta design não existe."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_design
    result = tool_ler_design()
    assert result["sucesso"] is False
    assert "não encontrada" in result["erro"]
 
 
# -------------------------------------------------------------------
# tool_gerar_doubt_artifact
# -------------------------------------------------------------------
 
def test_tool_gerar_doubt_artifact_na_raiz(tmp_path, monkeypatch):
    """Persiste arquivo .md na raiz do workspace."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    (tmp_path / "ws").mkdir(parents=True)
    from shared.tools.coding_tools.context_engineer_tools import tool_gerar_doubt_artifact
    result = tool_gerar_doubt_artifact(
        titulo="Manifesto de requirements não encontrado",
        fase_bloqueada="requirements",
        descricao="O orquestrador não repassou o manifesto no prompt.",
        acao_necessaria="Reprocessar a fase requirements antes de continuar.",
    )
    assert result["sucesso"] is True
    arquivo = tmp_path / "ws" / "Doubt_Artifact_context_engineer.md"
    assert arquivo.is_file()
 
 
def test_tool_gerar_doubt_artifact_em_subdir(tmp_path, monkeypatch):
    """Persiste arquivo .md em subdiretório especificado."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    (tmp_path / "ws").mkdir(parents=True)
    from shared.tools.coding_tools.context_engineer_tools import tool_gerar_doubt_artifact
    result = tool_gerar_doubt_artifact(
        titulo="Fase bloqueada",
        fase_bloqueada="requirements",
        descricao="Bloqueio detectado.",
        acao_necessaria="Reprocessar.",
        subdir="coder",
    )
    assert result["sucesso"] is True
    arquivo = tmp_path / "ws" / "coder" / "Doubt_Artifact_context_engineer.md"
    assert arquivo.is_file()
 
 
# -------------------------------------------------------------------
# tool_emitir_manifesto_bloqueado
# -------------------------------------------------------------------
 
def test_tool_emitir_manifesto_bloqueado_grava_disco_e_state(tmp_path, monkeypatch):
    """Grava manifesto com status=blocked em disco e no state via tool_context."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    coder_ws = tmp_path / "ws" / "coder"
    coder_ws.mkdir(parents=True)
 
    tool_ctx = MagicMock()
    tool_ctx.state = {}
 
    with patch(
        "shared.tools.coding_tools.context_engineer_tools.get_agent_workspace",
        return_value=coder_ws,
    ), patch(
        "shared.tools.coding_tools.context_engineer_tools.get_workspace_root",
        return_value=tmp_path / "ws",
    ):
        from shared.tools.coding_tools.context_engineer_tools import tool_emitir_manifesto_bloqueado
        result = tool_emitir_manifesto_bloqueado(
            motivo="Artefatos mínimos de requisitos ausentes",
            tool_context=tool_ctx,
        )
 
    assert result["sucesso"] is True
    assert result["status"] == "blocked"
    assert (coder_ws / "manifest.json").exists()
    data = json.loads((coder_ws / "manifest.json").read_text(encoding="utf-8"))
    assert data["phase"] == "coding"
    assert data["status"] == "blocked"
    assert data["summary"] == "Artefatos mínimos de requisitos ausentes"
    assert "coding_manifest" in tool_ctx.state
    assert tool_ctx.state["coding_manifest"]["status"] == "blocked"
 
 
# -------------------------------------------------------------------
# aguardar_resolucao_bloqueio (HITL)
# -------------------------------------------------------------------
 
def test_aguardar_resolucao_bloqueio_e_long_running():
    """aguardar_resolucao_bloqueio deve ser LongRunningFunctionTool."""
    from google.adk.tools import LongRunningFunctionTool
    from src.agents.workflow_coding_review.context_engineer.agent import agent
    hitl_tools = [
        t for t in agent.tools
        if isinstance(t, LongRunningFunctionTool)
    ]
    assert len(hitl_tools) == 1
    assert getattr(hitl_tools[0], "func", None).__name__ == "aguardar_resolucao_bloqueio"
 
 
@pytest.mark.asyncio
async def test_aguardar_resolucao_bloqueio_retorna_none():
    """aguardar_resolucao_bloqueio retorna None para pausar o pipeline."""
    from shared.tools.coding_tools.context_engineer_tools import aguardar_resolucao_bloqueio
    result = await aguardar_resolucao_bloqueio(
        fase_bloqueada="requirements",
        motivo="Manifesto ausente",
        acao_necessaria="Reprocessar requirements",
    )
    assert result is None