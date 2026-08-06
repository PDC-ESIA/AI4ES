"""Testes das camadas de validação anti-alucinação do Agente de Requisitos.

Cobre:
- C1: rejeição de artefato Markdown malformado antes da gravação
- C2: registro determinístico do que foi realmente gravado
- C4: auditoria cruzando o JSON declarado com os arquivos gravados

A matriz de rastreabilidade (C3) tem suíte própria em
`test_requirements_traceability.py`; aqui ela entra apenas como insumo
injetado na auditoria, exatamente como o callback faz em produção.
"""

import json
from unittest.mock import MagicMock

import pytest

from src.agents.requirements.traceability import STATE_MATRIZ, construir_matriz
from src.agents.requirements.validation import (
    STATE_ARTEFATOS,
    STATE_AUDITORIA,
    TOOL_DUVIDA,
    TOOL_SALVAR,
    auditar_analise,
    auditar_saida_final,
    extrair_bloco_json,
    rebaixar_duvida_de_glossario,
    registrar_artefato_persistido,
    validar_antes_de_salvar,
    validar_artefato_markdown,
)

# ---------------------------------------------------------------------------
# Fixtures de conteúdo
# ---------------------------------------------------------------------------

MD_HU = """# HU-001: Criação de Exercícios

## Metadados

| Campo   | Valor               |
|---------|---------------------|
| ID      | HU-001              |
| Tipo    | História de Usuário |
| Persona | Professor           |

## História

> Como **Professor**, quero **criar exercícios**, para que **os alunos pratiquem**.

## Critérios de Aceitação

- [ ] **CA-1:** O sistema deve permitir inserir o enunciado em Markdown.
"""

MD_RF = """# RF-005: Execução em Sandbox

## Metadados

| Campo      | Valor               |
|------------|---------------------|
| ID         | RF-005              |
| Tipo       | Requisito Funcional |
| Prioridade | Alta                |
| Deriva de  | HU-001              |

## Descrição

O sistema deve executar o código submetido em ambiente isolado.
"""


def _tool(nome=TOOL_SALVAR):
    tool = MagicMock()
    tool.name = nome
    return tool


def _ctx(state=None):
    ctx = MagicMock()
    ctx.state = state if state is not None else {}
    return ctx


# ---------------------------------------------------------------------------
# C1 — validar_artefato_markdown
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tipo,id_req,md", [("HU", "HU-001", MD_HU), ("RF", "RF-005", MD_RF)])
def test_artefato_no_padrao_e_aceito(tipo, id_req, md):
    assert validar_artefato_markdown(tipo, id_req, md) == []


def test_rejeita_id_incompativel_com_o_tipo():
    erros = validar_artefato_markdown("HU", "RF-007", MD_HU)
    assert any("não corresponde ao tipo" in e for e in erros)


def test_rejeita_h1_divergente_do_id_req():
    erros = validar_artefato_markdown("RF", "RF-009", MD_RF)
    assert any("título H1" in e for e in erros)


def test_rejeita_criterios_de_aceitacao_em_rf():
    md = MD_RF + "\n## Critérios de Aceitação\n\n- [ ] **CA-1:** algo verificável aqui.\n"
    erros = validar_artefato_markdown("RF", "RF-005", md)
    assert any("não é permitida em RF" in e for e in erros)


def test_rejeita_secao_obrigatoria_ausente():
    erros = validar_artefato_markdown("RF", "RF-005", MD_RF.split("## Descrição")[0])
    assert any("## Descrição" in e for e in erros)


def test_rejeita_id_divergente_na_tabela_de_metadados():
    erros = validar_artefato_markdown("HU", "HU-001", MD_HU.replace("| HU-001 ", "| HU-042 ", 1))
    assert any("metadados" in e for e in erros)


def test_rejeita_conteudo_vazio():
    assert validar_artefato_markdown("RN", "RN-001", "") == ["conteudo_md está vazio."]


def test_tipo_livre_e_aceito_para_gravacao_em_outros():
    """Matriz de rastreabilidade e UCs vão para Outros/ e não têm layout fixo."""
    assert validar_artefato_markdown("MTR", "MTR-001", "# Matriz\n\n| ID | Tipo |") == []
    assert validar_artefato_markdown("UC", "UC-001", "# UC-001: Submeter código") == []


def test_glossario_nao_exige_estrutura_de_artefato():
    assert validar_artefato_markdown("GLOSSARIO", "", "# Glossário\n\n| Termo | Definição |") == []


