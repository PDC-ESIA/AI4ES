"""Testes para o cr_reviewer do workflow_coding_review.

Cobertura:
- _discover_coder_files lista arquivos do workspace do coder
- O InstructionProvider injeta a lista de arquivos no momento da invocação
- tool_ler_arquivo está bound ao workspace do coder
- _analyzer tem after_agent_callback configurado (_persist_review)
- agent é alias direto de _analyzer (sem LlmAgent intermediário para o save)
- O callback _persist_review escreve verificacao_revisao.md no workspace do reviewer
"""

from pathlib import Path


def _summary_cobertura_completa():
    """Contrato completo publicado pelo TaskIterator para uma task aprovada."""
    return {
        "input_valid": True,
        "input_errors": [],
        "expected_task_ids": ["TASK-001"],
        "processed_task_ids": ["TASK-001"],
        "approved_task_ids": ["TASK-001"],
        "task_results": {
            "TASK-001": {
                "status": "aprovado",
                "blocking_reason": None,
                "report_path": None,
                "motivo_terminacao": "aprovado",
            }
        },
        "cobertura_completa": True,
    }


def test_discover_coder_files_workspace_vazio(tmp_path, monkeypatch):
    """Workspace sem arquivos: retorna marker '(workspace vazio)'."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    (tmp_path / "ws" / "coder").mkdir(parents=True)

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    result = cr_reviewer._discover_coder_files()
    assert "workspace vazio" in result or "nenhum arquivo" in result


def test_discover_coder_files_lista_arquivos_relativos(tmp_path, monkeypatch):
    """Workspace com arquivos: retorna bullets com paths relativos."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    coder_ws = Path(cr_reviewer._CODER_WS)
    (coder_ws / "app").mkdir(parents=True, exist_ok=True)
    (coder_ws / "app" / "main.py").write_text("# main")
    (coder_ws / "app" / "models.py").write_text("# models")
    (coder_ws / "requirements.txt").write_text("fastapi")

    result = cr_reviewer._discover_coder_files()
    assert "- app/main.py" in result
    assert "- app/models.py" in result
    assert "- requirements.txt" in result


def test_discover_coder_files_ignora_pycache(tmp_path, monkeypatch):
    """__pycache__ e seus arquivos não aparecem na lista."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    coder_ws = Path(cr_reviewer._CODER_WS)
    (coder_ws / "app" / "__pycache__").mkdir(parents=True, exist_ok=True)
    (coder_ws / "app" / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"x")
    (coder_ws / "app" / "main.py").write_text("# main")

    result = cr_reviewer._discover_coder_files()
    assert "main.py" in result
    assert "__pycache__" not in result
    assert ".pyc" not in result


def test_review_analyzer_instruction_provider_inclui_arquivos_descobertos(
    tmp_path, monkeypatch
):
    """O instruction provider do _analyzer chama _discover_coder_files e injeta no template."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    coder_ws = Path(cr_reviewer._CODER_WS)
    coder_ws.mkdir(parents=True, exist_ok=True)
    (coder_ws / "app").mkdir(exist_ok=True)
    (coder_ws / "app" / "main.py").write_text("# main")

    instr = cr_reviewer._analyzer.instruction
    if callable(instr):

        class _FakeCtx:
            pass

        rendered = instr(_FakeCtx())
        if hasattr(rendered, "__await__"):
            import asyncio

            rendered = asyncio.get_event_loop().run_until_complete(rendered)
    else:
        rendered = instr

    assert "- app/main.py" in rendered


