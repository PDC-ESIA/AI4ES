"""Pipeline TACO — Cenário 1 (Geração de Gabarito) e Cenário 2 (Revisão de Código).

Orquestra via Runner isolado (padrão confirmado em
benchmarks/coding_review/humaneval/coder_runner.py):

  Cenário 1: task_builder → cr_coder_agent → matching → validator → result_composer
  Cenário 2: review_builder → cr_review_analyzer_agent → feedback_composer

Entrada robusta via input_normalizer:
  Qualquer texto livre ou JSON parcial é normalizado para o formato TACO antes do
  roteamento. JSON válido segue direto (fast path, sem custo de LLM extra).

Limitações conhecidas desta versão (Estratégia C — sem reorganização):

1. System prompt SDLC imutável: o coder é instruído a criar PLAN.md,
   run.json e README como OBRIGATÓRIOS. O task_builder instrui o contrário,
   mas o system prompt tem precedência sobre o turno do usuário. O benchmark
   HumanEval confirma isso: "você ainda deve entregar run.json e README.md".

2. Workspace compartilhado: coder TACO e coder SDLC usam o mesmo diretório
   (workspace_output/coder/src/). O agent.py limpa antes de cada chamada
   TACO — aceitável para a PoC, bloqueante para produção concorrente.

3. challenge.examples ausente: os 60 JSONs de produção não têm este campo.
   O validator detecta e loga como achado para o time TACO.
"""

from __future__ import annotations

import json
import logging
import re
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

from shared.workspace import get_agent_workspace, get_workspace_root

from .feedback_composer.agent import agent as feedback_composer_agent
from .input_normalizer.agent import agent as input_normalizer_agent
from .matching import match_files
from .result_composer.agent import agent as result_composer_agent
from .review_builder.agent import agent as review_builder_agent
from .task_builder.agent import agent as task_builder_agent
from .validator import validate

logger = logging.getLogger(__name__)

_USER_ID = "taco-gabarito"

_SCHEMA_HINT = (
    "Envie um JSON no formato TACO.\n\n"
    "Cenário 1 — geração de gabarito:\n"
    '  {"challenge": {"title": "...", "description": "..."}, '
    '"solutionsRequested": 1, "variations": [{"label": "solucao", '
    '"strategy": "...", "use": [], "avoid": []}]}\n\n'
    "Cenário 2 — revisão de código do aluno:\n"
    '  {"codigo_aluno": "...", "exercicio": {"challenge": {...}, '
    '"solutionsRequested": 1, "variations": [...]}}'
)


# ---------------------------------------------------------------------------
# Utilitários de parsing
# ---------------------------------------------------------------------------


def _try_parse_json(text: str) -> dict | None:
    """Extrai e parseia o primeiro objeto JSON encontrado no texto.

    Tenta em ordem:
    1. json.loads() direto sobre o texto completo
    2. Conteúdo dentro de um bloco ```json ... ``` ou ``` ... ```
    3. Primeiro bloco { ... } balanceado encontrado no texto livre
    """
    if not text or not text.strip():
        return None
    text = text.strip()

    # 1. Parse direto
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # 2. Conteúdo entre markdown fences
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if fence:
        try:
            result = json.loads(fence.group(1).strip())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    # 3. Primeiro bloco { ... } balanceado no texto livre
    start = text.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        result = json.loads(text[start : i + 1])
                        if isinstance(result, dict):
                            return result
                    except json.JSONDecodeError:
                        pass
                    break

    return None


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
    try:
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        last_text = part.text
    finally:
        await runner.close()
    return last_text


def _limpar_workspace_coder() -> None:
    """Remove e recria o diretório do coder — isolamento entre exercícios."""
    ws = get_agent_workspace("cr_coder")
    if ws.exists():
        root = get_workspace_root()
        if not (root / ".ai4se_workspace").exists():
            raise RuntimeError(
                f"[TACO] Recusa em limpar workspace do coder '{ws}': "
                "marker .ai4se_workspace não encontrado no workspace raiz. "
                "Verifique se WORKSPACE_OUTPUT_DIR aponta para o diretório correto."
            )
        shutil.rmtree(ws)
    ws.mkdir(parents=True, exist_ok=True)
    logger.info("[TACO] workspace coder limpo: %s", ws)


