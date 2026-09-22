"""Catálogo e detecção das famílias publicadas pelo Coder."""

import json

import pytest

from shared.testing import UNIT_TEST_PROFILES, inspect_unit_test_project


@pytest.mark.parametrize(
    ("files", "expected_profile"),
    [
        (
            {"pyproject.toml": "[tool.pytest.ini_options]\n", "app/main.py": "x = 1\n"},
            "python-pytest",
        ),
        (
            {
                "package.json": json.dumps({"devDependencies": {"vitest": "latest"}}),
                "src/service.ts": "export const ok: boolean = true;\n",
            },
            "node-vitest",
        ),
        (
            {
                "package.json": json.dumps({"devDependencies": {"jest": "latest"}}),
                "src/service.tsx": "export const View = () => null;\n",
            },
            "node-jest",
        ),
        (
            {
                "package.json": json.dumps({"scripts": {"test": "node --test"}}),
                "src/service.js": "export const ok = true;\n",
            },
            "node-node-test",
        ),
        (
            {
                "package.json": json.dumps({"devDependencies": {"mocha": "latest"}}),
                "src/service.js": "module.exports = true;\n",
            },
            "node-mocha",
        ),
        (
            {
                "pom.xml": "<project />\n",
                "src/main/java/Sample.java": "public class Sample {}\n",
            },
            "java-junit",
        ),
        (
            {"go.mod": "module sample\n", "calculator.go": "package sample\n"},
            "go-testing",
        ),
    ],
)
def test_detecta_perfis_ativos(tmp_path, files, expected_profile):
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    result = inspect_unit_test_project(tmp_path)

    assert result["status"] == "suportado"
    assert result["perfil"]["profile_id"] == expected_profile


def test_catalogo_ativo_contem_somente_familias_do_coder():
    assert set(UNIT_TEST_PROFILES) == {
        "python-pytest",
        "node-vitest",
        "node-jest",
        "node-node-test",
        "node-mocha",
        "node-unconfigured",
        "java-junit",
        "go-testing",
    }


@pytest.mark.parametrize(
    ("declared_stack", "expected_profile"),
    [
        ("Python/FastAPI", "python-pytest"),
        ("Java/Spring", "java-junit"),
        ("Go", "go-testing"),
    ],
)
def test_resolve_familias_declaradas_pelo_coder(
    tmp_path, declared_stack, expected_profile
):
    result = inspect_unit_test_project(tmp_path, declared_stack=declared_stack)

    assert result["status"] == "suportado"
    assert result["perfil"]["profile_id"] == expected_profile


def test_typescript_declarado_usa_runner_do_package_json(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"devDependencies": {"vitest": "latest"}}),
        encoding="utf-8",
    )
    (tmp_path / "service.ts").write_text("export const ok = true;\n", encoding="utf-8")

    result = inspect_unit_test_project(tmp_path, declared_stack="TypeScript")

    assert result["status"] == "suportado"
    assert result["perfil"]["profile_id"] == "node-vitest"


def test_node_sem_runner_declarado_permanece_bloqueado(tmp_path):
    (tmp_path / "package.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "service.ts").write_text("export const ok = true;\n", encoding="utf-8")

    result = inspect_unit_test_project(tmp_path, declared_stack="Node/Express")

    assert result["status"] == "bloqueado"
    assert result["perfil"]["profile_id"] == "node-unconfigured"
    assert result["bloqueios"][0]["codigo"] == "PERFIL_NAO_IMPLEMENTADO"


def test_stack_fora_do_coder_nao_e_aceita(tmp_path):
    result = inspect_unit_test_project(tmp_path, declared_stack="Rust")

    assert result["status"] == "bloqueado"
    assert result["bloqueios"][0]["codigo"] == "STACK_DECLARADA_DESCONHECIDA"