def test_review_analyzer_tool_ler_arquivo_esta_bound_ao_coder_ws(tmp_path, monkeypatch):
    """tool_ler_arquivo do analyzer resolve paths relativos contra _CODER_WS."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    coder_ws = Path(cr_reviewer._CODER_WS)
    coder_ws.mkdir(parents=True, exist_ok=True)
    target_file = coder_ws / "test_file.py"
    target_file.write_text("CONTEUDO_ESPERADO")

    tools = cr_reviewer._analyzer.tools
    ler_tool = next(t for t in tools if "ler_arquivo" in t.func.__name__)
    result = ler_tool.func(caminho="test_file.py")
    assert isinstance(result, str)
    assert "CONTEUDO_ESPERADO" in result
    assert not result.startswith("Erro:")


def test_analyzer_tem_after_agent_callback(tmp_path, monkeypatch):
    """_analyzer.after_agent_callback inclui _persist_review.

    Desde o PoC de memória (mem0), o callback é uma lista — ADK roda cada
    item em ordem (google/adk/agents/base_agent.py::_handle_after_agent_callback)
    — e _persist_review continua sendo o primeiro, responsável pela
    persistência do relatório em disco.
    """
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    callbacks = cr_reviewer._analyzer.after_agent_callback
    assert isinstance(callbacks, list)
    assert callbacks[0] is cr_reviewer._persist_review


def test_agent_e_alias_do_analyzer(tmp_path, monkeypatch):
    """agent é alias direto de _analyzer — sem LlmAgent intermediário para o save."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    assert cr_reviewer.agent is cr_reviewer._analyzer


def test_persist_review_cria_arquivo_no_review_ws(tmp_path, monkeypatch):
    """_persist_review escreve verificacao_revisao.md no workspace do reviewer.

    Com cobertura de tasks comprovada — sem isso o gate determinístico bloquearia
    a análise (fail-closed) e o conteúdo persistido não seria o do LLM.
    """
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    review_ws = Path(cr_reviewer._REVIEW_WS)
    review_ws.mkdir(parents=True, exist_ok=True)

    class _FakeCallbackContext:
        state = {
            "review_analysis": "## Status: APROVADO\n\n## Resumo\nTudo ok.",
            "task_iteration_summary": _summary_cobertura_completa(),
        }

    cr_reviewer._persist_review(_FakeCallbackContext())

    relatorio = review_ws / "verificacao_revisao.md"
    assert relatorio.exists(), "Relatório não foi criado no workspace do reviewer"
    content = relatorio.read_text(encoding="utf-8")
    assert "APROVADO" in content


def test_persist_review_nao_cria_arquivo_se_analysis_vazia(tmp_path, monkeypatch):
    """_persist_review não cria arquivo quando review_analysis está ausente ou só whitespace.

    Cenário com cobertura comprovada: é o único em que a ausência de análise
    resulta em retorno cedo silencioso. Sem cobertura, o gate sintetiza um
    relatório de bloqueio — comportamento coberto pelos testes do gate.
    """
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    review_ws = Path(cr_reviewer._REVIEW_WS)
    review_ws.mkdir(parents=True, exist_ok=True)

    relatorio = review_ws / "verificacao_revisao.md"

    cobertura_ok = _summary_cobertura_completa()
    for state in [
        {},  # key ausente
        {"review_analysis": None},  # None explícito
        {"review_analysis": "   \n"},  # só whitespace
    ]:
        state["task_iteration_summary"] = cobertura_ok
        class _FakeCtx:
            pass

        _FakeCtx.state = state
        cr_reviewer._persist_review(_FakeCtx())
        assert not relatorio.exists(), f"Não deveria criar arquivo para state={state}"


def test_analyzer_tem_before_agent_callback(tmp_path, monkeypatch):
    """_analyzer.before_agent_callback está configurado com _inject_static_findings."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    assert (
        cr_reviewer._analyzer.before_agent_callback
        is cr_reviewer._inject_static_findings
    )


def test_inject_static_findings_popula_state(tmp_path, monkeypatch):
    """_inject_static_findings injeta static_findings_block no state do callback."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    monkeypatch.setenv("REVIEWER_STATIC_ANALYSIS", "1")

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    coder_ws = tmp_path / "ws" / "coder" / "src"
    coder_ws.mkdir(parents=True, exist_ok=True)
    (coder_ws / "app.py").write_text("import os\n")

    class _FakeCtx:
        state = {}

    cr_reviewer._inject_static_findings(_FakeCtx())
    assert "static_findings_block" in _FakeCtx.state
    assert isinstance(_FakeCtx.state["static_findings_block"], str)


