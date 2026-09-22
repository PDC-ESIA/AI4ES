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
        "tool_salvar_macro_context_cr",
        "tool_ler_artefatos",
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
        requirement_refs=["HU-001", "RNF-001"],
        design_refs=["design/analise_tecnica_HU-001.md"],
    )
    assert task.id == "TASK-001"
    assert task.business_rules == []
    assert task.contract.outputs == ["src/auth.py"]
    assert task.requirement_refs == ["HU-001", "RNF-001"]
 
 
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
 
 
def test_schemas_tasks_output_aceita_caminho_bloqueado():
    """O prompt manda PARAR sem gerar task — isso é resultado válido, não erro."""
    from src.agents.workflow_coding_review.context_engineer.schemas import TasksOutput
 
    saida = TasksOutput(
        status="bloqueado",
        bloqueio="Análise técnica ausente; a fase design deve ser reprocessada.",
    )
 
    assert saida.tasks == []
    assert saida.macro_context is None
    assert saida.bloqueado
 
 
def test_schemas_tasks_output_aceita_resposta_livre_do_modelo():
    """O modelo NÃO enxerga o schema — recusar vocabulário fora do enum recriaria o crash."""
    from src.agents.workflow_coding_review.context_engineer.schemas import TasksOutput
 
    saida = TasksOutput.model_validate_json(
        json.dumps({
            "status": "EXECUÇÃO PARALISADA",
            "motivo": "Análise técnica ausente no workspace de design",
            "acao": "A fase design deve ser reprocessada antes de continuar",
        })
    )
 
    assert saida.status == "EXECUÇÃO PARALISADA"
    assert saida.bloqueado
 
 
def test_envelope_bloqueado_vira_input_invalido_no_iterator():
    """O bloqueio segue o caminho fail-closed em vez de derrubar o pipeline."""
    from src.agents.workflow_coding_review.context_engineer.schemas import TasksOutput
    from src.agents.workflow_coding_review.task_iterator import (
        calcular_cobertura,
        validar_envelope_de_tasks,
    )
 
    envelope = TasksOutput(status="bloqueado", bloqueio="sem design").model_dump(
        exclude_none=True
    )
 
    tasks, erros = validar_envelope_de_tasks(envelope)
 
    assert tasks == []
    assert [erro["type"] for erro in erros] == ["lista_vazia"]
    assert calcular_cobertura(False, [], [], []) is False
 
 
def test_schemas_tasks_output_status_default_no_caminho_normal():
    """Quem gera tasks não precisa declarar status — o default cobre."""
    from src.agents.workflow_coding_review.context_engineer.schemas import (
        Contract, MacroContext, Task, TasksOutput,
    )
 
    saida = TasksOutput(
        macro_context=MacroContext(summary="X", tech_stack=["Python"], global_rules=["Y"]),
        tasks=[Task(id="TASK-001", type="component", complexity="low", description="Z",
                    acceptance_criteria=["A"], contract=Contract(), requirement_id="RF-001")],
    )
 
    assert saida.status == "concluido"
    assert not saida.bloqueado
 
 
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
# tool_ler_artefatos — via paths do manifesto
# -------------------------------------------------------------------
 
def test_tool_ler_artefatos_com_paths_validos(tmp_path, monkeypatch):
    """Lê artefatos corretamente quando paths são fornecidos."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta_hus = tmp_path / "ws" / "requirements" / "HUs"
    pasta_rfs = tmp_path / "ws" / "requirements" / "RFs"
    pasta_hus.mkdir(parents=True)
    pasta_rfs.mkdir(parents=True)
    (pasta_hus / "HU-001.md").write_text("# HU-001", encoding="utf-8")
    (pasta_rfs / "RF-001.md").write_text("# RF-001", encoding="utf-8")
 
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_artefatos
    paths = _paths_json(["requirements/HUs/HU-001.md", "requirements/RFs/RF-001.md"])
    result = tool_ler_artefatos(paths_json=paths, fase="requirements")
    assert result["sucesso"] is True
    assert result["total_lidos"] == 2
    assert result["fallback"] is False
 
 
def test_tool_ler_artefatos_preserva_tipo_manifesto(tmp_path, monkeypatch):
    """tipo_manifesto do manifesto é preservado no artefato retornado."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta_rfs = tmp_path / "ws" / "requirements" / "RFs"
    pasta_rfs.mkdir(parents=True)
    (pasta_rfs / "RF-001.md").write_text("# RF-001", encoding="utf-8")
 
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_artefatos
    paths = json.dumps([{"path": "requirements/RFs/RF-001.md", "tipo": "RF"}])
    result = tool_ler_artefatos(paths_json=paths, fase="requirements")
    assert result["sucesso"] is True
    assert result["artefatos"][0]["tipo_manifesto"] == "RF"
 
 
