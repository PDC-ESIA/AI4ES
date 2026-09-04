"""Testes da lógica pura do PoC de memória (mem0) em memory_feedforward.py.

Cobre as funções determinísticas, sem I/O nem rede — `stack_key` e
`_formatar_memory_context` — e o interruptor geral (`AI4ES_MEMORY_ENABLED`)
do `_MemoryProvisioner`, que também não exige mem0/Postgres de verdade (o
gate impede a chamada de existir). O resto do agente (busca de verdade no
mem0) é validado via `scripts/mem0_poc_smoke_test.py` e teste manual, não aqui.
"""

from src.agents.workflow_coding_review.memory_feedforward import (
    _formatar_memory_context,
    agent as memory_feedforward_agent,
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


class _FakeSession:
    def __init__(self, state):
        self.state = state


class _FakeInvocationContext:
    def __init__(self, state):
        self.session = _FakeSession(state)
        self.invocation_id = "test-invocation"


class TestMemoryProvisionerDesabilitado:
    """Interruptor geral (`AI4ES_MEMORY_ENABLED`) — não chama o mem0 quando desligado."""

    async def test_desabilitado_nao_chama_get_memory(self, monkeypatch):
        monkeypatch.delenv("AI4ES_MEMORY_ENABLED", raising=False)

        import src.agents.workflow_coding_review.memory_feedforward as mf

        def _explode():
            raise AssertionError(
                "get_memory() não deveria ser chamado (flag desligada)"
            )

        monkeypatch.setattr(mf, "get_memory", _explode)

        ctx = _FakeInvocationContext(
            {"tasks": {"macro_context": {"tech_stack": ["Python"]}}}
        )
        eventos = [e async for e in memory_feedforward_agent._run_async_impl(ctx)]

        assert len(eventos) == 1
        state_delta = eventos[0].actions.state_delta
        assert state_delta["memory_context"] == ""
        assert state_delta["memory_stack_key"] == "python"


class TestMemoryProvisionerMacroContextInvalido:
    """Regressão: macro_context num formato inesperado (não dict) não pode
    quebrar o agente — essa extração roda ANTES até da checagem do
    interruptor geral, então nem o gate `memoria_habilitada()` protegeria."""

    async def test_macro_context_nao_dict_nao_derruba(self, monkeypatch):
        monkeypatch.delenv("AI4ES_MEMORY_ENABLED", raising=False)

        ctx = _FakeInvocationContext({"tasks": {"macro_context": "formato-inesperado"}})
        eventos = [e async for e in memory_feedforward_agent._run_async_impl(ctx)]

        assert len(eventos) == 1
        assert (
            eventos[0].actions.state_delta["memory_stack_key"] == "stack-desconhecida"
        )
