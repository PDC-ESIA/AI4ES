"""Testes da normalização de critérios de aceite (Fase 0 — identidade)."""

from __future__ import annotations

import pytest

from shared.tools.coding_tools.criterios_aceite import (
    AcceptanceCriterion,
    canonizar_id,
    descricoes,
    normalizar_criterios,
    normalizar_mapa_de_testes,
)


# ---------------------------------------------------------------------------
# Formato antigo (lista de strings) — tasks geradas antes desta mudança
# ---------------------------------------------------------------------------


def test_lista_de_strings_recebe_ids_sequenciais_e_automatable_padrao():
    criterios = normalizar_criterios(
        ["Retornar 401 com credenciais inválidas", "Persistir o ensaio"]
    )

    assert [c.id for c in criterios] == ["CA-01", "CA-02"]
    assert [c.description for c in criterios] == [
        "Retornar 401 com credenciais inválidas",
        "Persistir o ensaio",
    ]
    # Sem classificação declarada, assume-se automatizável: o custo de cobrar um
    # teste à toa é menor que o de um critério sumir da medição em silêncio.
    assert all(c.automatable is True for c in criterios)


def test_strings_vazias_sao_descartadas_sem_consumir_id():
    criterios = normalizar_criterios(["  ", "Critério real", ""])

    assert [(c.id, c.description) for c in criterios] == [("CA-01", "Critério real")]


# ---------------------------------------------------------------------------
# Formato novo (objetos)
# ---------------------------------------------------------------------------


def test_ids_declarados_validos_sao_preservados():
    """O id declarado é a chave do mapa teste ↔ critério; reatribuir quebraria."""
    criterios = normalizar_criterios(
        [
            {"id": "CA-07", "description": "Primeiro", "automatable": True},
            {"id": "CA-03", "description": "Segundo", "automatable": False},
        ]
    )

    assert [c.id for c in criterios] == ["CA-07", "CA-03"]
    assert [c.automatable for c in criterios] == [True, False]


@pytest.mark.parametrize(
    "grafia,canonico",
    [
        ("CA-01", "CA-01"),
        ("CA-1", "CA-01"),
        (" ca-1 ", "CA-01"),
        ("ca-007", "CA-07"),
        ("CA-100", "CA-100"),
        ("CA-9", "CA-09"),
    ],
)
def test_id_reconhecido_sai_sempre_na_forma_canonica(grafia, canonico):
    """As duas pontas do mapa teste ↔ critério precisam grafar o id igual.

    A task é escrita por um LLM e o mapa do manifesto por outro; se `CA-1` na
    task virar `CA-01` no manifesto (o exemplo do prompt usa dois dígitos), o
    vínculo quebraria em silêncio.
    """
    criterios = normalizar_criterios([{"id": grafia, "description": "X"}])

    assert [c.id for c in criterios] == [canonico]


def test_grafias_que_colapsam_no_mesmo_id_sao_tratadas_como_repeticao():
    """Canonizar pode colidir dois ids distintos na origem — sem perder nenhum."""
    criterios = normalizar_criterios(
        [{"id": "CA-1", "description": "A"}, {"id": "CA-01", "description": "B"}]
    )

    assert [c.id for c in criterios] == ["CA-01", "CA-02"]
    assert [c.description for c in criterios] == ["A", "B"]


@pytest.mark.parametrize(
    "id_invalido", ["CRIT-1", "CA", "ca-", "1", "", "CA-01-A", None, 7, []]
)
def test_id_fora_do_padrao_recebe_o_proximo_livre(id_invalido):
    criterios = normalizar_criterios(
        [{"id": id_invalido, "description": "Único critério"}]
    )

    assert [c.id for c in criterios] == ["CA-01"]


def test_id_repetido_mantem_a_primeira_ocorrencia_e_realoca_a_segunda():
    criterios = normalizar_criterios(
        [
            {"id": "CA-01", "description": "Primeiro"},
            {"id": "CA-01", "description": "Segundo"},
        ]
    )

    assert [c.id for c in criterios] == ["CA-01", "CA-02"]
    assert [c.description for c in criterios] == ["Primeiro", "Segundo"]


def test_id_gerado_nunca_colide_com_id_declarado_adiante():
    """O contador pula ids já reservados, mesmo os declarados depois na lista."""
    criterios = normalizar_criterios(
        [
            {"description": "Sem id"},
            {"id": "CA-01", "description": "Com id"},
            {"description": "Sem id também"},
        ]
    )

    assert [c.id for c in criterios] == ["CA-02", "CA-01", "CA-03"]
    assert len({c.id for c in criterios}) == 3


