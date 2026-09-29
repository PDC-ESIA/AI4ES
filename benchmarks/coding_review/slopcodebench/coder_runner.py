"""Invocação do Coder Agent real (cr_coder_agent) em um checkpoint.

Este módulo só pode ser importado APÓS `bootstrap.prepare_environment(...)`,
porque importar o agente resolve o workspace e faz o binding das tools no
momento do import.

Diferença essencial para o HumanEval: aqui o coder ESTENDE o próprio código.
O diretório de código (`coder/src/`) só é limpo no primeiro checkpoint de cada
problema; nos seguintes ele carrega o que o próprio coder deixou.

Cada checkpoint:
1. grava o contrato da task em `coder/tasks/` (apagando o do checkpoint
   anterior);
2. roda o `cr_coder_agent` num `Runner` com sessão NOVA — o coder não vê a
   conversa do checkpoint anterior, só a spec nova e o workspace (protocolo do
   SlopCodeBench);
3. a partir do 2º checkpoint, semeia o estado da sessão como o `TaskIterator`
   do workflow faz entre tasks (`NOVA_TASK:` + fotografia dos arquivos
   herdados), sem alterar prompt, guard ou loop;
4. devolve a telemetria da geração (tokens, interações, erro, timeout).
"""

from __future__ import annotations

import asyncio
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from shared.workspace import get_agent_workspace

# Pastas que não fazem parte da entrega do coder (nunca vão para o snapshot).
_IGNORAR_NO_SNAPSHOT = shutil.ignore_patterns(
    "__pycache__", "*.pyc", "venv", ".venv", ".git"
)


# Trechos que identificam cota/limite do provider na mensagem de erro, para os
# casos em que o erro chega embrulhado em outra exceção (ex.: pelo ADK).
_SINAIS_DE_COTA = ("quota", "rate limit", "rate_limit")


class LlmIndisponivel(RuntimeError):
    """O LLM do coder ficou indisponível (cota, limite, conexão, credencial).

    Não é uma falha do coder: o run é interrompido sem registrar o checkpoint,
    para que `--resume-dir` o refaça do zero quando o LLM voltar.
    """


def llm_indisponivel(exc: BaseException) -> bool:
    """Diz se a exceção (ou alguma causa dela) é indisponibilidade do LLM."""
    import litellm

    tipos = (
        litellm.RateLimitError,
        litellm.APIConnectionError,
        litellm.AuthenticationError,
        litellm.ServiceUnavailableError,
        litellm.BudgetExceededError,
    )
    atual: BaseException | None = exc
    while atual is not None:
        if isinstance(atual, tipos):
            return True
        if any(sinal in str(atual).lower() for sinal in _SINAIS_DE_COTA):
            return True
        atual = atual.__cause__ or atual.__context__
    return False


@dataclass
class CoderGeneration:
    """Resultado de uma execução do coder em um checkpoint."""

    task_id: str
    files: list[str]
    final_text: str = ""
    error: str | None = None
    timed_out: bool = False

    # Telemetria agregada do `usage_metadata` dos eventos do Runner.
    llm_interactions: int = 0
    tool_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0


def coder_src_dir() -> Path:
    """Diretório de código do coder (`coder/src/`)."""
    return get_agent_workspace("cr_coder")


def _tasks_dir() -> Path:
    """Diretório de contratos de task lido pelo coder (`coder/tasks/`)."""
    return get_agent_workspace("cr_context_engineer")


def _limpar_dir(caminho: Path) -> None:
    """Remove e recria um diretório vazio."""
    if caminho.exists():
        shutil.rmtree(caminho, ignore_errors=True)
    caminho.mkdir(parents=True, exist_ok=True)


def iniciar_problema() -> None:
    """Zera o código do coder antes do 1º checkpoint de um problema."""
    _limpar_dir(coder_src_dir())


