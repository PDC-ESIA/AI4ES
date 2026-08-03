"""Tests para src/agents/context_engineer/ — descoberta + schemas + tools."""
 
import json
from pathlib import Path
 
import pytest
 
 
def test_context_engineer_root_agent_importavel():
    from src.agents.context_engineer import root_agent
    assert root_agent is not None
    assert root_agent.name == "context_engineer"
 
 
def test_context_engineer_tem_output_schema():
    from src.agents.context_engineer import root_agent
    from src.agents.context_engineer.schemas import TasksOutput
    assert root_agent.output_schema == TasksOutput
 
 
def test_context_engineer_tem_tools_esperadas():
    from src.agents.context_engineer import root_agent
    tool_names = {getattr(getattr(t, "func", t), "__name__", "") for t in root_agent.tools}
    assert {
        "tool_salvar_task",
        "tool_ler_requirements",
        "tool_ler_design",
        "tool_gerar_doubt_artifact",
    } <= tool_names
 
 
def test_schemas_macro_context_minimal():
    from src.agents.context_engineer.schemas import MacroContext
    mc = MacroContext(
        summary="Sistema de autenticação JWT",
        tech_stack=["Python", "FastAPI"],
        global_rules=["RESTful"],
    )
    assert mc.summary.startswith("Sistema")
    assert len(mc.tech_stack) == 2
 
 
def test_schemas_task_com_contract():
    from src.agents.context_engineer.schemas import Task, Contract
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
    from src.agents.context_engineer.schemas import Task, Contract
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
    from src.agents.context_engineer.schemas import Contract
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
 
 
def test_schemas_contract_interfaces_aceita_lista_e_string():
    from src.agents.context_engineer.schemas import Contract
 
    as_list = Contract.model_validate({
        "inputs": [],
        "outputs": [],
        "interfaces": ["GET /users", "DELETE /users/<id>"],
    })
    assert as_list.interfaces == ["GET /users", "DELETE /users/<id>"]
 
    as_string = Contract.model_validate({
        "inputs": [],
        "outputs": [],
        "interfaces": "POST /auth/login",
    })
    assert as_string.interfaces == ["POST /auth/login"]
 
 
def test_schemas_tasks_output_completo():
    from src.agents.context_engineer.schemas import TasksOutput, MacroContext, Task, Contract
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
 
 
def test_tool_salvar_task_persiste_json(tmp_path, monkeypatch):
    """tool_salvar_task escreve JSON em workspace/tasks/<id>.json."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from src.agents.context_engineer.tools import tool_salvar_task
    task_json = json.dumps({
        "id": "TASK-001",
        "type": "backend",
        "description": "Criar endpoint",
    })
    result = tool_salvar_task("TASK-001", task_json)
    assert result["sucesso"] is True
    arquivo = tmp_path / "ws" / "tasks" / "TASK-001.json"
    assert arquivo.is_file()
    conteudo = json.loads(arquivo.read_text(encoding="utf-8"))
    assert conteudo["id"] == "TASK-001"
 
 
def test_tool_salvar_task_id_invalido_rejeita(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from src.agents.context_engineer.tools import tool_salvar_task
    result = tool_salvar_task("INVALID-001", json.dumps({"x": 1}))
    assert result["sucesso"] is False
    assert "TASK-" in result["erro"]
 
 
def test_tool_salvar_task_json_invalido_rejeita(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from src.agents.context_engineer.tools import tool_salvar_task
    result = tool_salvar_task("TASK-002", "not a json")
    assert result["sucesso"] is False
    assert "JSON inválido" in result["erro"] or "JSON invalido" in str(result.get("erro", ""))
 
 
def test_tool_ler_requirements_com_hu_e_rf(tmp_path, monkeypatch):
    """tool_ler_requirements lê com HUs e RFs — cenário completo."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta_hus = tmp_path / "ws" / "requirements" / "HUs"
    pasta_rfs = tmp_path / "ws" / "requirements" / "RFs"
    pasta_hus.mkdir(parents=True)
    pasta_rfs.mkdir(parents=True)
    (pasta_hus / "HU-001.md").write_text("# HU-001", encoding="utf-8")
    (pasta_rfs / "RF-001.md").write_text("# RF-001", encoding="utf-8")
    from src.agents.context_engineer.tools import tool_ler_requirements
    result = tool_ler_requirements()
    assert result["sucesso"] is True
    assert result["artefatos_minimos_presentes"] is True
    assert result["tem_hu"] is True
    assert result["total_lidos"] == 2
 
 