def test_inject_static_findings_desabilitado_nao_popula_state(tmp_path, monkeypatch):
    """Com REVIEWER_STATIC_ANALYSIS=0, o state não é modificado."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    monkeypatch.setenv("REVIEWER_STATIC_ANALYSIS", "0")

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    class _FakeCtx:
        state = {}

    cr_reviewer._inject_static_findings(_FakeCtx())
    assert "static_findings_block" not in _FakeCtx.state


def test_adk_runner_dispara_after_agent_callback(tmp_path, monkeypatch):
    """Verifica que o ADK Runner dispara after_agent_callback após _analyzer completar.

    Usa before_model_callback para bypassar a chamada real ao Gemini — o ADK
    trata a resposta fake como output do agente, salva em state via output_key,
    e então dispara after_agent_callback (_persist_review).
    """
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)

    review_ws = Path(cr_reviewer._REVIEW_WS)
    review_ws.mkdir(parents=True, exist_ok=True)

    from google.adk.models.llm_response import LlmResponse
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types as genai_types

    fake_analysis = "## Status: APROVADO\n\n## Issues\nNenhum.\n\n## Resumo\nCodigo ok."

    def _stub_llm(callback_context, llm_request):
        """Bypassa chamada real ao Gemini — retorna análise fake."""
        return LlmResponse(
            content=genai_types.Content(
                role="model",
                parts=[genai_types.Part(text=fake_analysis)],
            )
        )

    _original_cb = cr_reviewer._analyzer.before_model_callback
    cr_reviewer._analyzer.before_model_callback = _stub_llm
    try:
        session_svc = InMemorySessionService()
        # Cobertura comprovada no state inicial: sem ela, o after_agent_callback
        # (_persist_review) sobrescreveria a análise fake com o texto BLOQUEADO.
        session_svc.create_session_sync(
            app_name="test_persist",
            user_id="test_user",
            session_id="test_session",
            state={"task_iteration_summary": _summary_cobertura_completa()},
        )
        runner = Runner(
            agent=cr_reviewer._analyzer,
            app_name="test_persist",
            session_service=session_svc,
        )
        list(
            runner.run(
                user_id="test_user",
                session_id="test_session",
                new_message=genai_types.Content(
                    role="user",
                    parts=[genai_types.Part(text="revisar")],
                ),
            )
        )
    finally:
        cr_reviewer._analyzer.before_model_callback = _original_cb

    relatorio = review_ws / "verificacao_revisao.md"
    assert relatorio.exists(), (
        "after_agent_callback não foi disparado pelo ADK Runner — "
        "verificacao_revisao.md não foi criado"
    )
    assert "APROVADO" in relatorio.read_text(encoding="utf-8")


def _reload_reviewer(tmp_path, monkeypatch):
    """Helper comum aos testes abaixo — mesmo padrão de import/reload do resto do arquivo."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))

    import importlib
    from shared.tools.coding_tools import review_tools
    import src.agents.workflow_coding_review.reviewer.agent as cr_reviewer

    importlib.reload(review_tools)
    importlib.reload(cr_reviewer)
    return cr_reviewer


class TestResolverStackKey:
    """`_resolver_stack_key` — PoC de memória (mem0)."""

    def test_usa_memory_stack_key_quando_presente(self, tmp_path, monkeypatch):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        state = {"memory_stack_key": "python"}
        assert cr_reviewer._resolver_stack_key(state) == "python"

    def test_fallback_recalcula_a_partir_do_tech_stack(self, tmp_path, monkeypatch):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        state = {"tasks": {"macro_context": {"tech_stack": ["Python", "FastAPI"]}}}
        assert cr_reviewer._resolver_stack_key(state) == "python"

    def test_fallback_bate_com_stack_key_original(self, tmp_path, monkeypatch):
        """O fallback tem que gerar a MESMA chave que memory_feedforward.stack_key
        usou na leitura — senão a escrita erra o agent_id e a lição nunca é achada."""
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        tech_stack = ["FastAPI", "Python"]
        state = {"tasks": {"macro_context": {"tech_stack": tech_stack}}}
        assert cr_reviewer._resolver_stack_key(state) == cr_reviewer.stack_key(
            tech_stack
        )

    def test_state_vazio_devolve_stack_desconhecida(self, tmp_path, monkeypatch):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        assert cr_reviewer._resolver_stack_key({}) == "stack-desconhecida"


