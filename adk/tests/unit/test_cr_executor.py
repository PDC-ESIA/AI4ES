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
from google.adk.sessions.state import State

from shared.tools.coding_tools.harness_schemas import (
    CriterionEvidence,
    CriterionOutcome,
)
from src.agents.workflow_coding_review.executor.qa_criterios import ResultadoQA


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


async def test_rodada_aprovada_entra_no_historico(executor_module, monkeypatch):
    """Sem isso, a nota final da task seria a da penúltima rodada (reprovada)."""
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    ctx = _Contexto({"validation": _veredito("aprovado", "atendido")})

    devolvido = await executor_module.aplicar_politica_de_progresso(ctx)

    assert ctx.state["progress_score_history"], (
        "rodada aprovada ficou fora do histórico"
    )
    assert ctx.state["progress_score_details"][-1] is not None
    assert devolvido is None, "o texto de confirmação do executor foi sobrescrito"


async def test_aprovacao_encerra_o_loop_deterministicamente(
    executor_module, monkeypatch
):
    """Não depende do LLM lembrar de chamar `exit_loop`."""
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    ctx = _Contexto({"validation": _veredito("aprovado", "atendido")})

    await executor_module.aplicar_politica_de_progresso(ctx)

    assert ctx.actions.escalate is True


async def test_aprovacao_nao_marca_motivo_de_parada(executor_module, monkeypatch):
    """Task concluída com sucesso não pode terminar rotulada como travada."""
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    ctx = _Contexto({"validation": _veredito("aprovado", "atendido")})

    await executor_module.aplicar_politica_de_progresso(ctx)

    assert "loop_stop_reason" not in ctx.state


async def test_rodada_reprovada_com_progresso_nao_encerra(executor_module, monkeypatch):
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    ctx = _Contexto({"validation": _veredito("reprovado", "nao_atendido")})

    devolvido = await executor_module.aplicar_politica_de_progresso(ctx)

    assert ctx.actions.escalate is None
    assert devolvido is None, "deixar de devolver None impediria o ErrorReport"


async def test_nota_seis_com_testes_falhos_nao_encerra(executor_module, monkeypatch):
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

    devolvido = await executor_module.aplicar_politica_de_progresso(ctx)

    assert ctx.state["progress_score_history"] == [0.6]
    assert ctx.actions.escalate is None
    assert devolvido is None


async def test_erro_repetido_encerra_e_substitui_o_turno(executor_module, monkeypatch):
    """Mesma falha e nota parada: encerra pelo acelerador, antes da janela cheia.

    Exige que a ausência de progresso tenha PERSISTIDO — uma única rodada sem
    melhora não basta, senão um vale isolado derrubaria a task.

    No encerramento o turno é substituído: o coder não pode receber um relatório
    "conserte isto" referente a uma rodada que não vai existir.
    """
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    ctx = _Contexto({"validation": _veredito("reprovado", "nao_atendido")})

    primeira = await executor_module.aplicar_politica_de_progresso(ctx)
    segunda = await executor_module.aplicar_politica_de_progresso(ctx)
    terceira = await executor_module.aplicar_politica_de_progresso(ctx)

    assert primeira is None, "a 1ª rodada não tem com o que comparar"
    assert segunda is None, "um único tropeço não pode encerrar a task"
    assert ctx.actions.escalate is True
    assert ctx.state["loop_stop_reason"] == "erro_repetido"
    assert "NÃO é aprovação" in terceira.parts[0].text


async def test_falha_sempre_inedita_atravessa_o_plato_ate_o_orcamento(
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
        await executor_module.aplicar_politica_de_progresso(ctx)
        for _ in range(orcamento + 1)
    ]

    # Onde a política antiga já teria encerrado (4ª rodada), o loop segue.
    assert decisoes[3] is None, "encerrou por platô apesar de a falha ser inédita"
    # E o encerramento vem do orçamento, não do platô.
    assert all(d is None for d in decisoes[:orcamento])
    assert decisoes[orcamento] is not None
    assert ctx.state["loop_stop_reason"] == "orcamento_de_falhas_distintas"


async def test_mesma_falha_repetida_ainda_encerra_cedo(executor_module, monkeypatch):
    """Contrapartida: a tolerância é para erro NOVO, não para repisar o mesmo."""
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    monkeypatch.setattr(executor_module, "assinatura_erro", lambda *_: "sempre-a-mesma")
    ctx = _Contexto({"validation": _veredito("reprovado", "nao_atendido")})

    decisoes = [
        await executor_module.aplicar_politica_de_progresso(ctx) for _ in range(3)
    ]

    assert decisoes[2] is not None
    assert ctx.state["loop_stop_reason"] == "erro_repetido"


