"""Integração interna do QA Agent — Cenário 1: contratos entre módulos.

Cobre a fronteira action_planner → e2e_test_generator (contrato de handoff
já validado por `plan_validator` + `_validar_plano_acao`) e a fronteira
receive_requirements → pytest_runner (contrato de artefato/caminho), sem
depender de LLM real: apenas `_gerar_pytest_via_llm` é stubado.
"""

import json
from pathlib import Path

import pytest


# ──────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_workspace(tmp_path: Path, monkeypatch) -> Path:
    """Workspace isolado por teste, substituindo workspace_output."""
    ws = tmp_path / "workspace_output"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / ".ai4se_workspace").write_text("marker", encoding="utf-8")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws))

    from shared import workspace as _ws_mod

    monkeypatch.setattr(_ws_mod, "_DEFAULT_WORKSPACE", str(ws))
    return ws


def _plano_valido(tools: list[str], entrada_original: str = "Testar o fluxo de login.") -> dict:
    """Plano mínimo que satisfaz `plan_validator` integralmente."""
    plano = {
        "tipo_entrada": "requisito",
        "modo": "requisito",
        "tools": tools,
        "analise_inicial": "Requisito de login recebido.",
        "analise_progressiva": "Nenhuma etapa anterior.",
        "criterios_verificaveis": [
            "Login com credenciais validas deve autenticar o usuario."
        ],
        "objetivo_qa": "Validar o fluxo de login.",
        "estrategia": "Gerar cenarios autonomos de baixo risco.",
        "checklist_inicial": [
            {"id": "C1", "descricao": "Mapear cenario feliz.", "status": "pendente"},
        ],
        "relatorio_conformidade_esperado": {
            "comparar_planejado_vs_executado": True,
            "incluir_evidencias": True,
            "incluir_divergencias": True,
            "status_possiveis": ["conforme", "parcialmente_conforme", "nao_conforme"],
        },
        "doubt": None,
        "risk_assessment": {
            "nivel": "baixo",
            "motivos": ["Acao local, reversivel e sem efeito externo."],
            "acoes_reversiveis": True,
            "efeito_externo": False,
        },
        "autonomy_decision": {
            "mode": "autonomous",
            "reason": "Geracao/execucao local, reversivel e de baixo risco.",
            "less_prompt_more_action": True,
        },
        "lifecycle": {
            "status": "planejado_para_execucao",
            "execution_allowed": True,
            "next_step": "executar_plano",
        },
        "hitl_checkpoint": {"required": False},
    }
    if "e2e_test_generator" in tools:
        plano["handoff_context"] = {
            "objetivo": "Validar login via E2E.",
            "contexto_compacto": "Requisito unico de login.",
            "artefatos_relevantes": [],
            "decisoes_tomadas": [],
            "riscos_e_duvidas": [],
            "evidencias_necessarias": [],
            "entrada_original": entrada_original,
        }
    return plano


# ──────────────────────────────────────────────────────────────────────────────
# action_planner → e2e_test_generator (handoff validado por plan_validator)
# ──────────────────────────────────────────────────────────────────────────────


def test_e2e_aceita_plano_autorizado():
    """Plano válido, autônomo, com e2e_test_generator selecionado: autoriza."""
    from src.agents.qa_agent.subagents.e2e_test_generator.tools.gerar_testes_e2e import (
        _validar_plano_acao,
    )

    plano_json = json.dumps(_plano_valido(["e2e_test_generator"]))
    plano, bloqueio, _origem = _validar_plano_acao(plano_json)

    assert bloqueio is None
    assert plano is not None
    assert plano["tools"] == ["e2e_test_generator"]
    assert plano["lifecycle"]["execution_allowed"] is True


