"""Invocação do Reviewer Agent real (cr_review_analyzer) sobre uma resposta do par.

Este módulo só pode ser importado APÓS `bootstrap.prepare_environment(...)`:
o pacote `workflow_coding_review` resolve o workspace e faz o binding das tools
no momento do import (`review_tools._CODER_WS` é calculado no import).

Cada avaliação:
1. limpa `coder/src/` e `coder/review/` — isolamento entre respostas;
2. grava o código extraído da resposta em `coder/src/solution.py`;
3. cria a sessão com `tasks` e o `task_iteration_summary` sintético no state;
4. roda o reviewer num `Runner` isolado, entregando a mensagem-contrato;
5. lê o veredito com a MESMA função que o manifesto usa em produção
   (`manifest._validation_verdict`) e interpreta o markdown como `ReviewOutput`.

A resposta é reavaliada (retry) quando o manifesto não reconhece veredito
nenhum — é o equivalente, no pipeline, a uma revisão sem status utilizável.
"""

from __future__ import annotations

import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from shared.workspace import get_agent_workspace

from .contract import (
    SOLUTION_FILENAME,
    build_reviewer_message,
    build_solution_file,
    build_tasks_envelope,
    extract_code,
    parse_review_markdown,
    synthetic_iteration_summary,
)
from .dataset import RepairPair

REPORT_FILENAME = "verificacao_revisao.md"


@dataclass
class ReviewAttempt:
    """Uma chamada ao reviewer (a avaliação pode ter mais de uma, por retry)."""

    verdict: str  # "pass" | "fail" | "absent" (vocabulário do manifesto)
    lenient_status: str | None
    gate_applied: bool
    duration_s: float
    error: str | None = None
    llm_interactions: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class ReviewerVerdict:
    """Resultado da avaliação de UMA resposta (pos ou neg) de um par."""

    pair_id: str
    which: str  # "pos" | "neg"
    verdict: str  # veredito final: "pass" | "fail" | "absent"
    code_found: bool
    attempts: list[ReviewAttempt] = field(default_factory=list)
    review_output: dict | None = None  # ReviewOutput.model_dump()
    markdown: str = ""

    @property
    def first_attempt_valid(self) -> bool:
        return bool(self.attempts) and self.attempts[0].verdict != "absent"

    @property
    def error(self) -> str | None:
        return self.attempts[-1].error if self.attempts else None

    @property
    def outcome_kind(self) -> str:
        """Classifica o desfecho, separando falha do ambiente de falha do reviewer.

        - ``ok``: o manifesto reconheceu um veredito (pass/fail);
        - ``invalid``: o reviewer respondeu, mas sem status reconhecível — é a
          métrica de resposta inválida;
        - ``operational``: a chamada falhou (cota, timeout, rede) — não conta
          contra o reviewer, é refeita ou reportada à parte;
        - ``no_code``: a resposta do dataset não tinha bloco de código.
        """
        if not self.code_found:
            return "no_code"
        if self.verdict != "absent":
            return "ok"
        if self.attempts and self.attempts[-1].error:
            return "operational"
        return "invalid"

    def to_record(self) -> dict:
        """Forma serializável gravada no progress.jsonl (sem o markdown, salvo à parte)."""
        return {
            "which": self.which,
            "verdict": self.verdict,
            "outcome_kind": self.outcome_kind,
            "code_found": self.code_found,
            "attempts": [asdict(a) for a in self.attempts],
            "issues": (self.review_output or {}).get("issues", []),
        }


def _coder_src_dir() -> Path:
    return get_agent_workspace("cr_coder")


def _review_dir() -> Path:
    return get_agent_workspace("cr_reviewer")


def _limpar_dir(caminho: Path) -> None:
    if caminho.exists():
        shutil.rmtree(caminho, ignore_errors=True)
    caminho.mkdir(parents=True, exist_ok=True)


def _ler_relatorio() -> str:
    relatorio = _review_dir() / REPORT_FILENAME
    if not relatorio.is_file():
        return ""
    return relatorio.read_text(encoding="utf-8", errors="replace")


