"""Geração no layout das famílias não Python publicadas pelo Coder."""

from pathlib import Path

import pytest

from src.agents.qa_agent.subagents.unit_test_generator import profile_generation


def _execution_success(profile_id, _root, target):
    return {"status": "sucesso", "perfil": profile_id, "arquivo": str(target)}


@pytest.mark.parametrize(
    ("profile_id", "source_path", "source", "generated", "expected_suffix"),
    [
        (
            "node-vitest",
            "src/calculator.ts",
            "export const add = (a: number, b: number) => a + b;\n",
            "import { describe, expect, it } from 'vitest';\n"
            "describe('add', () => { it('adds', () => expect(1 + 1).toBe(2)); });\n",
            "tests/unit/rf_001.test.ts",
        ),
        (
            "node-jest",
            "src/calculator.tsx",
            "export const add = (a: number, b: number) => a + b;\n",
            "test('adds', () => { expect(1 + 1).toBe(2); });\n",
            "tests/unit/rf_001.test.ts",
        ),
        (
            "node-node-test",
            "src/calculator.js",
            "export const add = (a, b) => a + b;\n",
            "import test from 'node:test';\nimport assert from 'node:assert/strict';\n"
            "test('adds', () => assert.equal(1 + 1, 2));\n",
            "tests/unit/rf_001.test.js",
        ),
        (
            "node-mocha",
            "src/calculator.js",
            "module.exports = (a, b) => a + b;\n",
            "describe('add', () => { it('adds', () => {}); });\n",
            "tests/unit/rf_001.test.js",
        ),
        (
            "java-junit",
            "src/main/java/com/example/Calculator.java",
            "package com.example; public class Calculator {}\n",
            "package com.example;\nimport org.junit.jupiter.api.Test;\n"
            "class CalculatorTest { @Test void adds() {} }\n",
            "src/test/java/com/example/CalculatorTest.java",
        ),
        (
            "go-testing",
            "calculator.go",
            "package calculator\nfunc Add(a, b int) int { return a + b }\n",
            'package calculator\nimport "testing"\n'
            "func TestAdd(t *testing.T) { if Add(1, 1) != 2 { t.Fail() } }\n",
            "calculator_test.go",
        ),
    ],
)
def test_gera_no_layout_nativo_e_executa(
    tmp_path,
    monkeypatch,
    profile_id,
    source_path,
    source,
    generated,
    expected_suffix,
):
    source_file = tmp_path / source_path
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text(source, encoding="utf-8")
    monkeypatch.setattr(
        profile_generation, "_generate_test_code", lambda *_args, **_kwargs: generated
    )
    monkeypatch.setattr(
        profile_generation, "executar_teste_unitario", _execution_success
    )

    result = profile_generation.gerar_testes_do_perfil(
        profile_id,
        [
            {
                "id_artefato": "RF-001",
                "tipo": "RF",
                "conteudo": "Somar dois números.",
                "modulo": "calculator",
            }
        ],
        tmp_path,
    )

    detail = result["detalhes"][0]
    generated_path = Path(detail["arquivo_gerado"])
    assert detail["status"] == "sucesso", detail.get("erro")
    assert detail["resultado_execucao"]["status"] == "sucesso"
    assert generated_path.relative_to(tmp_path).as_posix() == expected_suffix


def test_sem_codigo_gera_esqueleto_sem_executar(tmp_path, monkeypatch):
    monkeypatch.setattr(
        profile_generation,
        "_generate_test_code",
        lambda *_args, **_kwargs: (
            "import { describe, it } from 'vitest';\n"
            "describe.skip('pendente', () => { it('documenta', () => {}); });\n"
        ),
    )

    def fail_if_called(*_args, **_kwargs):
        pytest.fail("Esqueleto sem fonte não deve ser executado")

    monkeypatch.setattr(profile_generation, "executar_teste_unitario", fail_if_called)

    result = profile_generation.gerar_testes_do_perfil(
        "node-vitest",
        [
            {
                "id_artefato": "RF-002",
                "tipo": "RF",
                "conteudo": "Validar senha.",
                "modulo": "auth",
            }
        ],
        tmp_path,
    )

    assert result["detalhes"][0]["fluxo"] == "B"
    assert result["detalhes"][0]["resultado_execucao"] is None


def test_sem_conteudo_usa_codigo_persistido_como_contexto(tmp_path, monkeypatch):
    source_file = tmp_path / "src" / "CalculatorService.ts"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        "export const somar = (a: number, b: number) => a + b;\n",
        encoding="utf-8",
    )
    existing_test = tmp_path / "test" / "CalculatorService.unit.test.ts"
    existing_test.parent.mkdir(parents=True)
    existing_test.write_text("test('existente', () => {});\n", encoding="utf-8")
    captured = {}

    def fake_generate(profile_id, artifact, root, target, sources):
        captured.update(
            profile_id=profile_id,
            artifact=artifact,
            root=root,
            target=target,
            sources=sources,
        )
        return "test('soma', () => { expect(1 + 1).toBe(2); });\n"

    monkeypatch.setattr(profile_generation, "_generate_test_code", fake_generate)
    monkeypatch.setattr(
        profile_generation, "executar_teste_unitario", _execution_success
    )

    result = profile_generation.gerar_testes_do_perfil(
        "node-jest",
        [{"id": "CalculatorServiceNew", "path": "src/CalculatorService.ts"}],
        tmp_path,
    )

    detail = result["detalhes"][0]
    assert detail["status"] == "sucesso"
    assert detail["id_artefato"] == "CalculatorServiceNew"
    assert captured["artifact"]["id_artefato"] == "CalculatorServiceNew"
    assert captured["sources"] == [source_file]
    assert Path(detail["arquivo_gerado"]).relative_to(tmp_path).as_posix() == (
        "test/calculatorservicenew.unit.test.ts"
    )
    assert detail["resultado_execucao"]["status"] == "sucesso"


def test_sem_conteudo_e_sem_codigo_permanece_bloqueado(tmp_path):
    result = profile_generation.gerar_testes_do_perfil(
        "node-jest",
        [{"id": "RF-SEM-CONTEXTO"}],
        tmp_path,
    )

    detail = result["detalhes"][0]
    assert detail["status"] == "bloqueado"
    assert "requisito textual nem código-fonte" in detail["mensagem"]


def test_perfil_fora_do_coder_nao_possui_gerador(tmp_path):
    with pytest.raises(ValueError, match="Perfil unitário desconhecido"):
        profile_generation.gerar_testes_do_perfil(
            "rust-cargo",
            [{"id_artefato": "RF-003", "conteudo": "Validar."}],
            tmp_path,
        )
