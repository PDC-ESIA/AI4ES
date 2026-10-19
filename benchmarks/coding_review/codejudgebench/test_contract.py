"""Testes unitários do contract.py do CodeJudgeBench (sem LLM)."""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest

from benchmarks.coding_review.codejudgebench import contract
from benchmarks.coding_review.codejudgebench.dataset import RepairPair

F = "`" * 3


def _par(**extra) -> RepairPair:
    base = dict(
        pair_id="claude_3.7_sonnet/7",
        split="claude_3.7_sonnet",
        row_idx=7,
        question_id="abc123_a",
        question_title="A",
        question_content="Leia N e imprima N+1.",
        platform="atcoder",
        difficulty="hard",
        starter_code="",
        wrong_code="print(int(input()))",
        pos_response="ok",
        neg_response="ko",
        wrong_meta={"error_message": "Wrong answer: 1 != 2", "inputs": "1", "expected": "2", "output": "1"},
    )
    base.update(extra)
    return RepairPair(**base)


# ---------------------------------------------------------------------------
# extract_code / explanation_without_code
# ---------------------------------------------------------------------------


def test_extrai_bloco_python():
    resposta = f"O erro era X.\n\n{F}python\nprint(1)\n{F}\n"
    assert contract.extract_code(resposta) == "print(1)\n"


def test_multiplos_blocos_usa_o_ultimo_python():
    resposta = f"{F}python\nrascunho()\n{F}\ntexto\n{F}text\nsaida\n{F}\n{F}python\nfinal()\n{F}"
    assert contract.extract_code(resposta) == "final()\n"


def test_sem_bloco_python_usa_ultimo_bloco():
    assert contract.extract_code(f"{F}\nx = 1\n{F}") == "x = 1\n"


def test_sem_bloco_devolve_none():
    assert contract.extract_code("só explicação") is None


def test_explicacao_troca_codigo_por_marcador():
    resposta = f"Antes.\n{F}python\nprint(1)\n{F}\nDepois."
    texto = contract.explanation_without_code(resposta)
    assert "print(1)" not in texto
    assert contract.CODE_PLACEHOLDER in texto
    assert texto.startswith("Antes.") and texto.endswith("Depois.")


# ---------------------------------------------------------------------------
# Ambiente de execução (cabeçalho do LiveCodeBench)
# ---------------------------------------------------------------------------

_LEETCODE = "class Solution:\n    def f(self, nums: List[int]) -> int:\n        return len(Counter(nums))\n"


def test_solution_file_tem_ambiente_e_resposta_em_ordem():
    conteudo = contract.build_solution_file(_LEETCODE)
    assert conteudo.startswith("# ruff: noqa: F401, F403, F405\n")
    assert "from typing import *" in conteudo and "from collections import *" in conteudo
    assert conteudo.index(contract.HEADER_END) < conteudo.index("class Solution")
    assert conteudo.endswith(_LEETCODE)


def test_solution_file_executa_leetcode_sem_import_explicito():
    escopo: dict = {}
    exec(contract.build_solution_file(_LEETCODE), escopo)  # noqa: S102 — código fixo do teste
    assert escopo["Solution"]().f([1, 1, 2]) == 2


def test_ruff_nao_acusa_nome_vindo_do_ambiente(tmp_path):
    import shutil
    import subprocess

    ruff = shutil.which("ruff") or str(Path(sys.executable).parent / "ruff")
    if not Path(ruff).exists() and not shutil.which("ruff"):
        pytest.skip("ruff não instalado")
    arquivo = tmp_path / "solution.py"
    arquivo.write_text(contract.build_solution_file(_LEETCODE), encoding="utf-8")
    saida = subprocess.run([ruff, "check", "--output-format", "json", str(arquivo)], capture_output=True, text=True)
    assert json.loads(saida.stdout or "[]") == []


def test_contrato_explica_o_ambiente():
    descricao = contract.build_task_contract(_par())["description"]
    assert "AMBIENTE DE EXECUÇÃO DA PLATAFORMA" in descricao
    assert "não faz parte da correção" in descricao


# ---------------------------------------------------------------------------
# Contrato e mensagem
# ---------------------------------------------------------------------------


def test_contrato_no_formato_do_context_engineer():
    task = contract.build_task_contract(_par())
    assert task["id"] == contract.TASK_ID
    assert task["complexity"] == "high"
    assert task["contract"]["outputs"] == [contract.SOLUTION_FILENAME]
    assert {c["id"] for c in task["acceptance_criteria"]} == {"CA-01", "CA-02"}
    assert "Leia N e imprima N+1." in task["description"]
    assert "Wrong answer: 1 != 2" in task["description"]
    assert "print(int(input()))" in task["description"]


def test_starter_code_vira_interface_e_library():
    par = _par(starter_code="class Solution:\n    def f(self): ...", platform="leetcode")
    envelope = contract.build_tasks_envelope(par)
    assert envelope["macro_context"]["product_type"] == "library"
    assert envelope["tasks"][0]["contract"]["interfaces"] == ["class Solution:\n    def f(self): ..."]


def test_trecho_de_falha_longo_e_truncado():
    par = _par(wrong_meta={"error_message": "TLE", "inputs": "9" * 5000})
    descricao = contract.build_task_contract(par)["description"]
    assert "caracteres omitidos" in descricao
    assert len(descricao) < 3000


def test_mensagem_nao_contem_o_codigo_da_resposta():
    resposta = f"Troquei o laço.\n{F}python\nSEGREDO_DO_CODIGO = 1\n{F}"
    msg = contract.build_reviewer_message(_par(), resposta)
    assert "SEGREDO_DO_CODIGO" not in msg
    assert "Troquei o laço." in msg
    envelope = msg.split(f"{F}json\n")[1].split(f"\n{F}")[0]
    assert json.loads(envelope)["tasks"][0]["id"] == contract.TASK_ID


