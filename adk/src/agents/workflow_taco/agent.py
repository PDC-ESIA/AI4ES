"""Pipeline TACO — Cenário 1 (Geração de Gabarito).

Orquestra via Runner isolado (padrão confirmado em
benchmarks/coding_review/humaneval/coder_runner.py):

    task_builder → cr_coder_agent → matching → validator → result_composer

O cr_coder_agent é importado de forma lazy (dentro da função async) para
garantir que o binding de workspace das tools já ocorreu antes do import,
seguindo o mesmo padrão do coder_runner.py do benchmark HumanEval.
O task_builder e o result_composer são rodados via Runner isolado — mesma
abordagem dos outros agentes não-SDLC do projeto.

Limitações conhecidas desta versão (Estratégia C — sem reorganização):

1. System prompt SDLC imutável: o coder é instruído a criar PLAN.md,
   run.json e README como OBRIGATÓRIOS. O task_builder instrui o contrário,
   mas o system prompt tem precedência sobre o turno do usuário. O benchmark
   HumanEval confirma isso: "você ainda deve entregar run.json e README.md".
   O task_builder instrui o contrário — o system prompt vence.

2. Workspace compartilhado: coder TACO e coder SDLC usam o mesmo diretório
   (workspace_output/coder/src/). O agent.py limpa antes de cada chamada
   TACO — aceitável para a PoC, bloqueante para produção concorrente.

3. challenge.examples ausente: os 60 JSONs de produção não têm este campo.
   O validator detecta e loga como achado para o time TACO.
"""

from __future__ import annotations

import json
import logging
import shutil
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from pydantic import ConfigDict

from shared.workspace import get_agent_workspace

from .feedback_composer.agent import agent as feedback_composer_agent
from .matching import match_files
from .result_composer.agent import agent as result_composer_agent
from .review_builder.agent import agent as review_builder_agent
from .task_builder.agent import agent as task_builder_agent
from .validator import validate

logger = logging.getLogger(__name__)

_USER_ID = "taco-gabarito"


def _extrair_mensagem_usuario(ctx: InvocationContext) -> str:
    for event in reversed(list(ctx.session.events or [])):
        if (
            getattr(event, "author", None) == "user"
            and event.content
            and event.content.parts
        ):
            for part in event.content.parts:
                if part.text:
                    return part.text
    return ""