def _review_output(markdown: str, verdict: str) -> dict:
    """Markdown → `ReviewOutput` do schema do reviewer (reviewer/schemas.py)."""
    from src.agents.workflow_coding_review.reviewer.schemas import ReviewIssue, ReviewOutput

    lido = parse_review_markdown(markdown)
    status = {"pass": "APROVADO", "fail": "BLOQUEADO"}.get(verdict, "INVALIDO")
    return ReviewOutput(
        status=status,
        issues=[ReviewIssue(**issue) for issue in lido.issues],
        report_path=REPORT_FILENAME if markdown else None,
    ).model_dump()


async def _uma_revisao(
    pair: RepairPair, response: str, *, user_id: str, include_explanation: bool
) -> tuple[ReviewAttempt, str]:
    import time

    from src.agents.workflow_coding_review.manifest import _validation_verdict
    from src.agents.workflow_coding_review.reviewer.agent import agent as reviewer_agent

    _limpar_dir(_review_dir())
    inicio = time.time()
    prompt_tokens = completion_tokens = llm_interactions = 0
    erro: str | None = None

    try:
        runner = Runner(
            app_name=reviewer_agent.name,
            agent=reviewer_agent,
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        session = await runner.session_service.create_session(
            app_name=reviewer_agent.name,
            user_id=user_id,
            state={
                "tasks": build_tasks_envelope(pair),
                "task_iteration_summary": synthetic_iteration_summary(),
            },
        )
        mensagem = types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=build_reviewer_message(
                        pair, response, include_explanation=include_explanation
                    )
                )
            ],
        )
        try:
            async for event in runner.run_async(
                user_id=session.user_id, session_id=session.id, new_message=mensagem
            ):
                if event.usage_metadata:
                    prompt_tokens += event.usage_metadata.prompt_token_count or 0
                    completion_tokens += event.usage_metadata.candidates_token_count or 0
                    llm_interactions += 1
        finally:
            await runner.close()
    except Exception as exc:  # noqa: BLE001 — falha de revisão vira dado, não crash
        erro = f"{type(exc).__name__}: {exc}"

    markdown = _ler_relatorio()
    lido = parse_review_markdown(markdown)
    tentativa = ReviewAttempt(
        verdict=_validation_verdict(_review_dir().parent),
        lenient_status=lido.lenient_status,
        gate_applied=lido.gate_applied,
        duration_s=round(time.time() - inicio, 2),
        error=erro,
        llm_interactions=llm_interactions,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    return tentativa, markdown


async def run_reviewer(
    pair: RepairPair,
    which: str,
    *,
    model: str | None = None,
    max_retries: int = 1,
    include_explanation: bool = True,
    user_id: str = "codejudgebench-bench",
) -> ReviewerVerdict:
    """Avalia a resposta `which` ("pos" ou "neg") do par com o reviewer real."""
    from src.agents.workflow_coding_review.reviewer.agent import agent as reviewer_agent

    if which not in ("pos", "neg"):
        raise ValueError(f"which deve ser 'pos' ou 'neg', não {which!r}.")
    if model:
        reviewer_agent.model = model

    response = pair.pos_response if which == "pos" else pair.neg_response
    codigo = extract_code(response)

    src_dir = _coder_src_dir()
    _limpar_dir(src_dir)
    if codigo is None:
        # Sem código não há o que revisar; registrado como resposta inválida
        # do DATASET (não do reviewer) — o run.py reporta à parte.
        return ReviewerVerdict(pair_id=pair.pair_id, which=which, verdict="absent", code_found=False)
    (src_dir / SOLUTION_FILENAME).write_text(build_solution_file(codigo), encoding="utf-8")

    tentativas: list[ReviewAttempt] = []
    markdown = ""
    for _ in range(1 + max(0, max_retries)):
        tentativa, markdown = await _uma_revisao(
            pair, response, user_id=user_id, include_explanation=include_explanation
        )
        tentativas.append(tentativa)
        if tentativa.verdict != "absent":
            break

    final = tentativas[-1].verdict
    return ReviewerVerdict(
        pair_id=pair.pair_id,
        which=which,
        verdict=final,
        code_found=True,
        attempts=tentativas,
        review_output=_review_output(markdown, final) if markdown else None,
        markdown=markdown,
    )
