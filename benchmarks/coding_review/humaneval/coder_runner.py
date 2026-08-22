"""Invocação do Coder Agent real (cr_coder_agent) para gerar a solução.

Este módulo só pode ser importado APÓS `bootstrap.prepare_environment(...)`,
porque importar o agente resolve o workspace e faz o binding das tools no
momento do import.

Cada geração:
1. limpa o diretório de código do coder (`coder/src/`) — isolamento entre
   problemas/amostras;
2. grava o contrato da task em `coder/tasks/TASK-XXX.json`;
3. roda o `cr_coder_agent` num `Runner` isolado, entregando a mensagem-contrato;
4. devolve os artefatos gerados (caminho do `solution.py`, arquivos, texto final).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from shared.workspace import get_agent_workspace

from .contract import SOLUTION_FILENAME, build_coder_message, build_task_contract
from .dataset import HumanEvalProblem


@dataclass
class CoderGeneration:
    """Resultado de uma geração do coder para um problema."""

    task_id: str
    solution_dir: Path
    solution_file: Path | None
    files: list[str] = field(default_factory=list)
    final_text: str = ""
    error: str | None = None

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


def _persistir_task(problem: HumanEvalProblem) -> None:
    """Grava o `TASK-XXX.json` que o coder pode ler via `tool_ler_workspace`."""
    import json

    tasks_dir = _tasks_dir()
    contrato = build_task_contract(problem)
    (tasks_dir / f"{contrato['id']}.json").write_text(
        json.dumps(contrato, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _localizar_solucao(src_dir: Path, entry_point: str) -> Path | None:
    """Localiza o arquivo que expõe a função-alvo.

    Preferência absoluta pelo contrato do benchmark (`solution.py`). Como
    fallback resiliente, varre os `.py` do diretório procurando a definição
    `def <entry_point>` no nível de módulo.
    """
    preferido = src_dir / SOLUTION_FILENAME
    if preferido.is_file():
        return preferido

    marcador = f"def {entry_point}"
    candidatos = sorted(src_dir.rglob("*.py"))
    for arquivo in candidatos:
        try:
            texto = arquivo.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if marcador in texto:
            return arquivo
    return None


async def run_coder(
    problem: HumanEvalProblem,
    model: str | None = None,
    *,
    user_id: str = "humaneval-bench",
) -> CoderGeneration:
    """Roda o coder para um problema e devolve os artefatos gerados.

    Importa o agente de forma tardia (lazy) para garantir que o bootstrap já
    fixou o workspace/`sys.path` antes do binding das tools.
    """
    from src.agents.workflow_coding_review.coder.agent import agent as coder_agent

    if model:
        coder_agent.model = model

    task_id = problem.slug
    src_dir = _coder_src_dir()

    # Isolamento: cada geração parte de um diretório de código limpo.
    _limpar_dir(src_dir)
    _persistir_task(problem)

    mensagem = build_coder_message(problem)

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
    )
