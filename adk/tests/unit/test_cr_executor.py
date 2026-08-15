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
    assert "executar_harness_tool" in names        # harness (bound ao workspace do workflow)
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
# Integração: instrução do coder resolvida (InstructionProvider)
# ===========================================================================


class _FakeReadonlyContext:
    """Contexto mínimo aceito pelo InstructionProvider do coder."""

    def __init__(self, state=None):
        self.state = state or {}


def _instrucao_resolvida(cr_coder, state=None):
    """Renderiza a instrução do coder como o ADK faria antes de chamar o modelo."""
    return cr_coder.agent.canonical_instruction.__self__.instruction(
        _FakeReadonlyContext(state)
    )


def test_coder_instruction_injeta_execution_result_sem_placeholder_literal(
    tmp_path, monkeypatch
):
    """O ErrorReport chega resolvido — e nenhum placeholder literal sobrevive.

    Regressão do modo de falha silencioso: um InstructionProvider faz o ADK
    devolver bypass_state_injection=True, então templates `{chave?}` NÃO são
    resolvidos. Se o placeholder vazasse literal, o coder veria o bloco vazio,
    se julgaria em "primeira execução" e recriaria o projeto a cada iteração,
    sobrescrevendo as correções.
    """
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import coder as cr_coder

    importlib.reload(cr_coder)

    instr = _instrucao_resolvida(cr_coder, {"execution_result": "ERRO-DO-EXECUTOR"})
    assert "ERRO-DO-EXECUTOR" in instr, (
        "ErrorReport não chegou à instrução do coder — o loop de correção fica cego."
    )
    for marcador in ("{execution_result?}", "__EXECUTION_RESULT__",
                     "__CONTRATO_DA_TASK__", "__ARVORE_DE_ARQUIVOS__"):
        assert marcador not in instr, f"placeholder {marcador} vazou literal para o modelo"


def test_coder_instruction_sem_execution_result_deixa_bloco_vazio(tmp_path, monkeypatch):
    """Sem execution_result no state, o bloco fica VAZIO (semântica do `{chave?}`).

    É esse vazio que o prompt usa para distinguir a primeira execução.
    """
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import coder as cr_coder

    importlib.reload(cr_coder)

    instr = _instrucao_resolvida(cr_coder, {})
    assert "--- RESULTADO DA EXECUÇÃO ANTERIOR ---\n\n--- FIM DO RESULTADO ---" in instr
    assert "None" not in instr.split("RESULTADO DA EXECUÇÃO ANTERIOR")[1][:80]


def test_visao_geral_das_tasks_some_apos_o_plano(tmp_path, monkeypatch):
    """A visão global é insumo do PLAN.md: existe antes dele, some depois.

    O PLAN.md é um manifesto GLOBAL (arquivos → responsabilidade → tasks,
    consolidando outputs repetidos). Planejá-lo vendo só a task atual produziria
    um esqueleto que as demais tasks não habitam. Depois que o plano existe, ele
    passa a ser a fonte da verdade e a visão geral vira custo por requisição.
    """
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import coder as cr_coder

    importlib.reload(cr_coder)

    state = {
        "task_id": "TASK-002",
        "tasks": {
            "macro_context": {"tech_stack": ["FastAPI"]},
            "tasks": [
                {
                    "id": "TASK-001",
                    "description": "Modelo de ensaio",
                    "contract": {"outputs": ["models/ensaio.py"],
                                 "interfaces": ["POST /ensaios"]},
                },
                {
                    "id": "TASK-002",
                    "description": "Upload de fotos",
                    "acceptance_criteria": ["CRITERIO-DA-ATUAL"],
                    "contract": {"outputs": ["controllers/upload.py"]},
                },
            ],
        },
    }

    # --- antes do PLAN.md: conjunto completo visível ---
    instr = _instrucao_resolvida(cr_coder, state)
    assert "Visão geral das tasks" in instr
    assert "TASK-001" in instr and "Modelo de ensaio" in instr
    assert "POST /ensaios" in instr           # interfaces alimentam o checklist
    assert "models/ensaio.py" in instr        # outputs alimentam o manifesto
    assert "CRITERIO-DA-ATUAL" in instr       # a task atual segue completa

    # --- depois do PLAN.md: o plano governa, a visão geral sai ---
    from pathlib import Path as _Path

    coder_src = _Path(tmp_path / "ws" / "coder" / "src")
    coder_src.mkdir(parents=True, exist_ok=True)
    (coder_src / "PLAN.md").write_text("# plano", encoding="utf-8")

    depois = _instrucao_resolvida(cr_coder, state)
    assert "Visão geral das tasks" not in depois
    assert "Modelo de ensaio" not in depois
    assert "CRITERIO-DA-ATUAL" in depois, "a task atual não pode sumir com o plano"
    # O plano toma o lugar da visão geral: sem histórico de sessão, ele não
    # chegaria ao coder de outra forma, e o prompt o chama de fonte da verdade.
    assert "PLAN.md (sua fonte da verdade)" in depois
    assert "# plano" in depois


