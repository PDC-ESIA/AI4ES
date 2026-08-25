"""Regressões da proteção contra sobrescrita cega entre tasks do coder."""

from __future__ import annotations

from src.agents.workflow_coding_review.coder.workspace_guard import (
    CHAVE_ARQUIVOS_HERDADOS,
    _MAX_ARQUIVOS_NO_AVISO,
    anunciar_arquivos_herdados,
    bloquear_sobrescrita_herdada,
    preparar_arquivos_herdados,
)


class _Tool:
    def __init__(self, name: str = "tool_criar_arquivo"):
        self.name = name


class _Context:
    def __init__(self, state: dict):
        self.state = state


def _chamar(state: dict, caminho: str, tool_name: str = "tool_criar_arquivo"):
    return bloquear_sobrescrita_herdada(
        _Tool(tool_name),
        {"caminho": caminho, "conteudo": "novo"},
        _Context(state),
    )


def test_primeira_task_nao_bloqueia_criacao_ou_sobrescrita():
    state = {CHAVE_ARQUIVOS_HERDADOS: []}

    assert _chamar(state, "PLAN.md") is None
    assert _chamar(state, "src/app.py") is None


def test_task_posterior_bloqueia_arquivo_herdado_com_mensagem_acionavel():
    state = {CHAVE_ARQUIVOS_HERDADOS: ["PLAN.md", "src/app.py"]}

    resposta = _chamar(state, "src/app.py")

    assert resposta is not None
    assert resposta["sucesso"] is False
    assert resposta["codigo"] == "SOBRESCRITA_INTER_TASK_BLOQUEADA"
    assert "tool_ler_arquivo" in resposta["erro"]
    assert "tool_substituir_trecho" in resposta["erro"]


def test_alias_de_caminho_nao_contorna_o_guard():
    state = {CHAVE_ARQUIVOS_HERDADOS: ["PLAN.md"]}

    assert _chamar(state, "./PLAN.md")["codigo"] == "SOBRESCRITA_INTER_TASK_BLOQUEADA"
    assert _chamar(state, ".\\PLAN.md")["codigo"] == "SOBRESCRITA_INTER_TASK_BLOQUEADA"


def test_arquivo_novo_da_task_pode_ser_recriado_em_retry(tmp_path):
    """A baseline é fixa: existir agora não torna o arquivo herdado."""
    state = {CHAVE_ARQUIVOS_HERDADOS: ["src/app.py"]}
    novo = tmp_path / "src" / "feature.py"
    novo.parent.mkdir()
    novo.write_text("primeira versão", encoding="utf-8")

    assert _chamar(state, "src/feature.py") is None


def test_edicao_parcial_de_arquivo_herdado_continua_permitida():
    state = {CHAVE_ARQUIVOS_HERDADOS: ["src/app.py"]}

    assert _chamar(state, "src/app.py", "tool_substituir_trecho") is None


def test_execucao_direta_sem_baseline_preserva_comportamento_legado():
    assert _chamar({}, "src/app.py") is None


def test_baseline_invalida_bloqueia_por_seguranca():
    resposta = _chamar({CHAVE_ARQUIVOS_HERDADOS: "src/app.py"}, "src/app.py")

    assert resposta["codigo"] == "BASELINE_DA_TASK_INVALIDA"