async def test_veredito_ausente_nao_registra_rodada(executor_module):
    ctx = _Contexto({})

    assert await executor_module.aplicar_politica_de_progresso(ctx) is None
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


# ===========================================================================
# QA de critérios no loop (PoC #394) — a evidência do QA substitui a do harness
# ===========================================================================


def _report_tecnico_verde() -> dict:
    """Estágios técnicos todos em sucesso, para isolar o degrau de critérios."""
    return {
        "stages": [
            {
                "stage": "preparacao_ambiente",
                "status": "sucesso",
                "evidence": {"surface": "service", "test_commands": ["pytest -v"]},
            },
            {"stage": "implantacao_artefato", "status": "sucesso"},
            {"stage": "inicializacao_aplicacao", "status": "sucesso"},
            {
                "stage": "testes_automatizados",
                "status": "sucesso",
                "evidence": {
                    "resultados": [
                        {"resumo": {"passaram": 5, "falharam": 0, "erros": 0}}
                    ]
                },
            },
        ]
    }


def _report_com_criterios(*outcomes) -> dict:
    return {
        "criteria_evidence": [
            {
                "criterion": f"Critério {i + 1}",
                "criterion_id": f"CA-{i + 1:02d}",
                "outcome": outcome,
                "automatable": outcome != "nao_automatizavel",
            }
            for i, outcome in enumerate(outcomes)
        ]
    }


@pytest.fixture
def executor_com_report(executor_module, monkeypatch):
    """Injeta o ExecutionReport que o callback enxerga e neutraliza o QA.

    O QA é desligado por padrão porque sobe aplicação e chama LLM: um teste
    unitário que o exercitasse de verdade dependeria de rede e de Docker. Os
    testes que precisam dele o religam explicitamente.
    """
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)

    async def _sem_qa(_task_id, _report, **_kwargs):
        return ResultadoQA(executado=False, motivo="desligado no teste")

    monkeypatch.setattr(executor_module, "verificar_criterios_por_e2e", _sem_qa)

    def _configurar(report: dict):
        monkeypatch.setattr(
            executor_module, "_carregar_execution_report", lambda _: report
        )
        return executor_module

    return _configurar


async def test_cobertura_de_criterios_e_publicada_a_cada_rodada(executor_com_report):
    mod = executor_com_report(
        _report_com_criterios("atendido", "nao_atendido", "nao_automatizavel")
    )
    ctx = _Contexto({"validation": _veredito("reprovado"), "task_id": "TASK-001"})

    await mod.aplicar_politica_de_progresso(ctx)
    aceite = ctx.state["acceptance_score"]

    # Sem QA, a evidência é a autoavaliação do coder: a contagem bruta é
    # publicada para auditoria, mas `nota`/`cobertura` vão zeradas e a FONTE diz
    # por quê. Publicá-las como se fossem verificação independente enganaria o
    # reviewer e o manifesto.
    assert aceite["fonte"] == "harness_testes_do_coder"
    assert aceite["nota"] is None
    assert aceite["cobertura"] == 0.0
    assert aceite["total"] == 3


async def test_cobertura_do_qa_e_publicada_com_a_fonte(executor_module, monkeypatch):
    """Com QA, a nota de aceite vale e a procedência acompanha."""
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    monkeypatch.setattr(
        executor_module, "_carregar_execution_report", lambda _: _report_tecnico_verde()
    )

    async def _qa(_task_id, _report, **_kwargs):
        return ResultadoQA(
            executado=True,
            evidencias=[
                CriterionEvidence(
                    criterion="A",
                    criterion_id="CA-01",
                    outcome=CriterionOutcome.ATENDIDO,
                    checkable=True,
                    check_performed="Playwright",
                    observed="passou",
                ),
                CriterionEvidence(
                    criterion="B",
                    criterion_id="CA-02",
                    outcome=CriterionOutcome.NAO_ATENDIDO,
                    checkable=True,
                    check_performed="Playwright",
                    observed="falhou",
                ),
            ],
        )

    monkeypatch.setattr(executor_module, "verificar_criterios_por_e2e", _qa)
    ctx = _Contexto({"validation": _veredito("reprovado"), "task_id": "TASK-001"})

    await executor_module.aplicar_politica_de_progresso(ctx)
    aceite = ctx.state["acceptance_score"]

    assert aceite["fonte"] == "qa_e2e"
    assert aceite["nota"] == 0.5
    assert aceite["cobertura"] == 1.0


