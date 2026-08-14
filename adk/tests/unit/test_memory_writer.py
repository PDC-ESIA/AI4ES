"""Testes do `cr_memory_writer` e da injeção no prompt do coder.

Cobre o ciclo completo do ponto de vista do pipeline: o passo lê o veredito e o
`ExecutionReport` do estado, destila (LLM stubado), julga, grava — e a run
seguinte recebe aquilo no prompt.

O invariante mais importante aqui não é o caminho feliz: é que **nada disso
pode derrubar o pipeline**. A memória é acessório do prompt; uma run que
produziu código bom não pode ser marcada como falha porque a destilação não
respondeu.
"""

import importlib
import json
from types import SimpleNamespace

import pytest

from shared.memory.schemas import (
    MemoryItem,
    MemoryOutcome,
    MemoryProvenance,
    MemoryStatus,
)
from shared.memory.store import MemoryStore
from shared.workspace import get_agent_workspace

# Nos dois pacotes o `__init__.py` faz `from .agent import agent`, o que rebinda
# o nome `agent` para a INSTÂNCIA e sombreia o submódulo homônimo. Por isso os
# módulos vêm do importlib — um `from ... import agent` devolveria o agente.
memory_writer_mod = importlib.import_module(
    "src.agents.workflow_coding_review.memory_writer.agent"
)
coder_mod = importlib.import_module("src.agents.workflow_coding_review.coder.agent")

REPORT = {
    "work_item_id": "TASK-001",
    "iteration": 3,
    "overall_status": "falha",
    "stages": [
        {"stage": "preparacao_ambiente", "status": "sucesso", "error_code": None},
        {
            "stage": "implantacao_artefato",
            "status": "falha",
            "error_code": "FALHA_BUILD",
            "summary": "Build falhou.",
            "evidence": {"build_logs_tail": "pip: not found"},
        },
    ],
}

VALIDATION = {
    "work_item_id": "TASK-001",
    "status": "reprovado",
    "blocking_reason": "Build não concluiu.",
    "criteria_verdicts": [
        {
            "criterion": "A aplicação sobe",
            "status": "nao_atendido",
            "reasoning": "Build falhou antes de subir.",
        }
    ],
}

SAIDA_LLM = """
# Memory Item 1
## Title Não assumir gerenciador de pacotes no sandbox direct
## Description O sandbox direct roda no shell da máquina, sem garantia de PATH.
## Content Comandos de build que invocam um instalador de pacotes falham quando
o binário não está no PATH do sandbox. Declare sandbox docker quando a stack
precisar instalar dependências no build.
"""


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    """Isola banco e workspace: nenhum teste toca o banco real do usuário."""
    monkeypatch.setenv("AI4ES_MEMORY_DIR", str(tmp_path / "memoria"))
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    monkeypatch.delenv("AI4ES_MEMORY_ENABLED", raising=False)

    report_path = tmp_path / "TASK-001.report.json"
    report_path.write_text(json.dumps(REPORT), encoding="utf-8")

    from shared.workspace import get_agent_workspace

    macro = get_agent_workspace("cr_context_engineer") / "_macro_context.json"
    macro.write_text(
        json.dumps({"summary": "App de ensaios", "tech_stack": "python-fastapi"}),
        encoding="utf-8",
    )

    return SimpleNamespace(report_path=report_path, tmp_path=tmp_path)


def _ctx(state):
    return SimpleNamespace(
        session=SimpleNamespace(id="sessao-1", state=state), invocation_id="inv-1"
    )


def _stub_destilacao(monkeypatch, saida=SAIDA_LLM):
    """Stub da única chamada de LLM do passo (a destilação)."""
    monkeypatch.setattr(
        "shared.memory.extract._completar", lambda si, traj, model: saida
    )


# --- caminho feliz ---------------------------------------------------------


def test_ciclo_completo_grava_item_promovido(ambiente, monkeypatch):
    _stub_destilacao(monkeypatch)
    state = {"validation": VALIDATION, "report_path": str(ambiente.report_path)}

    resumo = memory_writer_mod.agent._executar(_ctx(state))

    itens = MemoryStore().load()
    assert len(itens) == 1
    assert itens[0].status == MemoryStatus.PROMOVIDO
    assert itens[0].error_codes == ["FALHA_BUILD"]
    assert itens[0].tech_stack == "python-fastapi"
    assert itens[0].outcome == MemoryOutcome.FALHA
    assert "promovido" in resumo