def test_task_atual_sobrevive_a_visao_geral_gigante(tmp_path, monkeypatch):
    """Nenhum bloco anterior pode empurrar a task atual para fora do contrato.

    Regressão real: um teto monolítico sobre o contrato montado cortava o
    ÚLTIMO bloco — justamente a task atual — e o coder implementava sem nunca
    ver os próprios critérios de aceite.
    """
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import coder as cr_coder

    importlib.reload(cr_coder)

    state = {
        "task_id": "TASK-002",
        "tasks": {
            "macro_context": {"tech_stack": ["Python"]},
            "tasks": [
                {"id": "TASK-001", "description": "base",
                 "contract": {"outputs": ["x" * 15_000]}},
                {"id": "TASK-002", "description": "atual",
                 "acceptance_criteria": ["CRITERIO-INDISPENSAVEL"],
                 "contract": {"outputs": ["app.py"]}},
            ],
        },
    }

    instr = _instrucao_resolvida(cr_coder, state)
    assert "Task atual — TASK-002" in instr
    assert "CRITERIO-INDISPENSAVEL" in instr
    assert "TASK-001" in instr, "os ids do épico continuam visíveis"


def test_visao_geral_degrada_campos_antes_de_descartar_tasks(tmp_path, monkeypatch):
    """Abreviar é melhor que omitir: o manifesto é global por definição."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import coder as cr_coder

    importlib.reload(cr_coder)
    modulo = importlib.import_module(
        "src.agents.workflow_coding_review.coder.agent"
    )

    tasks = [
        {"id": f"TASK-{i:03d}", "description": "D" * 500,
         "contract": {"outputs": [f"f{i}.py"], "interfaces": [f"GET /r{i}"]}}
        for i in range(1, 41)
    ]

    visao = modulo._visao_geral_das_tasks(tasks, "TASK-001")
    assert len(visao) <= modulo._MAX_TASKS_COMPACTAS_CHARS
    for i in range(1, 41):
        assert f"TASK-{i:03d}" in visao, "nenhuma task pode sumir em silêncio"


def test_visao_geral_cai_para_o_disco_sem_state(tmp_path, monkeypatch):
    """Sem `state["tasks"]`, o conjunto é remontado dos arquivos em coder/tasks."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import coder as cr_coder

    importlib.reload(cr_coder)

    from pathlib import Path as _Path

    tasks_dir = _Path(tmp_path / "ws" / "coder" / "tasks")
    tasks_dir.mkdir(parents=True, exist_ok=True)
    for identificador, descricao in [("TASK-001", "Do disco um"), ("TASK-002", "Do disco dois")]:
        (tasks_dir / f"{identificador}.json").write_text(
            f'{{"id": "{identificador}", "description": "{descricao}"}}', encoding="utf-8"
        )

    instr = _instrucao_resolvida(cr_coder, {"task_id": "TASK-001"})
    assert "Do disco um" in instr and "Do disco dois" in instr


def test_coder_instruction_injeta_contrato_e_arvore(tmp_path, monkeypatch):
    """Contrato da task e árvore de arquivos entram na instrução (evita redescoberta)."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import coder as cr_coder

    importlib.reload(cr_coder)

    from pathlib import Path as _Path

    tasks_dir = _Path(tmp_path / "ws" / "coder" / "tasks")
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "TASK-001.json").write_text(
        '{"id": "TASK-001", "acceptance_criteria": ["CRITERIO-INJETADO"]}',
        encoding="utf-8",
    )
    (tasks_dir / "_macro_context.json").write_text(
        '{"tech_stack": ["STACK-INJETADA"]}', encoding="utf-8"
    )
    src_dir = _Path(cr_coder.agent.name and tmp_path / "ws" / "coder" / "src")
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "ja_existe.py").write_text("# x", encoding="utf-8")

    instr = _instrucao_resolvida(cr_coder, {"task_id": "TASK-001"})
    assert "CRITERIO-INJETADO" in instr
    assert "STACK-INJETADA" in instr
    assert "- ja_existe.py" in instr


def test_coder_instruction_contem_modo_operacao(tmp_path, monkeypatch):
    """O coder.instruction deve conter a seção MODO DE OPERAÇÃO."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import coder as cr_coder

    importlib.reload(cr_coder)

    instr = _instrucao_resolvida(cr_coder)
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
    # O acoplamento agora é pela chave de state que o provider do coder lê:
    # o que o executor publica em output_key precisa aparecer na instrução.
    instr = _instrucao_resolvida(cr_coder, {output_key: "VALOR-PUBLICADO-PELO-EXECUTOR"})
    assert "VALOR-PUBLICADO-PELO-EXECUTOR" in instr


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

    from src.agents.workflow_coding_review import coder as cr_coder

    importlib.reload(cr_coder)

    instr = _instrucao_resolvida(cr_coder)
    assert "README.md" in instr
    assert "http://localhost:8000" in instr


def test_coder_instruction_exige_run_json(tmp_path, monkeypatch):
    """O coder.instruction deve exigir o manifesto run.json dirigido pela surface."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    from src.agents.workflow_coding_review import coder as cr_coder

    importlib.reload(cr_coder)

    instr = _instrucao_resolvida(cr_coder)
    # run.json é o novo artefato de execução obrigatório (substitui Docker).
    assert "run.json" in instr
    # A superfície (service/command/none) deriva o comportamento do harness.
    assert "surface" in instr
    for surface in ("service", "command", "none"):
        assert surface in instr, f"superfície ausente no prompt: {surface}"