def test_mensagem_sem_relato():
    msg = contract.build_reviewer_message(_par(), "Troquei o laço.", include_explanation=False)
    assert "Relato do coder" not in msg


def test_mensagem_identica_para_pos_e_neg_fora_do_relato():
    par = _par()
    a = contract.build_reviewer_message(par, "relato A").split("## Relato do coder")[0]
    b = contract.build_reviewer_message(par, "relato B").split("## Relato do coder")[0]
    assert a == b


# ---------------------------------------------------------------------------
# Summary sintético contra o gate REAL de cobertura
# ---------------------------------------------------------------------------


@pytest.fixture
def review_tools(tmp_path, monkeypatch):
    """Importa o review_tools real com o workspace apontado para tmp_path."""
    adk = Path(__file__).resolve().parents[3] / "adk"
    monkeypatch.syspath_prepend(str(adk))
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))
    modulo = "shared.tools.coding_tools.review_tools"
    sys.modules.pop(modulo, None)
    try:
        return importlib.import_module(modulo)
    finally:
        sys.modules.pop(modulo, None)
        os.environ.pop("WORKSPACE_OUTPUT_DIR", None)


def test_summary_sintetico_passa_no_gate_de_cobertura(review_tools):
    state = {"task_iteration_summary": contract.synthetic_iteration_summary()}
    assert review_tools.cobertura_comprovada(state) is True


def test_sem_summary_o_gate_bloquearia(review_tools):
    assert review_tools.cobertura_comprovada({}) is False


# ---------------------------------------------------------------------------
# parse_review_markdown
# ---------------------------------------------------------------------------

_MARKDOWN = """## Status: BLOQUEADO

## Issues
### Critical
- `solution.py`: laço não trata N=0 (corretude)
### Warning
- Falta arquivo de testes (testes)
- Nenhum

## Resumo
A correção ainda falha no caso de borda.
"""


def test_parse_status_e_issues():
    lido = contract.parse_review_markdown(_MARKDOWN)
    assert lido.lenient_status == "BLOQUEADO"
    assert [(i["severity"], i["layer"]) for i in lido.issues] == [
        ("critical", "corretude"),
        ("warning", "testes"),
    ]
    assert lido.issues[0]["file"] == "solution.py"
    assert lido.gate_applied is False


def test_parse_status_com_formato_fora_do_padrao():
    lido = contract.parse_review_markdown("**Status:** Aprovado\n\nTudo certo.")
    assert lido.lenient_status == "APROVADO"


def test_parse_status_ambiguo():
    lido = contract.parse_review_markdown("## Status: APROVADO\n...\nStatus: BLOQUEADO na v1")
    assert lido.lenient_status == "AMBIGUO"


def test_parse_sem_status():
    lido = contract.parse_review_markdown("Revisão sem conclusão.")
    assert lido.lenient_status is None and lido.issues == []


def test_parse_severidade_inline():
    lido = contract.parse_review_markdown("## Issues\n- [CRITICAL] erro de lógica em solution.py (corretude)")
    assert lido.issues[0]["severity"] == "critical"


@pytest.mark.parametrize(
    ("markdown", "esperado"),
    [
        # Severidade no item, camada na linha de continuação (formato mais comum do gpt-5-mini).
        (
            "## Issues\n\n- Severity: critical  \n  File: solution.py — Camada: corretude  \n"
            "  Descrição: off-by-one no laço.\n\n## Resumo\nx",
            [("critical", "corretude", "solution.py")],
        ),
        # Sub-itens são continuação, não issues novas.
        (
            "## Issues\n- CRITICAL — solution.py / corretude\n  - Descrição: falha com N=0 (testes não cobrem)\n"
            "- WARNING — solution.py / completude\n  - Descrição: falta README\n## Resumo\nx",
            [("critical", "corretude", "solution.py"), ("warning", "completude", "solution.py")],
        ),
        # Rótulo explícito vence a primeira camada citada.
        (
            "## Issues\n- [CRITICAL] solution.py / camada=arquitetura\n  Descrição: lógica de corretude acoplada\n",
            [("critical", "arquitetura", "solution.py")],
        ),
        # Camada composta: vale a primeira depois do rótulo.
        (
            "## Issues\n- Severidade: critical\n  Arquivo: solution.py — Camada: arquitetura / corretude\n",
            [("critical", "arquitetura", "solution.py")],
        ),
        # Bloco de código dentro do item não abre issue nova.
        (
            "## Issues\n- critical — corretude — solution.py\n  ```python\n  - x = 1\n  ```\n",
            [("critical", "corretude", "solution.py")],
        ),
    ],
)
def test_parse_formatos_reais_do_reviewer(markdown, esperado):
    lido = contract.parse_review_markdown(markdown)
    assert [(i["severity"], i["layer"], i["file"]) for i in lido.issues] == esperado


def test_nenhum_problema_nao_vira_issue_mas_nenhum_teste_vira():
    sem = contract.parse_review_markdown("## Issues\n- Nenhum problema identificado.\n")
    com = contract.parse_review_markdown("## Issues\n- Nenhum teste foi fornecido (testes)\n")
    assert sem.issues == []
    assert [(i["layer"]) for i in com.issues] == ["testes"]


def test_detecta_gate_aplicado():
    texto = f"## Status: BLOQUEADO\n\n{contract.GATE_MARKER}\nnota\n<!-- task-coverage-gate:end -->"
    assert contract.parse_review_markdown(texto).gate_applied is True
