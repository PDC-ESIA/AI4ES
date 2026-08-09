"""Testes para o cr_context_engineer do workflow_coding_review.

Foco no fix do GAP-00 (schema + tools mutuamente exclusivos no ADK):
- O agente roda SEM output_schema, com output_key="tasks_raw" e tools.
- O after_agent_callback `_persistir_tasks_output` reconstrói o TasksOutput
  validado em state["tasks"] de forma determinística:
  * tasks: fonte autoritativa é o disco (coder/tasks/TASK-*.json);
  * macro_context: extraído do JSON emitido pelo LLM (com fallback degradado);
  * texto do LLM em prosa/JSON inválido → estrutura de melhor esforço.
"""

import json
from pathlib import Path


def _reload_cr_context_engineer():
    import importlib
    from src.agents.workflow_coding_review.context_engineer import agent as cr_context_engineer
    importlib.reload(cr_context_engineer)
    return cr_context_engineer


def _task_valida(task_id: str = "TASK-001", delivery_mode: str = "command") -> dict:
    return {
        "id": task_id,
        "type": "backend",
        "complexity": "low",
        "delivery_mode": delivery_mode,
        "description": "Implementar função de benchmark",
        "business_rules": [],
        "acceptance_criteria": ["Retornar o tempo médio em ms"],
        "contract": {"inputs": [], "outputs": ["bench.py"], "interfaces": []},
        "requirement_id": "RF-001",
        "design_refs": [],
    }


def _macro_valido(tech_stack=None) -> dict:
    return {
        "summary": "Suite de benchmark",
        "tech_stack": tech_stack or ["Rust"],
        "global_rules": ["Seguir padrões do projeto"],
    }


class _FakeCtx:
    def __init__(self, state):
        self.state = state


# ---------------------------------------------------------------------------
# Configuração do agente
# ---------------------------------------------------------------------------

def test_agente_sem_output_schema(tmp_path, monkeypatch):
    """GAP-00: o agente NÃO pode ter output_schema (quebra function calling)."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    ce = _reload_cr_context_engineer()
    assert ce.agent.output_schema is None


def test_agente_output_key_e_raw(tmp_path, monkeypatch):
    """O texto bruto do LLM cai em state['tasks_raw'], não em state['tasks']."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    ce = _reload_cr_context_engineer()
    assert ce.agent.output_key == "tasks_raw"


def test_agente_mantem_tools(tmp_path, monkeypatch):
    """As tools continuam disponíveis (o motivo de não usar output_schema)."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    ce = _reload_cr_context_engineer()
    nomes = {getattr(getattr(t, "func", t), "__name__", "") for t in ce.agent.tools}
    assert {
        "tool_salvar_task_cr",
        "tool_ler_requirements",
        "tool_ler_design",
        "tool_gerar_doubt_artifact",
    } <= nomes


def test_after_agent_callback_configurado(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    ce = _reload_cr_context_engineer()
    assert ce.agent.after_agent_callback is ce._persistir_tasks_output


# ---------------------------------------------------------------------------
# _extrair_json_obj
# ---------------------------------------------------------------------------

def test_extrair_json_puro(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    ce = _reload_cr_context_engineer()
    assert ce._extrair_json_obj('{"a": 1}') == {"a": 1}


def test_extrair_json_com_cerca_e_prosa(tmp_path, monkeypatch):
    """Tolera markdown e prosa ao redor do JSON."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    ce = _reload_cr_context_engineer()
    texto = 'Aqui está:\n```json\n{"a": 1, "b": [2, 3]}\n```\nFim.'
    assert ce._extrair_json_obj(texto) == {"a": 1, "b": [2, 3]}


def test_extrair_json_prosa_pura_retorna_none(tmp_path, monkeypatch):
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    ce = _reload_cr_context_engineer()
    assert ce._extrair_json_obj("Vou iniciar a leitura dos artefatos.") is None
    assert ce._extrair_json_obj("") is None


# ---------------------------------------------------------------------------
# _persistir_tasks_output
# ---------------------------------------------------------------------------

