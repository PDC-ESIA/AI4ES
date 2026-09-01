"""Adaptadores multistack de integração e E2E sem chamadas externas."""

import json
from subprocess import CompletedProcess

import pytest

from shared.testing import integration_adapters
from src.agents.qa_agent.subagents.e2e_test_generator import (
    profile_adapter as e2e_adapter,
)
from src.agents.qa_agent.subagents.integration_tests_agent import (
    profile_generation as integration_generation,
)


def _test_file(root, relative):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("test\n", encoding="utf-8")
    return path


def test_comando_python_de_integracao_usa_interpretador_atual(tmp_path):
    test_file = _test_file(tmp_path, "tests/integration/test_service.py")

    command, framework, blocker = integration_adapters.build_integration_command(
        "python-integration", tmp_path, test_file
    )

    assert blocker is None
    assert framework == "pytest"
    assert command[1:] == [
        "-m",
        "pytest",
        "tests/integration/test_service.py",
        "-q",
        "--tb=short",
    ]


def test_comando_node_usa_vitest_local_sem_npx(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text(
        json.dumps({"devDependencies": {"vitest": "latest"}}),
        encoding="utf-8",
    )
    entry = tmp_path / "node_modules/vitest/vitest.mjs"
    entry.parent.mkdir(parents=True)
    entry.write_text("", encoding="utf-8")
    test_file = _test_file(tmp_path, "tests/integration/service.test.ts")
    monkeypatch.setattr(integration_adapters, "_command_path", lambda _name: "/node")

    command, framework, blocker = integration_adapters.build_integration_command(
        "node-integration", tmp_path, test_file
    )

    assert blocker is None
    assert framework == "vitest"
    assert command[0] == "/node"
    assert "vitest.mjs" in command[1]
    assert "npx" not in command


def test_comando_java_usa_junit_maven(tmp_path, monkeypatch):
    (tmp_path / "pom.xml").write_text("<project />\n", encoding="utf-8")
    test_file = _test_file(
        tmp_path,
        "src/test/java/com/example/ServiceIntegrationTest.java",
    )
    test_file.write_text(
        "package com.example; class ServiceIntegrationTest {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(integration_adapters, "_command_path", lambda _name: "/mvn")

    command, framework, blocker = integration_adapters.build_integration_command(
        "java-integration", tmp_path, test_file
    )

    assert blocker is None
    assert framework == "junit-maven"
    assert command == [
        "/mvn",
        "-Dtest=com.example.ServiceIntegrationTest",
        "test",
    ]


def test_comando_go_usa_pacote_do_teste(tmp_path, monkeypatch):
    (tmp_path / "go.mod").write_text("module sample\n", encoding="utf-8")
    test_file = _test_file(tmp_path, "service/service_integration_test.go")
    monkeypatch.setattr(integration_adapters, "_command_path", lambda _name: "/go")

    command, framework, blocker = integration_adapters.build_integration_command(
        "go-integration", tmp_path, test_file
    )

    assert blocker is None
    assert framework == "go-testing"
    assert command == ["/go", "test", "-json", "./service"]


def test_execucao_de_integracao_e_sem_shell_e_define_ci(tmp_path, monkeypatch):
    test_file = _test_file(tmp_path, "tests/integration/test_service.py")
    observed = {}
    monkeypatch.setattr(
        integration_adapters,
        "build_integration_command",
        lambda *_args: (["python", "-m", "pytest"], "pytest", None),
    )

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed.update(kwargs)
        return CompletedProcess(command, 0, stdout="1 passed", stderr="")

    monkeypatch.setattr(integration_adapters.subprocess, "run", fake_run)

    result = integration_adapters.execute_integration_adapter(
        "python-integration", tmp_path, test_file
    )

    assert result["status"] == "sucesso"
    assert observed["shell"] is False
    assert observed["env"]["CI"] == "1"


@pytest.mark.parametrize(
    ("profile_id", "source_path", "source", "generated", "framework"),
    [
        (
            "python-integration",
            "app/service.py",
            "def execute(): return True\n",
            "def test_service_integration():\n    assert True\n",
            "pytest",
        ),
        (
            "node-integration",
            "src/service.ts",
            "export const execute = (): boolean => true;\n",
            "import test from 'node:test';\ntest('integration', () => {});\n",
            "node:test",
        ),
        (
            "java-integration",
            "src/main/java/com/example/Service.java",
            "package com.example; public class Service {}\n",
            (
                "package com.example;\n"
                "import org.junit.jupiter.api.Test;\n"
                "class ServiceIntegrationTest { @Test void integration() {} }\n"
            ),
            "junit",
        ),
        (
            "go-integration",
            "service.go",
            "package sample\nfunc Execute() bool { return true }\n",
            (
                "package sample\n"
                "import \"testing\"\n"
                "func TestIntegration(t *testing.T) {}\n"
            ),
            "go-testing",
        ),
    ],
)
def test_gerador_de_integracao_despacha_todos_os_perfis(
    tmp_path,
    monkeypatch,
    profile_id,
    source_path,
    source,
    generated,
    framework,
):
    source_file = tmp_path / source_path
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text(source, encoding="utf-8")
    if profile_id == "node-integration":
        (tmp_path / "package.json").write_text("{}\n", encoding="utf-8")
    observed = {}
    monkeypatch.setattr(
        integration_generation,
        "_completion_content",
        lambda *_args: generated,
    )

    def fake_execute(received_profile, root, target):
        observed.update(profile=received_profile, root=root, target=target)
        return {
            "status": "sucesso",
            "perfil": received_profile,
            "framework": framework,
            "comando": ["runner"],
            "codigo_saida": 0,
            "stdout": "1 passed",
            "stderr": "",
            "bloqueios": [],
        }

    monkeypatch.setattr(
        integration_generation,
        "execute_integration_adapter",
        fake_execute,
    )

    result = integration_generation.run_integration_profile_adapter(
        profile_id,
        [
            {
                "id_artefato": "RF-001",
                "modulo": "service",
                "conteudo": "Validar a integração do serviço.",
            }
        ],
        tmp_path,
    )

    detail = result["detalhes"][0]
    assert detail["status"] == "gerado"
    assert detail["framework"] == framework
    assert observed["profile"] == profile_id
    assert observed["target"].is_file()
    assert observed["target"].read_text(encoding="utf-8") == generated


@pytest.mark.parametrize(
    "profile_id",
    ["python-e2e", "node-e2e", "java-e2e", "go-e2e"],
)
def test_adaptador_e2e_despacha_todos_os_perfis_com_playwright(
    tmp_path, monkeypatch, profile_id
):
    observed = {}

    def fake_generate(**kwargs):
        observed.update(kwargs)
        return {"tipo_saida": "codigo_playwright", "arquivos_gerados": []}

    monkeypatch.setattr(e2e_adapter, "gerar_testes_e2e", fake_generate)

    result = e2e_adapter.run_e2e_profile_adapter(
        profile_id,
        [{"id_artefato": "RF-001", "conteudo": "Validar checkout."}],
        tmp_path,
        plano_acao="plano validado",
        ambiente_execucao_json=json.dumps(
            {
                "timeout_segundos": 90,
                "browser": "firefox",
                "auto_instalar_runtime": True,
            }
        ),
    )

    envelope = json.loads(observed["requisitos"])
    environment = json.loads(observed["ambiente_execucao"])
    assert result["tipo_saida"] == "codigo_playwright"
    assert envelope["metadados"]["perfil_stack"] == profile_id
    assert observed["framework_alvo"] == "playwright"
    assert observed["comando_execucao"] == "npx playwright test"
    assert environment == {
        "timeout_segundos": 90,
        "tipo": "local",
        "browser": "chromium",
        "auto_instalar_runtime": False,
    }