def test_proveniencia_registra_a_run_e_o_report(ambiente, monkeypatch):
    _stub_destilacao(monkeypatch)
    state = {"validation": VALIDATION, "report_path": str(ambiente.report_path)}

    memory_writer_mod.agent._executar(_ctx(state))

    (item,) = MemoryStore().load()
    assert item.provenance.run_id == "sessao-1"
    assert item.provenance.task_id == "TASK-001"
    assert item.provenance.iteration == 3
    assert item.provenance.report_path == str(ambiente.report_path)


def test_a_trajetoria_enviada_ao_llm_carrega_a_evidencia_bruta(ambiente, monkeypatch):
    """O destilador precisa ver o log, não só o nome do estágio."""
    capturado = {}

    def _captura(si, trajetoria, model):
        capturado["si"] = si
        capturado["trajetoria"] = trajetoria
        return SAIDA_LLM

    monkeypatch.setattr("shared.memory.extract._completar", _captura)
    state = {"validation": VALIDATION, "report_path": str(ambiente.report_path)}

    memory_writer_mod.agent._executar(_ctx(state))

    assert "FALHA_BUILD" in capturado["trajetoria"]
    assert "pip: not found" in capturado["trajetoria"]
    assert "reprovado" in capturado["trajetoria"]
    # Run reprovada precisa usar o prompt de FALHA do ReasoningBank.
    assert "but failed" in capturado["si"]


def test_run_aprovada_usa_o_prompt_de_sucesso(ambiente, monkeypatch):
    capturado = {}

    def _captura(si, trajetoria, model):
        capturado["si"] = si
        return SAIDA_LLM

    monkeypatch.setattr("shared.memory.extract._completar", _captura)
    state = {
        "validation": {**VALIDATION, "status": "aprovado"},
        "report_path": str(ambiente.report_path),
    }

    memory_writer_mod.agent._executar(_ctx(state))

    assert "successfully resolved" in capturado["si"]


# --- kill switch e no-ops --------------------------------------------------


def test_kill_switch_nao_grava_nada(ambiente, monkeypatch):
    _stub_destilacao(monkeypatch)
    monkeypatch.setenv("AI4ES_MEMORY_ENABLED", "0")
    state = {"validation": VALIDATION, "report_path": str(ambiente.report_path)}

    resumo = memory_writer_mod.agent._executar(_ctx(state))

    assert "Desabilitada" in resumo
    assert MemoryStore().load() == []


def test_run_sem_report_nem_veredito_nao_grava(ambiente, monkeypatch):
    _stub_destilacao(monkeypatch)

    resumo = memory_writer_mod.agent._executar(_ctx({}))

    assert "Nada a aprender" in resumo
    assert MemoryStore().load() == []


# --- resiliência: nada aqui pode derrubar o pipeline ----------------------


def test_falha_do_llm_nao_derruba_o_passo(ambiente, monkeypatch):
    def _explode(si, traj, model):
        raise RuntimeError("endpoint fora do ar")

    monkeypatch.setattr("shared.memory.extract._completar", _explode)
    state = {"validation": VALIDATION, "report_path": str(ambiente.report_path)}

    resumo = memory_writer_mod.agent._executar(_ctx(state))

    assert "não produziu nenhum item" in resumo
    assert MemoryStore().load() == []


def test_saida_ininteligivel_do_llm_nao_derruba_o_passo(ambiente, monkeypatch):
    _stub_destilacao(monkeypatch, saida="Desculpe, não consegui analisar.")
    state = {"validation": VALIDATION, "report_path": str(ambiente.report_path)}

    resumo = memory_writer_mod.agent._executar(_ctx(state))

    assert "não produziu nenhum item" in resumo


def test_report_path_invalido_nao_derruba_o_passo(ambiente, monkeypatch):
    """Sem o report em disco, o veredito no estado ainda ancora a lição.

    Não há `error_code` (que só sai do ExecutionReport), mas os critérios
    reprovados do `ValidationVerdict` continuam sendo verdade de campo — é o
    segundo sinal de ancoragem. O passo termina e o pipeline segue.
    """
    _stub_destilacao(monkeypatch)
    state = {"validation": VALIDATION, "report_path": "/caminho/que/nao/existe.json"}

    resumo = memory_writer_mod.agent._executar(_ctx(state))

    assert "Falhou" not in resumo
    (item,) = MemoryStore().load()
    assert item.error_codes == []
    assert item.unmet_criteria == ["A aplicação sobe"]


