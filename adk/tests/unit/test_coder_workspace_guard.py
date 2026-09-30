"""Regressões da proteção contra sobrescrita cega entre tasks do coder."""

from __future__ import annotations

import pytest

from src.agents.workflow_coding_review.coder.workspace_guard import (
    CHAVE_ARQUIVOS_HERDADOS,
    _MAX_ARQUIVOS_NO_AVISO,
    anunciar_arquivos_herdados,
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


@pytest.mark.parametrize(
    "caminho",
    [
        "coder/tasks/TASK-006.json",
        "coder/src/app/main.py",
        "coder/execution/TASK-001.report.json",
        "coder/review/parecer.md",
    ],
)
def test_prefixo_global_coder_e_bloqueado_mesmo_na_primeira_task(caminho):
    resposta = _chamar({CHAVE_ARQUIVOS_HERDADOS: []}, caminho)

    assert resposta["codigo"] == "PREFIXO_DE_WORKSPACE_PROIBIDO"
    assert "coder/src" in resposta["erro"]
    assert "somente leitura" in resposta["erro"]


@pytest.mark.parametrize(
    "caminho", ["coder/parser.py", "coder/__init__.py", "coder", "app/coder/src.py"]
)
def test_pacote_do_projeto_chamado_coder_nao_e_colateral(caminho):
    """O erro é de ESCOPO, não de nome: só o layout compartilhado é bloqueado.

    `coder/src`, `coder/tasks` e irmãs endereçam o workspace compartilhado; um
    módulo `coder/parser.py` do próprio projeto é código legítimo e não pode ser
    recusado por coincidência de nome.
    """
    assert _chamar({CHAVE_ARQUIVOS_HERDADOS: []}, caminho) is None


def test_subpastas_compartilhadas_vem_do_mapa_oficial_de_agentes():
    """Derivadas de AGENT_DIRS para não divergirem quando uma irmã for criada."""
    from src.agents.workflow_coding_review.coder.workspace_guard import (
        SUBPASTAS_COMPARTILHADAS,
    )

    assert {"src", "tasks", "execution", "review", "validation"} <= (
        SUBPASTAS_COMPARTILHADAS
    )


def test_task_posterior_bloqueia_arquivo_herdado_com_mensagem_acionavel():
    state = {CHAVE_ARQUIVOS_HERDADOS: ["PLAN.md", "src/app.py"]}

    resposta = _chamar(state, "src/app.py")

    assert resposta is not None
    assert resposta["sucesso"] is False
    assert resposta["codigo"] == "SOBRESCRITA_INTER_TASK_BLOQUEADA"
    assert "tool_ler_arquivo" in resposta["erro"]
    assert "tool_substituir_trecho" in resposta["erro"]


def test_run_json_herdado_pode_ser_reescrito_pela_task_atual():
    """O manifesto é POR TASK: bloqueá-lo zeraria a cobertura de aceite.

    Desde que `acceptance_task_id` namespaceia o mapa teste↔critério, um
    `run.json` da task anterior é stale por construção e o harness descarta
    todos os vínculos. Se o guard impedisse a regravação, toda task a partir da
    2ª ficaria com cobertura zero — sem que o coder tivesse como consertar.
    """
    state = {CHAVE_ARQUIVOS_HERDADOS: ["PLAN.md", "run.json", "src/app.py"]}

    assert _chamar(state, "run.json") is None
    assert _chamar(state, "./run.json") is None
    # A exceção é só do manifesto; o resto da baseline segue protegido.
    assert _chamar(state, "PLAN.md")["codigo"] == "SOBRESCRITA_INTER_TASK_BLOQUEADA"


def test_run_json_e_regravavel_mesmo_com_baseline_invalida():
    """Nada do estado da fotografia pode impedir a entrega do manifesto."""
    assert _chamar({CHAVE_ARQUIVOS_HERDADOS: "corrompida"}, "run.json") is None


def test_run_json_sob_subpasta_nao_e_a_excecao():
    """A exceção é o manifesto na raiz — não qualquer arquivo com esse nome."""
    state = {CHAVE_ARQUIVOS_HERDADOS: ["fixtures/run.json"]}

    assert _chamar(state, "fixtures/run.json")["codigo"] == (
        "SOBRESCRITA_INTER_TASK_BLOQUEADA"
    )


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
    assert coder_agent.anunciar_arquivos_herdados in coder_agent.agent.after_tool_callback
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

    assert coder_agent.auditar_remocao in coder_agent.agent.after_tool_callback

    remover = [t for t in coder_agent.agent.tools if t.name == "tool_remover_arquivo"]
    assert len(remover) == 1, "a tool de remoção precisa estar registrada uma vez"
    assert "base_dir" not in inspect.signature(remover[0].func).parameters, (
        "base_dir tem que ficar invisível ao LLM — senão o modelo sobrescreve o binding"
    )


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
    # E precisa abrir a exceção do manifesto, senão o coder não regrava o
    # `acceptance_task_id` e perde a cobertura de aceite da task.
    excecao = resposta["excecao_run_json"]
    assert "run.json" in excecao
    assert "acceptance_task_id" in excecao


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


def test_gate_abre_a_excecao_do_manifesto_por_task():
    """O gate prevalece sobre as demais seções: a exceção precisa estar NELE.

    Sem isso, "nunca `tool_criar_arquivo` em arquivo existente" leria como
    proibição de regravar o `run.json` — e o manifesto stale da task anterior
    faria o harness descartar todos os vínculos de aceite.
    """
    from src.agents.workflow_coding_review.coder import prompt

    instrucao = prompt.build_instruction("/ws")
    abertura = instrucao[: instrucao.index("# PERFIL DO AGENTE")]

    assert 'tool_criar_arquivo("run.json"' in abertura
    assert "acceptance_task_id" in abertura


def test_gate_preserva_o_placeholder_de_estado_do_adk():
    """`{execution_result?}` precisa chegar literal para o ADK resolver em runtime.

    O gate não passa por `.format()` justamente por isso; se alguém o incluir na
    formatação, o placeholder vira `KeyError` ou some — e o coder perde o único
    dado que distingue os dois modos.
    """
    from src.agents.workflow_coding_review.coder import prompt

    assert "{execution_result?}" in prompt.build_instruction("/ws")


def test_exemplos_de_run_json_instalam_em_virtualenv():
    """Regressão de execução real: `pip install` solto reprova todo build Python.

    O harness roda os comandos num host com Python gerenciado pelo sistema
    (PEP 668). Numa run do "fotógrafo", a TASK-001 gerou
    `"build": ["pip install -r requirements.txt"]` — exatamente o exemplo que o
    prompt ensinava — e morreu em FALHA_BUILD antes de executar uma linha do
    código, sem nunca ter chance de aprovar. O próprio coder achou a saída (venv)
    na task seguinte; o prompt passa a ensinar isso desde o começo.
    """
    from src.agents.workflow_coding_review.coder import prompt

    instrucao = prompt.build_instruction("/ws")

    import json
    import re

    exemplos = [
        json.loads(bloco)
        for bloco in re.findall(r"```json\n(\{.*?\})\n```", instrucao, re.S)
    ]
    assert exemplos, "os exemplos de run.json sumiram do prompt"

    for exemplo in exemplos:
        comandos = [
            *exemplo.get("build", []),
            *([exemplo["run"]] if exemplo.get("run") else []),
            *exemplo.get("test", []),
        ]
        assert any("venv" in cmd for cmd in comandos), exemplo
        for cmd in comandos:
            if "pip install" in cmd:
                assert cmd.startswith("venv/bin/pip"), f"instala fora do venv: {cmd}"
            # `activate` não sobrevive entre comandos — cada um roda no seu
            # próprio shell. Os binários têm de vir por caminho.
            assert "activate" not in cmd, f"depende de activate: {cmd}"