def test_callback_json_valido_do_llm(tmp_path, monkeypatch):
    """LLM emite TasksOutput válido e não há disco → usa o JSON do LLM."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    ce = _reload_cr_context_engineer()

    payload = {"macro_context": _macro_valido(), "tasks": [_task_valida()]}
    ctx = _FakeCtx({"tasks_raw": json.dumps(payload)})
    ce._persistir_tasks_output(ctx)

    out = ctx.state["tasks"]
    assert out["macro_context"]["tech_stack"] == ["Rust"]
    assert len(out["tasks"]) == 1
    assert out["tasks"][0]["id"] == "TASK-001"
    assert out["tasks"][0]["delivery_mode"] == "command"


def test_callback_disco_e_autoritativo(tmp_path, monkeypatch):
    """Tasks do disco prevalecem sobre as ecoadas no texto do LLM."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    ce = _reload_cr_context_engineer()

    # Disco: duas tasks persistidas pela tool
    pasta = ce.get_agent_workspace("cr_context_engineer")
    for tid in ("TASK-001", "TASK-002"):
        (pasta / f"{tid}.json").write_text(
            json.dumps(_task_valida(tid)), encoding="utf-8"
        )

    # LLM ecoou só UMA task (divergente) — o disco deve ganhar
    payload = {"macro_context": _macro_valido(), "tasks": [_task_valida("TASK-999")]}
    ctx = _FakeCtx({"tasks_raw": json.dumps(payload)})
    ce._persistir_tasks_output(ctx)

    ids = {t["id"] for t in ctx.state["tasks"]["tasks"]}
    assert ids == {"TASK-001", "TASK-002"}
    # macro_context ainda vem do LLM (não existe no disco)
    assert ctx.state["tasks"]["macro_context"]["tech_stack"] == ["Rust"]


def test_callback_prosa_pura_gera_estrutura_degradada(tmp_path, monkeypatch):
    """LLM devolveu prosa (bug original) e sem disco → best-effort degradado."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    ce = _reload_cr_context_engineer()

    ctx = _FakeCtx({"tasks_raw": "Vou iniciar a leitura dos artefatos."})
    ce._persistir_tasks_output(ctx)

    out = ctx.state["tasks"]
    assert out["macro_context"]["tech_stack"] == ["a definir"]
    assert out["tasks"] == []


def test_callback_prosa_com_disco_recupera_tasks(tmp_path, monkeypatch):
    """Mesmo com prosa do LLM, as tasks persistidas no disco são recuperadas."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    ce = _reload_cr_context_engineer()

    pasta = ce.get_agent_workspace("cr_context_engineer")
    (pasta / "TASK-001.json").write_text(
        json.dumps(_task_valida("TASK-001")), encoding="utf-8"
    )

    ctx = _FakeCtx({"tasks_raw": "Prosa sem JSON."})
    ce._persistir_tasks_output(ctx)

    out = ctx.state["tasks"]
    assert [t["id"] for t in out["tasks"]] == ["TASK-001"]
    assert out["macro_context"]["tech_stack"] == ["a definir"]


def test_callback_task_invalida_no_disco_usa_melhor_esforco(tmp_path, monkeypatch):
    """Task do disco sem campos obrigatórios → grava melhor esforço sem crashar."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    ce = _reload_cr_context_engineer()

    pasta = ce.get_agent_workspace("cr_context_engineer")
    (pasta / "TASK-001.json").write_text(
        json.dumps({"id": "TASK-001"}), encoding="utf-8"  # faltam campos
    )

    ctx = _FakeCtx({"tasks_raw": json.dumps({"macro_context": _macro_valido()})})
    ce._persistir_tasks_output(ctx)

    # Não valida como TasksOutput → estrutura de melhor esforço, sem exceção
    out = ctx.state["tasks"]
    assert out["tasks"] == [{"id": "TASK-001"}]
    assert out["macro_context"]["tech_stack"] == ["Rust"]


def test_callback_ignora_arquivo_ilegivel_no_disco(tmp_path, monkeypatch):
    """JSON corrompido no disco é ignorado (não derruba o callback)."""
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws"))
    ce = _reload_cr_context_engineer()

    pasta = ce.get_agent_workspace("cr_context_engineer")
    (pasta / "TASK-001.json").write_text("{corrompido", encoding="utf-8")
    (pasta / "TASK-002.json").write_text(
        json.dumps(_task_valida("TASK-002")), encoding="utf-8"
    )

    ctx = _FakeCtx({"tasks_raw": json.dumps({"macro_context": _macro_valido()})})
    ce._persistir_tasks_output(ctx)

    ids = [t["id"] for t in ctx.state["tasks"]["tasks"]]
    assert ids == ["TASK-002"]
