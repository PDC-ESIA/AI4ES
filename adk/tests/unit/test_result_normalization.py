"""Normalização comum dos resultados de integração e E2E."""

import json

import pytest

from shared.testing.result_normalization import (
    normalize_e2e_result,
    normalize_integration_execution,
    normalize_integration_result,
    parse_integration_counts,
)


@pytest.mark.parametrize(
    ("framework", "output"),
    [
        ("pytest", "1 failed, 3 passed, 1 skipped in 0.10s"),
        ("vitest", "Tests  1 failed | 1 skipped | 3 passed"),
        ("jest", "Tests: 1 failed, 1 skipped, 3 passed, 5 total"),
        ("mocha", "3 passing\n1 pending\n1 failing"),
        ("node:test", "# tests 5\n# pass 3\n# fail 1\n# skipped 1"),
        (
            "junit-maven",
            "Tests run: 5, Failures: 1, Errors: 0, Skipped: 1",
        ),
        ("junit-gradle", "5 tests completed, 1 failed, 1 skipped"),
    ],
)
def test_normaliza_contagens_dos_executores_de_integracao(framework, output):
    assert parse_integration_counts(framework, output) == {
        "total": 5,
        "sucessos": 3,
        "falhas": 1,
        "ignorados": 1,
    }


def test_normaliza_eventos_go_de_integracao():
    output = "\n".join(
        json.dumps({"Action": action, "Test": name})
        for action, name in (
            ("pass", "TestA"),
            ("fail", "TestB"),
            ("skip", "TestC"),
        )
    )

    assert parse_integration_counts("go-testing", output) == {
        "total": 3,
        "sucessos": 1,
        "falhas": 1,
        "ignorados": 1,
    }


def test_execucao_de_integracao_sem_testes_e_falha():
    raw = {
        "status": "sucesso",
        "perfil": "python-integration",
        "framework": "pytest",
        "comando": ["python", "-m", "pytest"],
        "codigo_saida": 0,
        "stdout": "no tests ran",
        "stderr": "",
        "bloqueios": [],
    }

    result = normalize_integration_execution(raw)

    assert result["status"] == "falha"
    assert result["testes"]["total"] == 0
    assert result["erros"][0]["codigo"] == "NENHUM_TESTE_EXECUTADO"
    assert result["resultado_bruto"] is raw


def test_consolida_resultado_misto_de_integracao():
    raw = {
        "status": "concluido",
        "detalhes": [
            {
                "id_artefato": "RF-OK",
                "status": "gerado",
                "arquivo_gerado": "tests/integration/test_ok.py",
                "resultado_execucao": {
                    "status": "sucesso",
                    "perfil": "python-integration",
                    "framework": "pytest",
                    "comando": ["python", "-m", "pytest"],
                    "codigo_saida": 0,
                    "stdout": "1 passed in 0.01s",
                    "stderr": "",
                    "bloqueios": [],
                },
            },
            {
                "id_artefato": "RF-BLOCK",
                "status": "gerado",
                "arquivo_gerado": "tests/integration/test_block.py",
                "resultado_execucao": {
                    "status": "bloqueado",
                    "perfil": "python-integration",
                    "framework": None,
                    "codigo_saida": None,
                    "stdout": "",
                    "stderr": "",
                    "bloqueios": [
                        {
                            "codigo": "RUNTIME_DEPENDENCY_MISSING",
                            "mensagem": "pytest ausente",
                        }
                    ],
                },
            },
            {
                "id_artefato": "RF-FAIL",
                "status": "falha",
                "arquivo_gerado": None,
                "resultado_execucao": None,
                "erro": "geração inválida",
            },
        ],
    }

    result = normalize_integration_result(
        {"status": "suportado"},
        {"profile_id": "python-integration"},
        raw,
    )

    assert result["status"] == "parcial"
    assert result["resumo"] == {
        "total": 3,
        "sucessos": 1,
        "bloqueados": 1,
        "falhas": 1,
        "executados": 1,
    }
    assert len(result["arquivos_gerados"]) == 2
    assert result["bloqueios"][0]["codigo"] == "RUNTIME_DEPENDENCY_MISSING"
    assert result["resultado_bruto"] is raw


def test_normaliza_execucao_e2e_aprovada_por_artefato():
    raw = {
        "tipo_saida": "executado",
        "arquivos_gerados": ["tests/e2e/checkout.spec.ts"],
        "resultado_execucao": {
            "status": "aprovado",
            "comando": "npx playwright test",
            "codigo_saida": 0,
            "testes_executados": 3,
            "testes_aprovados": 2,
            "testes_falhos": 0,
            "testes_pulados": 1,
            "logs_resumidos": ["2 passed, 1 skipped"],
        },
        "bloqueios": [],
    }
    artifacts = [{"id_artefato": "RF-1"}, {"id_artefato": "RF-2"}]

    result = normalize_e2e_result(
        {"status": "suportado"},
        {"profile_id": "node-e2e"},
        raw,
        artifacts,
    )

    assert result["status"] == "sucesso"
    assert result["resumo"] == {
        "total": 2,
        "sucessos": 2,
        "bloqueados": 0,
        "falhas": 0,
        "executados": 3,
    }
    assert [detail["id_artefato"] for detail in result["detalhes"]] == [
        "RF-1",
        "RF-2",
    ]
    assert result["detalhes"][0]["resultado_execucao"]["testes"] == {
        "total": 3,
        "sucessos": 2,
        "falhas": 0,
        "ignorados": 1,
    }
    assert result["resultado_bruto"] is raw


@pytest.mark.parametrize("runtime_status", ["bloqueado_infraestrutura", "timeout", "erro_execucao"])
def test_normaliza_bloqueios_de_infraestrutura_e2e(runtime_status):
    raw = {
        "tipo_saida": "executado",
        "arquivos_gerados": ["tests/e2e/checkout.spec.ts"],
        "resultado_execucao": {
            "status": runtime_status,
            "codigo_saida": None,
            "logs_resumidos": ["runtime indisponível"],
        },
        "bloqueios": [],
    }

    result = normalize_e2e_result(
        {"status": "suportado"},
        {"profile_id": "node-e2e"},
        raw,
        [{"id_artefato": "RF-1"}],
    )

    assert result["status"] == "parcial"
    assert result["resumo"]["bloqueados"] == 1
    assert result["detalhes"][0]["resultado_execucao"]["status"] == "bloqueado"
    assert result["bloqueios"][0]["codigo"] == "RUNTIME_E2E_BLOQUEADO"


def test_plano_e2e_sem_codigo_e_normalizado_como_parcial():
    raw = {
        "tipo_saida": "plano_e2e",
        "arquivos_gerados": [],
        "resultado_execucao": None,
        "cenarios": [{"id": "CEN-1"}],
        "bloqueios": [{"codigo": "URL_AUSENTE", "mensagem": "Informe a URL."}],
    }

    result = normalize_e2e_result(
        {"status": "suportado"},
        {"profile_id": "python-e2e"},
        raw,
        [{"id_artefato": "RF-1"}],
    )

    assert result["status"] == "parcial"
    assert result["resumo"]["bloqueados"] == 1
    assert result["detalhes"][0]["status"] == "bloqueado"
    assert result["cenarios"] == [{"id": "CEN-1"}]
