"""Tests para o cr_executor do workflow_coding_review.

Após a integração final, o executor NÃO roda mais Docker diretamente nem decide
o encerramento por status de execução. Ele compõe:
  - `tool_rodar_harness` (invoca o harness de validação);
  - o Agente de Validação (AgentTool);
  - `exit_loop` (encerramento, autorizado APENAS pelo veredito).

Cobertura:
- Agent wiring: nome, output_key, as 3 peças compostas;
- ausência das tools/decisões antigas (sem exit-por-status);
- salvaguarda de prompt presente;
- integração com o LoopAgent (coder ANTES do executor) e placeholder do coder.

Os helpers determinísticos do Docker são testados em test_harness_docker.py;
o harness em test_harness_execucao.py; o validador em
test_implementation_validator.py.
"""

import importlib

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def executor_module(tmp_path, monkeypatch):
    """Reimporta cr_executor com workspace temporário."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import src.agents.workflow_coding_review.executor.agent as cr_executor

    importlib.reload(cr_executor)
    return cr_executor


def _tool_names(agent):
    return [getattr(t, "name", None) for t in agent.tools]


# ===========================================================================
# Agent wiring
# ===========================================================================


def test_executor_agent_name(executor_module):
    assert executor_module.agent.name == "cr_executor_agent"


def test_executor_agent_output_key(executor_module):
    assert executor_module.agent.output_key == "execution_result"


def test_executor_agent_tem_3_tools(executor_module):
    """Executor compõe exatamente 3 peças: harness, validador e exit_loop."""
    assert len(executor_module.agent.tools) == 3


def test_executor_compoe_harness_validador_exit_loop(executor_module):
    """As três peças novas estão presentes e nomeadas."""
    names = _tool_names(executor_module.agent)
    assert "executar_harness_tool" in names  # harness (bound ao workspace do workflow)
    assert "implementation_validator" in names  # AgentTool do validador
    assert "exit_loop" in names  # encerramento pelo veredito


# ===========================================================================
# O vício original sumiu — sem exit por status de execução
# ===========================================================================


def test_executor_sem_exit_loop_guarded_antigo(executor_module):
    """A tool guarded antiga (tool_exit_loop_se_sucesso) não existe mais."""
    names = _tool_names(executor_module.agent)
    assert "tool_exit_loop_se_sucesso" not in names
    assert not hasattr(executor_module, "tool_exit_loop_se_sucesso")


def test_executor_sem_tool_docker_direto(executor_module):
    """O executor não roda mais Docker por conta própria."""
    assert not hasattr(executor_module, "tool_executar_em_docker")


def test_executor_sem_last_exec_status(executor_module):
    """Não há mais decisão baseada em _last_exec_status no módulo."""
    import inspect

    fonte = inspect.getsource(executor_module)
    assert "_last_exec_status" not in fonte


# ===========================================================================
# Salvaguarda de prompt
# ===========================================================================


def test_executor_instruction_tem_salvaguarda(executor_module):
    """A instrução impõe a obediência ao veredito e proíbe exit por execução."""
    instr = executor_module.agent.instruction.lower()
    assert "obede" in instr  # DEVE OBEDECER ao veredito
    assert "apenas o veredito" in instr  # só o veredito encerra
    assert "não decide" in instr or "nao decide" in instr


def test_executor_instruction_exit_loop_ligado_ao_veredito(executor_module):
    """A instrução liga o exit_loop ao status 'aprovado' do veredito."""
    instr = executor_module.agent.instruction.lower()
    assert "veredito" in instr
    assert "aprovado" in instr


# ===========================================================================
# Integração: coder instruction contém {execution_result?}
# ===========================================================================


def test_coder_instruction_contem_execution_result_placeholder(tmp_path, monkeypatch):
    """O coder.instruction deve conter {execution_result?} para ADK state injection."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import coder as cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    assert "{execution_result?}" in instr, (
        "Placeholder {execution_result?} ausente na instrução do coder. "
        "O LoopAgent não conseguirá injetar logs de erro do executor."
    )


