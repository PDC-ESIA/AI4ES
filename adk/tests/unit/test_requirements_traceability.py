"""Testes da construção determinística da Matriz de Rastreabilidade (Time 1).

O ponto sob teste é o que motivou o módulo: a matriz não pode depender de o
LLM lembrar de transcrevê-la, e não pode materializar vínculos sujos que o
próprio LLM inventou para "fechar" uma lacuna.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.agents.requirements.traceability import (
    ID_MATRIZ,
    STATE_MATRIZ,
    SUBPASTA_MATRIZ,
    construir_matriz,
    gerar_matriz_rastreabilidade,
    renderizar_markdown,
)


def _hu(id_hu="HU-001", criterios=None):
    return {
        "id": id_hu,
        "title": "Criação de Exercícios",
        "description": "Como professor, quero criar exercícios.",
        "acceptance_criteria": criterios if criterios is not None else ["CA-1", "CA-2"],
    }


def _rf(id_rf="RF-005", hu_parent="HU-001", prioridade="Alta"):
    return {
        "id": id_rf,
        "title": "Execução em Sandbox",
        "description": "O sistema deve executar o código em sandbox.",
        "hu_parent": hu_parent,
        "priority": prioridade,
    }


def _dados(**extra):
    base = {
        "user_stories": [_hu()],
        "functional_requirements": [_rf()],
        "traceability_rationale": [
            {
                "id_artefato": "HU-001",
                "origem": "Descrição inicial do professor",
                "motivo_inclusao": "Necessidade relatada de disponibilizar exercícios",
            },
            {
                "id_artefato": "RF-005",
                "origem": "Trecho: 'executar o código em sandbox isolada'",
                "motivo_inclusao": "Mitigar risco de comprometimento do servidor",
            },
        ],
    }
    base.update(extra)
    return base


def _por_id(matriz):
    return {item["id_artefato"]: item for item in matriz["itens"]}


# --------------------------------------------------------------------------
# construir_matriz — derivação dos vínculos
# --------------------------------------------------------------------------

def test_matriz_deriva_backward_e_forward_de_hu_parent():
    matriz = construir_matriz(_dados())
    itens = _por_id(matriz)

    backward = itens["RF-005"]["rastreabilidade_backward"]
    assert backward == [{
        "id_artefato_relacionado": "HU-001",
        "tipo_artefato_relacionado": "HU",
        "tipo_relacao": "deriva_de",
    }]

    forward = itens["HU-001"]["rastreabilidade_forward"]
    assert forward == [{
        "id_artefato_relacionado": "RF-005",
        "tipo_artefato_relacionado": "RF",
        "tipo_relacao": "origina",
    }]


def test_hu_parent_apontando_para_rf_nao_vira_vinculo():
    """O bug real observado em produção: RF-006 com hu_parent = RF-005.

    Materializar esse vínculo transformaria erro do LLM em rastreabilidade
    aparentemente legítima. A matriz deve recusar e reportar a lacuna.
    """
    dados = _dados(functional_requirements=[
        _rf("RF-005", hu_parent="HU-001"),
        _rf("RF-006", hu_parent="RF-005"),
    ])
    itens = _por_id(construir_matriz(dados))

    assert itens["RF-006"]["rastreabilidade_backward"] == []
    assert itens["RF-006"]["lacuna_detectada"] is True
    assert itens["RF-005"]["rastreabilidade_forward"] == []


def test_hu_parent_apontando_para_id_inexistente_nao_vira_vinculo():
    dados = _dados(functional_requirements=[_rf("RF-005", hu_parent="HU-999")])
    itens = _por_id(construir_matriz(dados))

    assert itens["RF-005"]["rastreabilidade_backward"] == []
    assert itens["RF-005"]["lacuna_detectada"] is True


# --------------------------------------------------------------------------
# construir_matriz — lacunas
# --------------------------------------------------------------------------

def test_rf_sem_hu_parent_gera_lacuna_backward():
    dados = _dados(functional_requirements=[_rf("RF-009", hu_parent=None)])
    matriz = construir_matriz(dados)
    item = _por_id(matriz)["RF-009"]

    assert item["lacuna_detectada"] is True
    assert "backward" in item["lacuna_descricao"]
    assert any("RF-009" in l for l in matriz["lacunas_candidatas_doubt"])


def test_hu_sem_derivados_gera_lacuna_forward():
    dados = _dados(functional_requirements=[])
    matriz = construir_matriz(dados)
    item = _por_id(matriz)["HU-001"]

    assert item["lacuna_detectada"] is True
    assert "forward" in item["lacuna_descricao"]


def test_artefatos_rastreados_nao_geram_lacuna():
    matriz = construir_matriz(_dados())

    assert matriz["lacunas_candidatas_doubt"] == []
    assert all(item["lacuna_detectada"] is False for item in matriz["itens"])
    assert all(item["lacuna_descricao"] is None for item in matriz["itens"])


@pytest.mark.parametrize("colecao,tipo", [
    ("use_cases", "UC"),
    ("non_functional_requirements", "RNF"),
    ("business_rules", "RN"),
])
def test_uc_rnf_e_rn_tambem_exigem_backward(colecao, tipo):
    dados = {colecao: [{"id": f"{tipo}-001", "description": "Qualquer coisa"}]}
    item = _por_id(construir_matriz(dados))[f"{tipo}-001"]

    assert item["tipo"] == tipo
    assert item["lacuna_detectada"] is True


# --------------------------------------------------------------------------
# construir_matriz — rationale e campos derivados
# --------------------------------------------------------------------------

def test_rationale_do_llm_preenche_origem_e_motivo():
    item = _por_id(construir_matriz(_dados()))["RF-005"]

    assert item["origem"] == "Trecho: 'executar o código em sandbox isolada'"
    assert item["motivo_inclusao"] == "Mitigar risco de comprometimento do servidor"


def test_artefato_sem_rationale_recebe_nao_identificado():
    dados = _dados(traceability_rationale=[])
    item = _por_id(construir_matriz(dados))["RF-005"]

    assert item["origem"] == "Não identificado"
    assert item["motivo_inclusao"] == "Não identificado"


def test_rationale_vazio_ou_em_branco_nao_sobrescreve_com_lixo():
    dados = _dados(traceability_rationale=[
        {"id_artefato": "RF-005", "origem": "   ", "motivo_inclusao": None},
    ])
    item = _por_id(construir_matriz(dados))["RF-005"]

    assert item["origem"] == "Não identificado"
    assert item["motivo_inclusao"] == "Não identificado"


def test_campos_neutros_nunca_sao_inventados():
    item = _por_id(construir_matriz(_dados()))["RF-005"]

    assert item["casos_teste"] == "A definir"
    assert item["id_agente_origem"] == "requirements_agent"


def test_prioridade_ausente_vira_nao_identificado():
    dados = _dados(functional_requirements=[_rf(prioridade=None)])
    item = _por_id(construir_matriz(dados))["RF-005"]

    assert item["prioridade"] == "Não identificado"


def test_rn_sem_title_usa_description_como_descricao():
    dados = {"business_rules": [
        {"id": "RN-001", "description": "O exercício deve possuir enunciado."},
    ]}
    item = _por_id(construir_matriz(dados))["RN-001"]

    assert item["descricao"] == "O exercício deve possuir enunciado."


def test_artefato_sem_id_e_ignorado():
    dados = _dados(functional_requirements=[_rf(), {"title": "Sem ID"}])
    matriz = construir_matriz(dados)

    assert [i["id_artefato"] for i in matriz["itens"]] == ["HU-001", "RF-005"]


def test_colecao_com_tipo_inesperado_nao_derruba():
    dados = _dados(functional_requirements="não é lista", use_cases=None)
    matriz = construir_matriz(dados)

    assert [i["id_artefato"] for i in matriz["itens"]] == ["HU-001"]


def test_matriz_sem_artefatos_retorna_none():
    assert construir_matriz({}) is None
    assert construir_matriz({"user_stories": [], "functional_requirements": []}) is None


# --------------------------------------------------------------------------
# renderizar_markdown
# --------------------------------------------------------------------------

def test_markdown_tem_as_dez_colunas_obrigatorias():
    matriz = construir_matriz(_dados())
    cabecalho = matriz["markdown"].splitlines()[2]

    for coluna in (
        "ID do Artefato", "Tipo", "Descrição/Título", "Origem",
        "Motivo de Inclusão", "Prioridade", "Rastreabilidade Backward",
        "Rastreabilidade Forward", "Critérios de Aceitação", "Caso(s) de Teste",
    ):
        assert coluna in cabecalho
    assert cabecalho.count("|") == 11


def test_markdown_tem_uma_linha_por_artefato():
    dados = _dados(functional_requirements=[_rf("RF-005"), _rf("RF-006")])
    linhas = [l for l in construir_matriz(dados)["markdown"].splitlines()
              if l.startswith("| ")]

    # cabeçalho + 3 artefatos
    assert len(linhas) == 4


def test_markdown_usa_placeholders_para_vinculos_ausentes():
    dados = _dados(user_stories=[], functional_requirements=[_rf(hu_parent=None)])
    markdown = construir_matriz(dados)["markdown"]

    assert "Não identificado" in markdown
    assert "Nenhum" in markdown


def test_markdown_lista_as_lacunas_detectadas():
    dados = _dados(functional_requirements=[_rf("RF-009", hu_parent=None)])
    markdown = construir_matriz(dados)["markdown"]

    assert "## Lacunas de Rastreabilidade Detectadas" in markdown
    assert "RF-009" in markdown


def test_markdown_omite_secao_de_lacunas_quando_nao_ha():
    markdown = construir_matriz(_dados())["markdown"]

    assert "Lacunas de Rastreabilidade" not in markdown


def test_criterios_ausentes_viram_nao_aplicavel_no_markdown():
    dados = {"business_rules": [{"id": "RN-001", "description": "Regra"}]}
    markdown = renderizar_markdown(construir_matriz(dados))

    assert "Não aplicável" in markdown


# --------------------------------------------------------------------------
# gerar_matriz_rastreabilidade (after_agent_callback)
# --------------------------------------------------------------------------

def _ctx(state):
    return SimpleNamespace(state=state)


def test_callback_publica_matriz_no_state_e_persiste_arquivo(tmp_path):
    state = {"analysis_result": json.dumps(_dados())}

    with patch("src.agents.requirements.traceability.get_agent_workspace",
               return_value=tmp_path):
        assert gerar_matriz_rastreabilidade(_ctx(state)) is None

    matriz = state[STATE_MATRIZ]
    assert matriz["id"] == ID_MATRIZ
    assert len(matriz["itens"]) == 2

    arquivo = tmp_path / SUBPASTA_MATRIZ / f"{ID_MATRIZ}.md"
    assert arquivo.exists()
    assert arquivo.read_text(encoding="utf-8") == matriz["markdown"]


def test_callback_extrai_json_de_saida_com_texto_ao_redor(tmp_path):
    bruto = (
        "PASSO 1: elicitação concluída.\n"
        "```json\n" + json.dumps(_dados()) + "\n```\n"
    )
    state = {"analysis_result": bruto}

    with patch("src.agents.requirements.traceability.get_agent_workspace",
               return_value=tmp_path):
        gerar_matriz_rastreabilidade(_ctx(state))

    assert STATE_MATRIZ in state


@pytest.mark.parametrize("bruto", [
    "",
    "PASSO 1: nenhuma saída estruturada.",
    "{ isso não é json válido",
    json.dumps(["lista", "no", "topo"]),
    json.dumps({"summary": "sem artefato nenhum"}),
])
def test_callback_degrada_sem_publicar_matriz(bruto, tmp_path):
    state = {"analysis_result": bruto}

    with patch("src.agents.requirements.traceability.get_agent_workspace",
               return_value=tmp_path):
        assert gerar_matriz_rastreabilidade(_ctx(state)) is None

    assert STATE_MATRIZ not in state


def test_callback_nao_propaga_falha_de_escrita(tmp_path):
    state = {"analysis_result": json.dumps(_dados())}

    with patch("src.agents.requirements.traceability.get_agent_workspace",
               side_effect=OSError("disco cheio")):
        assert gerar_matriz_rastreabilidade(_ctx(state)) is None


def test_callback_sem_analysis_result_nao_quebra(tmp_path):
    state = {}

    with patch("src.agents.requirements.traceability.get_agent_workspace",
               return_value=tmp_path):
        assert gerar_matriz_rastreabilidade(_ctx(state)) is None

    assert STATE_MATRIZ not in state