class TestEntradasBrutas:
    """`_entradas_brutas` — achata error_history em entradas por estágio."""

    def test_sem_estagios_falhos_retorna_vazio(self, tmp_path, monkeypatch):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        error_history = [{"blocking_reason": "erro genérico", "failed_stages": []}]
        assert cr_reviewer._entradas_brutas(error_history, "python") == []

    def test_uma_entrada_por_estagio_falho(self, tmp_path, monkeypatch):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        error_history = [
            {
                "work_item_id": "wi-1",
                "iteration": 2,
                "blocking_reason": "dependência ausente",
                "failed_stages": [
                    {"stage": "implantacao_artefato", "error_code": "FALHA_BUILD"}
                ],
            }
        ]
        entradas = cr_reviewer._entradas_brutas(error_history, "python")
        assert len(entradas) == 1
        entrada = entradas[0]
        assert entrada["stack_key"] == "python"
        assert entrada["work_item_id"] == "wi-1"
        assert entrada["iteration"] == 2
        assert entrada["stage"] == "implantacao_artefato"
        assert entrada["error_code"] == "FALHA_BUILD"
        assert entrada["blocking_reason"] == "dependência ausente"
        assert "created_at" in entrada

    def test_multiplos_estagios_na_mesma_iteracao_geram_multiplas_entradas(
        self, tmp_path, monkeypatch
    ):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        error_history = [
            {
                "blocking_reason": "vários problemas",
                "failed_stages": [
                    {"stage": "testes_automatizados", "error_code": "FALHA_TESTE"},
                    {"stage": "inicializacao_aplicacao", "summary": "porta ocupada"},
                ],
            }
        ]
        entradas = cr_reviewer._entradas_brutas(error_history, "python")
        assert len(entradas) == 2
        assert entradas[1]["error_code"] is None
        assert entradas[1]["summary"] == "porta ocupada"


class TestAssinaturaErro:
    """`_assinatura_erro` — identifica erro repetido entre entradas."""

    def test_mesmo_estagio_e_codigo_gera_mesma_assinatura(self, tmp_path, monkeypatch):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        a = {"stage": "testes_automatizados", "error_code": "FALHA_TESTE"}
        b = {"stage": "TESTES_AUTOMATIZADOS", "error_code": "falha_teste"}
        assert cr_reviewer._assinatura_erro(a) == cr_reviewer._assinatura_erro(b)

    def test_estagios_diferentes_geram_assinaturas_diferentes(
        self, tmp_path, monkeypatch
    ):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        a = {"stage": "testes_automatizados", "error_code": "X"}
        b = {"stage": "implantacao_artefato", "error_code": "X"}
        assert cr_reviewer._assinatura_erro(a) != cr_reviewer._assinatura_erro(b)

    def test_usa_summary_quando_nao_ha_error_code(self, tmp_path, monkeypatch):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        a = {"stage": "preparacao_ambiente", "summary": "task não encontrada"}
        b = {"stage": "preparacao_ambiente", "summary": "task não encontrada"}
        assert cr_reviewer._assinatura_erro(a) == cr_reviewer._assinatura_erro(b)