def test_coder_instruction_contem_modo_operacao(tmp_path, monkeypatch):
    """O coder.instruction deve conter a seção MODO DE OPERAÇÃO."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import coder as cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    assert "MODO DE OPERAÇÃO" in instr
    assert "RESULTADO DA EXECUÇÃO ANTERIOR" in instr


def test_executor_output_key_matches_coder_placeholder(tmp_path, monkeypatch):
    """executor.output_key deve ser 'execution_result' (same key used in coder placeholder)."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import coder as cr_coder
    import src.agents.workflow_coding_review.executor.agent as cr_executor

    importlib.reload(cr_executor)
    importlib.reload(cr_coder)

    output_key = cr_executor.agent.output_key
    assert output_key == "execution_result"
    # Confirm the placeholder in coder matches
    assert f"{{{output_key}?}}" in cr_coder.agent.instruction


# ===========================================================================
# LoopAgent structure — topologia [coder → executor] intocada
# ===========================================================================


def test_max_iterations_e_rede_de_seguranca_alta():
    """O teto deixou de ser o controle esperado (issue #394).

    Ele agora protege contra um defeito na própria política de progresso, então
    precisa ser alto o bastante para não cortar tarefas legítimas antes dela —
    e nunca zero/negativo, o que desligaria a rede.
    """
    from src.agents.workflow_coding_review.agent import _code_execute_loop

    assert _code_execute_loop.max_iterations >= 10


def test_teto_invalido_no_ambiente_cai_para_o_padrao(monkeypatch):
    """Um valor quebrado na env var não pode desligar a rede de segurança."""
    from src.agents.workflow_coding_review.executor.loop_policy import config_inteiro

    for invalido in ("", "abc", "0", "-3"):
        monkeypatch.setenv("AI4ES_MAX_LOOP_ITERATIONS", invalido)
        assert config_inteiro("AI4ES_MAX_LOOP_ITERATIONS", 20, minimo=1) == 20


# ===========================================================================
# Política de progresso (issue #394) — decisão de parada fora do LLM
# ===========================================================================


class _Acoes:
    """Espelha `CallbackContext.actions` no que importa para a política."""

    def __init__(self):
        self.escalate = None


class _Contexto:
    def __init__(self, state=None):
        self.state = state if state is not None else {}
        self.actions = _Acoes()


def _veredito(status: str, *criterios: str) -> dict:
    return {
        "work_item_id": "TASK-001",
        "status": status,
        "criteria_verdicts": [
            {"criterion": f"CA-{i}", "status": s, "reasoning": ""}
            for i, s in enumerate(criterios)
        ],
    }


def test_prompt_nao_pede_mais_deteccao_de_estagnacao(executor_module):
    """O critério de aceite pede a remoção explícita desse trecho do prompt.

    Enquanto ele existisse, o LLM continuaria tentando julgar travamento por
    conta própria — em paralelo e possivelmente em conflito com a política.
    """
    instrucao = executor_module.agent.instruction

    assert "PROTOCOLO ANTI-ESTAGNAÇÃO" not in instrucao
    assert "STATUS: bloqueado" not in instrucao


def test_marcador_de_estagnacao_removido_do_modulo(executor_module):
    import inspect

    assert "_MARCADOR_ESTAGNACAO" not in inspect.getsource(executor_module)


def test_ordem_dos_after_callbacks_e_carga_estrutural(executor_module):
    """A política precisa vir ANTES de `montar_error_report`.

    O ADK para no primeiro callback que devolve Content, e o error report
    devolve Content em toda rodada reprovada — o caso comum. Invertida, a
    política nunca rodaria nas rodadas que ela existe para julgar.
    """
    callbacks = executor_module.agent.after_agent_callback

    assert isinstance(callbacks, list)
    assert callbacks[0] is executor_module.aplicar_politica_de_progresso
    assert callbacks[1] is executor_module.montar_error_report


def test_rodada_aprovada_entra_no_historico(executor_module, monkeypatch):
    """Sem isso, a nota final da task seria a da penúltima rodada (reprovada)."""
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    ctx = _Contexto({"validation": _veredito("aprovado", "atendido")})

    devolvido = executor_module.aplicar_politica_de_progresso(ctx)

    assert ctx.state["progress_score_history"], (
        "rodada aprovada ficou fora do histórico"
    )
    assert ctx.state["progress_score_details"][-1] is not None
    assert devolvido is None, "o texto de confirmação do executor foi sobrescrito"


