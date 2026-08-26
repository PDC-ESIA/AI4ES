"""Regressões da proteção contra sobrescrita cega entre tasks do coder."""

from __future__ import annotations

from src.agents.workflow_coding_review.coder.workspace_guard import (
    CHAVE_ARQUIVOS_HERDADOS,
    auditar_remocao,
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


def _auditar(state: dict, caminho: str, resposta: object, tool_name: str = "tool_remover_arquivo"):
    return auditar_remocao(
        _Tool(tool_name),
        {"caminho": caminho},
        _Context(state),
        resposta,
    )


def _remocao_ok(caminho: str, tipo: str = "arquivo") -> dict:
    return {
        "sucesso": True,
        "codigo": None,
        "erro": None,
        "caminho": f"/ws/coder/src/{caminho}",
        "tipo": tipo,
    }


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
    assert "SOMENTE QUANDO execution_result ESTIVER AUSENTE" in coder_agent.agent.instruction


# ---------------------------------------------------------------------------
# Auditoria de remoção (issue #388)
# ---------------------------------------------------------------------------


def test_remocao_bem_sucedida_e_registrada_com_a_task(caplog):
    """Critério 6: o log identifica o caminho removido e a task corrente."""
    state = {"task_id": "TASK-004", CHAVE_ARQUIVOS_HERDADOS: []}

    with caplog.at_level(
        "INFO", logger="src.agents.workflow_coding_review.coder.workspace_guard"
    ):
        assert _auditar(state, "app/legado.py", _remocao_ok("app/legado.py")) is None

    assert "TASK-004" in caplog.text
    assert "app/legado.py" in caplog.text
    assert "REMOVIDO" in caplog.text


def test_remocao_recusada_e_registrada_como_warning(caplog):
    state = {"task_id": "TASK-004", CHAVE_ARQUIVOS_HERDADOS: ["app/legado.py"]}
    recusa = {"sucesso": False, "codigo": "DIRETORIO_NAO_VAZIO", "caminho": "app"}

    with caplog.at_level(
        "WARNING", logger="src.agents.workflow_coding_review.coder.workspace_guard"
    ):
        assert _auditar(state, "app", recusa) is None

    assert "RECUSADA" in caplog.text
    assert "DIRETORIO_NAO_VAZIO" in caplog.text
    assert state[CHAVE_ARQUIVOS_HERDADOS] == ["app/legado.py"], "recusa não mexe na baseline"


def test_remocao_explicita_libera_o_arquivo_herdado_na_baseline():
    """Remover é ato consciente: o caminho deixa de ser 'herdado' e pode voltar."""
    state = {"task_id": "TASK-004", CHAVE_ARQUIVOS_HERDADOS: ["PLAN.md", "app/legado.py"]}

    _auditar(state, "app/legado.py", _remocao_ok("app/legado.py"))

    assert state[CHAVE_ARQUIVOS_HERDADOS] == ["PLAN.md"]
    assert _chamar(state, "app/legado.py") is None, "recriar após remover é permitido"
    assert _chamar(state, "PLAN.md")["codigo"] == "SOBRESCRITA_INTER_TASK_BLOQUEADA"


def test_remocao_de_pasta_tira_da_baseline_o_que_estava_sob_ela():
    state = {
        "task_id": "TASK-004",
        CHAVE_ARQUIVOS_HERDADOS: ["app/legado/a.py", "app/legado/b.py", "app/main.py"],
    }

    _auditar(state, "app/legado", _remocao_ok("app/legado", tipo="diretorio"))

    assert state[CHAVE_ARQUIVOS_HERDADOS] == ["app/main.py"]


def test_auditoria_ignora_outras_tools():
    state = {"task_id": "TASK-004", CHAVE_ARQUIVOS_HERDADOS: ["app/legado.py"]}

    resultado = _auditar(
        state, "app/legado.py", _remocao_ok("app/legado.py"), tool_name="tool_criar_arquivo"
    )

    assert resultado is None
    assert state[CHAVE_ARQUIVOS_HERDADOS] == ["app/legado.py"]


def test_auditoria_sem_baseline_nao_quebra():
    """Coder fora do TaskIterator: sem fotografia, só audita."""
    state = {}

    assert _auditar(state, "app/legado.py", _remocao_ok("app/legado.py")) is None
    assert CHAVE_ARQUIVOS_HERDADOS not in state


def test_auditoria_com_resposta_inesperada_nao_quebra():
    state = {"task_id": "TASK-004", CHAVE_ARQUIVOS_HERDADOS: ["app/legado.py"]}

    assert _auditar(state, "app/legado.py", "resposta em texto") is None
    assert state[CHAVE_ARQUIVOS_HERDADOS] == ["app/legado.py"]


def test_coder_agent_expoe_a_tool_de_remocao_bindada_e_auditada(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    import importlib
    import inspect

    coder_agent = importlib.import_module(
        "src.agents.workflow_coding_review.coder.agent"
    )
    importlib.reload(coder_agent)

    assert coder_agent.agent.after_tool_callback is coder_agent.auditar_remocao

    remover = [t for t in coder_agent.agent.tools if t.name == "tool_remover_arquivo"]
    assert len(remover) == 1, "a tool de remoção precisa estar registrada uma vez"
    assert "base_dir" not in inspect.signature(remover[0].func).parameters, (
        "base_dir tem que ficar invisível ao LLM — senão o modelo sobrescreve o binding"
    )
