"""Cobertura da estrutura base do subagente de testes unitários."""

import json

import pytest

from shared.testing import inspect_unit_test_project, list_unit_test_profiles
from src.agents.qa_agent.subagents.unit_test_generator import orchestration


def test_registry_implementa_stacks_unitarias_prioritarias():
    profiles = list_unit_test_profiles()

    implemented = {
        profile["profile_id"] for profile in profiles if profile["implemented"]
    }

    assert implemented == {
        "python-pytest",
        "node-vitest",
        "node-jest",
        "node-node-test",
        "node-mocha",
        "java-junit",
        "go-testing",
    }
    assert {
        profile["profile_id"] for profile in profiles if not profile["implemented"]
    } == {
        "node-unconfigured",
    }


def test_inspector_detecta_python_pytest(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "sample"\n', encoding="utf-8"
    )
    source = tmp_path / "src"
    source.mkdir()
    (source / "calculator.py").write_text(
        "def add(a, b): return a + b\n", encoding="utf-8"
    )

    result = inspect_unit_test_project(tmp_path)

    assert result["status"] == "suportado"
    assert result["perfil"]["profile_id"] == "python-pytest"
    assert "src/calculator.py" in result["arquivos_fonte"]
    assert result["bloqueios"] == []


def test_inspector_identifica_vitest_como_suportado(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"devDependencies": {"vitest": "latest"}}), encoding="utf-8"
    )
    (tmp_path / "service.ts").write_text("export const ok = true;\n", encoding="utf-8")

    result = inspect_unit_test_project(tmp_path)

    assert result["status"] == "suportado"
    assert result["perfil"]["profile_id"] == "node-vitest"
    assert result["bloqueios"] == []


def test_stack_typescript_declarada_preserva_framework_detectado(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"devDependencies": {"vitest": "latest"}}), encoding="utf-8"
    )

    result = inspect_unit_test_project(tmp_path, declared_stack="typescript")

    assert result["perfil"]["profile_id"] == "node-vitest"
    assert result["status"] == "suportado"


@pytest.mark.parametrize(
    ("marker", "source_name", "profile_id"),
    [
        ("pom.xml", "Calculator.java", "java-junit"),
        ("go.mod", "calculator.go", "go-testing"),
    ],
)
def test_inspector_detecta_java_e_go_como_suportados(
    tmp_path, marker, source_name, profile_id
):
    (tmp_path / marker).write_text("config\n", encoding="utf-8")
    (tmp_path / source_name).write_text("source\n", encoding="utf-8")

    result = inspect_unit_test_project(tmp_path)

    assert result["status"] == "suportado"
    assert result["perfil"]["profile_id"] == profile_id


