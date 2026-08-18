"""Regressões da proteção contra sobrescrita cega entre tasks do coder."""

from __future__ import annotations

from src.agents.workflow_coding_review.coder.workspace_guard import (
    CHAVE_ARQUIVOS_HERDADOS,
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
    assert "SOMENTE QUANDO execution_result ESTIVER AUSENTE" in coder_agent.agent.instruction