# --- o outro lado do ciclo: a run seguinte recebe a memória ---------------


def test_run_seguinte_recebe_no_prompt_o_que_a_anterior_aprendeu(
    ambiente, monkeypatch
):
    """O teste que define a PoC: run A escreve, run B lê."""
    monkeypatch.setattr(
        "shared.memory.retrieve._get_embedder", lambda: None
    )  # fallback por recência, sem download
    _stub_destilacao(monkeypatch)

    # Run A: falha, destila e grava.
    state_a = {"validation": VALIDATION, "report_path": str(ambiente.report_path)}
    memory_writer_mod.agent._executar(_ctx(state_a))

    # Run B: o coder monta a instrução e recebe a lição da run A.
    instrucao = coder_mod._instruction_provider(
        SimpleNamespace(state={"tasks": "Cadastro de ensaios"})
    )

    assert "MEMÓRIA DE RUNS ANTERIORES" in instrucao
    assert "sandbox direct" in instrucao
    # A instrução base continua inteira embaixo do bloco.
    assert "# PERFIL DO AGENTE" in instrucao


def test_sem_memoria_o_coder_recebe_exatamente_o_prompt_de_develop(ambiente, monkeypatch):
    monkeypatch.setattr("shared.memory.retrieve._get_embedder", lambda: None)

    instrucao = coder_mod._instruction_provider(SimpleNamespace(state={}))

    assert instrucao == coder_mod._INSTRUCTION


def test_kill_switch_restaura_o_prompt_de_develop(ambiente, monkeypatch):
    """Braço de controle do A/B: com o switch off, o coder é o de `develop`."""
    monkeypatch.setattr("shared.memory.retrieve._get_embedder", lambda: None)
    MemoryStore().append(
        [
            MemoryItem(
                title="Lição que não deve aparecer",
                description="d",
                content="Conteúdo longo o suficiente para ser considerado válido.",
                outcome=MemoryOutcome.FALHA,
                error_codes=["FALHA_BUILD"],
                tech_stack="python-fastapi",
                status=MemoryStatus.PROMOVIDO,
                provenance=MemoryProvenance(run_id="r", report_path="/tmp/r.json"),
            )
        ]
    )
    monkeypatch.setenv("AI4ES_MEMORY_ENABLED", "0")

    instrucao = coder_mod._instruction_provider(
        SimpleNamespace(state={"tasks": "Cadastro"})
    )

    assert instrucao == coder_mod._INSTRUCTION


def test_falha_na_injecao_degrada_para_o_prompt_base(ambiente, monkeypatch):
    def _explode(*a, **k):
        raise RuntimeError("banco corrompido")

    monkeypatch.setattr(coder_mod, "recuperar", _explode)

    instrucao = coder_mod._instruction_provider(
        SimpleNamespace(state={"tasks": "Cadastro"})
    )

    assert instrucao == coder_mod._INSTRUCTION


# --- escopo: disco primeiro, estado como reserva --------------------------
#
# Regressão de um run real (13/08): o `cr_context_engineer` NARROU o TasksOutput
# como texto em vez de chamar `tool_salvar_task_cr`. O `_macro_context.json`
# nunca chegou ao disco, todo item ficou sem escopo, e os 6 itens destilados —
# corretos e bem ancorados — foram para quarentena por falta de `tech_stack`.

TASKS_NARRADO = json.dumps(
    {
        "macro_context": {
            "summary": "Aplicação web para gestão de ensaios fotográficos.",
            "product_type": "web_app",
            "tech_stack": ["Python", "FastAPI", "Jinja2", "SQLAlchemy"],
        },
        "tasks": [],
    },
    ensure_ascii=False,
)


def test_escopo_vem_do_macro_context_quando_ele_existe(ambiente):
    stack, objetivo = memory_writer_mod._tech_stack_e_objetivo({})

    assert stack == "python-fastapi"
    assert objetivo == "App de ensaios"


def test_escopo_cai_para_o_state_quando_o_context_engineer_nao_gravou(
    ambiente, monkeypatch
):
    """Sem o arquivo em disco, o contrato ainda está em state['tasks']."""
    (
        get_agent_workspace("cr_context_engineer") / "_macro_context.json"
    ).unlink()

    stack, objetivo = memory_writer_mod._tech_stack_e_objetivo(
        {"tasks": TASKS_NARRADO}
    )

    assert stack == "Python, FastAPI, Jinja2, SQLAlchemy"
    assert objetivo == "Aplicação web para gestão de ensaios fotográficos."