async def test_criterios_verificados_pelo_qa_entram_na_nota_registrada(
    executor_module, monkeypatch
):
    """A nota do histórico embute o degrau de critérios quando o QA decidiu."""
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    monkeypatch.setattr(
        executor_module, "_carregar_execution_report", lambda _: _report_tecnico_verde()
    )

    def _qa_com(outcome):
        async def _executar(_task_id, _report, **_kwargs):
            return ResultadoQA(
                executado=True,
                evidencias=[
                    CriterionEvidence(
                        criterion="Critério 1",
                        criterion_id="CA-01",
                        outcome=outcome,
                        checkable=True,
                        check_performed="Playwright",
                        observed="-",
                    )
                ],
            )

        return _executar

    monkeypatch.setattr(
        executor_module,
        "verificar_criterios_por_e2e",
        _qa_com(CriterionOutcome.ATENDIDO),
    )
    ctx_bom = _Contexto({"validation": _veredito("reprovado"), "task_id": "TASK-001"})
    await executor_module.aplicar_politica_de_progresso(ctx_bom)

    monkeypatch.setattr(
        executor_module,
        "verificar_criterios_por_e2e",
        _qa_com(CriterionOutcome.NAO_ATENDIDO),
    )
    ctx_ruim = _Contexto({"validation": _veredito("reprovado"), "task_id": "TASK-001"})
    await executor_module.aplicar_politica_de_progresso(ctx_ruim)

    assert (
        ctx_bom.state["progress_score_history"][0]
        > ctx_ruim.state["progress_score_history"][0]
    )


async def test_evidencia_do_harness_nao_mexe_na_nota(executor_com_report):
    """Sem QA, a nota volta a ser a técnica pura — o coder não se autoavalia."""
    atendido = executor_com_report(
        {**_report_tecnico_verde(), **_report_com_criterios("atendido")}
    )
    ctx_a = _Contexto({"validation": _veredito("reprovado"), "task_id": "TASK-001"})
    await atendido.aplicar_politica_de_progresso(ctx_a)

    nao_atendido = executor_com_report(
        {**_report_tecnico_verde(), **_report_com_criterios("nao_atendido")}
    )
    ctx_b = _Contexto({"validation": _veredito("reprovado"), "task_id": "TASK-001"})
    await nao_atendido.aplicar_politica_de_progresso(ctx_b)

    assert (
        ctx_a.state["progress_score_history"][0]
        == ctx_b.state["progress_score_history"][0]
    )


async def test_evidencia_do_qa_substitui_a_do_harness(executor_module, monkeypatch):
    """Quando o QA roda, é a palavra dele que vale — ele navegou a aplicação.

    O harness só olha o resultado dos testes que o próprio coder escreveu e
    vinculou; misturar as duas fontes produziria dois resultados para o mesmo
    critério sem regra de desempate.
    """
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    monkeypatch.setattr(
        executor_module,
        "_carregar_execution_report",
        lambda _: _report_com_criterios("sem_teste_mapeado"),
    )

    async def _qa_reprova(_task_id, _report, **_kwargs):
        return ResultadoQA(
            executado=True,
            evidencias=[
                CriterionEvidence(
                    criterion="Critério 1",
                    criterion_id="CA-01",
                    outcome=CriterionOutcome.NAO_ATENDIDO,
                    checkable=True,
                    check_performed="Playwright",
                    observed="falhou",
                )
            ],
        )

    monkeypatch.setattr(executor_module, "verificar_criterios_por_e2e", _qa_reprova)
    ctx = _Contexto({"validation": _veredito("reprovado"), "task_id": "TASK-001"})

    await executor_module.aplicar_politica_de_progresso(ctx)

    # O harness dizia `sem_teste_mapeado` (nada decidido, degrau fora da conta);
    # o QA decidiu, e o critério reprovado passa a descontar da nota.
    assert ctx.state["acceptance_score"]["nao_atendidos"] == 1
    assert ctx.state["acceptance_score"]["cobertura"] == 1.0


async def test_qa_indisponivel_degrada_para_a_evidencia_do_harness(
    executor_com_report,
):
    """Medida auxiliar ausente não pode piorar a leitura da rodada."""
    mod = executor_com_report(_report_com_criterios("atendido"))
    ctx = _Contexto({"validation": _veredito("reprovado"), "task_id": "TASK-001"})

    await mod.aplicar_politica_de_progresso(ctx)

    assert ctx.state["acceptance_score"]["atendidos"] == 1
    assert ctx.state["qa_criterios_resultado"]["executado"] is False