def test_alias_criterion_e_aceito_como_texto():
    criterios = normalizar_criterios([{"criterion": "Texto pelo alias"}])

    assert [c.description for c in criterios] == ["Texto pelo alias"]


def test_dict_sem_texto_aproveitavel_e_descartado():
    criterios = normalizar_criterios(
        [{"id": "CA-01"}, {"description": "   "}, {"description": "Vale"}]
    )

    assert [c.description for c in criterios] == ["Vale"]


# ---------------------------------------------------------------------------
# `automatable` — leitura tolerante, default explícito
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (True, True),
        (False, False),
        ("true", True),
        ("false", False),
        ("  FALSE  ", False),
    ],
)
def test_automatable_aceita_bool_e_string(valor, esperado):
    criterios = normalizar_criterios([{"description": "X", "automatable": valor}])

    assert criterios[0].automatable is esperado


def test_alias_automatizavel_e_aceito():
    criterios = normalizar_criterios([{"description": "X", "automatizavel": False}])

    assert criterios[0].automatable is False


@pytest.mark.parametrize("valor", ["talvez", 1, None, {}, []])
def test_automatable_ilegivel_cai_para_o_padrao(valor):
    criterios = normalizar_criterios([{"description": "X", "automatable": valor}])

    assert criterios[0].automatable is True


# ---------------------------------------------------------------------------
# Totalidade: a entrada vem de um LLM e nunca pode derrubar a invocação
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("valor", [None, "texto", 42, {"a": 1}, object()])
def test_entrada_nao_lista_devolve_vazio_sem_levantar(valor):
    assert normalizar_criterios(valor) == []


def test_itens_de_tipo_inesperado_sao_descartados_sem_levantar():
    criterios = normalizar_criterios([None, 42, ["aninhado"], "Sobrevivente"])

    assert [(c.id, c.description) for c in criterios] == [("CA-01", "Sobrevivente")]


def test_lista_vazia_devolve_vazio():
    assert normalizar_criterios([]) == []


def test_modelos_ja_normalizados_passam_intactos():
    """Idempotência: renormalizar não pode remexer em ids nem na classificação."""
    original = normalizar_criterios(
        [
            {"id": "CA-05", "description": "Primeiro", "automatable": False},
            "Segundo",
        ]
    )

    assert normalizar_criterios(original) == original


def test_descricoes_extrai_apenas_os_textos_na_ordem():
    criterios = [
        AcceptanceCriterion(id="CA-01", description="A"),
        AcceptanceCriterion(id="CA-02", description="B", automatable=False),
    ]

    assert descricoes(criterios) == ["A", "B"]


# ---------------------------------------------------------------------------
# Mapa teste ↔ critério (Fase 1)
# ---------------------------------------------------------------------------


def _criterios(*ids_e_automatable) -> list[AcceptanceCriterion]:
    return [
        AcceptanceCriterion(id=id_, description=f"Critério {id_}", automatable=auto)
        for id_, auto in ids_e_automatable
    ]


def test_mapa_liga_criterios_existentes_aos_seus_testes():
    mapa = normalizar_mapa_de_testes(
        {"CA-01": ["tests/test_a.py::test_x"], "CA-02": ["tests/test_b.py::test_y"]},
        _criterios(("CA-01", True), ("CA-02", True)),
    )

    assert mapa.por_criterio == {
        "CA-01": ["tests/test_a.py::test_x"],
        "CA-02": ["tests/test_b.py::test_y"],
    }
    assert mapa.ids_desconhecidos == []


def test_mapa_canoniza_a_chave_antes_de_casar():
    """O coder escreve o mapa lendo a Task, mas pode variar a grafia do id."""
    mapa = normalizar_mapa_de_testes(
        {"ca-1": ["tests/test_a.py::test_x"]}, _criterios(("CA-01", True))
    )

    assert mapa.por_criterio == {"CA-01": ["tests/test_a.py::test_x"]}
    assert mapa.ids_desconhecidos == []


def test_grafias_diferentes_do_mesmo_id_somam_os_testes():
    """Convergir para a mesma chave não pode fazer uma lista sobrescrever a outra."""
    mapa = normalizar_mapa_de_testes(
        {"CA-1": ["t::a"], "CA-01": ["t::b", "t::a"]}, _criterios(("CA-01", True))
    )

    assert mapa.por_criterio == {"CA-01": ["t::a", "t::b"]}