def test_escopo_do_state_aceita_json_cercado_em_crase(ambiente):
    (get_agent_workspace("cr_context_engineer") / "_macro_context.json").unlink()

    stack, _ = memory_writer_mod._tech_stack_e_objetivo(
        {"tasks": f"```json\n{TASKS_NARRADO}\n```"}
    )

    assert "FastAPI" in stack


@pytest.mark.parametrize(
    "state",
    [{}, {"tasks": ""}, {"tasks": "não consegui gerar"}, {"tasks": "{}"}],
    ids=["vazio", "string-vazia", "prosa", "json-sem-macro"],
)
def test_sem_nenhuma_fonte_o_escopo_fica_vazio(ambiente, state):
    """Aí a quarentena é a resposta certa, não um bug."""
    (get_agent_workspace("cr_context_engineer") / "_macro_context.json").unlink()

    assert memory_writer_mod._tech_stack_e_objetivo(state)[0] == ""


def test_item_e_promovido_com_escopo_vindo_do_state(ambiente, monkeypatch):
    """O cenário do run de 13/08, agora terminando em promoção."""
    (get_agent_workspace("cr_context_engineer") / "_macro_context.json").unlink()
    _stub_destilacao(monkeypatch)
    state = {
        "validation": VALIDATION,
        "report_path": str(ambiente.report_path),
        "tasks": TASKS_NARRADO,
    }

    memory_writer_mod.agent._executar(_ctx(state))

    (item,) = MemoryStore().load()
    assert item.status == MemoryStatus.PROMOVIDO
    assert "FastAPI" in item.tech_stack


# --- o Enum no estado vivo vs. a string no session.db ---------------------
#
# Regressão de um run real (13/08, 5 iterações, veredito final APROVADO): dentro
# da run `state['validation']['status']` é o Enum `VerdictStatus.APROVADO`, e só
# ao persistir vira `'aprovado'`. Comparar sem normalizar classificava a run
# aprovada como FALHA, escolhia o prompt errado do ReasoningBank, e o modelo
# chegou a citar `VerdictStatus.APROVADO` dentro do texto da lição.

from src.agents.implementation_validator.schemas import VerdictStatus  # noqa: E402


@pytest.mark.parametrize(
    "bruto,esperado",
    [
        (VerdictStatus.APROVADO, "aprovado"),
        (VerdictStatus.REPROVADO, "reprovado"),
        ("VerdictStatus.APROVADO", "aprovado"),
        ("aprovado", "aprovado"),
        ("  Aprovado  ", "aprovado"),
        (None, ""),
        ("", ""),
    ],
    ids=["enum-ok", "enum-nok", "repr-do-enum", "string", "com-espacos", "none", "vazio"],
)
def test_normalizar_status_aceita_as_tres_formas(bruto, esperado):
    from shared.memory import normalizar_status

    assert normalizar_status(bruto) == esperado


def test_run_aprovada_com_enum_no_estado_e_destilada_como_sucesso(
    ambiente, monkeypatch
):
    """O cenário exato do run de 13/08."""
    capturado = {}

    def _captura(si, trajetoria, model):
        capturado["si"] = si
        capturado["trajetoria"] = trajetoria
        return SAIDA_LLM

    monkeypatch.setattr("shared.memory.extract._completar", _captura)
    state = {
        # Enum, como o estado VIVO da sessão entrega — não a string do banco.
        "validation": {**VALIDATION, "status": VerdictStatus.APROVADO},
        "report_path": str(ambiente.report_path),
    }

    memory_writer_mod.agent._executar(_ctx(state))

    # Prompt de SUCESSO do ReasoningBank, não o de falha.
    assert "successfully resolved" in capturado["si"]
    # E o repr do Enum não vaza para o texto que o modelo lê.
    assert "VerdictStatus" not in capturado["trajetoria"]
    assert "status: aprovado" in capturado["trajetoria"]

    (item,) = MemoryStore().load()
    assert item.outcome == MemoryOutcome.SUCESSO


