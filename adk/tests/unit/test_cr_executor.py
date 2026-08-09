"""Tests para o cr_executor do workflow_coding_review.

Após a convergência determinística (#335), o executor NÃO roda mais Docker
diretamente nem decide o encerramento do loop. Ele compõe apenas:
  - `executar_harness_tool` (invoca o harness de validação);
  - o Agente de Validação (AgentTool).

A terminação do loop saiu do executor e virou responsabilidade do
`convergence_checker` — por isso NÃO há mais `exit_loop` nem protocolo de
estagnação aqui. O executor usa instrução e schemas PRÓPRIOS
(`executor/prompt.py` / `executor/schemas.py`), sem derivar do pacote `executor/`.

Cobertura:
- Agent wiring: nome, output_key, as 2 peças compostas;
- ausência das tools/decisões antigas (sem exit_loop, sem exit-por-status);
- salvaguarda de prompt presente;
- schemas locais estruturalmente equivalentes aos canônicos;
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

    from src.agents.workflow_coding_review.executor import agent as cr_executor

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


def test_executor_agent_tem_2_tools(executor_module):
    """Executor compõe exatamente 2 peças: harness e validador (sem exit_loop)."""
    assert len(executor_module.agent.tools) == 2


def test_executor_compoe_harness_e_validador(executor_module):
    """As duas peças estão presentes e nomeadas — e exit_loop NÃO está mais lá."""
    names = _tool_names(executor_module.agent)
    assert "executar_harness_tool" in names       # harness (bound ao workspace do workflow)
    assert "implementation_validator" in names     # AgentTool do validador
    assert "exit_loop" not in names                # terminação é do convergence_checker


# ===========================================================================
# O vício original sumiu — sem exit por status de execução, sem exit_loop
# ===========================================================================


def test_executor_sem_exit_loop(executor_module):
    """O executor não tem mais a tool exit_loop nem a importa."""
    names = _tool_names(executor_module.agent)
    assert "exit_loop" not in names
    assert not hasattr(executor_module, "exit_loop")


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
    """A instrução impõe a obediência ao veredito e nega ao executor a decisão."""
    instr = executor_module.agent.instruction.lower()
    assert "obede" in instr                     # DEVE OBEDECER ao veredito
    assert "não decide" in instr or "nao decide" in instr


def test_executor_instruction_sem_exit_loop_delega_convergencia(executor_module):
    """A instrução NÃO menciona exit_loop e atribui a terminação ao checker."""
    instr = executor_module.agent.instruction.lower()
    assert "exit_loop" not in instr
    assert "converg" in instr   # verificador de convergência assume a terminação
    assert "veredito" in instr and "aprovado" in instr


# ===========================================================================
# Integração: coder instruction contém {execution_result?}
# ===========================================================================


def test_coder_instruction_contem_execution_result_placeholder(tmp_path, monkeypatch):
    """O coder.instruction deve conter {execution_result?} para ADK state injection."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review.coder import agent as cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    assert "{execution_result?}" in instr, (
        "Placeholder {execution_result?} ausente na instrução do coder. "
        "O LoopAgent não conseguirá injetar logs de erro do executor."
    )


def test_coder_instruction_contem_modo_operacao(tmp_path, monkeypatch):
    """O coder.instruction deve conter a seção MODO DE OPERAÇÃO."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review.coder import agent as cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    assert "MODO DE OPERAÇÃO" in instr
    assert "RESULTADO DA EXECUÇÃO ANTERIOR" in instr


def test_executor_output_key_matches_coder_placeholder(tmp_path, monkeypatch):
    """executor.output_key deve ser 'execution_result' (same key used in coder placeholder)."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review.coder import agent as cr_coder
    from src.agents.workflow_coding_review.executor import agent as cr_executor

    importlib.reload(cr_executor)
    importlib.reload(cr_coder)

    output_key = cr_executor.agent.output_key
    assert output_key == "execution_result"
    # Confirm the placeholder in coder matches
    assert f"{{{output_key}?}}" in cr_coder.agent.instruction


# ===========================================================================
# Contrato dos schemas locais — equivalência estrutural com os canônicos
# ===========================================================================


def test_error_report_schemas_locais_equivalem_aos_canonicos():
    """executor/schemas.py é uma cópia local (independência do pacote executor/),
    mas precisa permanecer estruturalmente idêntico aos schemas canônicos — este
    teste é o único acoplamento e alarma se um dos lados mudar."""
    from src.agents.executor import schemas as canon
    from src.agents.workflow_coding_review.executor import schemas as local

    for nome in ("ErrorReport", "FailedCriterion", "FailedStage"):
        campos_canon = getattr(canon, nome).model_fields.keys()
        campos_local = getattr(local, nome).model_fields.keys()
        assert set(campos_local) == set(campos_canon), (
            f"{nome}: campos divergentes entre local e canônico"
        )


# ===========================================================================
# LoopAgent structure — topologia [coder → executor → convergence_checker]
# ===========================================================================


def test_loop_agent_max_iterations():
    """O teto do LoopAgent é a rede de segurança (default 300); a terminação
    real é do convergence_checker."""
    from src.agents.workflow_coding_review.agent import _code_execute_loop

    assert _code_execute_loop.max_iterations == 300


def test_loop_agent_sub_agents_order():
    """LoopAgent: coder → executor → convergence_checker (validador é AgentTool
    interna do executor, não sub-agente do loop)."""
    from src.agents.workflow_coding_review.agent import _code_execute_loop

    names = [sa.name for sa in _code_execute_loop.sub_agents]
    assert names[0] == "cr_coder_agent"
    assert names[1] == "cr_executor_agent"
    assert names[2] == "cr_convergence_checker"
    assert len(names) == 3  # o validador NÃO é sub-agente do loop


def test_coder_instruction_exige_readme(tmp_path, monkeypatch):
    """O coder.instruction deve exigir criação de README.md com URL de acesso."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review.coder import agent as cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    assert "README.md" in instr
    assert "http://localhost:8000" in instr


def test_coder_instruction_cobre_manifesto_e_dois_modos(tmp_path, monkeypatch):
    """Fase 1 (agnóstico): o coder deve conhecer o manifesto de execução e os
    dois modos de entrega (service/command), não só o web/service Python."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review.coder import agent as cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    # Manifesto de execução agnóstico é obrigatório na saída do coder
    assert ".ai4se_run.json" in instr
    assert "delivery_mode" in instr
    # Ambos os modos de entrega devem ser explicados
    assert "service" in instr
    assert "command" in instr


def test_coder_instruction_erros_comuns_agnosticos(tmp_path, monkeypatch):
    """Fase 1 (agnóstico): a seção de erros comuns lidera por princípios de
    qualquer stack; Python/FastAPI fica como apêndice condicional."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review.coder import agent as cr_coder

    importlib.reload(cr_coder)

    instr = cr_coder.agent.instruction
    # Conteúdo principal é agnóstico
    assert "QUALQUER STACK" in instr
    # Python/FastAPI aparece apenas como apêndice opcional
    assert "APÊNDICE" in instr
    idx_principio = instr.find("PRINCÍPIOS QUE VALEM PARA QUALQUER STACK")
    idx_apendice = instr.find("APÊNDICE")
    assert idx_principio != -1 and idx_apendice != -1
    # Os princípios agnósticos vêm ANTES do apêndice Python
    assert idx_principio < idx_apendice