def restaurar_de_snapshot(snapshot_dir: Path) -> None:
    """Recoloca em `coder/src/` o estado de um checkpoint já concluído (retomada)."""
    src = coder_src_dir()
    _limpar_dir(src)
    shutil.copytree(snapshot_dir, src, dirs_exist_ok=True)


def salvar_snapshot(destino: Path) -> None:
    """Copia o estado atual de `coder/src/` para o snapshot do checkpoint."""
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(coder_src_dir(), destino, ignore=_IGNORAR_NO_SNAPSHOT)


def _persistir_task(contrato: dict) -> None:
    """Deixa em `coder/tasks/` somente o contrato do checkpoint atual."""
    tasks_dir = _tasks_dir()
    _limpar_dir(tasks_dir)
    (tasks_dir / f"{contrato['id']}.json").write_text(
        json.dumps(contrato, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _estado_inicial(task_id: str, *, primeiro_checkpoint: bool) -> dict:
    """Estado da sessão ADK, espelhando o que o `TaskIterator` faz entre tasks."""
    from src.agents.workflow_coding_review.coder.workspace_guard import (
        preparar_arquivos_herdados,
    )
    from src.agents.workflow_coding_review.task_iterator import marcador_nova_task

    state: dict = {"task_id": task_id}
    preparar_arquivos_herdados(state, primeira=primeiro_checkpoint)
    if not primeiro_checkpoint:
        state["execution_result"] = marcador_nova_task(task_id)
    return state


async def run_coder(
    mensagem: str,
    contrato: dict,
    *,
    primeiro_checkpoint: bool,
    model: str | None = None,
    timeout_s: float | None = None,
    user_id: str = "slopcodebench-bench",
) -> CoderGeneration:
    """Roda o coder em um checkpoint e devolve a telemetria da geração.

    Importa o agente de forma tardia (lazy) para garantir que o bootstrap já
    fixou o workspace/`sys.path` antes do binding das tools.
    """
    from src.agents.workflow_coding_review.coder.agent import agent as coder_agent

    if model:
        coder_agent.model = model

    task_id = contrato["id"]
    _persistir_task(contrato)
    geracao = CoderGeneration(task_id=task_id, files=[])

    async def _executar() -> None:
        runner = Runner(
            app_name=coder_agent.name,
            agent=coder_agent,
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        try:
            session = await runner.session_service.create_session(
                app_name=coder_agent.name,
                user_id=user_id,
                state=_estado_inicial(task_id, primeiro_checkpoint=primeiro_checkpoint),
            )
            content = types.Content(
                role="user", parts=[types.Part.from_text(text=mensagem)]
            )
            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=content,
            ):
                # Cada evento com `usage_metadata` é uma resposta finalizada do LLM.
                uso = event.usage_metadata
                if uso:
                    geracao.prompt_tokens += uso.prompt_token_count or 0
                    geracao.completion_tokens += uso.candidates_token_count or 0
                    geracao.cached_tokens += uso.cached_content_token_count or 0
                    geracao.reasoning_tokens += uso.thoughts_token_count or 0
                    geracao.llm_interactions += 1
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.function_call:
                            geracao.tool_calls += 1
                        if part.text:
                            geracao.final_text = part.text
        finally:
            await runner.close()

    try:
        await asyncio.wait_for(_executar(), timeout=timeout_s)
    except TimeoutError:
        # Como no paper: o limite de tempo encerra o checkpoint, e o que o coder
        # já gravou no workspace segue para avaliação.
        geracao.timed_out = True
    except Exception as exc:  # noqa: BLE001 — falha de geração vira dado, não crash
        if llm_indisponivel(exc):
            # Não é desempenho do coder: o checkpoint não é registrado e o run
            # para, para ser retomado (--resume-dir) quando o LLM voltar.
            raise LlmIndisponivel(f"{type(exc).__name__}: {exc}") from exc
        geracao.error = f"{type(exc).__name__}: {exc}"

    src_dir = coder_src_dir()
    geracao.files = [
        str(p.relative_to(src_dir)) for p in sorted(src_dir.rglob("*")) if p.is_file()
    ]
    return geracao