# ---------------------------------------------------------------------------
# C1 — before_tool_callback
# ---------------------------------------------------------------------------

def test_callback_deixa_passar_artefato_valido():
    args = {"tipo": "HU", "id_req": "HU-001", "conteudo_md": MD_HU}
    assert validar_antes_de_salvar(_tool(), args, _ctx()) is None


def test_callback_curto_circuita_artefato_invalido():
    args = {"tipo": "RF", "id_req": "RF-005", "conteudo_md": "sem estrutura"}
    resposta = validar_antes_de_salvar(_tool(), args, _ctx())
    assert resposta is not None
    assert "ERRO DE VALIDAÇÃO" in resposta["result"]
    assert "chame tool_salvar_artefato_requisito novamente" in resposta["result"]


def test_callback_ignora_outras_tools():
    args = {"qualquer": "coisa"}
    assert validar_antes_de_salvar(_tool("run_slicer"), args, _ctx()) is None


# ---------------------------------------------------------------------------
# C1 — dúvida sobre glossário não nasce bloqueante
# ---------------------------------------------------------------------------

def _duvida(artefato, bloqueante=True):
    return {
        "id_duvida": "D-001",
        "id_artefato_afetado": artefato,
        "bloqueante": bloqueante,
    }


@pytest.mark.parametrize(
    "artefato",
    ["Glossario", "Glossário", "Glossary", "[Glossário]", "GLOSSARIO-001"],
)
def test_duvida_de_glossario_perde_o_poder_de_veto(artefato):
    args = _duvida(artefato)
    assert rebaixar_duvida_de_glossario(_tool(TOOL_DUVIDA), args, _ctx()) is None
    assert args["bloqueante"] is False


def test_duvida_de_requisito_continua_bloqueando():
    args = _duvida("HU-001")
    rebaixar_duvida_de_glossario(_tool(TOOL_DUVIDA), args, _ctx())
    assert args["bloqueante"] is True


def test_duvida_de_glossario_nao_bloqueante_fica_intacta():
    args = _duvida("Glossario", bloqueante=False)
    rebaixar_duvida_de_glossario(_tool(TOOL_DUVIDA), args, _ctx())
    assert args["bloqueante"] is False


def test_rebaixamento_nunca_cancela_a_tool():
    """A dúvida continua sendo registrada; só muda a severidade."""
    args = _duvida("Glossario")
    assert rebaixar_duvida_de_glossario(_tool(TOOL_DUVIDA), args, _ctx()) is None


def test_rebaixamento_ignora_outras_tools():
    args = _duvida("Glossario")
    assert rebaixar_duvida_de_glossario(_tool(TOOL_SALVAR), args, _ctx()) is None
    assert args["bloqueante"] is True


# ---------------------------------------------------------------------------
# C2 — after_tool_callback
# ---------------------------------------------------------------------------

def test_registra_artefato_gravado_com_sucesso():
    ctx = _ctx()
    args = {"tipo": "hu", "id_req": "HU-001", "conteudo_md": MD_HU}
    registrar_artefato_persistido(_tool(), args, ctx, {"result": "SUCESSO: HU HU-001 salvo em /ws/HUs/HU-001.md"})
    assert ctx.state[STATE_ARTEFATOS] == [
        {"tipo": "HU", "id": "HU-001", "path": "/ws/HUs/HU-001.md"}
    ]


def test_nao_registra_quando_a_tool_falha():
    ctx = _ctx()
    args = {"tipo": "HU", "id_req": "HU-001", "conteudo_md": MD_HU}
    registrar_artefato_persistido(_tool(), args, ctx, {"result": "ERRO ao salvar artefato: I/O"})
    assert STATE_ARTEFATOS not in ctx.state


def test_regravacao_do_mesmo_artefato_nao_duplica():
    ctx = _ctx()
    args = {"tipo": "HU", "id_req": "HU-001", "conteudo_md": MD_HU}
    for _ in range(2):
        registrar_artefato_persistido(_tool(), args, ctx, {"result": "SUCESSO: HU HU-001 salvo em /ws/HUs/HU-001.md"})
    assert len(ctx.state[STATE_ARTEFATOS]) == 1


# ---------------------------------------------------------------------------
# C4 — auditoria
# ---------------------------------------------------------------------------