def test_tool_ler_requirements_so_rf_valido(tmp_path, monkeypatch):
    """tool_ler_requirements aceita cenário com apenas RF — HU ausente não bloqueia sozinha."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta_rfs = tmp_path / "ws" / "requirements" / "RFs"
    pasta_rfs.mkdir(parents=True)
    (pasta_rfs / "RF-001.md").write_text("# RF-001", encoding="utf-8")
    from src.agents.context_engineer.tools import tool_ler_requirements
    result = tool_ler_requirements()
    assert result["sucesso"] is True
    assert result["artefatos_minimos_presentes"] is True
    assert result["tem_hu"] is False
 
 
def test_tool_ler_requirements_sem_rf_bloqueia(tmp_path, monkeypatch):
    """tool_ler_requirements bloqueia quando não existe RF — único mínimo obrigatório."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta_hus = tmp_path / "ws" / "requirements" / "HUs"
    pasta_hus.mkdir(parents=True)
    (pasta_hus / "HU-001.md").write_text("# HU-001", encoding="utf-8")
    from src.agents.context_engineer.tools import tool_ler_requirements
    result = tool_ler_requirements()
    assert result["sucesso"] is True
    assert result["artefatos_minimos_presentes"] is False
    assert any("RF" in msg for msg in result["artefatos_minimos_ausentes"])
 
 
def test_tool_ler_requirements_pasta_inexistente(tmp_path, monkeypatch):
    """tool_ler_requirements retorna erro se pasta não existe."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from src.agents.context_engineer.tools import tool_ler_requirements
    result = tool_ler_requirements()
    assert result["sucesso"] is False
    assert "não encontrada" in result["erro"]
 
 
def test_tool_ler_design_com_analise(tmp_path, monkeypatch):
    """tool_ler_design detecta analise_tecnica presente."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta = tmp_path / "ws" / "design"
    pasta.mkdir(parents=True)
    (pasta / "analise_tecnica_HU-001.md").write_text("# Análise", encoding="utf-8")
    from src.agents.context_engineer.tools import tool_ler_design
    result = tool_ler_design()
    assert result["sucesso"] is True
    assert result["artefatos_minimos_presentes"] is True
 
 
def test_tool_ler_design_sem_analise(tmp_path, monkeypatch):
    """tool_ler_design detecta ausência de analise_tecnica."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    pasta = tmp_path / "ws" / "design" / "diagrams"
    pasta.mkdir(parents=True)
    (pasta / "diagrama_HU-001.mmd").write_text("graph TD", encoding="utf-8")
    from src.agents.context_engineer.tools import tool_ler_design
    result = tool_ler_design()
    assert result["sucesso"] is True
    assert result["artefatos_minimos_presentes"] is False
 
 
def test_tool_ler_design_pasta_inexistente(tmp_path, monkeypatch):
    """tool_ler_design retorna erro se pasta não existe."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    from src.agents.context_engineer.tools import tool_ler_design
    result = tool_ler_design()
    assert result["sucesso"] is False
    assert "não encontrada" in result["erro"]
 
 
def test_tool_gerar_doubt_artifact(tmp_path, monkeypatch):
    """tool_gerar_doubt_artifact persiste arquivo .md no workspace."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    (tmp_path / "ws").mkdir(parents=True)
    from src.agents.context_engineer.tools import tool_gerar_doubt_artifact
    result = tool_gerar_doubt_artifact(
        titulo="Artefatos mínimos ausentes",
        fase_bloqueada="requirements",
        descricao="Nenhum RF encontrado na pasta requirements/RFs/",
        acao_necessaria="Reprocessar a fase requirements",
    )
    assert result["sucesso"] is True
    assert result["fase_bloqueada"] == "requirements"
    arquivo = tmp_path / "ws" / "Doubt_Artifact_context_engineer.md"
    assert arquivo.is_file()
    conteudo = arquivo.read_text(encoding="utf-8")
    assert "requirements" in conteudo