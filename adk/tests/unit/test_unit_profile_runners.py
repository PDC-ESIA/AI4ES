"""Contratos dos executores das famílias publicadas pelo Coder."""

import json
from subprocess import CompletedProcess

import pytest

from shared.testing import unit_runner


def _test_file(root, relative="tests/unit/sample.test.ts"):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("test\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("profile_id", "entry", "expected_fragment"),
    [
        ("node-vitest", "node_modules/vitest/vitest.mjs", "vitest.mjs"),
        ("node-jest", "node_modules/jest/bin/jest.js", "jest.js"),
        ("node-mocha", "node_modules/mocha/bin/mocha.js", "mocha.js"),
    ],
)
def test_node_usa_instalacao_local_sem_npx(
    tmp_path, monkeypatch, profile_id, entry, expected_fragment
):
    test_file = _test_file(tmp_path)
    local_entry = tmp_path / entry
    local_entry.parent.mkdir(parents=True)
    local_entry.write_text("", encoding="utf-8")
    monkeypatch.setattr(unit_runner, "_command_path", lambda name: f"/{name}")

    command, blocker, _coverage = unit_runner._build_command(
        profile_id, tmp_path, test_file
    )

    assert blocker is None
    assert command[0] == "/node"
    assert expected_fragment in " ".join(command)
    assert "npx" not in command


def test_node_test_aceita_arquivo_typescript_declarado(tmp_path, monkeypatch):
    test_file = _test_file(tmp_path, "tests/unit/sample.test.ts")
    monkeypatch.setattr(unit_runner, "_command_path", lambda name: f"/{name}")

    command, blocker, _coverage = unit_runner._build_command(
        "node-node-test", tmp_path, test_file
    )

    assert blocker is None
    assert command == ["/node", "--test", "tests/unit/sample.test.ts"]


def test_framework_node_ausente_retorna_bloqueio(tmp_path, monkeypatch):
    test_file = _test_file(tmp_path)
    monkeypatch.setattr(unit_runner, "_command_path", lambda name: f"/{name}")

    command, blocker, _coverage = unit_runner._build_command(
        "node-vitest", tmp_path, test_file
    )

    assert command is None
    assert "não está instalado localmente" in blocker


def test_java_maven_usa_nome_qualificado(tmp_path, monkeypatch):
    (tmp_path / "pom.xml").write_text("<project />", encoding="utf-8")
    test_file = _test_file(tmp_path, "src/test/java/com/example/CalculatorTest.java")
    test_file.write_text(
        "package com.example; class CalculatorTest {}\n", encoding="utf-8"
    )
    monkeypatch.setattr(unit_runner, "_command_path", lambda name: f"/{name}")

    command, blocker, _coverage = unit_runner._build_command(
        "java-junit", tmp_path, test_file
    )

    assert blocker is None
    assert command == ["/mvn", "-Dtest=com.example.CalculatorTest", "test"]


def test_java_maven_usa_classe_declarada_em_nome_legado(tmp_path, monkeypatch):
    (tmp_path / "pom.xml").write_text("<project />", encoding="utf-8")
    test_file = _test_file(
        tmp_path,
        "src/test/java/com/example/CalculatorTest.generated.java",
    )
    test_file.write_text(
        "package com.example; class CalculatorTestGenerated {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(unit_runner, "_command_path", lambda name: f"/{name}")

    command, blocker, _coverage = unit_runner._build_command(
        "java-junit", tmp_path, test_file
    )

    assert blocker is None
    assert command == ["/mvn", "-Dtest=com.example.CalculatorTestGenerated", "test"]


def test_go_usa_go_mod_e_gera_coverprofile(tmp_path, monkeypatch):
    (tmp_path / "go.mod").write_text("module sample\n", encoding="utf-8")
    test_file = _test_file(tmp_path, "calculator_test.go")
    coverage = tmp_path / "coverage"
    monkeypatch.setattr(unit_runner, "_command_path", lambda name: f"/{name}")
    monkeypatch.setattr(unit_runner, "get_agent_workspace", lambda _name: tmp_path)

    command, blocker, coverage_path = unit_runner._build_command(
        "go-testing", tmp_path, test_file
    )

    assert blocker is None
    assert command[:3] == ["/go", "test", "-json"]
    assert str(coverage) in command[3]
    assert coverage_path == coverage / "calculator_test.out"


@pytest.mark.parametrize(
    ("profile_id", "output", "expected"),
    [
        (
            "node-vitest",
            "Tests  3 passed | 1 failed | 1 skipped",
            {"total": 5, "sucessos": 3, "falhas": 1, "ignorados": 1},
        ),
        (
            "node-jest",
            "Tests: 1 failed, 1 skipped, 3 passed, 5 total",
            {"total": 5, "sucessos": 3, "falhas": 1, "ignorados": 1},
        ),
        (
            "node-mocha",
            "3 passing\n1 pending\n1 failing",
            {"total": 5, "sucessos": 3, "falhas": 1, "ignorados": 1},
        ),
        (
            "java-junit",
            "Tests run: 5, Failures: 1, Errors: 0, Skipped: 1",
            {"total": 5, "sucessos": 3, "falhas": 1, "ignorados": 1},
        ),
    ],
)
def test_normaliza_contagens(profile_id, output, expected):
    assert unit_runner._parse_counts(profile_id, output, 1) == expected


def test_normaliza_contagem_vitest_com_ansi_do_github_actions():
    output = (
        "\x1b[2m Test Files \x1b[22m \x1b[1m\x1b[32m1 passed\x1b[39m\x1b[22m"
        "\x1b[90m (1)\x1b[39m\n"
        "\x1b[2m      Tests \x1b[22m \x1b[1m\x1b[32m2 passed\x1b[39m\x1b[22m"
        "\x1b[90m (2)\x1b[39m"
    )

    assert unit_runner._parse_counts("node-vitest", output, 0) == {
        "total": 2,
        "sucessos": 2,
        "falhas": 0,
        "ignorados": 0,
    }


def test_normaliza_eventos_go():
    output = "\n".join(
        json.dumps({"Action": action, "Test": name})
        for action, name in (("pass", "TestA"), ("fail", "TestB"), ("skip", "TestC"))
    )

    assert unit_runner._parse_counts("go-testing", output, 1) == {
        "total": 3,
        "sucessos": 1,
        "falhas": 1,
        "ignorados": 1,
    }


def test_execucao_sem_testes_e_falha(tmp_path, monkeypatch):
    test_file = _test_file(tmp_path, "sample.test.js")
    monkeypatch.setattr(
        unit_runner,
        "_build_command",
        lambda *_args: (["node", "--test", "sample.test.js"], None, None),
    )
    monkeypatch.setattr(
        unit_runner.subprocess,
        "run",
        lambda *_args, **_kwargs: CompletedProcess(
            [], 0, stdout="no tests were found", stderr=""
        ),
    )

    result = unit_runner.executar_teste_unitario("node-node-test", tmp_path, test_file)

    assert result["status"] == "falha"
    assert result["erros"][0]["codigo"] == "NENHUM_TESTE_EXECUTADO"


def test_ambiente_de_execucao_define_ci():
    environment = unit_runner.unit_profile_execution_environment("node-vitest", "node")

    assert environment["CI"] == "1"


def test_teste_fora_do_projeto_e_bloqueado(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    external = _test_file(tmp_path / "external", "sample.test.js")

    result = unit_runner.executar_teste_unitario("node-node-test", project, external)

    assert result["status"] == "bloqueado"
    assert result["erros"][0]["codigo"] == "CAMINHO_TESTE_INVALIDO"