async def test_registro_do_qa_vai_para_o_state(executor_com_report):
    """Auditoria: o que o QA fez (ou por que não fez) precisa ficar registrado."""
    mod = executor_com_report(_report_com_criterios("atendido"))
    ctx = _Contexto({"validation": _veredito("reprovado"), "task_id": "TASK-001"})

    await mod.aplicar_politica_de_progresso(ctx)

    assert ctx.state["qa_criterios_resultado"]["motivo"] == "desligado no teste"


async def test_criterio_reprovado_pelo_qa_bloqueia_a_aprovacao(
    executor_module, monkeypatch
):
    """Execução verde não basta: o QA provou que a entrega não faz o que pediram.

    Sem esta trava o agente de QA não teria influência nenhuma sobre o que é
    entregue — o loop encerraria por aprovação técnica e o achado dele viraria
    só um número no relatório.
    """
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    monkeypatch.setattr(
        executor_module, "_carregar_execution_report", lambda _: _report_tecnico_verde()
    )

    async def _qa_reprova(_task_id, _report, **_kwargs):
        return ResultadoQA(
            executado=True,
            evidencias=[
                CriterionEvidence(
                    criterion="A página inicial lista os álbuns",
                    criterion_id="CA-01",
                    outcome=CriterionOutcome.NAO_ATENDIDO,
                    checkable=True,
                    check_performed="Playwright",
                    observed="O teste de navegação falhou: heading não encontrado.",
                )
            ],
        )

    monkeypatch.setattr(executor_module, "verificar_criterios_por_e2e", _qa_reprova)
    ctx = _Contexto({"validation": _veredito("aprovado"), "task_id": "TASK-001"})

    devolvido = await executor_module.aplicar_politica_de_progresso(ctx)

    assert ctx.actions.escalate is None, "encerrou o loop apesar do critério reprovado"
    assert devolvido is not None
    texto = devolvido.parts[0].text
    assert "CA-01" in texto
    assert "heading não encontrado" in texto, "o coder não recebeu o que o QA observou"
    assert ctx.state["execution_result"] == texto


async def test_criterio_nao_comprovado_nao_bloqueia_a_aprovacao(
    executor_module, monkeypatch
):
    """Ausência de evidência não é evidência de ausência.

    Só falha PROVADA bloqueia — senão a trava recriaria a task que nunca aprova,
    que é o defeito histórico que este desenho inteiro evita.
    """
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    monkeypatch.setattr(
        executor_module, "_carregar_execution_report", lambda _: _report_tecnico_verde()
    )

    async def _qa_inconclusivo(_task_id, _report, **_kwargs):
        return ResultadoQA(
            executado=True,
            evidencias=[
                CriterionEvidence(
                    criterion="O visual é minimalista",
                    criterion_id="CA-01",
                    outcome=CriterionOutcome.NAO_AUTOMATIZAVEL,
                    checkable=False,
                    check_performed="-",
                    observed="fora do alcance da navegação",
                ),
                CriterionEvidence(
                    criterion="Lista álbuns",
                    criterion_id="CA-02",
                    outcome=CriterionOutcome.ATENDIDO,
                    checkable=True,
                    check_performed="Playwright",
                    observed="passou",
                ),
            ],
        )

    monkeypatch.setattr(
        executor_module, "verificar_criterios_por_e2e", _qa_inconclusivo
    )
    ctx = _Contexto({"validation": _veredito("aprovado"), "task_id": "TASK-001"})

    devolvido = await executor_module.aplicar_politica_de_progresso(ctx)

    assert ctx.actions.escalate is True
    assert devolvido is None


async def test_sem_qa_a_aprovacao_tecnica_encerra_como_antes(executor_com_report):
    """Sem verificação por navegação, o comportamento anterior é preservado."""
    mod = executor_com_report(_report_tecnico_verde())
    ctx = _Contexto({"validation": _veredito("aprovado"), "task_id": "TASK-001"})

    devolvido = await mod.aplicar_politica_de_progresso(ctx)

    assert ctx.actions.escalate is True
    assert devolvido is None