class TestFiltrarRecorrentes:
    """`_filtrar_recorrentes` — só mantém erro que se repetiu no lote."""

    def test_erro_isolado_e_descartado(self, tmp_path, monkeypatch):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        entradas = [
            {"stage": "a", "error_code": "X"},
            {"stage": "b", "error_code": "Y"},
            {"stage": "c", "error_code": "Z"},
        ]
        assert cr_reviewer._filtrar_recorrentes(entradas) == []

    def test_erro_repetido_e_mantido(self, tmp_path, monkeypatch):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        entradas = [
            {"stage": "a", "error_code": "X"},
            {"stage": "b", "error_code": "Y"},
            {"stage": "a", "error_code": "X"},
        ]
        resultado = cr_reviewer._filtrar_recorrentes(entradas)
        assert len(resultado) == 2
        assert all(cr_reviewer._assinatura_erro(e) == "a:x" for e in resultado)

    def test_lista_vazia_retorna_vazio(self, tmp_path, monkeypatch):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        assert cr_reviewer._filtrar_recorrentes([]) == []


class TestFormatarLicaoLote:
    """`_formatar_licao_lote` — texto de entrada pro mem0, a partir do lote filtrado."""

    def test_lista_vazia(self, tmp_path, monkeypatch):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        assert cr_reviewer._formatar_licao_lote([]) == ""

    def test_uma_entrada(self, tmp_path, monkeypatch):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        entradas = [
            {
                "stage": "implantacao_artefato",
                "error_code": "FALHA_BUILD",
                "blocking_reason": "dependência ausente",
            }
        ]
        resultado = cr_reviewer._formatar_licao_lote(entradas)
        assert resultado == (
            "Erro recorrente: estágio=implantacao_artefato, "
            "motivo=FALHA_BUILD, bloqueio=dependência ausente."
        )

    def test_varias_entradas_uma_por_linha(self, tmp_path, monkeypatch):
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)
        entradas = [
            {"stage": "a", "error_code": "X", "blocking_reason": "r1"},
            {"stage": "b", "error_code": "Y", "blocking_reason": "r2"},
        ]
        resultado = cr_reviewer._formatar_licao_lote(entradas)
        assert len(resultado.split("\n")) == 2


