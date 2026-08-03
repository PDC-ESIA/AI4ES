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

    from src.agents.workflow_coding_review import cr_executor

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
    assert "executar_harness_validacao" in names   # harness (bound ao workspace do workflow)
    assert "implementation_validator" in names     # AgentTool do validador
    assert "exit_loop" in names                    # encerramento pelo veredito


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
    assert "obede" in instr                     # DEVE OBEDECER ao veredito
    assert "apenas o veredito" in instr          # só o veredito encerra
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

    from src.agents.workflow_coding_review import cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    assert "{execution_result?}" in instr, (
        "Placeholder {execution_result?} ausente na instrução do coder. "
        "O LoopAgent não conseguirá injetar logs de erro do executor."
    )


def test_coder_instruction_contem_modo_operacao(tmp_path, monkeypatch):
    """O coder.instruction deve conter a seção MODO DE OPERAÇÃO."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    assert "MODO DE OPERAÇÃO" in instr
    assert "RESULTADO DA EXECUÇÃO ANTERIOR" in instr


def test_executor_output_key_matches_coder_placeholder(tmp_path, monkeypatch):
    """executor.output_key deve ser 'execution_result' (same key used in coder placeholder)."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import cr_coder, cr_executor

    importlib.reload(cr_executor)
    importlib.reload(cr_coder)

    output_key = cr_executor.agent.output_key
    assert output_key == "execution_result"
    # Confirm the placeholder in coder matches
    assert f"{{{output_key}?}}" in cr_coder.agent.instruction


# ===========================================================================
# LoopAgent structure — topologia [coder → executor] intocada
# ===========================================================================


def test_loop_agent_max_iterations():
    """LoopAgent deve ter max_iterations=5."""
    from src.agents.workflow_coding_review.agent import _code_execute_loop

    assert _code_execute_loop.max_iterations == 5


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

    from src.agents.workflow_coding_review import cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    assert "README.md" in instr
    assert "http://localhost:8000" in instr