async def test_sem_decisao_do_qa_funciona_com_state_real_do_adk(
    executor_com_report,
):
    """Regressão: `State` não implementa `pop`, usado antes nesta passagem.

    Em execução real, o AttributeError escapava do after callback e fazia o
    TaskIterator marcar todas as tasks como `erro_operacional`, logo após o
    primeiro turno do executor.
    """
    mod = executor_com_report(_report_tecnico_verde())
    state = State(
        {
            "validation": _veredito("aprovado"),
            "task_id": "TASK-001",
            "qa_criterios_evidencias": [{"outcome": "nao_atendido"}],
        },
        {},
    )
    ctx = _Contexto(state)

    devolvido = await mod.aplicar_politica_de_progresso(ctx)

    assert devolvido is None
    assert ctx.actions.escalate is True
    assert state["qa_criterios_evidencias"] == []


async def test_qa_reprovando_sempre_o_mesmo_criterio_acaba_encerrando(
    executor_module, monkeypatch
):
    """Bloquear a aprovação NÃO pode criar um loop sem freio.

    Regressão: a primeira versão desta trava devolvia Content sem passar por
    `registrar_e_avaliar`, então nenhuma decisão de continuidade era tomada e a
    task rodava até o teto do LoopAgent — um build completo e uma suíte de
    navegação por rodada. A rodada bloqueada pelo QA é uma rodada NÃO concluída
    como qualquer outra, e a política precisa julgá-la.
    """
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    monkeypatch.setattr(
        executor_module, "_carregar_execution_report", lambda _: _report_tecnico_verde()
    )

    async def _qa_reprova(_task_id, _report, **_kwargs):
        return ResultadoQA(
            executado=True,
            evidencias=[
                CriterionEvidence(
                    criterion="A página lista os álbuns",
                    criterion_id="CA-01",
                    outcome=CriterionOutcome.NAO_ATENDIDO,
                    checkable=True,
                    check_performed="Playwright",
                    observed="heading não encontrado",
                )
            ],
        )

    monkeypatch.setattr(executor_module, "verificar_criterios_por_e2e", _qa_reprova)
    ctx = _Contexto({"validation": _veredito("aprovado"), "task_id": "TASK-001"})

    for _ in range(6):
        await executor_module.aplicar_politica_de_progresso(ctx)
        if ctx.actions.escalate:
            break

    assert ctx.actions.escalate is True, "o loop rodaria até o teto do LoopAgent"
    assert ctx.state["loop_stop_reason"] is not None


async def test_rodada_bloqueada_pelo_qa_mantem_os_historicos_alinhados(
    executor_module, monkeypatch
):
    """Notas e assinaturas precisam ter o mesmo comprimento.

    `contar_rodadas_sem_avanco` indexa as assinaturas pelo índice da NOTA. Se a
    rodada bloqueada pelo QA entrasse só no histórico de notas, as duas listas
    desalinhavam e a novidade de uma rodada seria creditada a outra — o platô
    dispararia na task que estava avançando.
    """
    monkeypatch.setattr(executor_module, "fingerprint_mudou", lambda _: True)
    monkeypatch.setattr(
        executor_module, "_carregar_execution_report", lambda _: _report_tecnico_verde()
    )

    async def _qa_reprova(_task_id, _report, **_kwargs):
        return ResultadoQA(
            executado=True,
            evidencias=[
                CriterionEvidence(
                    criterion="A",
                    criterion_id="CA-01",
                    outcome=CriterionOutcome.NAO_ATENDIDO,
                    checkable=True,
                    check_performed="Playwright",
                    observed="falhou",
                )
            ],
        )

    monkeypatch.setattr(executor_module, "verificar_criterios_por_e2e", _qa_reprova)
    ctx = _Contexto({"validation": _veredito("aprovado"), "task_id": "TASK-001"})

    await executor_module.aplicar_politica_de_progresso(ctx)

    assert len(ctx.state["progress_score_history"]) == len(
        ctx.state["progress_error_signature_history"]
    )


async def test_criterios_reprovados_diferentes_renovam_a_tolerancia(executor_module):
    """Fechar um critério e cair no seguinte é AVANÇO, não repetição.

    Se a assinatura ignorasse quais critérios falharam, ela seria idêntica em
    todas essas rodadas (execução verde, mesmos estágios) e o gatilho de erro
    repetido cortaria a task na segunda tentativa.
    """
    primeira = executor_module._assinatura_da_rodada(
        _report_tecnico_verde(), [{"criterion_id": "CA-01"}]
    )
    mesma = executor_module._assinatura_da_rodada(
        _report_tecnico_verde(), [{"criterion_id": "CA-01"}]
    )
    outra = executor_module._assinatura_da_rodada(
        _report_tecnico_verde(), [{"criterion_id": "CA-02"}]
    )

    assert primeira == mesma
    assert primeira != outra