class TestEscreverMemoriaLote:
    """`_escrever_memoria` — fluxo completo de acúmulo + processamento em lote."""

    def _ctx(self, error_history, stack_key="python"):
        class _FakeCtx:
            state = {
                "error_history": error_history,
                "memory_stack_key": stack_key,
            }

        return _FakeCtx()

    def _erro(self, stage, error_code):
        return {
            "blocking_reason": "erro de teste",
            "failed_stages": [{"stage": stage, "error_code": error_code}],
        }

    async def test_abaixo_do_limite_so_acumula_nao_chama_mem0(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("AI4ES_MEMORY_ENABLED", "true")
        monkeypatch.setenv("AI4ES_MEMORY_DIR", str(tmp_path / "mem"))
        monkeypatch.setenv("AI4ES_MEMORY_BATCH_THRESHOLD", "3")
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)

        chamado = {"add": False}

        class _FakeMemory:
            async def add(self, **kwargs):
                chamado["add"] = True

        monkeypatch.setattr(cr_reviewer, "get_memory", lambda: _FakeMemory())

        ctx = self._ctx([self._erro("a", "X")])
        await cr_reviewer._escrever_memoria(ctx)

        assert chamado["add"] is False
        assert len(cr_reviewer.ler_erros_pendentes("python")) == 1

    async def test_atinge_limite_sem_repeticao_descarta_lote_sem_chamar_mem0(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("AI4ES_MEMORY_ENABLED", "true")
        monkeypatch.setenv("AI4ES_MEMORY_DIR", str(tmp_path / "mem"))
        monkeypatch.setenv("AI4ES_MEMORY_BATCH_THRESHOLD", "3")
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)

        chamado = {"add": False}

        class _FakeMemory:
            async def add(self, **kwargs):
                chamado["add"] = True

        monkeypatch.setattr(cr_reviewer, "get_memory", lambda: _FakeMemory())

        for stage, code in [("a", "X"), ("b", "Y"), ("c", "Z")]:
            await cr_reviewer._escrever_memoria(self._ctx([self._erro(stage, code)]))

        assert chamado["add"] is False
        assert cr_reviewer.ler_erros_pendentes("python") == []

    async def test_atinge_limite_com_repeticao_grava_no_mem0_e_limpa_lote(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("AI4ES_MEMORY_ENABLED", "true")
        monkeypatch.setenv("AI4ES_MEMORY_DIR", str(tmp_path / "mem"))
        monkeypatch.setenv("AI4ES_MEMORY_BATCH_THRESHOLD", "3")
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)

        recebido = {}

        class _FakeMemory:
            async def add(self, **kwargs):
                recebido.update(kwargs)

        monkeypatch.setattr(cr_reviewer, "get_memory", lambda: _FakeMemory())

        for stage, code in [("a", "X"), ("b", "Y"), ("a", "X")]:
            await cr_reviewer._escrever_memoria(self._ctx([self._erro(stage, code)]))

        assert recebido.get("agent_id") == "python"
        assert "estágio=a" in recebido.get("messages", "")
        assert cr_reviewer.ler_erros_pendentes("python") == []

    async def test_falha_no_mem0_preserva_lote_pendente(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_ENABLED", "true")
        monkeypatch.setenv("AI4ES_MEMORY_DIR", str(tmp_path / "mem"))
        monkeypatch.setenv("AI4ES_MEMORY_BATCH_THRESHOLD", "3")
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)

        class _FakeMemory:
            async def add(self, **kwargs):
                raise RuntimeError("mem0 indisponível")

        monkeypatch.setattr(cr_reviewer, "get_memory", lambda: _FakeMemory())

        for stage, code in [("a", "X"), ("b", "Y"), ("a", "X")]:
            await cr_reviewer._escrever_memoria(self._ctx([self._erro(stage, code)]))

        assert len(cr_reviewer.ler_erros_pendentes("python")) == 3

    async def test_sem_error_history_nao_grava_nada(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AI4ES_MEMORY_ENABLED", "true")
        monkeypatch.setenv("AI4ES_MEMORY_DIR", str(tmp_path / "mem"))
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)

        await cr_reviewer._escrever_memoria(self._ctx([]))

        assert cr_reviewer.ler_erros_pendentes("python") == []

    async def test_falha_inesperada_no_processamento_nao_derruba_pipeline(
        self, tmp_path, monkeypatch
    ):
        """Regressão: um bug em `limite_lote()` (ex.: env var vazia) chegou a
        derrubar a run inteira antes — agora fica contido aqui dentro."""
        monkeypatch.setenv("AI4ES_MEMORY_ENABLED", "true")
        monkeypatch.setenv("AI4ES_MEMORY_DIR", str(tmp_path / "mem"))
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)

        def _explode():
            raise ValueError("invalid literal for int() with base 10: ''")

        monkeypatch.setattr(cr_reviewer, "limite_lote", _explode)

        await cr_reviewer._escrever_memoria(self._ctx([self._erro("a", "X")]))


class TestEscreverMemoriaDesabilitada:
    """`_escrever_memoria` — interruptor geral (`AI4ES_MEMORY_ENABLED`)."""

    def _ctx(self, error_history, stack_key="python"):
        class _FakeCtx:
            state = {
                "error_history": error_history,
                "memory_stack_key": stack_key,
            }

        return _FakeCtx()

    async def test_desabilitada_nao_grava_erro_nem_chama_mem0(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.delenv("AI4ES_MEMORY_ENABLED", raising=False)
        monkeypatch.setenv("AI4ES_MEMORY_DIR", str(tmp_path / "mem"))
        monkeypatch.setenv("AI4ES_MEMORY_BATCH_THRESHOLD", "1")
        cr_reviewer = _reload_reviewer(tmp_path, monkeypatch)

        chamado = {"add": False}

        class _FakeMemory:
            async def add(self, **kwargs):
                chamado["add"] = True

        monkeypatch.setattr(cr_reviewer, "get_memory", lambda: _FakeMemory())

        erro = {
            "blocking_reason": "erro de teste",
            "failed_stages": [{"stage": "a", "error_code": "X"}],
        }
        await cr_reviewer._escrever_memoria(self._ctx([erro]))

        assert chamado["add"] is False
        assert cr_reviewer.ler_erros_pendentes("python") == []