def _escrever_codigo_aluno(codigo: str) -> None:
    """Escreve o código do aluno no workspace para análise estática (Ruff + Bandit)."""
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
            linhas.append(
                f"Arquivo: {mr.path.relative_to(workspace)} "
                f"(estratégia de match: {mr.strategy})"
            )
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


# ---------------------------------------------------------------------------
# Agentes de cenário
# ---------------------------------------------------------------------------


class TacoGabaritoAgent(BaseAgent):
    """Orquestra o Cenário 1 do TACO: geração de gabarito com soluções de referência."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _executar(self, raw: str) -> AsyncGenerator[Event, None]:
        """Executa o pipeline de gabarito a partir de um JSON TACO já validado."""
        json_input = json.loads(raw)
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
                parts=[types.Part.from_text(
                    text=resposta or "[result_composer sem saída]"
                )],
            ),
        )

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        raw = _extrair_mensagem_usuario(ctx)
        async for event in self._executar(raw):
            yield event


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

    async def _executar(self, raw: str) -> AsyncGenerator[Event, None]:
        """Executa o pipeline de revisão a partir de um JSON TACO já validado."""
        json_input = json.loads(raw)
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

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        raw = _extrair_mensagem_usuario(ctx)
        async for event in self._executar(raw):
            yield event


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


# ---------------------------------------------------------------------------
# Dispatcher principal
# ---------------------------------------------------------------------------


class TacoAgent(BaseAgent):
    """Ponto de entrada único do workflow TACO.

    Fluxo de entrada:
      1. Fast path: tenta json.loads() direto + extração de markdown fence/bloco livre.
      2. Slow path: se o parse falhar, chama input_normalizer_agent (1 LLM call) e
         repete o parse. Isso permite aceitar texto livre ou JSON fora do padrão TACO.
      3. Se ainda falhar: retorna mensagem de erro com dica do schema.

    Roteamento após parse bem-sucedido:
      - "codigo_aluno" no JSON → Cenário 2 (TacoReviewAgent)
      - caso contrário          → Cenário 1 (TacoGabaritoAgent)
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

        # Fast path: parse direto (JSON válido ou com fence/bloco livre)
        data = _try_parse_json(raw)

        if data is None:
            # Slow path: normaliza via LLM
            logger.info("[TACO] Entrada não é JSON — acionando input_normalizer.")
            normalized = await _invocar_agente(input_normalizer_agent, raw)
            data = _try_parse_json(normalized)

            if data is None:
                logger.warning("[TACO] input_normalizer não produziu JSON válido.")
                yield Event(
                    author=self.name,
                    content=types.Content(
                        role="model",
                        parts=[types.Part.from_text(
                            text=f"Não foi possível interpretar a entrada.\n\n{_SCHEMA_HINT}"
                        )],
                    ),
                )
                return

            # Usa o JSON normalizado para o restante do pipeline
            raw = json.dumps(data, ensure_ascii=False)
            logger.info("[TACO] Entrada normalizada com sucesso.")

        if "codigo_aluno" in data:
            logger.info("[TACO] → Cenário 2 (revisão de código do aluno)")
            async for event in _review_agent._executar(raw):
                yield event
        else:
            logger.info("[TACO] → Cenário 1 (geração de gabarito)")
            async for event in _gabarito_agent._executar(raw):
                yield event


agent = TacoAgent(
    name="taco_workflow",
    description=(
        "Workflow TACO: aceita qualquer entrada (texto livre ou JSON) e roteia para "
        "Cenário 1 (gabarito) ou Cenário 2 (revisão pedagógica)."
    ),
)

root_agent = agent
