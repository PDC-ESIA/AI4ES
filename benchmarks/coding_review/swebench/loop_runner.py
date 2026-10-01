"""Execução do `code_execute_loop` (coder ↔ executor) sobre UMA instância.

Só pode ser usado DEPOIS de `bootstrap.prepare_environment(...)`: os imports do
`adk/` são tardios de propósito (o workspace e o modelo são resolvidos no import
dos agentes).

Por que rodar o loop direto, e não o `TaskIterator`: na primeira task o
iterator apaga `execution_result`, o que manda o coder para o ramo "primeira
execução" do prompt — criar `PLAN.md` e implementar o projeto COMPLETO. Diante
de um repositório existente isso não faz sentido. Rodando o loop direto, o
estado inicial reproduz exatamente o que o próprio iterator monta da 2ª task em
diante, o ramo de "projeto existente" que já roda em produção:

- `execution_result` = marcador `NOVA_TASK:` (`task_iterator.marcador_nova_task`);
- arquivos herdados registrados (`preparar_arquivos_herdados(primeira=False)`),
  o que impede o coder de sobrescrever arquivos do repositório inteiros.

Nenhuma linha de produção muda. O desfecho é classificado pela MESMA função da
produção (`task_iterator.classificar_desfecho`). O tratamento de exceção, que
no pipeline completo fica no iterator (`erro_operacional`), é replicado aqui.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contract import TASK_ID, build_coder_message, build_task_contract
from .dataset import SWEInstance

APP_NAME = "swebench_coding_review"
MOTIVO_ERRO_OPERACIONAL = "erro_operacional"
MOTIVO_TIMEOUT = "timeout_da_instancia"
# O contexto da conversa passou do limite do modelo. É resultado do loop (o
# coder lê arquivos inteiros e não tem busca), não do provedor — mas merece
# rótulo próprio em vez de um `erro_operacional` genérico.
MOTIVO_ESTOURO_CONTEXTO = "estouro_de_contexto"
_SINAIS_ESTOURO_CONTEXTO = (
    "contextwindowexceeded",
    "context_length_exceeded",
    "maximum context length",
    "context length",
    "prompt token count",
    "exceeds the limit of",
)


def is_context_overflow(erro: str | None) -> bool:
    """Se o erro da instância é o contexto da conversa estourando o limite."""
    texto = (erro or "").lower()
    return any(sinal in texto for sinal in _SINAIS_ESTOURO_CONTEXTO)


def motivo_do_erro(erro: str, *, timed_out: bool) -> str:
    """`motivo_terminacao` de uma instância que terminou em erro."""
    if timed_out:
        return MOTIVO_TIMEOUT
    if is_context_overflow(erro):
        return MOTIVO_ESTOURO_CONTEXTO
    return MOTIVO_ERRO_OPERACIONAL

# Nomes de estágio do harness (`harness_schemas.StageName`), conferidos por teste.
STAGE_PREPARACAO = "preparacao_ambiente"
STAGE_TESTES = "testes_automatizados"

# Chaves do state final guardadas no registro. O resto (ex.: a lista de
# arquivos herdados, com milhares de caminhos) é grande e não entra em métrica.
_STATE_KEYS = (
    "validation",
    "report_path",
    "loop_stop_reason",
    "progress_score_history",
    "progress_error_signature_history",
    "acceptance_score",
)
_MAX_TEXTO_FINAL = 2000


@dataclass
class LoopRun:
    """O que aconteceu dentro do loop numa instância."""

    instance_id: str
    duration_s: float
    error: str | None = None
    timed_out: bool = False
    desfecho: dict[str, Any] = field(default_factory=dict)
    veredito_validador: str | None = None
    execucao: dict[str, Any] = field(default_factory=dict)
    guarda: dict[str, Any] = field(default_factory=dict)
    uso: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    texto_final: str = ""


def json_safe(valor: Any) -> Any:
    """Converte para tipos JSON puros (enums/objetos viram texto)."""
    return json.loads(json.dumps(valor, ensure_ascii=False, default=str))


def write_task_file(tasks_dir: Path, instance: SWEInstance) -> Path:
    """Grava `TASK-001.json` onde o harness e o coder o procuram."""
    tasks_dir.mkdir(parents=True, exist_ok=True)
    caminho = tasks_dir / f"{TASK_ID}.json"
    caminho.write_text(
        json.dumps(build_task_contract(instance), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return caminho


def build_initial_state(instance: SWEInstance) -> dict[str, Any]:
    """Estado inicial da sessão: o ramo "projeto existente" do workflow."""
    from src.agents.workflow_coding_review.coder.workspace_guard import (
        preparar_arquivos_herdados,
    )
    from src.agents.workflow_coding_review.task_iterator import marcador_nova_task

    state: dict[str, Any] = {
        "task_id": TASK_ID,
        "tasks": {"tasks": [build_task_contract(instance)]},
        "execution_result": marcador_nova_task(TASK_ID),
    }
    preparar_arquivos_herdados(state, primeira=False)
    return state


def validator_verdict(state: dict[str, Any]) -> str | None:
    """Último veredito do validador para esta task, ou `None` se não houver."""
    validation = state.get("validation")
    if hasattr(validation, "model_dump"):
        validation = validation.model_dump()
    if isinstance(validation, dict) and validation.get("work_item_id") == TASK_ID:
        status = validation.get("status")
        return str(getattr(status, "value", status)) if status is not None else None
    return None


def _inteiro(valor: Any) -> int:
    if isinstance(valor, bool) or not isinstance(valor, int):
        return 0
    return max(0, valor)


def summarize_execution_report(report: Any) -> dict[str, Any]:
    """Evidências do último `ExecutionReport` que qualificam uma aprovação."""
    if not isinstance(report, dict):
        return {}
    estagios = {
        s.get("stage"): s for s in report.get("stages") or [] if isinstance(s, dict)
    }
    prep = (estagios.get(STAGE_PREPARACAO) or {}).get("evidence") or {}
    testes = estagios.get(STAGE_TESTES) or {}
    evidencia = testes.get("evidence") or {}

    passaram = falharam = erros = 0
    for resultado in evidencia.get("resultados") or []:
        resumo = resultado.get("resumo") if isinstance(resultado, dict) else None
        if isinstance(resumo, dict):
            passaram += _inteiro(resumo.get("passaram"))
            falharam += _inteiro(resumo.get("falharam"))
            erros += _inteiro(resumo.get("erros"))

    comandos = prep.get("test_commands")
    if not isinstance(comandos, list):
        comandos = evidencia.get("test_commands") or []
    return {
        "iteracao": report.get("iteration"),
        "overall_status": report.get("overall_status"),
        "test_commands": list(comandos),
        "status_testes": testes.get("status"),
        "testes_identificados": evidencia.get("testes_identificados"),
        "passaram": passaram,
        "falharam": falharam,
        "erros": erros,
    }


def _ler_report(caminho: Any) -> dict[str, Any] | None:
    if not isinstance(caminho, str):
        return None
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


async def run_loop(
    instance: SWEInstance,
    *,
    plugin,
    timeout_s: float,
    user_id: str = "swebench-bench",
) -> LoopRun:
    """Roda o loop até ele parar sozinho (ou estourar `timeout_s`).

    O teto é APROXIMADO: as tools síncronas (o harness) rodam na thread do
    event loop, então o cancelamento só acontece quando a chamada em curso
    devolve o controle — o estouro pode passar do teto pelo tempo de um build
    ou de uma bateria de testes do harness.
    """
    from google.adk.apps import App
    from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types

    from src.agents.workflow_coding_review.agent import _code_execute_loop
    from src.agents.workflow_coding_review.task_iterator import classificar_desfecho

    plugin.start_instance(instance.image)
    app = App(name=APP_NAME, root_agent=_code_execute_loop, plugins=[plugin])
    runner = Runner(
        app=app,
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=user_id, state=build_initial_state(instance)
    )
    mensagem = types.Content(
        role="user", parts=[types.Part.from_text(text=build_coder_message(instance))]
    )

    texto_final = ""

    async def _consumir() -> None:
        nonlocal texto_final
        async for event in runner.run_async(
            user_id=user_id, session_id=session.id, new_message=mensagem
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        texto_final = part.text

    erro: str | None = None
    timed_out = False
    t0 = time.monotonic()
    try:
        await asyncio.wait_for(_consumir(), timeout=timeout_s)
    except TimeoutError:
        timed_out = True
        erro = f"Instância excedeu o teto de {timeout_s:.0f}s."
    except Exception as exc:  # noqa: BLE001 — falha da instância vira dado
        erro = f"{type(exc).__name__}: {exc}"
    duracao = round(time.monotonic() - t0, 2)

    try:
        final = await runner.session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session.id
        )
        state_final = dict(final.state) if final is not None else {}
    finally:
        await runner.close()

    desfecho = classificar_desfecho(state_final, TASK_ID)
    if erro is not None:
        desfecho = {
            **desfecho,
            "status": "reprovado",
            "motivo_terminacao": motivo_do_erro(erro, timed_out=timed_out),
            "blocking_reason": erro,
        }

    return LoopRun(
        instance_id=instance.instance_id,
        duration_s=duracao,
        error=erro,
        timed_out=timed_out,
        desfecho=json_safe(desfecho),
        veredito_validador=validator_verdict(state_final),
        execucao=json_safe(
            summarize_execution_report(_ler_report(desfecho.get("report_path")))
        ),
        guarda=plugin.summary(),
        uso=plugin.usage_totals(),
        state=json_safe({k: state_final.get(k) for k in _STATE_KEYS}),
        texto_final=texto_final[-_MAX_TEXTO_FINAL:],
    )