def test_preparar_baseline_primeira_task_e_task_posterior(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    coder_dir = tmp_path / "ws" / "coder" / "src"
    (coder_dir / "src").mkdir(parents=True)
    (coder_dir / "PLAN.md").write_text("plano", encoding="utf-8")
    (coder_dir / "src" / "app.py").write_text("app", encoding="utf-8")
    state: dict = {}

    preparar_arquivos_herdados(state, primeira=True)
    assert state[CHAVE_ARQUIVOS_HERDADOS] == []

    preparar_arquivos_herdados(state, primeira=False)
    assert state[CHAVE_ARQUIVOS_HERDADOS] == ["PLAN.md", "src/app.py"]


def test_coder_agent_conecta_o_guard(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    import importlib

    coder_agent = importlib.import_module(
        "src.agents.workflow_coding_review.coder.agent"
    )
    importlib.reload(coder_agent)

    assert coder_agent.agent.before_tool_callback is coder_agent.bloquear_sobrescrita_herdada
    assert coder_agent.agent.after_tool_callback is coder_agent.anunciar_arquivos_herdados
    assert "SOMENTE QUANDO execution_result ESTIVER AUSENTE" in coder_agent.agent.instruction


# ===========================================================================
# anunciar_arquivos_herdados — o aviso preventivo, no canal que o coder segue
# ===========================================================================
#
# Metade preventiva da proteção. A run do "fotógrafo" mostrou o coder abrindo
# TODAS as 5 tasks pós-primeira com `tool_criar_arquivo("PLAN.md")`, ignorando a
# instrução em prosa — mas reagindo corretamente ao resultado de uma tool em
# 19/19 bloqueios. Estes testes fixam que o aviso chega por esse canal.


def _anunciar(state: dict, resposta, tool_name: str = "tool_listar_workspace"):
    return anunciar_arquivos_herdados(
        _Tool(tool_name),
        {"caminho": "."},
        _Context(state),
        resposta,
    )


def test_primeira_task_nao_anuncia_projeto_existente():
    """Sem arquivos herdados o aviso seria falso: o projeto está nascendo."""
    assert _anunciar({CHAVE_ARQUIVOS_HERDADOS: []}, ["PLAN.md"]) is None
    assert _anunciar({}, ["PLAN.md"]) is None


def test_task_posterior_anuncia_projeto_e_preserva_a_listagem():
    state = {CHAVE_ARQUIVOS_HERDADOS: ["PLAN.md", "app/main.py"]}

    resposta = _anunciar(state, ["TASK-001.json", "TASK-002.json"])

    assert resposta is not None
    # A listagem original não se perde — o aviso é acréscimo, não substituição.
    assert resposta["itens"] == ["TASK-001.json", "TASK-002.json"]
    assert resposta["projeto_ja_implementado"] is True
    assert resposta["arquivos_existentes_no_workspace"] == ["PLAN.md", "app/main.py"]
    # O aviso precisa nomear a ação proibida e a alternativa correta.
    instrucao = resposta["instrucao_obrigatoria"]
    assert "PLAN.md" in instrucao
    assert "tool_substituir_trecho" in instrucao


def test_outras_tools_nao_sao_alteradas():
    """O aviso vai em UMA tool por task; anexá-lo a cada leitura seria ruído."""
    state = {CHAVE_ARQUIVOS_HERDADOS: ["PLAN.md"]}

    assert _anunciar(state, "conteudo", tool_name="tool_ler_arquivo") is None
    assert _anunciar(state, {"ok": True}, tool_name="tool_criar_arquivo") is None


def test_resposta_de_erro_da_tool_passa_intacta():
    """A tool sinaliza falha com uma string 'Erro:'; anexar o aviso confundiria."""
    state = {CHAVE_ARQUIVOS_HERDADOS: ["PLAN.md"]}

    assert _anunciar(state, "Erro: diretório 'x' não existe.") is None


def test_baseline_corrompida_nao_estoura():
    """Callback no meio do fluxo: derrubá-lo custaria a rodada inteira."""
    assert _anunciar({CHAVE_ARQUIVOS_HERDADOS: "PLAN.md"}, ["a"]) is None
    assert _anunciar({CHAVE_ARQUIVOS_HERDADOS: None}, ["a"]) is None


def test_projeto_grande_tem_a_lista_truncada_com_contagem():
    """Um projeto grande não pode transformar o aviso num despejo de contexto."""
    herdados = [f"src/modulo_{i}.py" for i in range(_MAX_ARQUIVOS_NO_AVISO + 25)]

    resposta = _anunciar({CHAVE_ARQUIVOS_HERDADOS: herdados}, ["a"])

    assert len(resposta["arquivos_existentes_no_workspace"]) == _MAX_ARQUIVOS_NO_AVISO
    assert resposta["arquivos_omitidos_deste_aviso"] == 25


# ===========================================================================
# Gate de abertura do prompt — a decisão de modo vem antes de tudo
# ===========================================================================


def test_gate_de_modo_abre_a_instrucao_do_coder():
    """A regra já existia em prosa e não pegava; a aposta aqui é POSIÇÃO.

    Enterrada depois de ~45 linhas de perfil e diretrizes, a exceção "não recrie
    o projeto" chegava tarde demais — o modelo já tinha entrado no fluxo
    "planeje e implemente". O gate precisa ser a PRIMEIRA coisa que ele lê.
    """
    from src.agents.workflow_coding_review.coder import prompt

    instrucao = prompt.build_instruction("/ws")
    abertura = instrucao[: instrucao.index("# PERFIL DO AGENTE")]

    # O gate está inteiro ANTES do perfil.
    assert abertura.lstrip().startswith("# ANTES DE QUALQUER OUTRA COISA")
    # E carrega a decisão binária com a proibição concreta.
    assert "modo CRIAÇÃO" in abertura
    assert "modo INCREMENTO" in abertura
    assert 'tool_criar_arquivo("PLAN.md")' in abertura
    assert "tool_substituir_trecho" in abertura


def test_gate_preserva_o_placeholder_de_estado_do_adk():
    """`{execution_result?}` precisa chegar literal para o ADK resolver em runtime.

    O gate não passa por `.format()` justamente por isso; se alguém o incluir na
    formatação, o placeholder vira `KeyError` ou some — e o coder perde o único
    dado que distingue os dois modos.
    """
    from src.agents.workflow_coding_review.coder import prompt

    assert "{execution_result?}" in prompt.build_instruction("/ws")
