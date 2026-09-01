"""Contratos das bases orientadas por perfis de integração e E2E."""

import json

import pytest

from shared.testing import (
    E2E_TEST_PROFILES,
    INTEGRATION_TEST_PROFILES,
    StackTestProfile,
    TestProfileRegistry as ProfileRegistry,
    inspect_test_project,
)
from shared.testing.coder_stack import load_coder_stack, resolve_coder_stack
from src.agents.qa_agent.subagents.e2e_test_generator.orchestration import (
    inspecionar_projeto_e2e,
    preparar_testes_e2e,
)
from src.agents.qa_agent.subagents.integration_tests_agent.orchestration import (
    inspecionar_projeto_integracao,
    preparar_testes_integracao,
)

_STACKS = {"python", "node", "java", "go"}


def test_catalogos_registram_as_quatro_familias_ativas_do_coder():
    assert {profile["stack"] for profile in E2E_TEST_PROFILES.list()} == _STACKS
    assert {profile["stack"] for profile in INTEGRATION_TEST_PROFILES.list()} == _STACKS
    assert all(profile["implemented"] for profile in E2E_TEST_PROFILES.list())
    assert all(profile["implemented"] for profile in INTEGRATION_TEST_PROFILES.list())


def test_typescript_resolve_para_node_nos_dois_niveis():
    assert E2E_TEST_PROFILES.resolve("TypeScript")[0].profile_id == "node-e2e"
    assert (
        INTEGRATION_TEST_PROFILES.resolve("TypeScript")[0].profile_id
        == "node-integration"
    )


@pytest.mark.parametrize(
    ("registry", "declared_stack", "expected_profile"),
    [
        (E2E_TEST_PROFILES, "Python/FastAPI", "python-e2e"),
        (E2E_TEST_PROFILES, "TypeScript", "node-e2e"),
        (INTEGRATION_TEST_PROFILES, "Java/Spring", "java-integration"),
        (INTEGRATION_TEST_PROFILES, "Go", "go-integration"),
    ],
)
def test_perfis_registrados_estao_disponiveis(
    tmp_path, registry, declared_stack, expected_profile
):
    result = inspect_test_project(
        tmp_path,
        registry,
        declared_stack=declared_stack,
    )

    assert result["status"] == "suportado"
    assert result["perfil"]["profile_id"] == expected_profile
    assert result["bloqueios"] == []


def test_contrato_comum_aceita_adaptador_implementado(tmp_path):
    (tmp_path / "sample.manifest").write_text("demo", encoding="utf-8")
    (tmp_path / "service.demo").write_text("source", encoding="utf-8")
    profile = StackTestProfile(
        profile_id="demo-integration",
        test_type="integracao",
        stack="demo",
        framework="demo-test",
        source_suffixes=(".demo",),
        marker_files=("sample.manifest",),
        test_file_pattern="<component>.integration.demo",
        generator="demo_generator",
        executor="demo_runner",
        implemented=True,
    )
    registry = ProfileRegistry("integracao", (profile,))

    result = inspect_test_project(tmp_path, registry)

    assert result["status"] == "suportado"
    assert result["perfil"]["profile_id"] == "demo-integration"


