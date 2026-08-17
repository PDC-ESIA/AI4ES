"""Testes da lógica pura do PoC de memória (mem0) em memory_feedforward.py.

Cobre só as funções determinísticas, sem I/O nem rede — `stack_key` e
`_formatar_memory_context`. O agente (`_MemoryProvisioner`) em si depende do
mem0/Postgres de verdade e é validado via `scripts/mem0_poc_smoke_test.py` e
teste manual, não aqui.
"""

from src.agents.workflow_coding_review.memory_feedforward import (
    _formatar_memory_context,
    stack_key,
)


class TestStackKey:
    def test_lista_vazia(self):
        assert stack_key([]) == "stack-desconhecida"

    def test_lista_so_com_nao_strings(self):
        assert stack_key([123, None, {}]) == "stack-desconhecida"

    def test_pega_primeiro_termo_em_minusculo(self):
        assert stack_key(["Python", "FastAPI"]) == "python"

    def test_ordem_diferente_gera_chave_diferente(self):
        """Documenta a fragilidade conhecida — não é o comportamento ideal,
        é o comportamento real do PoC (ver docstring de `stack_key`)."""
        assert stack_key(["FastAPI", "Python"]) == "fastapi"

    def test_normaliza_espacos_e_caixa(self):
        assert stack_key(["  FastAPI  "]) == "fastapi"

    def test_ignora_itens_nao_string_antes_do_primeiro_valido(self):
        assert stack_key([123, "Python", "FastAPI"]) == "python"

    def test_string_vazia_e_so_espacos_sao_ignoradas(self):
        assert stack_key(["", "   ", "Python"]) == "python"


class TestFormatarMemoryContext:
    def test_lista_vazia(self):
        assert _formatar_memory_context([]) == ""

    def test_resultados_sem_campo_memory_sao_ignorados(self):
        assert _formatar_memory_context([{"id": "1"}, {"memory": ""}]) == ""

    def test_uma_licao(self):
        assert _formatar_memory_context([{"memory": "lição A"}]) == "- lição A"

    def test_varias_licoes_uma_por_linha(self):
        resultado = _formatar_memory_context(
            [{"memory": "lição A"}, {"memory": "lição B"}]
        )
        assert resultado == "- lição A\n- lição B"

    def test_ignora_so_os_vazios_mantendo_ordem_dos_validos(self):
        resultado = _formatar_memory_context(
            [{"memory": "lição A"}, {"memory": ""}, {"memory": "lição B"}]
        )
        assert resultado == "- lição A\n- lição B"