def test_tool_ler_artefatos_fallback_workspace(tmp_path, monkeypatch):
    """Usa fallback de leitura direta quando paths_json está vazio."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta = tmp_path / "ws" / "requirements" / "RFs"
    pasta.mkdir(parents=True)
    (pasta / "RF-001.md").write_text("# RF-001", encoding="utf-8")
 
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_artefatos
    result = tool_ler_artefatos(
        paths_json="[]",
        fase="requirements",
        pasta_fallback="requirements",
    )
    assert result["sucesso"] is True
    assert result["total_lidos"] >= 1
    assert result["fallback"] is True
 
 
def test_tool_ler_artefatos_fallback_pasta_inexistente(tmp_path, monkeypatch):
    """Retorna erro quando fallback aponta para pasta inexistente."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_artefatos
    result = tool_ler_artefatos(
        paths_json="[]",
        fase="requirements",
        pasta_fallback="requirements",
    )
    assert result["sucesso"] is False
    assert result["fallback"] is True
 
 
def test_tool_ler_artefatos_path_traversal_rejeitado(tmp_path, monkeypatch):
    """Paths com .. são rejeitados."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_artefatos
    paths = _paths_json(["../../etc/passwd"])
    result = tool_ler_artefatos(paths_json=paths, fase="requirements")
    assert result["sucesso"] is True
    assert result["erros_leitura"] is not None
    assert any(".." in e or "inválido" in e for e in result["erros_leitura"])
 
 
def test_tool_ler_artefatos_design_via_paths(tmp_path, monkeypatch):
    """Lê artefatos de design via paths do manifesto de design."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta = tmp_path / "ws" / "design" / "analysis"
    pasta.mkdir(parents=True)
    (pasta / "analise_tecnica_HU-001.md").write_text("# Análise", encoding="utf-8")
 
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_artefatos
    paths = json.dumps([{
        "path": "workspace_output/design/analysis/analise_tecnica_HU-001.md",
        "tipo": "analise"
    }])
    result = tool_ler_artefatos(paths_json=paths, fase="design")
    assert result["sucesso"] is True
    assert result["total_lidos"] == 1
    assert result["artefatos"][0]["tipo_manifesto"] == "analise"
    assert result["fallback"] is False
 
 
def test_tool_ler_artefatos_design_fallback(tmp_path, monkeypatch):
    """Usa fallback de leitura direta do workspace para design."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta = tmp_path / "ws" / "design"
    pasta.mkdir(parents=True)
    (pasta / "analise_tecnica_HU-001.md").write_text("# Análise", encoding="utf-8")
 
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_artefatos
    result = tool_ler_artefatos(
        paths_json="[]",
        fase="design",
        pasta_fallback="workspace_output/design",
    )
    assert result["sucesso"] is True
    assert result["total_lidos"] >= 1
    assert result["fallback"] is True
 
 
def test_tool_ler_artefatos_sem_pasta_fallback_retorna_erro(tmp_path, monkeypatch):
    """Retorna erro quando paths_json vazio e pasta_fallback não definida."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_artefatos
    result = tool_ler_artefatos(paths_json="[]", fase="requirements")
    assert result["sucesso"] is False
    assert "pasta_fallback" in result["erro"]
 
 
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
            motivo="Nenhum requisito funcional implementável encontrado",
            tool_context=tool_ctx,
        )
 
    assert result["sucesso"] is True
    assert result["status"] == "blocked"
    assert (coder_ws / "manifest.json").exists()
    data = json.loads((coder_ws / "manifest.json").read_text(encoding="utf-8"))
    assert data["phase"] == "coding"
    assert data["status"] == "blocked"
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