def _saida(**overrides) -> str:
    dados = {
        "status": "concluido",
        "user_stories": [{
            "id": "HU-001", "title": "Criação de exercícios", "persona": "Professor",
            "action": "criar exercícios", "value": "alunos praticarem",
            "acceptance_criteria": ["CA-1: enunciado em Markdown"],
        }],
        "functional_requirements": [{
            "id": "RF-005", "title": "Execução em Sandbox",
            "description": "Executar o código submetido em ambiente isolado.",
            "priority": "Alta", "hu_parent": "HU-001",
        }],
        "non_functional_requirements": [{
            "id": "RNF-001", "title": "Tempo de Resposta",
            "description": "Responder em até 5 segundos no percentil 95.",
            "category": "Desempenho",
        }],
        "business_rules": [{
            "id": "RN-001", "description": "Aceitar exclusivamente arquivos .py.",
        }],
        "traceability_rationale": [
            {
                "id_artefato": id_artefato,
                "origem": "Descrição inicial do professor",
                "motivo_inclusao": "Necessidade explicitada no texto de entrada",
            }
            for id_artefato in ("HU-001", "RF-005", "RNF-001", "RN-001")
        ],
        "summary": "Resumo executivo do processamento realizado.",
    }
    dados.update(overrides)
    return "Raciocínio do agente.\n```json\n" + json.dumps(dados, ensure_ascii=False) + "\n```"


def _matriz(saida: str | None = None) -> dict | None:
    """Reproduz o que o callback C3 entrega à auditoria."""
    return construir_matriz(json.loads(extrair_bloco_json(saida or _saida())))


PERSISTIDOS = [
    {"tipo": "HU", "id": "HU-001", "path": "p"},
    {"tipo": "RF", "id": "RF-005", "path": "p"},
    {"tipo": "RNF", "id": "RNF-001", "path": "p"},
    {"tipo": "RN", "id": "RN-001", "path": "p"},
]


def test_saida_coerente():
    saida = _saida()
    relatorio = auditar_analise(saida, PERSISTIDOS, matriz=_matriz(saida))
    assert relatorio["schema_status"] == "ok"
    assert relatorio["coerente"] is True


def test_detecta_artefato_declarado_que_nunca_foi_gravado():
    relatorio = auditar_analise(_saida(), PERSISTIDOS[:3])
    assert relatorio["declarados_sem_arquivo"] == ["RN-001"]
    assert relatorio["coerente"] is False


def test_detecta_arquivo_gravado_ausente_do_json():
    extra = [*PERSISTIDOS, {"tipo": "RF", "id": "RF-099", "path": "p"}]
    relatorio = auditar_analise(_saida(), extra)
    assert relatorio["arquivos_sem_declaracao"] == ["RF-099"]


def test_detecta_referencia_orfa():
    saida = _saida(functional_requirements=[{
        "id": "RF-005", "title": "Execução em Sandbox",
        "description": "Executar o código submetido em ambiente isolado.",
        "priority": "Alta", "hu_parent": "HU-999",
    }])
    relatorio = auditar_analise(saida, PERSISTIDOS)
    assert any("HU-999" in orfa for orfa in relatorio["referencias_orfas"])


def test_detecta_hu_parent_apontando_para_tipo_errado():
    """RF derivando de outro RF é vínculo falso, mesmo com o ID existindo."""
    saida = _saida(functional_requirements=[
        {
            "id": "RF-005", "title": "Execução em Sandbox",
            "description": "Executar o código submetido em ambiente isolado.",
            "priority": "Alta", "hu_parent": None,
        },
        {
            "id": "RF-006", "title": "Limite de tempo",
            "description": "Interromper a execução após o tempo limite.",
            "priority": "Alta", "hu_parent": "RF-005",
        },
    ])
    relatorio = auditar_analise(saida, PERSISTIDOS)
    assert any(
        "RF-006" in orfa and "não uma HU" in orfa
        for orfa in relatorio["referencias_orfas"]
    )


def test_detecta_id_duplicado():
    duplicado = {
        "id": "RN-001", "description": "Outra regra completamente diferente.",
    }
    saida = _saida(business_rules=[
        {"id": "RN-001", "description": "Aceitar exclusivamente arquivos .py."},
        duplicado,
    ])
    relatorio = auditar_analise(saida, PERSISTIDOS)
    assert any("RN-001" in msg for msg in relatorio["ids_duplicados"])


def test_detecta_colecao_vazia():
    relatorio = auditar_analise(_saida(business_rules=[]), PERSISTIDOS)
    assert "business_rules" in relatorio["colecoes_vazias"]


