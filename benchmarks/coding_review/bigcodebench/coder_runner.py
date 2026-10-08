"""Invocação do Coder Agent real (cr_coder_agent) para gerar a solução.

Só pode ser importado APÓS `bootstrap.prepare_environment(...)`, porque importar
o agente resolve o workspace e faz o binding das tools no momento do import.

Cada geração:
1. limpa o diretório de código do coder (`coder/src/`) — isolamento entre tarefas;
2. grava o contrato da task em `coder/tasks/<slug>.json`;
3. roda o `cr_coder_agent` num `Runner` isolado, entregando a mensagem-contrato;
4. devolve os artefatos gerados (caminho do `solution.py`, arquivos, texto final).
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from shared.workspace import get_agent_workspace

from .contract import SOLUTION_FILENAME, build_coder_message, build_task_contract
from .dataset import BigCodeBenchProblem

__all__ = ["CoderGeneration", "run_coder"]


@dataclass
class CoderGeneration:
    """Resultado de uma geração do coder para uma tarefa."""

    task_id: str
    solution_dir: Path
    solution_file: Path | None
    files: list[str] = field(default_factory=list)
    final_text: str = ""
    error: str | None = None

    # Telemetria de execução: contagem de chamadas ao LLM e consumo de tokens,
    # agregados a partir do `usage_metadata` dos eventos. `cached_tokens` é a
    # parcela de `prompt_tokens` servida do cache do provider (cobrada mais
    # barato); `reasoning_tokens` já está contida em `completion_tokens`.
    llm_interactions: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0

    @property
    def has_solution(self) -> bool:
        return self.solution_file is not None and self.solution_file.is_file()


def _coder_src_dir() -> Path:
    """Diretório de código do coder (`coder/src/`)."""
    return get_agent_workspace("cr_coder")


def _tasks_dir() -> Path:
    """Diretório de contratos de task lido pelo coder (`coder/tasks/`)."""
    return get_agent_workspace("cr_context_engineer")


def _limpar_dir(caminho: Path) -> None:
    """Remove e recria um diretório vazio (isolamento entre execuções)."""
    if caminho.exists():
        shutil.rmtree(caminho, ignore_errors=True)
    caminho.mkdir(parents=True, exist_ok=True)


def _localizar_solucao(src_dir: Path, entry_point: str) -> Path | None:
    """Localiza o arquivo que expõe a função-alvo.

    Preferência absoluta pelo contrato do benchmark (`solution.py`). Como
    fallback resiliente, varre os `.py` do diretório procurando a definição
    `def <entry_point>`.
    """
    preferido = src_dir / SOLUTION_FILENAME
    if preferido.is_file():
        return preferido

    marcador = f"def {entry_point}"
    for arquivo in sorted(src_dir.rglob("*.py")):
        try:
            texto = arquivo.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if marcador in texto:
            return arquivo
    return None


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
    lean: bool = False,
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

    mensagem = build_coder_message(problem, lean=lean)

    # Telemetria agregada ao longo dos eventos emitidos pelo Runner.
    uso = dict.fromkeys(
        (
            "llm_interactions",
            "prompt_tokens",
            "completion_tokens",
            "cached_tokens",
            "reasoning_tokens",
        ),
        0,
    )

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
            # Cada evento com `usage_metadata` é uma resposta finalizada do LLM.
            um = event.usage_metadata
            if um:
                uso["llm_interactions"] += 1
                uso["prompt_tokens"] += um.prompt_token_count or 0
                uso["completion_tokens"] += um.candidates_token_count or 0
                uso["cached_tokens"] += um.cached_content_token_count or 0
                uso["reasoning_tokens"] += um.thoughts_token_count or 0
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
            **uso,
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
        **uso,
    )
