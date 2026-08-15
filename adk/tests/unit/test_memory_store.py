"""Testes da persistência — a resposta à crítica 1 do PR recusado.

Dois invariantes, e o primeiro é o que responde à crítica:

1. **o banco vive fora do `workspace_output/`**, portanto sobrevive ao
   `shutil.rmtree` que o `init_workspace()` faz a cada run. Sem isso não existe
   memória "entre runs" — existe memória "dentro de uma run", que é o que já
   havia;
2. gravar duas vezes a mesma lição não a duplica.
"""

import json

import pytest

from shared.memory.schemas import (
    MemoryItem,
    MemoryOutcome,
    MemoryProvenance,
    MemoryStatus,
    derivar_id,
)
from shared.memory.store import MemoryStore, get_memory_dir, memoria_habilitada


@pytest.fixture
def store(tmp_path):
    return MemoryStore(tmp_path / "bank.jsonl")


def _item(titulo="Declarar dependências", status=MemoryStatus.PROMOVIDO):
    return MemoryItem(
        title=titulo,
        description="Uma descrição.",
        content="Um conteúdo suficientemente longo para ser uma lição de verdade.",
        outcome=MemoryOutcome.FALHA,
        error_codes=["FALHA_BUILD"],
        tech_stack="python-fastapi",
        status=status,
        provenance=MemoryProvenance(run_id="r1", report_path="/tmp/r.json"),
    )


# --- crítica 1: o banco não pode viver dentro do workspace ----------------


def test_diretorio_default_fica_fora_do_workspace(monkeypatch):
    """O `init_workspace()` apaga o workspace inteiro; o banco não pode estar lá."""
    monkeypatch.delenv("AI4ES_MEMORY_DIR", raising=False)
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", "./workspace_output")

    from shared.workspace import get_workspace_root

    memoria = get_memory_dir()
    workspace = get_workspace_root()

    assert not str(memoria).startswith(str(workspace))
    assert workspace not in memoria.parents


def test_diretorio_e_configuravel_por_env(monkeypatch, tmp_path):
    """Trocar de banco (ou zerá-lo para o braço A/B) não pode exigir código."""
    monkeypatch.setenv("AI4ES_MEMORY_DIR", str(tmp_path / "outro"))

    assert get_memory_dir() == (tmp_path / "outro").resolve()


# --- round-trip ------------------------------------------------------------


def test_grava_e_recarrega_preservando_os_campos(store):
    original = _item()

    store.append([original])
    (recarregado,) = store.load()

    assert recarregado.id == original.id
    assert recarregado.title == original.title
    assert recarregado.content == original.content
    assert recarregado.status == MemoryStatus.PROMOVIDO
    assert recarregado.error_codes == ["FALHA_BUILD"]
    assert recarregado.provenance.report_path == "/tmp/r.json"


def test_arquivo_e_jsonl_valido(store):
    store.append([_item("Primeira"), _item("Segunda")])

    linhas = store.path.read_text(encoding="utf-8").strip().splitlines()

    assert len(linhas) == 2
    assert all(json.loads(linha)["title"] for linha in linhas)


def test_banco_inexistente_carrega_vazio(tmp_path):
    assert MemoryStore(tmp_path / "nao-existe.jsonl").load() == []


# --- dedup -----------------------------------------------------------------


def test_regravar_a_mesma_licao_nao_duplica(store):
    store.append([_item()])
    novos = store.append([_item()])

    assert novos == []
    assert len(store.load()) == 1


def test_dedup_tambem_vale_dentro_do_mesmo_lote(store):
    """Uma trajetória pode render dois itens com o mesmo título."""
    novos = store.append([_item(), _item()])

    assert len(novos) == 1
    assert len(store.load()) == 1


def test_dedup_ignora_caixa_e_espacos_no_titulo(store):
    store.append([_item("Declarar Dependências")])
    novos = store.append([_item("  declarar   dependências  ")])

    assert novos == []
    assert derivar_id("Declarar Dependências") == derivar_id("  declarar dependências ")


def test_titulos_diferentes_convivem(store):
    store.append([_item("Primeira lição")])
    novos = store.append([_item("Segunda lição")])

    assert len(novos) == 1
    assert len(store.load()) == 2


# --- resiliência -----------------------------------------------------------


def test_linha_corrompida_e_ignorada_sem_derrubar(store):
    """Banco parcialmente ilegível não pode quebrar o pipeline."""
    store.append([_item("Boa lição")])
    with store.path.open("a", encoding="utf-8") as fh:
        fh.write("{isto não é json}\n")

    itens = store.load()

    assert len(itens) == 1
    assert itens[0].title == "Boa lição"


# --- consultas -------------------------------------------------------------


def test_promovidos_exclui_quarentena_e_rejeitados(store):
    store.append(
        [
            _item("Promovida", MemoryStatus.PROMOVIDO),
            _item("Em revisão", MemoryStatus.REVISAR),
            _item("Rejeitada", MemoryStatus.REJEITADO),
        ]
    )

    promovidos = store.promovidos()

    assert [i.title for i in promovidos] == ["Promovida"]


def test_stats_conta_por_status(store):
    store.append(
        [
            _item("A", MemoryStatus.PROMOVIDO),
            _item("B", MemoryStatus.PROMOVIDO),
            _item("C", MemoryStatus.REVISAR),
        ]
    )

    assert store.stats() == {
        "total": 3,
        "promovido": 2,
        "revisar": 1,
        "rejeitado": 0,
    }


def test_registrar_uso_guarda_o_run_id_so_nos_itens_citados(store):
    store.append([_item("Usada"), _item("Não usada")])
    alvo = next(i for i in store.load() if i.title == "Usada")

    store.registrar_uso([alvo.id], "run-1")

    por_titulo = {i.title: i.used_in_runs for i in store.load()}
    assert por_titulo == {"Usada": ["run-1"], "Não usada": []}


def test_registrar_uso_e_idempotente_dentro_da_mesma_run(store):
    """O provider do coder roda a cada TURNO; repetir não pode inflar o dado.

    É esta idempotência que dispensa deduplicar por invocação do lado de fora —
    o que antes era um contador escalar mais uma lista de invocações em memória
    de processo.
    """
    store.append([_item("Usada")])
    alvo = store.load()[0]

    assert store.registrar_uso([alvo.id], "run-1") is True
    assert store.registrar_uso([alvo.id], "run-1") is False  # nada novo a gravar
    assert store.registrar_uso([alvo.id], "run-2") is True

    assert store.load()[0].used_in_runs == ["run-1", "run-2"]


def test_registrar_uso_sem_run_id_nao_grava(store):
    """Sem chave de run o registro seria inútil — não dá para cruzar com nada."""
    store.append([_item("Usada")])
    alvo = store.load()[0]

    assert store.registrar_uso([alvo.id], "") is False
    assert store.load()[0].used_in_runs == []


# --- kill switch -----------------------------------------------------------


@pytest.mark.parametrize("valor", ["0", "false", "no", "FALSE", "No"])
def test_kill_switch_desliga(monkeypatch, valor):
    monkeypatch.setenv("AI4ES_MEMORY_ENABLED", valor)

    assert memoria_habilitada() is False


@pytest.mark.parametrize("valor", ["1", "true", "sim", "qualquer-coisa"])
def test_kill_switch_ligado_por_default_e_por_valor(monkeypatch, valor):
    monkeypatch.setenv("AI4ES_MEMORY_ENABLED", valor)
    assert memoria_habilitada() is True

    monkeypatch.delenv("AI4ES_MEMORY_ENABLED")
    assert memoria_habilitada() is True
