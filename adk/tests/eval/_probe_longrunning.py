"""Diagnóstico avulso: o `aguardar_resolucao_bloqueio` é chamado, e o eval o vê?

A avaliação de `ce_protocolo_bloqueio` mostrou, em 4 de 4 execuções, a sequência
parando em `tool_emitir_manifesto_bloqueado`. Há duas explicações possíveis e elas
levam a conclusões opostas:

  (a) o agente realmente não chama a terceira tool  → defeito do pipeline;
  (b) o `AgentEvaluator` não captura a chamada de um `LongRunningFunctionTool`
      → limitação da ferramenta de avaliação, e o gate estaria dando falso positivo.

Este script roda o agente por um `Runner` cru, sem passar pelo eval, e imprime TODOS
os `function_call` de TODOS os eventos, mais `long_running_tool_ids`. Isso separa (a)
de (b).

Uso (de adk/):
    AI4ES_EVAL_WORKSPACE=... uv run python tests/eval/_probe_longrunning.py

Arquivo temporário de investigação — apagar depois de registrar o resultado.
"""

import asyncio
import os
from pathlib import Path

_AQUI = Path(__file__).resolve().parent
os.environ.setdefault("WORKSPACE_OUTPUT_DIR", str(_AQUI / "workspace_output"))

import app.main  # noqa: E402,F401  -- ordem fiel ao uvicorn

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

TEXTO = (
    "Gere as tasks de codificacao a partir dos manifestos abaixo.\n\n"
    "## phase: requirements (status: blocked)\n"
    "summary: A elicitacao foi interrompida: o cliente nao confirmou as regras de "
    "emprestimo, e os RFs de reserva ficaram sem criterio de aceite verificavel.\n"
    "artifacts:\n"
    "  - tipo=HU id=HU-001 path=requirements/HUs/HU-001.md\n"
    "doubts:\n"
    "  - id=D-001 severidade=alta bloqueante=True path=requirements/doubts/D-001.md\n"
)


async def main() -> None:
    from src.agents.workflow_coding_review import agent as pipeline

    agente = pipeline.agent.find_agent("cr_context_engineer")
    runner = InMemoryRunner(agent=agente, app_name="probe_longrunning")
    sessao = await runner.session_service.create_session(
        app_name="probe_longrunning", user_id="probe"
    )

    chamadas: list[str] = []
    long_running: list[str] = []

    async for evento in runner.run_async(
        user_id="probe",
        session_id=sessao.id,
        new_message=types.Content(role="user", parts=[types.Part(text=TEXTO)]),
    ):
        if evento.long_running_tool_ids:
            long_running.extend(evento.long_running_tool_ids)
        for parte in (evento.content.parts if evento.content else []) or []:
            if parte.function_call:
                chamadas.append(parte.function_call.name)
            if parte.function_response:
                chamadas.append(f"  <- resposta de {parte.function_response.name}")

    print("\n" + "=" * 74)
    print("PROBE — Runner cru, sem AgentEvaluator")
    print("=" * 74)
    for c in chamadas:
        print(" ", c)
    print("-" * 74)
    print("long_running_tool_ids observados:", long_running or "(nenhum)")
    chamou = any("aguardar_resolucao_bloqueio" in c for c in chamadas)
    print("chamou aguardar_resolucao_bloqueio:", chamou)
    print("=" * 74)
    if chamou:
        print("=> Hipotese (b): o agente CHAMA, e o AgentEvaluator nao capturou.")
    else:
        print("=> Hipotese (a): o agente NAO CHAMA a terceira tool do protocolo.")
    await runner.close()


asyncio.run(main())
