"""Invocação do Coder Agent real (cr_coder_agent) para gerar a solução.

Só pode ser importado APÓS `bootstrap.prepare_environment(...)`. Reutiliza do
humaneval o dataclass `CoderGeneration` e os helpers de workspace/localização;
só a persistência da task e a mensagem-contrato são específicas do BigCodeBench.
"""

from __future__ import annotations

import json

from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from benchmarks.coding_review.humaneval.coder_runner import (
    CoderGeneration,
    _coder_src_dir,
    _limpar_dir,
    _localizar_solucao,
    _tasks_dir,
)

from .contract import build_coder_message, build_task_contract
from .dataset import BigCodeBenchProblem

__all__ = ["CoderGeneration", "run_coder"]


def _persistir_task(problem: BigCodeBenchProblem) -> None:
    """Grava o `TASK-XXX.json` que o coder pode ler via `tool_ler_workspace`."""
    contrato = build_task_contract(problem)
    (_tasks_dir() / f"{contrato['id']}.json").write_text(
        json.dumps(contrato, ensure_ascii=False, indent=2), encoding="utf-8"
    )


async def run_coder(
    problem: BigCodeBenchProblem,
    model: str | None = None,
    *,
    user_id: str = "bigcodebench-bench",
) -> CoderGeneration:
    """Roda o coder para uma tarefa e devolve os artefatos gerados."""
    from src.agents.workflow_coding_review.coder.agent import agent as coder_agent

    if model:
        coder_agent.model = model

    task_id = problem.slug
    src_dir = _coder_src_dir()

    # Isolamento: cada geração parte de um diretório de código limpo.
    _limpar_dir(src_dir)
    _persistir_task(problem)

    mensagem = build_coder_message(problem)

    prompt_tokens = 0
    completion_tokens = 0
    llm_interactions = 0

    try:
        runner = Runner(
            app_name=coder_agent.name,
            agent=coder_agent,
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        session = await runner.session_service.create_session(
            app_name=coder_agent.name, user_id=user_id, state={}
        )
        content = types.Content(
            role="user", parts=[types.Part.from_text(text=mensagem)]
        )

        final_text = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.usage_metadata:
                prompt_tokens += event.usage_metadata.prompt_token_count or 0
                completion_tokens += event.usage_metadata.candidates_token_count or 0
                llm_interactions += 1
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        final_text = part.text
        await runner.close()
    except Exception as exc:  # noqa: BLE001 — falha de geração vira dado, não crash
        return CoderGeneration(
            task_id=task_id,
            solution_dir=src_dir,
            solution_file=None,
            error=f"{type(exc).__name__}: {exc}",
            llm_interactions=llm_interactions,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    solution_file = _localizar_solucao(src_dir, problem.entry_point)
    arquivos = [
        str(p.relative_to(src_dir)) for p in sorted(src_dir.rglob("*")) if p.is_file()
    ]
    return CoderGeneration(
        task_id=task_id,
        solution_dir=src_dir,
        solution_file=solution_file,
        files=arquivos,
        final_text=final_text,
        llm_interactions=llm_interactions,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