@pytest.mark.parametrize(
    (
        "inspect_tool",
        "prepare_tool",
        "adapter_path",
        "adapter_result",
        "test_type",
        "expected_profile",
    ),
    [
        (
            inspecionar_projeto_e2e,
            preparar_testes_e2e,
            (
                "src.agents.qa_agent.subagents.e2e_test_generator."
                "orchestration.run_e2e_profile_adapter"
            ),
            {
                "tipo_saida": "executado",
                "arquivos_gerados": ["tests/e2e/rf_001.spec.ts"],
                "resultado_execucao": {
                    "status": "aprovado",
                    "codigo_saida": 0,
                    "testes_executados": 1,
                    "testes_aprovados": 1,
                },
                "bloqueios": [],
            },
            "e2e",
            "node-e2e",
        ),
        (
            inspecionar_projeto_integracao,
            preparar_testes_integracao,
            (
                "src.agents.qa_agent.subagents.integration_tests_agent."
                "orchestration.run_integration_profile_adapter"
            ),
            {
                "status": "concluido",
                "detalhes": [
                    {
                        "id_artefato": "RF-001",
                        "status": "gerado",
                        "arquivo_gerado": "tests/integration/rf_001.test.ts",
                        "resultado_execucao": {
                            "status": "sucesso",
                            "perfil": "node-integration",
                            "framework": "node:test",
                            "comando": ["node", "--test"],
                            "codigo_saida": 0,
                            "stdout": "# tests 1\n# pass 1\n# fail 0",
                            "stderr": "",
                            "bloqueios": [],
                        },
                    }
                ],
            },
            "integracao",
            "node-integration",
        ),
    ],
)
def test_tools_reconhecem_typescript_e_retornam_resultado_normalizado(
    tmp_path,
    monkeypatch,
    inspect_tool,
    prepare_tool,
    adapter_path,
    adapter_result,
    test_type,
    expected_profile,
):
    workspace = tmp_path / "workspace"
    project = workspace / "coder" / "src"
    project.mkdir(parents=True)
    (project / "package.json").write_text("{}\n", encoding="utf-8")
    (project / "service.ts").write_text("export const ok = true;\n", encoding="utf-8")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    monkeypatch.setattr(adapter_path, lambda *_args, **_kwargs: adapter_result)

    inspection = inspect_tool(
        workspace_projeto=str(project),
        stack_declarada="TypeScript",
    )
    result = prepare_tool(
        artefatos_json=json.dumps(
            {"id_artefato": "RF-001", "conteudo": "Validar fluxo."}
        ),
        workspace_projeto=str(project),
        stack_declarada="TypeScript",
    )

    assert inspection["perfil"]["profile_id"] == expected_profile
    assert inspection["status"] == "suportado"
    assert inspection["bloqueios"] == []
    assert result["status"] == "sucesso"
    assert result["tipo_teste"] == test_type
    assert result["perfil"]["profile_id"] == expected_profile
    assert result["resumo"]["sucessos"] == 1
    assert result["resultado_bruto"] == adapter_result


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (["Python", "FastAPI"], "python"),
        (["Node.js", "Express", "TypeScript"], "node"),
        ("Java/Spring", "java"),
        (["Go"], "go"),
        (["Python", "TypeScript"], ""),
        (["a definir"], ""),
    ],
)
def test_normaliza_somente_stack_declarada_pelo_coder(value, expected):
    assert resolve_coder_stack(value) == expected


def test_carrega_stack_do_macro_context(tmp_path):
    macro = tmp_path / "_macro_context.json"
    macro.write_text(
        json.dumps({"tech_stack": ["Node.js", "Express", "TypeScript"]}),
        encoding="utf-8",
    )

    assert load_coder_stack(macro) == "node"


def test_agente_usa_stack_do_handoff_do_coder_sem_interpretar_codigo(
    tmp_path, monkeypatch
):
    workspace = tmp_path / "workspace"
    project = workspace / "coder" / "src"
    tasks = workspace / "coder" / "tasks"
    project.mkdir(parents=True)
    tasks.mkdir(parents=True)
    (tasks / "_macro_context.json").write_text(
        json.dumps({"tech_stack": ["Node.js", "Express", "TypeScript"]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))

    result = inspecionar_projeto_e2e(workspace_projeto=str(project))

    assert result["perfil"]["profile_id"] == "node-e2e"
    assert result["status"] == "suportado"
    assert result["bloqueios"] == []
    assert "stack_declarada:node" in result["evidencias"]


@pytest.mark.parametrize(
    ("agent_path", "tool_names"),
    [
        (
            "src.agents.qa_agent.subagents.e2e_test_generator.agent",
            {"inspecionar_projeto_e2e", "preparar_testes_e2e"},
        ),
        (
            "src.agents.qa_agent.subagents.integration_tests_agent.agent",
            {"inspecionar_projeto_integracao", "preparar_testes_integracao"},
        ),
    ],
)
def test_agentes_registram_apenas_tools_baseadas_em_perfis(agent_path, tool_names):
    module = __import__(agent_path, fromlist=["agent"])

    assert {tool.name for tool in module.agent.tools} == tool_names