@pytest.mark.parametrize("chave", ["CRIT-1", "CA-99", "", "tests/test_a.py"])
def test_ids_fora_da_task_sao_descartados_e_registrados(chave):
    """Anotação errada do coder precisa ser visível, sem virar cobertura."""
    mapa = normalizar_mapa_de_testes(
        {chave: ["tests/test_a.py::test_x"]}, _criterios(("CA-01", True))
    )

    assert mapa.por_criterio == {}
    assert mapa.ids_desconhecidos == [chave]


def test_criterio_sem_teste_declarado_simplesmente_nao_aparece():
    mapa = normalizar_mapa_de_testes(
        {"CA-01": ["t::a"]}, _criterios(("CA-01", True), ("CA-02", True))
    )

    assert set(mapa.por_criterio) == {"CA-01"}
    assert mapa.ids_desconhecidos == []


def test_lista_de_testes_vazia_nao_conta_como_cobertura():
    mapa = normalizar_mapa_de_testes(
        {"CA-01": [], "CA-02": ["  ", ""]}, _criterios(("CA-01", True), ("CA-02", True))
    )

    assert mapa.por_criterio == {}


def test_mapa_aceita_criterio_nao_automatizavel_se_o_coder_declarar():
    """A classificação orienta o coder; ela não invalida um vínculo declarado.

    Se um teste de fato existe e comprova o critério, descartá-lo por causa do
    rótulo jogaria fora evidência REAL — o rótulo é a expectativa, o teste é o
    fato.
    """
    mapa = normalizar_mapa_de_testes(
        {"CA-01": ["t::a"]}, _criterios(("CA-01", False))
    )

    assert mapa.por_criterio == {"CA-01": ["t::a"]}


@pytest.mark.parametrize("bruto", [None, "texto", 42, [], object()])
def test_mapa_malformado_devolve_vazio_sem_levantar(bruto):
    mapa = normalizar_mapa_de_testes(bruto, _criterios(("CA-01", True)))

    assert mapa.por_criterio == {}
    assert mapa.ids_desconhecidos == []


def test_mapa_sem_criterios_na_task_descarta_tudo():
    mapa = normalizar_mapa_de_testes({"CA-01": ["t::a"]}, [])

    assert mapa.por_criterio == {}
    assert mapa.ids_desconhecidos == ["CA-01"]


def test_mapa_usa_task_id_como_namespace_dos_criterios():
    mapa = normalizar_mapa_de_testes(
        {"CA-01": ["t::antigo"]},
        _criterios(("CA-01", True)),
        task_id="TASK-002",
        task_id_declarada="TASK-001",
    )

    assert mapa.por_criterio == {}
    assert mapa.escopo_valido is False
    assert mapa.task_id_declarada == "TASK-001"


@pytest.mark.parametrize("declarada", ["task-002", " TASK-002 ", "Task-002"])
def test_mapa_tolera_grafia_do_task_id_declarado(declarada):
    """Descarte é por ESCOPO, nunca por caixa ou espaço — os dois lados são LLM."""
    mapa = normalizar_mapa_de_testes(
        {"CA-01": ["t::atual"]},
        _criterios(("CA-01", True)),
        task_id="TASK-002",
        task_id_declarada=declarada,
    )

    assert mapa.por_criterio == {"CA-01": ["t::atual"]}
    assert mapa.escopo_valido is True


@pytest.mark.parametrize("task_id", [None, "", "   ", 42])
def test_sem_task_corrente_utilizavel_o_mapa_segue_pelo_caminho_legado(task_id):
    """Chamador que não informa a Task (uso fora do TaskIterator) não perde nada."""
    mapa = normalizar_mapa_de_testes(
        {"CA-01": ["t::x"]},
        _criterios(("CA-01", True)),
        task_id=task_id,
        task_id_declarada=None,
    )

    assert mapa.por_criterio == {"CA-01": ["t::x"]}
    assert mapa.escopo_valido is True


def test_mapa_aceita_ids_locais_quando_namespace_e_da_task_atual():
    mapa = normalizar_mapa_de_testes(
        {"CA-01": ["t::atual"]},
        _criterios(("CA-01", True)),
        task_id="TASK-002",
        task_id_declarada="TASK-002",
    )

    assert mapa.por_criterio == {"CA-01": ["t::atual"]}
    assert mapa.escopo_valido is True


@pytest.mark.parametrize(
    "bruto,esperado",
    [("CA-01", "CA-01"), ("ca-7", "CA-07"), ("CA-100", "CA-100")],
)
def test_canonizar_id_publico(bruto, esperado):
    assert canonizar_id(bruto) == esperado


@pytest.mark.parametrize("bruto", ["CRIT-1", "CA-", "", None, 7])
def test_canonizar_id_recusa_o_que_nao_e_id(bruto):
    assert canonizar_id(bruto) is None