def test_business_rules_vazio_reprova_no_schema():
    """RN é obrigatória: lista vazia é erro de schema, não coleção opcional."""
    relatorio = auditar_analise(_saida(business_rules=[]), PERSISTIDOS)
    assert relatorio["schema_status"] == "validation_error"
    assert any("business_rules" in erro for erro in relatorio["erros_schema"])
    assert relatorio["coerente"] is False


def test_matriz_ausente_reprova_a_fase():
    """A matriz é obrigatória: ausência = o builder determinístico falhou."""
    relatorio = auditar_analise(_saida(), PERSISTIDOS, matriz=None)
    assert relatorio["schema_status"] == "validation_error"
    assert any("ausente" in p for p in relatorio["matriz_rastreabilidade"])
    assert relatorio["coerente"] is False


def test_matriz_que_nao_cobre_todos_os_artefatos_e_detectada():
    parcial = _matriz()
    parcial["itens"] = [i for i in parcial["itens"] if i["id_artefato"] == "RF-005"]
    relatorio = auditar_analise(_saida(), PERSISTIDOS, matriz=parcial)
    assert any(
        "não rastreia" in p and "HU-001" in p
        for p in relatorio["matriz_rastreabilidade"]
    )
    assert relatorio["coerente"] is False


def test_matriz_sem_itens_ou_sem_markdown_e_detectada():
    vazia = {"id": "MTR-001", "itens": [], "lacunas_candidatas_doubt": [], "markdown": ""}
    problemas = auditar_analise(_saida(), PERSISTIDOS, matriz=vazia)[
        "matriz_rastreabilidade"
    ]
    assert any("sem itens" in p for p in problemas)
    assert any("markdown" in p for p in problemas)


def test_campo_inventado_e_reprovado_pelo_schema():
    saida = _saida(business_rules=[{
        "id": "RN-001", "description": "Aceitar exclusivamente arquivos .py.",
        "criticidade": "máxima",
    }])
    relatorio = auditar_analise(saida, PERSISTIDOS)
    assert relatorio["schema_status"] == "validation_error"
    assert any("criticidade" in erro for erro in relatorio["erros_schema"])


def test_cruzamento_roda_mesmo_com_schema_invalido():
    """Erro de campo isolado não pode cegar a detecção de alucinação."""
    saida = _saida(business_rules=[{"id": "RN-001", "description": "curta"}])
    relatorio = auditar_analise(saida, PERSISTIDOS[:3])
    assert relatorio["schema_status"] == "validation_error"
    assert relatorio["declarados_sem_arquivo"] == ["RN-001"]


def test_saida_ausente_ou_sem_json():
    assert auditar_analise("", PERSISTIDOS)["schema_status"] == "sem_saida"
    assert auditar_analise("texto sem json", PERSISTIDOS)["schema_status"] == "parse_error"


def test_auditar_saida_final_grava_relatorio_em_state():
    saida = _saida()
    ctx = _ctx({
        "analysis_result": saida,
        STATE_ARTEFATOS: PERSISTIDOS,
        STATE_MATRIZ: _matriz(saida),
    })
    assert auditar_saida_final(callback_context=ctx) is None
    assert ctx.state[STATE_AUDITORIA]["coerente"] is True


def test_saida_vazia_nao_e_reportada_como_ok():
    """JSON bem formado e vazio valida no schema, mas nada foi analisado."""
    vazio = json.dumps({"status": "concluido", "summary": "nada a fazer"})
    ctx = _ctx({"analysis_result": vazio, STATE_ARTEFATOS: []})
    auditar_saida_final(callback_context=ctx)
    assert ctx.state[STATE_AUDITORIA]["schema_status"] == "sem_analise"
    assert ctx.state[STATE_AUDITORIA]["coerente"] is False


def test_saida_vazia_nao_sobrescreve_auditoria_anterior():
    """Passada final estéril não pode apagar os achados da passada que produziu."""
    anterior = {"schema_status": "validation_error", "coerente": False}
    vazio = json.dumps({"status": "concluido", "summary": "nada a fazer"})
    ctx = _ctx({
        "analysis_result": vazio,
        STATE_ARTEFATOS: [],
        STATE_AUDITORIA: anterior,
    })
    auditar_saida_final(callback_context=ctx)
    assert ctx.state[STATE_AUDITORIA] is anterior


def test_auditar_saida_final_nao_propaga_excecao():
    ctx = MagicMock()
    type(ctx).state = property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
    assert auditar_saida_final(callback_context=ctx) is None