def test_inspector_bloqueia_empate_entre_stacks(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='sample'\n", encoding="utf-8"
    )
    (tmp_path / "package.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "app.ts").write_text("export const value = 1;\n", encoding="utf-8")

    result = inspect_unit_test_project(tmp_path)

    assert result["status"] == "bloqueado"
    assert result["perfil"] is None
    assert result["bloqueios"][0]["codigo"] == "STACK_AMBIGUA"


def test_inspector_aceita_stack_declarada_sem_codigo(tmp_path):
    result = inspect_unit_test_project(tmp_path, declared_stack="python")

    assert result["status"] == "suportado"
    assert result["perfil"]["profile_id"] == "python-pytest"
    assert result["confianca"] == 1.0


def test_tool_de_inspecao_bloqueia_workspace_externo(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    result = orchestration.inspecionar_projeto_unitario(
        workspace_projeto=str(tmp_path / "outside")
    )

    assert result["status"] == "bloqueado"
    assert result["bloqueios"][0]["codigo"] == "ENTRADA_INSPECAO_INVALIDA"


def test_fluxo_python_gera_e_executa_sem_alterar_runner(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    project = workspace / "coder" / "src"
    project.mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        "[project]\nname='sample'\n", encoding="utf-8"
    )
    (project / "calculator.py").write_text(
        "def add(a, b): return a + b\n", encoding="utf-8"
    )
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    test_path = workspace / "tests" / "inputs" / "rf_001" / "test_rf_001.py"
    generation = {
        "status": "concluido",
        "resumo": {"total": 1, "sucessos": 1, "bloqueados": 0, "falhas": 0},
        "detalhes": [
            {
                "id_artefato": "RF-001",
                "status": "sucesso",
                "fluxo": "A",
                "arquivo_gerado": str(test_path),
            }
        ],
    }
    monkeypatch.setattr(
        orchestration, "receber_requisitos", lambda _payload: generation
    )
    monkeypatch.setattr(
        orchestration,
        "executar_pytest_tool",
        lambda path: {
            "status": "sucesso",
            "tipo_teste": "pytest",
            "testes_gerados": [{"arquivo": path}],
            "cobertura": {"percentual": 100.0},
        },
    )

    result = orchestration.gerar_testes_unitarios(
        json.dumps(
            {
                "id_artefato": "RF-001",
                "tipo": "RF",
                "conteudo": "Somar dois números.",
                "modulo": "calculator",
            }
        )
    )

    assert result["status"] == "sucesso"
    assert result["perfil"]["profile_id"] == "python-pytest"
    assert result["resumo"]["executados"] == 1
    assert result["arquivos_gerados"] == [str(test_path)]
    assert result["detalhes"][0]["resultado_execucao"]["status"] == "sucesso"


def test_fluxo_python_normaliza_resumo_do_workflow_como_conteudo(
    tmp_path, monkeypatch
):
    workspace = tmp_path / "workspace"
    project = workspace / "coder" / "src"
    project.mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        "[project]\nname='sample'\n", encoding="utf-8"
    )
    (project / "calculator.py").write_text(
        "def add(a, b): return a + b\n", encoding="utf-8"
    )
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    captured = {}

    def fake_receive(payload):
        captured["artifacts"] = json.loads(payload)
        return {"status": "concluido", "detalhes": []}

    monkeypatch.setattr(orchestration, "receber_requisitos", fake_receive)

    result = orchestration.gerar_testes_unitarios(
        json.dumps(
            {
                "resumo_do_requisito": (
                    "Somar dois números e lançar ValueError na divisão por zero."
                ),
                "objetivo_qa": "Executar somente testes unitários.",
                "arquivos_relevantes": [
                    "workspace_output/coder/src/calculator.py"
                ],
            }
        )
    )

    assert result["perfil"]["profile_id"] == "python-pytest"
    assert captured["artifacts"][0]["conteudo"].startswith("Somar dois números")
    assert captured["artifacts"][0]["arquivos_apoio"] == [
        {"path": "coder/src/calculator.py"}
    ]


def test_fluxo_sem_codigo_gera_esqueleto_apenas_com_stack_declarada(
    tmp_path, monkeypatch
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    generation = {
        "status": "concluido",
        "resumo": {"total": 1, "sucessos": 1, "bloqueados": 0, "falhas": 0},
        "detalhes": [
            {
                "id_artefato": "RF-002",
                "status": "sucesso",
                "fluxo": "B",
                "arquivo_gerado": str(
                    workspace / "tests" / "inputs" / "rf_002" / "test_rf_002.py"
                ),
            }
        ],
    }
    monkeypatch.setattr(
        orchestration, "receber_requisitos", lambda _payload: generation
    )

    def fail_if_called(_path):
        pytest.fail("pytest_runner não deve executar esqueletos")

    monkeypatch.setattr(orchestration, "executar_pytest_tool", fail_if_called)

    result = orchestration.gerar_testes_unitarios(
        json.dumps(
            {
                "id_artefato": "RF-002",
                "tipo": "RF",
                "conteudo": "Validar senha.",
                "modulo": "auth",
            }
        ),
        stack_declarada="python",
    )

    assert result["status"] == "sucesso"
    assert result["resumo"]["executados"] == 0
    assert result["detalhes"][0]["resultado_execucao"] is None


def test_fluxo_node_usa_gerador_e_executor_do_perfil(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    project = workspace / "coder" / "src"
    project.mkdir(parents=True)
    (project / "package.json").write_text(
        json.dumps({"devDependencies": {"vitest": "latest"}}), encoding="utf-8"
    )
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    test_path = project / "tests" / "unit" / "rf_003.test.ts"
    captured = {}

    def fake_profile_generation(profile_id, artifacts, project_root):
        captured.update(
            profile_id=profile_id,
            artifacts=artifacts,
            project_root=project_root,
        )
        return {
            "status": "concluido",
            "detalhes": [
                {
                    "id_artefato": "RF-003",
                    "status": "sucesso",
                    "fluxo": "A",
                    "arquivo_gerado": str(test_path),
                    "resultado_execucao": {"status": "sucesso"},
                }
            ],
        }

    monkeypatch.setattr(
        orchestration, "gerar_testes_do_perfil", fake_profile_generation
    )

    result = orchestration.gerar_testes_unitarios(
        json.dumps(
            {
                "id_artefato": "RF-003",
                "tipo": "RF",
                "conteudo": "Validar serviço.",
                "modulo": "service",
            }
        )
    )

    assert result["status"] == "sucesso"
    assert result["inspecao"]["perfil"]["profile_id"] == "node-vitest"
    assert result["resumo"]["executados"] == 1
    assert captured["profile_id"] == "node-vitest"
    assert captured["project_root"] == project.resolve()


def test_agent_e_planner_expoem_fluxos_unitario_e_bases_por_perfis():
    from shared.tools.planner_tools import list_available_tools
    from src.agents.qa_agent.agent import agent as qa_agent
    from src.agents.workflow_qa.agent import agent as qa_pipeline

    qa_tools = {tool.name for tool in qa_agent.tools}
    pipeline_tools = {tool.name for tool in qa_pipeline.tools}
    planner_tools = {item["name"] for item in list_available_tools("qa_agent")["tools"]}

    assert "unit_test_generator" in qa_tools
    assert "integration_tests_agent" in qa_tools
    assert "e2e_test_generator" in qa_tools
    assert "executar_testes_de_integracao" not in qa_tools
    assert "gerar_testes_unitarios" in pipeline_tools
    assert "integration_tests_agent" in pipeline_tools
    assert "executar_testes_de_integracao" not in pipeline_tools
    assert "unit_test_generator" in planner_tools
    assert "integration_tests_agent" in planner_tools
    assert "e2e_test_generator" in planner_tools
    assert "executar_testes_de_integracao" not in planner_tools
    assert "receber_requisitos" not in qa_tools
    assert "receber_requisitos" not in pipeline_tools
