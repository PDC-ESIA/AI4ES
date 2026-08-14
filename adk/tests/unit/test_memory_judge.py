"""Testes da curadoria ternária — a resposta à crítica 2 do PR recusado.

O invariante que estes testes protegem: **a promoção é o caso excepcional, não
o default**. Todo caminho de dúvida termina em `REVISAR`, e só um item com
rastro para o `ExecutionReport`, com `error_code` (quando é lição de falha) e
com escopo de stack chega a `PROMOVIDO` — que é o único status que o
`retrieve` injeta no prompt do coder.
"""

import pytest

from shared.memory.judge import julgar, julgar_lote
from shared.memory.schemas import (
    MemoryItem,
    MemoryOutcome,
    MemoryProvenance,
    MemoryStatus,
)

CONTEUDO_VALIDO = (
    "Declare a dependência no manifesto sempre que importar um símbolo novo, "
    "porque o build resolve os imports contra o manifesto e não contra o código."
)


def _prov(report_path="/tmp/TASK-001.report.json"):
    return MemoryProvenance(
        run_id="run-1", task_id="TASK-001", report_path=report_path
    )


def _item(**kwargs):
    """Item ancorado e promovível; cada teste degrada um campo por vez."""
    base = dict(
        title="Declarar dependências no manifesto",
        description="Import sem pacote declarado quebra o build.",
        content=CONTEUDO_VALIDO,
        outcome=MemoryOutcome.FALHA,
        error_codes=["FALHA_BUILD"],
        unmet_criteria=[],
        tech_stack="python-fastapi",
        provenance=_prov(),
    )
    base.update(kwargs)
    return MemoryItem(**base)


# --- promoção -------------------------------------------------------------


def test_item_totalmente_ancorado_e_promovido():
    julgado = julgar(_item())

    assert julgado.status == MemoryStatus.PROMOVIDO
    assert "TASK-001.report.json" in julgado.judge_reason


def test_lição_de_sucesso_nao_exige_error_code():
    """Só a lição de FALHA precisa de código; sucesso não tem o que citar."""
    julgado = julgar(
        _item(outcome=MemoryOutcome.SUCESSO, error_codes=[]),
        veredito_status="aprovado",
    )

    assert julgado.status == MemoryStatus.PROMOVIDO


# --- rejeição (camada de forma) -------------------------------------------


@pytest.mark.parametrize(
    "campo,valor,fragmento",
    [
        ("title", "ab", "Título"),
        ("content", "Curto.", "abaixo do mínimo"),
        ("description", "", "Sem descrição"),
    ],
    ids=["titulo-curto", "conteudo-truncado", "sem-descricao"],
)
def test_item_malformado_e_rejeitado(campo, valor, fragmento):
    julgado = julgar(_item(**{campo: valor}))

    assert julgado.status == MemoryStatus.REJEITADO
    assert fragmento in julgado.judge_reason


# --- rejeição (contra-evidência, GovMem) ----------------------------------


def test_licao_de_sucesso_em_run_reprovada_e_rejeitada():
    """Contra-evidência: a alegação contradiz o veredito determinístico."""
    julgado = julgar(
        _item(outcome=MemoryOutcome.SUCESSO), veredito_status="reprovado"
    )

    assert julgado.status == MemoryStatus.REJEITADO
    assert "contradiz a evidência" in julgado.judge_reason


# --- quarentena (o terceiro veredito) -------------------------------------


def test_item_sem_rastro_para_o_report_fica_em_quarentena():
    """Sem `report_path` a alegação não é auditável depois — mas pode ser boa."""
    julgado = julgar(_item(provenance=None))

    assert julgado.status == MemoryStatus.REVISAR
    assert "auditável" in julgado.judge_reason


def test_licao_de_falha_sem_nenhuma_ancora_fica_em_quarentena():
    """Sem error_code E sem critério reprovado, o modelo teorizou sozinho."""
    julgado = julgar(_item(error_codes=[], unmet_criteria=[]))

    assert julgado.status == MemoryStatus.REVISAR
    assert "não" in julgado.judge_reason and "ancorada" in julgado.judge_reason


def test_criterio_reprovado_ancora_a_licao_mesmo_sem_error_code():
    """A reprovação SEMÂNTICA não gera error_code — mas é verdade de campo.

    Regressão de um run real (13/08): `overall_status: sucesso`, zero estágios
    falhos, veredito `reprovado` com 2 critérios inconclusivos. Exigir
    error_code ali quarentenava lições que citavam os critérios pelo nome.
    """
    julgado = julgar(
        _item(
            error_codes=[],
            unmet_criteria=[
                "Renderizar grid respeitando a ordem persistida",
                "Informar recurso inexistente quando o álbum não for encontrado",
            ],
        )
    )

    assert julgado.status == MemoryStatus.PROMOVIDO
    assert "critérios reprovados=2" in julgado.judge_reason


def test_item_sem_escopo_de_stack_fica_em_quarentena():
    """Item sem escopo seria injetado em qualquer projeto (OEP: confinamento)."""
    julgado = julgar(_item(tech_stack=""))

    assert julgado.status == MemoryStatus.REVISAR
    assert "escopo" in julgado.judge_reason


def test_o_default_nunca_e_promovido():
    """Item recém-construído, antes de julgar, já nasce em quarentena."""
    assert MemoryItem(
        title="t", description="d", content="c", outcome=MemoryOutcome.FALHA
    ).status == MemoryStatus.REVISAR


# --- lote ------------------------------------------------------------------


def test_julgar_lote_atribui_status_a_todos_e_preserva_a_ordem():
    itens = [
        _item(title="Promovido este"),
        _item(title="Quarentena este", error_codes=[]),
        _item(title="Rejeitado este", content="curto"),
    ]

    julgados = julgar_lote(itens)

    assert [j.status for j in julgados] == [
        MemoryStatus.PROMOVIDO,
        MemoryStatus.REVISAR,
        MemoryStatus.REJEITADO,
    ]
    assert all(j.judge_reason for j in julgados)


def test_julgamento_nao_chama_llm(monkeypatch):
    """O julgamento é função pura sobre a evidência — nada de rede.

    Se algum dia alguém introduzir uma chamada de modelo aqui, este teste
    quebra: `litellm.completion` passa a levantar.
    """
    import litellm

    def _proibido(*a, **k):
        raise AssertionError("judge não pode chamar LLM")

    monkeypatch.setattr(litellm, "completion", _proibido)

    assert julgar(_item()).status == MemoryStatus.PROMOVIDO