def test_aprovacao_encerra_o_loop_deterministicamente(executor_module, monkeypatch):
    """Não depende do LLM lembrar de chamar `exit_loop`."""
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    ctx = _Contexto({"validation": _veredito("aprovado", "atendido")})

    executor_module.aplicar_politica_de_progresso(ctx)

    assert ctx.actions.escalate is True


def test_aprovacao_nao_marca_motivo_de_parada(executor_module, monkeypatch):
    """Task concluída com sucesso não pode terminar rotulada como travada."""
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    ctx = _Contexto({"validation": _veredito("aprovado", "atendido")})

    executor_module.aplicar_politica_de_progresso(ctx)

    assert "loop_stop_reason" not in ctx.state


def test_rodada_reprovada_com_progresso_nao_encerra(executor_module, monkeypatch):
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    ctx = _Contexto({"validation": _veredito("reprovado", "nao_atendido")})

    devolvido = executor_module.aplicar_politica_de_progresso(ctx)

    assert ctx.actions.escalate is None
    assert devolvido is None, "deixar de devolver None impediria o ErrorReport"


def test_nota_seis_com_testes_falhos_nao_encerra(executor_module, monkeypatch):
    """Nota mede progresso; 0.6 não é limiar de aprovação.

    Reproduz a run em que ambiente, build e aplicação passaram, mas a suíte
    ficou vermelha. Com o veredito reprovado, o coder precisa receber outra
    rodada para corrigir os testes em vez de a task ser aprovada imediatamente.
    """
    from src.agents.workflow_coding_review.executor.progress_score import NotaProgresso

    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    monkeypatch.setattr(
        executor_module,
        "calcular_nota",
        lambda _: NotaProgresso(
            total=0.6,
            por_degrau={},
            degraus_aplicaveis=frozenset(),
            pesos_efetivos={},
        ),
    )
    ctx = _Contexto({"validation": _veredito("reprovado", "inconclusivo")})

    devolvido = executor_module.aplicar_politica_de_progresso(ctx)

    assert ctx.state["progress_score_history"] == [0.6]
    assert ctx.actions.escalate is None
    assert devolvido is None


def test_erro_repetido_encerra_e_substitui_o_turno(executor_module, monkeypatch):
    """Mesma falha e nota parada: encerra pelo acelerador, antes da janela cheia.

    Exige que a ausência de progresso tenha PERSISTIDO — uma única rodada sem
    melhora não basta, senão um vale isolado derrubaria a task.

    No encerramento o turno é substituído: o coder não pode receber um relatório
    "conserte isto" referente a uma rodada que não vai existir.
    """
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    ctx = _Contexto({"validation": _veredito("reprovado", "nao_atendido")})

    primeira = executor_module.aplicar_politica_de_progresso(ctx)
    segunda = executor_module.aplicar_politica_de_progresso(ctx)
    terceira = executor_module.aplicar_politica_de_progresso(ctx)

    assert primeira is None, "a 1ª rodada não tem com o que comparar"
    assert segunda is None, "um único tropeço não pode encerrar a task"
    assert ctx.actions.escalate is True
    assert ctx.state["loop_stop_reason"] == "erro_repetido"
    assert "NÃO é aprovação" in terceira.parts[0].text


def test_falha_sempre_inedita_atravessa_o_plato_ate_o_orcamento(
    executor_module, monkeypatch
):
    """Inversão deliberada: falha nova a cada rodada NÃO é platô.

    A nota é cega dentro de um degrau — `build_concluido` é binário, então o
    coder pode derrubar um erro de import, depois uma dependência faltando,
    depois um erro de sintaxe, com a nota parada o tempo todo. A política
    anterior lia isso como platô e encerrava na 4ª rodada, matando tasks que
    terminariam. Agora a novidade renova a tolerância, e o freio é o orçamento
    de falhas distintas.
    """
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    contador = iter(range(100))
    monkeypatch.setattr(
        executor_module, "assinatura_erro", lambda *_: f"falha-{next(contador)}"
    )
    ctx = _Contexto({"validation": _veredito("reprovado", "nao_atendido")})

    from src.agents.workflow_coding_review.executor.loop_policy import (
        ORCAMENTO_FALHAS_DISTINTAS as orcamento,
    )
    decisoes = [
        executor_module.aplicar_politica_de_progresso(ctx)
        for _ in range(orcamento + 1)
    ]

    # Onde a política antiga já teria encerrado (4ª rodada), o loop segue.
    assert decisoes[3] is None, "encerrou por platô apesar de a falha ser inédita"
    # E o encerramento vem do orçamento, não do platô.
    assert all(d is None for d in decisoes[:orcamento])
    assert decisoes[orcamento] is not None
    assert ctx.state["loop_stop_reason"] == "orcamento_de_falhas_distintas"