def test_e2e_rejeita_plano_sem_e2e_selecionado():
    """Plano válido mas sem e2e_test_generator em tools: bloqueia com código específico."""
    from src.agents.qa_agent.subagents.e2e_test_generator.tools.gerar_testes_e2e import (
        _validar_plano_acao,
    )

    plano_json = json.dumps(_plano_valido(["receber_requisitos"]))
    plano, bloqueio, _origem = _validar_plano_acao(plano_json)

    assert plano is None
    assert bloqueio is not None
    assert bloqueio["tipo_saida"] == "bloqueado"
    assert bloqueio["bloqueios"][0]["codigo"] == "E2E_NAO_SELECIONADO_PELO_PLANNER"


def test_e2e_rejeita_plano_invalido():
    """Plano incompleto (falha no plan_validator) propaga como PLANO_ACAO_INVALIDO."""
    from src.agents.qa_agent.subagents.e2e_test_generator.tools.gerar_testes_e2e import (
        _validar_plano_acao,
    )

    plano_json = json.dumps({"tipo_entrada": "requisito"})
    plano, bloqueio, _origem = _validar_plano_acao(plano_json)

    assert plano is None
    assert bloqueio is not None
    assert bloqueio["bloqueios"][0]["codigo"] == "PLANO_ACAO_INVALIDO"


def test_e2e_exige_plano_acao():
    """Sem plano algum (string vazia), o e2e recusa por ausência do action_planner."""
    from src.agents.qa_agent.subagents.e2e_test_generator.tools.gerar_testes_e2e import (
        _validar_plano_acao,
    )

    plano, bloqueio, _origem = _validar_plano_acao("")

    assert plano is None
    assert bloqueio is not None
    assert bloqueio["bloqueios"][0]["codigo"] == "ACTION_PLANNER_OBRIGATORIO"


# ──────────────────────────────────────────────────────────────────────────────
# receive_requirements → pytest_runner (contrato de artefato bloqueado / caminho)
# ──────────────────────────────────────────────────────────────────────────────


def test_artefato_sem_conteudo_gera_doubt(tmp_workspace: Path):
    """Artefato com 'conteudo' vazio nunca chega à geração via LLM: bloqueia com Doubt Artifact."""
    from src.agents.qa_agent.subagents.receive_requirements import orchestration

    artefato = {
        "id_artefato": "RF-VAZIO",
        "tipo": "RF",
        "conteudo": "",
        "modulo": "geral",
        "criticidade": "alta",
    }
    resultado = orchestration.receber_requisitos(json.dumps([artefato]))

    assert resultado["status"] == "concluido"
    assert resultado["resumo"]["bloqueados"] == 1
    detalhe = resultado["detalhes"][0]
    assert detalhe["status"] == "bloqueado"
    assert Path(detalhe["arquivo_duvida"]).exists()


def test_contrato_receive_pytest_runner(
    tmp_workspace: Path, monkeypatch
):
    """O caminho retornado por receive_requirements é aceito sem rewrite por pytest_runner."""
    from src.agents.qa_agent.subagents.receive_requirements import orchestration
    from shared.tools.pytest_runner import _normalizar_caminho_arquivo

    monkeypatch.setattr(
        orchestration,
        "_gerar_pytest_via_llm",
        lambda **kwargs: "def test_ok():\n    assert True\n",
    )

    artefato = {
        "id_artefato": "HU-100",
        "tipo": "HU",
        "conteudo": "Comportamento X deve ocorrer.",
        "modulo": "mod",
        "criticidade": "media",
    }
    resultado = orchestration.receber_requisitos(json.dumps([artefato]))

    assert resultado["status"] == "concluido"
    detalhe = resultado["detalhes"][0]
    assert detalhe["status"] == "sucesso"
    assert set(detalhe) >= {
        "id_artefato",
        "status",
        "fluxo",
        "pasta_gerada",
        "arquivo_gerado",
        "arquivos_apoio",
        "erro",
    }
    assert detalhe["erro"] is None

    caminho_normalizado = _normalizar_caminho_arquivo(detalhe["arquivo_gerado"])
    assert caminho_normalizado == Path(detalhe["arquivo_gerado"])
    assert caminho_normalizado.exists()