async def _invocar_agente(agent, user_text: str) -> str:
    """Roda um agente em Runner isolado e retorna o último texto produzido.

    Padrão idêntico ao planner_wrapper.py e ao coder_runner.py do benchmark.
    """
    runner = Runner(
        app_name=agent.name,
        agent=agent,
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    session = await runner.session_service.create_session(
        app_name=agent.name, user_id=_USER_ID, state={},
    )
    content = types.Content(
        role="user", parts=[types.Part.from_text(text=user_text)],
    )
    last_text = ""
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    last_text = part.text
    await runner.close()
    return last_text


def _limpar_workspace_coder() -> None:
    """Remove e recria o diretório do coder — isolamento entre exercícios.

    Mesmo padrão de _limpar_dir() usado no benchmark HumanEval.
    """
    ws = get_agent_workspace("cr_coder")
    if ws.exists():
        shutil.rmtree(ws, ignore_errors=True)
    ws.mkdir(parents=True, exist_ok=True)
    logger.info("[TACO] workspace coder limpo: %s", ws)


def _escrever_codigo_aluno(codigo: str) -> None:
    """Escreve o código do aluno no workspace do coder para análise estática.

    O cr_review_analyzer_agent usa _inject_static_findings (Ruff + Bandit)
    que lê arquivos de workspace_output/coder/src/. O arquivo precisa existir
    antes da chamada ao revisor para que a análise estática funcione.
    """
    ws = get_agent_workspace("cr_coder")
    student_file = ws / "student_solution.py"
    student_file.write_text(codigo, encoding="utf-8")
    logger.info("[TACO-REVIEW] Código do aluno escrito em: %s", student_file)


def _construir_input_composer(
    json_input: dict,
    match: dict,
    validation: dict,
) -> str:
    """Monta o texto consolidado que o result_composer recebe como input."""
    workspace = get_agent_workspace("cr_coder")
    linhas = [
        "EXERCÍCIO ORIGINAL:",
        json.dumps(json_input, ensure_ascii=False, indent=2),
        "",
        "RESULTADOS POR VARIAÇÃO:",
    ]
    for var in json_input.get("variations", []):
        label = var["label"]
        mr = match.get(label)
        vr = validation.get(label, {})

        linhas.append(f"\n--- {label} ---")
        if mr and mr.path:
            try:
                codigo = mr.path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                codigo = "[ERRO AO LER ARQUIVO]"
            linhas.append(f"Arquivo: {mr.path.relative_to(workspace)} (estratégia de match: {mr.strategy})")
            linhas.append(f"Validação sintática: {vr.get('status', 'N/A')}")
            linhas.append("Código:")
            linhas.append(codigo)
        else:
            cause = mr.cause if mr else "SEM_ARQUIVO"
            linhas.append(f"Arquivo: NÃO ENCONTRADO ({cause})")
            linhas.append(f"Validação sintática: {vr.get('status', cause)}")

        examples_run = vr.get("examples_run", [])
        if examples_run:
            linhas.append("Exemplos executados:")
            for ex in examples_run:
                status = "PASSOU" if ex.get("passed") else "FALHOU"
                linhas.append(
                    f"  [{status}] entrada={ex['input']!r} "
                    f"esperado={ex['expected']!r} obtido={ex['actual']!r}"
                )
        else:
            linhas.append("Exemplos: challenge.examples ausente no JSON de entrada.")

    return "\n".join(linhas)


class TacoGabaritoAgent(BaseAgent):
    """Orquestra o Cenário 1 do TACO: geração de gabarito com soluções de referência."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        raw = _extrair_mensagem_usuario(ctx)
        if not raw.strip():
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text="Nenhuma mensagem recebida.")],
                ),
            )
            return

        try:
            json_input = json.loads(raw)
        except json.JSONDecodeError as exc:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=f"JSON inválido: {exc}")],
                ),
            )
            return

        variations = json_input.get("variations", [])
        examples = json_input.get("challenge", {}).get("examples")
        titulo = json_input.get("challenge", {}).get("title", "?")

        logger.info(
            "[TACO] Iniciando gabarito: '%s' | %d variações", titulo, len(variations)
        )

        # 1. Task Builder: JSON TACO → task para o coder
        logger.info("[TACO] Passo 1/4 — task_builder")
        task = await _invocar_agente(task_builder_agent, raw)
        if not task.strip():
            task = (
                f"Implemente o exercício '{titulo}' com {len(variations)} variações "
                f"conforme o JSON: {raw}"
            )
            logger.warning("[TACO] task_builder retornou vazio — usando fallback.")

        # 2. Limpeza do workspace (isolamento entre exercícios)
        _limpar_workspace_coder()

        # 3. Coder: task → arquivos Python no workspace
        # Lazy import para garantir que o binding de workspace já ocorreu.
        logger.info("[TACO] Passo 2/4 — coder")
        from src.agents.workflow_coding_review.coder.agent import (  # noqa: PLC0415
            agent as cr_coder_agent,
        )
        await _invocar_agente(cr_coder_agent, task)

        # 4. Matching + validação (determinísticos, sem LLM)
        logger.info("[TACO] Passo 3/4 — matching + validação")
        workspace = get_agent_workspace("cr_coder")
        match = match_files(workspace, variations)
        validation = validate(match, examples)

        # 5. Result Composer: consolida resultado final
        logger.info("[TACO] Passo 4/4 — result_composer")
        composer_input = _construir_input_composer(json_input, match, validation)
        resposta = await _invocar_agente(result_composer_agent, composer_input)

        logger.info("[TACO] Pipeline concluído para '%s'.", titulo)

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=resposta or "[result_composer sem saída]")],
            ),
        )


class TacoReviewAgent(BaseAgent):
    """Orquestra o Cenário 2 do TACO: revisão pedagógica do código do aluno.

    Fluxo: review_builder → cr_review_analyzer_agent → feedback_composer

    O cr_review_analyzer_agent é importado de forma lazy pelo mesmo motivo
    que o cr_coder_agent: binding de workspace ocorre no import.
    O código do aluno é escrito em workspace_output/coder/src/student_solution.py
    antes da chamada, para que o Ruff + Bandit do _inject_static_findings
    consigam analisar o arquivo.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        raw = _extrair_mensagem_usuario(ctx)

        try:
            json_input = json.loads(raw)
        except json.JSONDecodeError as exc:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=f"JSON inválido: {exc}")],
                ),
            )
            return

        codigo_aluno = json_input.get("codigo_aluno", "")
        exercicio = json_input.get("exercicio", {})
        titulo = exercicio.get("challenge", {}).get("title", "?")

        logger.info("[TACO-REVIEW] Iniciando revisão: '%s'", titulo)

        # 1. Review Builder: JSON → tarefa formatada para o reviewer SDLC
        logger.info("[TACO-REVIEW] Passo 1/3 — review_builder")
        task = await _invocar_agente(review_builder_agent, raw)
        if not task.strip():
            task = (
                f"Revise o código Python do aluno para o exercício '{titulo}':\n\n"
                f"{codigo_aluno}"
            )
            logger.warning("[TACO-REVIEW] review_builder retornou vazio — usando fallback.")

        # 2. Prepara workspace + cr_review_analyzer_agent (lazy import)
        _limpar_workspace_coder()
        if codigo_aluno.strip():
            _escrever_codigo_aluno(codigo_aluno)

        logger.info("[TACO-REVIEW] Passo 2/3 — reviewer SDLC")
        from src.agents.workflow_coding_review.reviewer.agent import (  # noqa: PLC0415
            agent as cr_review_analyzer_agent,
        )
        review_raw = await _invocar_agente(cr_review_analyzer_agent, task)

        # 3. Feedback Composer: revisão SDLC → feedback pedagógico
        logger.info("[TACO-REVIEW] Passo 3/3 — feedback_composer")
        feedback = await _invocar_agente(
            feedback_composer_agent, review_raw or task,
        )

        logger.info("[TACO-REVIEW] Revisão concluída para '%s'.", titulo)

        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(
                    text=feedback or "[feedback_composer sem saída]"
                )],
            ),
        )