def test_contra_evidencia_funciona_com_o_enum(ambiente):
    """O judge também precisa normalizar, ou a checagem do GovMem passa batido."""
    from shared.memory import julgar
    from shared.memory.schemas import MemoryItem as MI

    item = MI(
        title="Lição de sucesso indevida",
        description="d",
        content="Conteúdo longo o bastante para passar do piso de caracteres do juiz.",
        outcome=MemoryOutcome.SUCESSO,
        tech_stack="python-fastapi",
        provenance=MemoryProvenance(run_id="r", report_path="/tmp/r.json"),
    )

    julgado = julgar(item, veredito_status=VerdictStatus.REPROVADO)

    assert julgado.status == MemoryStatus.REJEITADO
    assert "contradiz a evidência" in julgado.judge_reason


# --- contagem de uso: uma vez por RUN, não por turno ----------------------
#
# Regressão do A/B de 13/08: o ADK chama o InstructionProvider a cada turno do
# LLM, e `times_retrieved` chegou a 92 numa única run — medindo chamadas de
# modelo, não runs em que a lição serviu.


def _ctx_leitura(state, invocation_id="inv-A"):
    return SimpleNamespace(state=state, invocation_id=invocation_id)


def _semear_promovido(titulo="Lição promovida"):
    MemoryStore().append(
        [
            MemoryItem(
                title=titulo,
                description="d",
                content="Conteúdo longo o suficiente para o juiz considerar válido.",
                outcome=MemoryOutcome.FALHA,
                error_codes=["FALHA_BUILD"],
                tech_stack="python-fastapi",
                status=MemoryStatus.PROMOVIDO,
                provenance=MemoryProvenance(run_id="r", report_path="/tmp/r.json"),
            )
        ]
    )


def test_varios_turnos_da_mesma_run_contam_uma_vez(ambiente, monkeypatch):
    monkeypatch.setattr("shared.memory.retrieve._get_embedder", lambda: None)
    coder_mod._invocacoes_contabilizadas.clear()
    _semear_promovido()
    ctx = _ctx_leitura({"tasks": "Cadastro"}, invocation_id="inv-1")

    for _ in range(5):  # 5 turnos do coder dentro da MESMA invocação
        instrucao = coder_mod._instruction_provider(ctx)

    assert "MEMÓRIA DE RUNS ANTERIORES" in instrucao  # injeta em TODOS os turnos
    assert MemoryStore().load()[0].times_retrieved == 1  # mas conta uma vez


def test_runs_diferentes_contam_separado(ambiente, monkeypatch):
    monkeypatch.setattr("shared.memory.retrieve._get_embedder", lambda: None)
    coder_mod._invocacoes_contabilizadas.clear()
    _semear_promovido()

    coder_mod._instruction_provider(_ctx_leitura({"tasks": "Cadastro"}, invocation_id="inv-1"))
    coder_mod._instruction_provider(_ctx_leitura({"tasks": "Cadastro"}, invocation_id="inv-2"))

    assert MemoryStore().load()[0].times_retrieved == 2


def test_sem_invocation_id_conta_normalmente(ambiente, monkeypatch):
    """Degradação segura: sem chave de dedup, o comportamento antigo vale."""
    monkeypatch.setattr("shared.memory.retrieve._get_embedder", lambda: None)
    coder_mod._invocacoes_contabilizadas.clear()
    _semear_promovido()

    coder_mod._instruction_provider(SimpleNamespace(state={"tasks": "Cadastro"}))
    coder_mod._instruction_provider(SimpleNamespace(state={"tasks": "Cadastro"}))

    assert MemoryStore().load()[0].times_retrieved == 2


def test_lista_de_invocacoes_nao_cresce_sem_limite(ambiente, monkeypatch):
    monkeypatch.setattr("shared.memory.retrieve._get_embedder", lambda: None)
    coder_mod._invocacoes_contabilizadas.clear()
    _semear_promovido()

    for n in range(coder_mod._MAX_INVOCACOES_LEMBRADAS + 50):
        coder_mod._instruction_provider(_ctx_leitura({"tasks": "Cadastro"}, invocation_id=f"inv-{n}"))

    assert (
        len(coder_mod._invocacoes_contabilizadas)
        == coder_mod._MAX_INVOCACOES_LEMBRADAS
    )


# --- registro no pipeline --------------------------------------------------


def test_memory_writer_e_o_ultimo_passo_do_pipeline():
    from src.agents.workflow_coding_review.agent import agent as pipeline

    nomes = [sa.name for sa in pipeline.sub_agents]

    assert nomes == [
        "cr_context_engineer",
        "code_execute_loop",
        "cr_review_analyzer",
        "cr_memory_writer",
    ]
