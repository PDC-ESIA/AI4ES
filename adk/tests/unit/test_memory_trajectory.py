"""Testes da montagem da trajetória entregue ao destilador.

O invariante que estes testes protegem é o do R1: **uma run aprovada não pode
chegar ao destilador como um recibo**. Antes de 14/08 a montagem só trazia
objetivo, veredito e os estágios em falha — e numa run que passou esse último
bloco é vazio por definição, então o modelo recebia cinco linhas e devolvia
platitude ("trabalhar em ciclos curtos até convergir", banco de 13/08).

O que fecha esse buraco são dois blocos, cobertos aqui:

- **a entrega** (`montar_manifesto`) — os arquivos produzidos e o `run.json`;
- **o caminho** (`resumir_tentativas` sobre `carregar_historico`) — o que quebrou
  em cada passagem do loop antes da que passou.

O segundo depende do arquivamento por iteração feito no harness: o report
canônico não carrega a iteração no nome e é sobrescrito a cada passagem.
"""

import json

import pytest

from shared.memory.trajectory import (
    carregar_historico,
    montar_manifesto,
    montar_trajetoria,
    resumir_tentativas,
)


def _report(iteration, status="falha", generated_at=None, error_code="FALHA_BUILD"):
    return {
        "iteration": iteration,
        "generated_at": generated_at or f"2026-08-14T10:0{iteration}:00Z",
        "overall_status": status,
        "stages": [
            {"stage": "preparacao_ambiente", "status": "sucesso", "error_code": None},
            {
                "stage": "implantacao_artefato",
                "status": "falha",
                "error_code": error_code,
                "summary": f"Build da iteração {iteration} falhou.",
                "evidence": {"build_logs_tail": "pip: not found"},
            },
        ]
        if status == "falha"
        else [
            {"stage": "preparacao_ambiente", "status": "sucesso", "error_code": None}
        ],
    }


@pytest.fixture
def execucao(tmp_path):
    """Simula `coder/execution/` com o report canônico e a pasta `historico/`."""
    canonico = tmp_path / "TASK-001.report.json"
    canonico.write_text(json.dumps(_report(3, status="sucesso")), encoding="utf-8")
    (tmp_path / "historico").mkdir()
    return tmp_path


def _arquivar(execucao, report, seq, task_id="TASK-001"):
    alvo = (
        execucao
        / "historico"
        / f"{task_id}.{seq:02d}_iter{report['iteration']}.report.json"
    )
    alvo.write_text(json.dumps(report), encoding="utf-8")


# --- carregar_historico ----------------------------------------------------


def test_historico_vem_em_ordem_de_arquivamento(execucao):
    _arquivar(execucao, _report(1), seq=1)
    _arquivar(execucao, _report(2), seq=2)

    historico = carregar_historico(str(execucao / "TASK-001.report.json"))

    assert [r["iteration"] for r in historico] == [1, 2]


def test_ordem_nao_depende_da_iteracao_relatada(execucao):
    """A iteração é auto-relatada pelo LLM executor; a ordem vem da sequência.

    Duas passagens relatando a mesma iteração não podem colapsar nem embaralhar
    o histórico — é o modo de falha que faria a memória perder o delta em
    silêncio.
    """
    _arquivar(execucao, _report(1, error_code="PRIMEIRA"), seq=1)
    _arquivar(execucao, _report(1, error_code="SEGUNDA"), seq=2)

    historico = carregar_historico(str(execucao / "TASK-001.report.json"))

    assert len(historico) == 2
    assert [r["stages"][1]["error_code"] for r in historico] == ["PRIMEIRA", "SEGUNDA"]


def test_historico_de_outra_task_nao_vaza(execucao):
    _arquivar(execucao, _report(1), seq=1)
    _arquivar(execucao, _report(1), seq=1, task_id="TASK-002")

    historico = carregar_historico(str(execucao / "TASK-001.report.json"))

    assert len(historico) == 1


def test_sem_pasta_de_historico_devolve_vazio(tmp_path):
    canonico = tmp_path / "TASK-001.report.json"
    canonico.write_text("{}", encoding="utf-8")

    assert carregar_historico(str(canonico)) == []


def test_sem_report_path_devolve_vazio():
    assert carregar_historico(None) == []
    assert carregar_historico("") == []


