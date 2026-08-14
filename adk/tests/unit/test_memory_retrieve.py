"""Testes da recuperação — pré-filtro determinístico + ranking do ReasoningBank.

Nenhum teste aqui baixa modelo de embedding: o `_get_embedder` é substituído por
um duplo determinístico, ou por `None` para exercitar o caminho degradado. Um
teste que dependesse de rede seria justamente o tipo de teste que não roda no
dia da apresentação.
"""

import pytest

from shared.memory import retrieve
from shared.memory.retrieve import recuperar, render_bloco
from shared.memory.schemas import (
    MemoryItem,
    MemoryOutcome,
    MemoryProvenance,
    MemoryStatus,
)
from shared.memory.store import MemoryStore


class FakeEmbedder:
    """Embedder determinístico: vetor = contagem de termos-âncora do texto.

    Não simula semântica de verdade — só garante que o item que compartilha
    mais termos com a consulta ranqueie na frente, que é a propriedade do
    cosseno que a recuperação depende.
    """

    TERMOS = ("porta", "build", "banco", "docker")

    def embed(self, textos):
        for texto in textos:
            baixo = texto.casefold()
            yield [float(baixo.count(t)) for t in self.TERMOS] + [0.1]


@pytest.fixture
def store(tmp_path):
    return MemoryStore(tmp_path / "bank.jsonl")


@pytest.fixture(autouse=True)
def _sem_download(monkeypatch):
    """Nenhum teste deste arquivo pode tentar baixar o modelo ONNX."""
    monkeypatch.setattr(retrieve, "_get_embedder", lambda: FakeEmbedder())


def _item(titulo, *, conteudo="", codigos=("FALHA_BUILD",), stack="python-fastapi",
          status=MemoryStatus.PROMOVIDO):
    return MemoryItem(
        title=titulo,
        description="Descrição.",
        content=conteudo or f"Lição sobre {titulo}, longa o bastante para valer.",
        outcome=MemoryOutcome.FALHA,
        error_codes=list(codigos),
        tech_stack=stack,
        status=status,
        provenance=MemoryProvenance(run_id="r1", report_path="/tmp/r.json"),
    )


# --- só o que foi promovido chega ao prompt -------------------------------


def test_quarentena_e_rejeitados_nunca_sao_recuperados(store):
    store.append(
        [
            _item("Promovida"),
            _item("Em revisão", status=MemoryStatus.REVISAR),
            _item("Rejeitada", status=MemoryStatus.REJEITADO),
        ]
    )

    titulos = [i.title for i in recuperar("qualquer", tech_stack="python-fastapi", store=store)]

    assert titulos == ["Promovida"]


def test_banco_vazio_devolve_nada(store):
    assert recuperar("qualquer", store=store) == []


def test_kill_switch_impede_a_recuperacao(store, monkeypatch):
    store.append([_item("Promovida")])
    monkeypatch.setenv("AI4ES_MEMORY_ENABLED", "0")

    assert recuperar("qualquer", tech_stack="python-fastapi", store=store) == []


# --- pré-filtro por escopo (OEP: perspective confinement) -----------------


def test_item_de_outra_stack_nao_vaza(store):
    store.append([_item("Do Python"), _item("Do Node", stack="node-express")])

    titulos = [i.title for i in recuperar("x", tech_stack="python-fastapi", store=store)]

    assert titulos == ["Do Python"]


def test_item_generico_passa_em_qualquer_stack(store):
    store.append([_item("Genérica", stack="")])

    titulos = [i.title for i in recuperar("x", tech_stack="python-fastapi", store=store)]

    assert titulos == ["Genérica"]


def test_stack_desconhecida_retem_itens_com_escopo(store):
    """Sem saber a stack da run, o filtro fica MAIS restritivo, não menos."""
    store.append([_item("Com escopo"), _item("Genérica", stack="")])

    titulos = [i.title for i in recuperar("x", tech_stack="", store=store)]

    assert titulos == ["Genérica"]


# --- pré-filtro por error_code (a vantagem que o ReasoningBank não tem) ---


def test_error_code_da_run_seleciona_o_item_correspondente(store):
    store.append(
        [
            _item("Sobre build", codigos=["FALHA_BUILD"]),
            _item("Sobre inicialização", codigos=["APP_NAO_INICIALIZOU"]),
        ]
    )

    titulos = [
        i.title
        for i in recuperar(
            "x", error_codes=["APP_NAO_INICIALIZOU"], tech_stack="python-fastapi", store=store
        )
    ]

    assert titulos == ["Sobre inicialização"]


def test_error_code_sem_correspondencia_nao_esvazia_o_bloco(store):
    """Melhor ranquear o banco inteiro do que entregar memória vazia."""
    store.append([_item("Sobre build", codigos=["FALHA_BUILD"])])

    itens = recuperar(
        "x", error_codes=["CODIGO_INEDITO"], tech_stack="python-fastapi", store=store
    )

    assert [i.title for i in itens] == ["Sobre build"]


def test_comparacao_de_error_code_ignora_caixa(store):
    store.append([_item("Sobre build", codigos=["falha_build"])])

    itens = recuperar(
        "x", error_codes=["FALHA_BUILD"], tech_stack="python-fastapi", store=store
    )

    assert len(itens) == 1


# --- ranking e teto --------------------------------------------------------


def test_ranking_traz_o_item_mais_proximo_da_consulta_primeiro(store):
    store.append(
        [
            _item("Sobre banco", conteudo="banco banco banco de dados relacional aqui"),
            _item("Sobre porta", conteudo="porta porta porta do serviço declarada aqui"),
        ]
    )

    itens = recuperar(
        "porta porta porta", tech_stack="python-fastapi", store=store
    )

    assert itens[0].title == "Sobre porta"


def test_top_k_limita_o_tamanho_do_bloco(store):
    store.append([_item(f"Lição {n}") for n in range(10)])

    assert len(recuperar("x", tech_stack="python-fastapi", store=store, k=3)) == 3


def test_fallback_por_recencia_quando_nao_ha_embedder(store, monkeypatch):
    """Sem fastembed a memória continua funcionando, só perde o desempate."""
    monkeypatch.setattr(retrieve, "_get_embedder", lambda: None)
    store.append([_item("Antiga"), _item("Recente")])

    itens = recuperar("x", tech_stack="python-fastapi", store=store)

    assert {i.title for i in itens} == {"Antiga", "Recente"}


def test_falha_do_embedder_nao_propaga(store, monkeypatch):
    class Explosivo:
        def embed(self, textos):
            raise RuntimeError("modelo corrompido")

    monkeypatch.setattr(retrieve, "_get_embedder", lambda: Explosivo())
    store.append([_item("Sobrevivente")])

    itens = recuperar("x", tech_stack="python-fastapi", store=store)

    assert [i.title for i in itens] == ["Sobrevivente"]


# --- renderização do bloco -------------------------------------------------


def test_bloco_vazio_para_lista_vazia():
    assert render_bloco([]) == ""


def test_bloco_traz_titulo_conteudo_e_error_code_de_origem():
    bloco = render_bloco([_item("Declarar a porta", codigos=["APP_NAO_INICIALIZOU"])])

    assert "Declarar a porta" in bloco
    assert "APP_NAO_INICIALIZOU" in bloco
    assert "Lição sobre Declarar a porta" in bloco


def test_bloco_se_declara_subordinado_ao_contrato_da_task():
    """A memória é aviso, não requisito — senão compete com o contrato."""
    bloco = render_bloco([_item("Qualquer")])

    assert "NÃO como requisito" in bloco
    assert "o contrato vence" in bloco