def test_mesma_falha_repetida_ainda_encerra_cedo(executor_module, monkeypatch):
    """Contrapartida: a tolerância é para erro NOVO, não para repisar o mesmo."""
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    monkeypatch.setattr(executor_module, "assinatura_erro", lambda *_: "sempre-a-mesma")
    ctx = _Contexto({"validation": _veredito("reprovado", "nao_atendido")})

    decisoes = [executor_module.aplicar_politica_de_progresso(ctx) for _ in range(3)]

    assert decisoes[2] is not None
    assert ctx.state["loop_stop_reason"] == "erro_repetido"


def test_veredito_ausente_nao_registra_rodada(executor_module):
    ctx = _Contexto({})

    assert executor_module.aplicar_politica_de_progresso(ctx) is None
    assert "progress_score_history" not in ctx.state


# ---------------------------------------------------------------------------
# Gate estrutural — rodadas recusadas também passam pela política
# ---------------------------------------------------------------------------


def test_recusa_registra_nota_zero(executor_module, monkeypatch):
    """O gate corta o turno antes de qualquer after_agent_callback; se ele não
    registrasse, essas rodadas ficariam invisíveis a todos os gatilhos."""
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: False)
    ctx = _Contexto({"task_id": "TASK-001"})

    executor_module.recusar_execucao_incompleta(ctx)

    assert ctx.state["progress_score_history"] == [0.0]
    assert ctx.state["progress_score_details"] == [None]


def test_recusas_seguidas_encerram_o_loop(executor_module, monkeypatch):
    """Regressão: registrar o zero sem AVALIAR deixaria o coder travado no gate
    rodando até o teto de segurança."""
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: False)
    ctx = _Contexto({"task_id": "TASK-001"})

    for _ in range(4):
        executor_module.recusar_execucao_incompleta(ctx)

    assert ctx.actions.escalate is True
    assert ctx.state["loop_stop_reason"] is not None


def test_primeira_recusa_nao_encerra(executor_module, monkeypatch):
    """Uma recusa isolada é normal — o coder ainda vai implementar."""
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: False)
    ctx = _Contexto({"task_id": "TASK-001"})

    executor_module.recusar_execucao_incompleta(ctx)

    assert ctx.actions.escalate is None


def test_recusa_preserva_a_mensagem_ao_coder(executor_module, monkeypatch):
    """O relatório de recusa continua sendo o que o coder recebe."""
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: False)
    ctx = _Contexto({"task_id": "TASK-001"})

    devolvido = executor_module.recusar_execucao_incompleta(ctx)

    assert devolvido is not None
    assert executor_module._CABECALHO_RECUSA in ctx.state["execution_result"]


def test_loop_agent_sub_agents_order():
    """LoopAgent deve ter coder ANTES de executor (validador é AgentTool interna)."""
    from src.agents.workflow_coding_review.agent import _code_execute_loop

    names = [sa.name for sa in _code_execute_loop.sub_agents]
    assert names[0] == "cr_coder_agent"
    assert names[1] == "cr_executor_agent"
    assert len(names) == 2  # o validador NÃO é sub-agente do loop


def test_coder_instruction_exige_readme(tmp_path, monkeypatch):
    """O coder.instruction deve exigir criação de README.md com URL de acesso."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import coder as cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    assert "README.md" in instr
    assert "http://localhost:8000" in instr


def test_coder_instruction_exige_run_json(tmp_path, monkeypatch):
    """O coder.instruction deve exigir o manifesto run.json dirigido pela surface."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import coder as cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    # run.json é o novo artefato de execução obrigatório (substitui Docker).
    assert "run.json" in instr
    # A superfície (service/command/none) deriva o comportamento do harness.
    assert "surface" in instr
    for surface in ("service", "command", "none"):
        assert surface in instr, f"superfície ausente no prompt: {surface}"
