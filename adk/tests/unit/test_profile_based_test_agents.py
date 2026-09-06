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
    _artefatos_com_handoff,
    inspecionar_projeto_e2e,
    preparar_testes_e2e,
)
from src.agents.qa_agent.subagents.e2e_test_generator.tools.extrair_contrato_textual import (
    extrair_contrato_textual_e2e,
)
from src.agents.qa_agent.subagents.integration_tests_agent.orchestration import (
    inspecionar_projeto_integracao,
    preparar_testes_integracao,
)

_STACKS = {"python", "node", "java", "go"}


def test_e2e_extrai_jornada_natural_de_artefato_json():
    prompt = (
        "Execute E2E na URL http://127.0.0.1:8765/index.html e valide este fluxo "
        "ponta a ponta: verificar o título 'Aplicação pronta', preencher o campo "
        "'Nome' com 'QA', clicar em 'Confirmar' e verificar a mensagem 'Olá, QA!'. "
        "Gere e execute o teste."
    )

    result = extrair_contrato_textual_e2e(
        [{"id_artefato": "E2E-001", "tipo": "RF", "conteudo": prompt}]
    )

    assert result["base_url"] == "http://127.0.0.1:8765/index.html"
    assert result["rotas_ou_telas"] == [
        {
            "nome": "Jornada E2E",
            "rota": "http://127.0.0.1:8765/index.html",
            "passos_automacao": [
                {
                    "acao": "verificar_visivel",
                    "localizador": {"tipo": "text", "valor": "Aplicação pronta"},
                },
                {
                    "acao": "preencher",
                    "localizador": {"tipo": "label", "valor": "Nome"},
                    "chave_dado": "nome",
                },
                {
                    "acao": "clicar",
                    "localizador": {"tipo": "text", "valor": "Confirmar"},
                },
                {
                    "acao": "verificar_visivel",
                    "localizador": {"tipo": "text", "valor": "Olá, QA!"},
                },
            ],
        }
    ]
    assert result["dados_teste"] == {"nome": "QA"}


def test_e2e_preserva_requisito_original_quando_modelo_envia_resumo():
    plano = json.dumps({"handoff_context": {"entrada_original": "Fluxo E2E integral."}})
    resumo = json.dumps(
        [{"id_artefato": "RES-001", "tipo": "RF", "conteudo": "Resumo."}]
    )

    result = json.loads(_artefatos_com_handoff(resumo, plano))

    assert result == [
        {"id_artefato": "RES-001", "tipo": "RF", "conteudo": "Resumo."},
        {
            "id_artefato": "E2E-HANDOFF-001",
            "tipo": "RF",
            "conteudo": "Fluxo E2E integral.",
        },
    ]


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


def test_e2e_recupera_plano_e_requisito_do_estado_da_sessao(
    tmp_path,
    monkeypatch,
):
    workspace = tmp_path / "workspace"
    project = workspace / "coder" / "src"
    project.mkdir(parents=True)
    (project / "package.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace))
    original_request = (
        "Use Playwright na URL http://127.0.0.1:8765/index.html e valide este "
        "fluxo ponta a ponta: verificar o título 'Aplicação pronta', preencher "
        "o campo 'Nome' com 'QA', clicar em 'Confirmar' e verificar a mensagem "
        "'Olá, QA!'."
    )
    plan = {
        "tools": ["e2e_test_generator"],
        "lifecycle": {
            "status": "planejado_para_execucao",
            "execution_allowed": True,
            "next_step": "executar_plano",
        },
        "handoff_context": {
            "entrada_original": original_request,
        },
    }
    tool_context = type(
        "FakeToolContext",
        (),
        {"state": {"last_action_plan": json.dumps(plan)}},
    )()
    captured = {}

    def fake_adapter(profile_id, artifacts, project_root, **kwargs):
        captured.update(
            profile_id=profile_id,
            artifacts=artifacts,
            project_root=project_root,
            kwargs=kwargs,
        )
        return {
            "tipo_saida": "executado",
            "arquivos_gerados": ["tests/e2e/e2e-001.spec.ts"],
            "resultado_execucao": {
                "status": "aprovado",
                "codigo_saida": 0,
                "testes_executados": 1,
                "testes_aprovados": 1,
            },
            "bloqueios": [],
        }

    monkeypatch.setattr(
        "src.agents.qa_agent.subagents.e2e_test_generator."
        "orchestration.run_e2e_profile_adapter",
        fake_adapter,
    )

    result = preparar_testes_e2e(
        artefatos_json="[]",
        plano_acao="plano incompleto criado pelo modelo",
        tipo_sistema="aplicacao-web-invalida",
        base_url="http://127.0.0.1:9999/invalida",
        rotas_ou_telas_json=json.dumps(
            [
                {
                    "nome": "Resumo do modelo",
                    "rota": "/",
                    "passos_automacao": [{"acao": "acao_inventada"}],
                }
            ]
        ),
        tool_context=tool_context,
    )

    assert result["status"] == "sucesso"
    assert captured["profile_id"] == "node-e2e"
    assert captured["kwargs"]["plano_acao"] == json.dumps(plan)
    assert captured["artifacts"] == [
        {
            "id_artefato": "E2E-001",
            "tipo": "RF",
            "conteudo": original_request,
        }
    ]
    assert captured["kwargs"]["tipo_sistema"] == "web"
    assert captured["kwargs"]["base_url"] == "http://127.0.0.1:8765/index.html"
    assert json.loads(captured["kwargs"]["rotas_ou_telas_json"])[0][
        "passos_automacao"
    ] == [
        {
            "acao": "verificar_visivel",
            "localizador": {"tipo": "text", "valor": "Aplicação pronta"},
        },
        {
            "acao": "preencher",
            "localizador": {"tipo": "label", "valor": "Nome"},
            "chave_dado": "nome",
        },
        {
            "acao": "clicar",
            "localizador": {"tipo": "text", "valor": "Confirmar"},
        },
        {
            "acao": "verificar_visivel",
            "localizador": {"tipo": "text", "valor": "Olá, QA!"},
        },
    ]


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
            {
                "obter_plano_acao",
                "inspecionar_projeto_e2e",
                "preparar_testes_e2e",
            },
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