# ---------------------------------------------------------------------------
# Instâncias internas — usadas pelo dispatcher TacoAgent
# ---------------------------------------------------------------------------

_gabarito_agent = TacoGabaritoAgent(
    name="taco_gabarito_workflow",
    description=(
        "Pipeline TACO Cenário 1: gera soluções de referência (gabarito) via "
        "task_builder → cr_coder_agent → matching → validator → result_composer."
    ),
)

_review_agent = TacoReviewAgent(
    name="taco_review_workflow",
    description=(
        "Pipeline TACO Cenário 2: revisão pedagógica do código do aluno via "
        "review_builder → cr_review_analyzer_agent → feedback_composer."
    ),
)


class TacoAgent(BaseAgent):
    """Ponto de entrada único do workflow TACO.

    Despacha para Cenário 1 (gabarito) ou Cenário 2 (revisão) com base no JSON:
    - Cenário 1: campo "variations" presente (JSON do exercício TACO)
    - Cenário 2: campo "codigo_aluno" presente
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        raw = _extrair_mensagem_usuario(ctx)
        if not raw.strip():
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text="Nenhuma mensagem recebida.")],
                ),
            )
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=f"JSON inválido: {exc}")],
                ),
            )
            return

        if "codigo_aluno" in data:
            logger.info("[TACO] → Cenário 2 (revisão de código do aluno)")
            async for event in _review_agent._run_async_impl(ctx):
                yield event
        else:
            logger.info("[TACO] → Cenário 1 (geração de gabarito)")
            async for event in _gabarito_agent._run_async_impl(ctx):
                yield event


agent = TacoAgent(
    name="taco_workflow",
    description=(
        "Workflow TACO: Cenário 1 (gabarito) via JSON de exercício, "
        "Cenário 2 (revisão pedagógica) via JSON com campo 'codigo_aluno'."
    ),
)

root_agent = agent