def test_arquivo_ilegivel_nao_invalida_os_outros(execucao):
    _arquivar(execucao, _report(1), seq=1)
    (execucao / "historico" / "TASK-001.02_iter2.report.json").write_text(
        "{ isto não é json", encoding="utf-8"
    )

    historico = carregar_historico(str(execucao / "TASK-001.report.json"))

    assert [r["iteration"] for r in historico] == [1]


# --- resumir_tentativas ----------------------------------------------------


def test_tentativa_corrente_fica_de_fora(execucao):
    """Ela já aparece adiante, com evidência bruta — repetir só gasta contexto."""
    atual = _report(2, status="sucesso", generated_at="2026-08-14T11:00:00Z")

    resumo = resumir_tentativas([_report(1), atual], atual)

    assert "iteração 1" in resumo
    assert "iteração 2" not in resumo


def test_corrente_nao_arquivada_nao_descarta_tentativa_boa(execucao):
    """A exclusão é por `generated_at`, não por posição.

    Se o arquivamento da tentativa corrente tiver falhado, a última entrada do
    histórico é uma tentativa ANTERIOR de verdade e não pode sumir do resumo.
    """
    atual = _report(2, status="sucesso", generated_at="2026-08-14T11:00:00Z")

    resumo = resumir_tentativas([_report(1)], atual)

    assert "iteração 1" in resumo


def test_resumo_nomeia_o_estagio_e_o_codigo(execucao):
    resumo = resumir_tentativas([_report(1)], _report(9))

    assert "implantacao_artefato" in resumo
    assert "FALHA_BUILD" in resumo
    assert "Build da iteração 1 falhou." in resumo


def test_resumo_nao_traz_evidencia_bruta(execucao):
    """Só o `summary`: a evidência das tentativas somadas estouraria o contexto."""
    resumo = resumir_tentativas([_report(1)], _report(9))

    assert "pip: not found" not in resumo


def test_historico_vazio_nao_gera_bloco():
    assert resumir_tentativas([], _report(1)) == ""


# --- montar_manifesto ------------------------------------------------------


def test_manifesto_lista_arquivos_e_o_run_json(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("x = 1", encoding="utf-8")
    (tmp_path / "run.json").write_text('{"surface": "service"}', encoding="utf-8")

    manifesto = montar_manifesto(tmp_path)

    assert "- app/main.py" in manifesto
    assert "- run.json" in manifesto
    assert '"surface": "service"' in manifesto


def test_manifesto_ignora_pycache(tmp_path):
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "m.pyc").write_text("bin", encoding="utf-8")
    (tmp_path / "main.py").write_text("x = 1", encoding="utf-8")

    assert "pyc" not in montar_manifesto(tmp_path)


def test_manifesto_de_diretorio_inexistente_ou_vazio(tmp_path):
    assert montar_manifesto(tmp_path / "nao-existe") == ""
    assert montar_manifesto(tmp_path) == ""


def test_manifesto_tem_teto_de_arquivos(tmp_path):
    for n in range(70):
        (tmp_path / f"f{n:03d}.py").write_text("x", encoding="utf-8")

    manifesto = montar_manifesto(tmp_path)

    assert "e mais 10 arquivo(s)" in manifesto


# --- montar_trajetoria -----------------------------------------------------


def test_trajetoria_de_sucesso_deixa_de_ser_um_recibo(tmp_path):
    """O caso que motivou tudo: run aprovada, nenhum estágio em falha."""
    (tmp_path / "main.py").write_text("x = 1", encoding="utf-8")
    aprovado = _report(3, status="sucesso")

    trajetoria = montar_trajetoria(
        aprovado,
        {"status": "aprovado", "criteria_verdicts": []},
        tech_stack="python-fastapi",
        objetivo="App de ensaios",
        historico=[_report(1), _report(2)],
        manifesto=montar_manifesto(tmp_path),
    )

    assert "Nenhum — todos os estágios passaram" in trajetoria  # segue verdade
    assert "O que esta run entregou" in trajetoria
    assert "- main.py" in trajetoria
    assert "Tentativas anteriores nesta run" in trajetoria
    assert "iteração 1" in trajetoria and "iteração 2" in trajetoria


def test_sem_historico_nem_manifesto_a_montagem_degrada(tmp_path):
    """Ausentes, os blocos somem — a trajetória não quebra."""
    trajetoria = montar_trajetoria(_report(1), None, objetivo="App")

    assert "O que esta run entregou" not in trajetoria
    assert "Tentativas anteriores nesta run" not in trajetoria
    assert "FALHA_BUILD" in trajetoria  # o que já existia continua lá
