"""Convergence checker do workflow coding_review — early-stopping determinístico.

Terceiro sub-agente do loop `[coder → executor → convergence_checker]`. Roda
DEPOIS do executor e decide, de forma 100% determinística (sem LLM), se o loop
deve continuar ou encerrar. A decisão sai do LLM e vira este checker: o executor
não controla mais a terminação do loop.

O `LoopAgent` encerra quando um sub-agente emite `Event(actions.escalate=True)`
OU quando atinge `max_iterations`. Este checker é a fonte real de terminação;
`max_iterations` (`AI4ES_LOOP_MAX_ITERATIONS`, default 300) é apenas a rede de
segurança final.

## O que o checker lê do `session.state` (tudo já existente)
- `state['validation']`  — ValidationVerdict do implementation_validator
  (status aprovado/reprovado, criteria_verdicts, blocking_reason).
- `state['report_path']` — caminho do ExecutionReport em disco (gravado pelo
  harness), de onde saem os estágios e seus error_codes.
- `coder/src` (via `get_agent_workspace('cr_coder')`) — hasheado para detectar,
  deterministicamente, quando o coder NÃO alterou nada entre iterações.

## Score de progresso
`score = (deepest_stage, -unmet)`, comparado lexicograficamente (maior é melhor):
- `deepest_stage`: maior índice (na ordem canônica dos estágios) de um estágio
  com status `sucesso` — quão fundo no pipeline a execução chegou;
- `unmet`: quantos critérios ficaram `nao_atendido`/`inconclusivo` no veredito.

## Regras de parada (em ordem de prioridade)
- **S0** veredito `aprovado` → convergiu.
- **S1** estagnação dura: `src_hash` idêntico ao da iteração anterior e ainda
  reprovado → o coder não mudou nada; insistir é inútil.
- **S2** sem progresso por `AI4ES_LOOP_PATIENCE` iterações (default 3): o score
  não melhorou estritamente durante a janela de paciência.
- **S3** teto `AI4ES_LOOP_MAX_ITERATIONS` (default 300).

Fail-safe: na dúvida (estado ilegível, status desconhecido) o checker assume
"sem progresso" e NUNCA "aprovado".

## Independência
A ordem canônica dos estágios é uma tupla LOCAL (`_STAGE_ORDER`) — o checker não
depende, em runtime, do enum `StageName` do executor. Um teste importa o enum
canônico e afirma a igualdade (independência em runtime, consistência em teste).
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from google.adk.agents import BaseAgent
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions

from shared.workspace import get_agent_workspace

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuração por ambiente (centralizada em ../config.py — DRY com o pipeline).
# `_CEILING` (teto/rede de segurança) e `_PATIENCE` (janela sem progresso) são
# apenas aliases locais das constantes já resolvidas no import-time.
# ---------------------------------------------------------------------------
from ..config import LOOP_MAX_ITERATIONS as _CEILING
from ..config import LOOP_PATIENCE as _PATIENCE


# ---------------------------------------------------------------------------
# Ordem canônica dos estágios (tupla LOCAL — drift-guard por teste)
# ---------------------------------------------------------------------------
_STAGE_ORDER = (
    "preparacao_ambiente",
    "implantacao_artefato",
    "coleta_logs_implantacao",
    "inicializacao_aplicacao",
    "coleta_logs_execucao",
    "testes_automatizados",
    "validacoes_work_item",
    "consolidacao_evidencias",
    "geracao_relatorio",
)
_STAGE_INDEX = {nome: i for i, nome in enumerate(_STAGE_ORDER)}

# Critérios que contam como "não atendidos" para o score/assinatura.
_UNMET = frozenset({"nao_atendido", "inconclusivo"})
# Estágios que carregam evidência de falha (para os error_codes da assinatura).
_STATUS_FALHA = frozenset({"falha", "erro"})

# Chave do bookkeeping de convergência persistido entre iterações do loop.
_CONV_STATE_KEY = "convergence"

# Score sentinela (o pior possível) usado quando o estado é ilegível: garante
# que a iteração nunca conte como progresso (fail-safe).
_SCORE_MINIMO = (-1, -(10**9))


# ---------------------------------------------------------------------------
# Núcleo puro — sem I/O, sem ADK (totalmente testável)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Decisao:
    """Resultado do checker: parar ou não, o motivo, e o novo bookkeeping."""

    parar: bool
    motivo: str
    novo_estado: dict


def hash_src(src_dir) -> str:
    """SHA-256 determinístico do conteúdo de `coder/src`.

    Ignora `__pycache__/` e arquivos `.pyc`. Os arquivos entram ordenados pelo
    caminho relativo; o hash cobre o caminho + os bytes de cada arquivo, de modo
    que renomear ou mover também muda o hash. Diretório inexistente/vazio → hash
    do conjunto vazio (constante).
    """
    h = hashlib.sha256()
    base = Path(src_dir) if src_dir else None
    if base and base.exists():
        arquivos = sorted(
            p
            for p in base.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        )
        for p in arquivos:
            h.update(p.relative_to(base).as_posix().encode("utf-8"))
            h.update(b"\0")
            try:
                h.update(p.read_bytes())
            except OSError:
                h.update(b"<ilegivel>")
            h.update(b"\0")
    return h.hexdigest()


def _deepest_stage(exec_report: dict) -> int:
    """Maior índice de estágio com status `sucesso`; -1 se nenhum."""
    profundidade = -1
    for s in exec_report.get("stages", []):
        if s.get("status") == "sucesso":
            idx = _STAGE_INDEX.get(s.get("stage", ""))
            if idx is not None and idx > profundidade:
                profundidade = idx
    return profundidade


def _unmet(validation: dict) -> int:
    """Quantos critérios ficaram nao_atendido/inconclusivo no veredito."""
    return sum(
        1
        for cv in validation.get("criteria_verdicts", [])
        if cv.get("status") in _UNMET
    )


def calcular_score(validation: dict, exec_report: dict) -> tuple[int, int]:
    """`(deepest_stage, -unmet)` — comparável lexicograficamente (maior=melhor)."""
    return (_deepest_stage(exec_report), -_unmet(validation))


def calcular_assinatura(validation: dict, exec_report: dict) -> tuple:
    """Assinatura do modo de falha (para auditoria/telemetria do bookkeeping).

    `(blocking_reason, critérios não-atendidos ordenados, error_codes ordenados)`.
    Duas iterações com a mesma assinatura falharam exatamente da mesma forma.
    """
    blocking = validation.get("blocking_reason")
    criterios = tuple(
        sorted(
            cv.get("criterion", "")
            for cv in validation.get("criteria_verdicts", [])
            if cv.get("status") in _UNMET
        )
    )
    codigos = tuple(
        sorted(
            s.get("error_code")
            for s in exec_report.get("stages", [])
            if s.get("status") in _STATUS_FALHA and s.get("error_code")
        )
    )
    return (blocking, criterios, codigos)


def decidir(
    prev: dict,
    *,
    status: str,
    score: tuple,
    assinatura: tuple,
    src_hash: str,
    patience: int | None = None,
    ceiling: int | None = None,
) -> Decisao:
    """Aplica as regras de parada de forma determinística.

    `prev` é o bookkeeping da iteração anterior (`{}` na primeira). Retorna a
    `Decisao` com o bookkeeping atualizado para persistir no state.
    """
    patience = _PATIENCE if patience is None else patience
    ceiling = _CEILING if ceiling is None else ceiling

    iteration = int(prev.get("iteration", 0)) + 1
    best_raw = prev.get("best_score")
    best = tuple(best_raw) if best_raw is not None else None
    last_hash = prev.get("last_src_hash")

    # Progresso é definido pelo score: só reseta a paciência se melhorou ESTRITO.
    houve_progresso = best is None or tuple(score) > best
    if houve_progresso:
        best = tuple(score)
        sem_progresso = 0
    else:
        sem_progresso = int(prev.get("sem_progresso", 0)) + 1

    novo = {
        "iteration": iteration,
        "best_score": list(best),
        "last_score": list(score),
        "sem_progresso": sem_progresso,
        "last_src_hash": src_hash,
        "last_status": status,
        "last_assinatura": [assinatura[0], list(assinatura[1]), list(assinatura[2])],
    }

    if status == "aprovado":
        return Decisao(True, "S0_aprovado", novo)
    if last_hash is not None and src_hash == last_hash:
        return Decisao(True, "S1_estagnacao_dura", novo)
    if sem_progresso >= patience:
        return Decisao(True, "S2_sem_progresso", novo)
    if iteration >= ceiling:
        return Decisao(True, "S3_teto", novo)
    return Decisao(False, "continua", novo)


# ---------------------------------------------------------------------------
# Leitura do state (I/O) + orquestração da decisão
# ---------------------------------------------------------------------------
def _carregar_execution_report(state) -> dict:
    """Lê o ExecutionReport do disco via `state['report_path']`.

    Guarda leve: o nome do arquivo precisa ser `<task_id>.report.json` (o path é
    gravado deterministicamente pelo harness, não pelo LLM). Qualquer falha →
    `{}` (o score cai para `deepest_stage=-1`; nunca quebra o checker).
    """
    caminho = state.get("report_path")
    task_id = state.get("task_id") or ""
    if not caminho:
        return {}
    p = Path(caminho)
    if task_id and p.name != f"{task_id}.report.json":
        logger.warning(
            "cr_convergence_checker: report_path inesperado (%s); ignorando.", caminho
        )
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        logger.warning(
            "cr_convergence_checker: falha ao ler o ExecutionReport em %s", caminho
        )
        return {}


def _estado_convergencia(state) -> dict:
    prev = state.get(_CONV_STATE_KEY)
    return dict(prev) if isinstance(prev, dict) else {}


def avaliar(state, *, src_hash_fn=hash_src) -> Decisao:
    """Lê tudo o que precisa do `state` e retorna a `Decisao`.

    Fail-safe em cada leitura: exceções degradam para o pior caso ("sem
    progresso") e o status desconhecido nunca vira "aprovado".
    """
    prev = _estado_convergencia(state)

    validation = state.get("validation") or {}
    status = str(validation.get("status") or "reprovado")
    if status not in ("aprovado", "reprovado"):
        status = "reprovado"

    exec_report = _carregar_execution_report(state)

    try:
        score = calcular_score(validation, exec_report)
    except Exception:
        logger.warning("cr_convergence_checker: falha ao calcular score; assumindo pior caso.")
        score = _SCORE_MINIMO

    try:
        assinatura = calcular_assinatura(validation, exec_report)
    except Exception:
        assinatura = (None, (), ())

    try:
        src_hash = src_hash_fn(get_agent_workspace("cr_coder"))
    except Exception:
        logger.warning("cr_convergence_checker: falha ao hashear coder/src; usando vazio.")
        src_hash = ""

    return decidir(
        prev, status=status, score=score, assinatura=assinatura, src_hash=src_hash
    )


# ---------------------------------------------------------------------------
# Adapter ADK — sub-agente sem LLM que traduz a Decisao em Event/escalate
# ---------------------------------------------------------------------------
class ConvergenceChecker(BaseAgent):
    """Sub-agente determinístico do loop de codificação.

    Não usa LLM: chama `avaliar(state)` e emite um único `Event`. `escalate=True`
    encerra o `LoopAgent`; o `state_delta` persiste o bookkeeping de convergência
    para a próxima iteração.
    """

    async def _run_async_impl(self, ctx):
        decisao = avaliar(ctx.session.state)
        logger.info(
            "cr_convergence_checker: parar=%s motivo=%s iteration=%s score=%s",
            decisao.parar,
            decisao.motivo,
            decisao.novo_estado.get("iteration"),
            decisao.novo_estado.get("last_score"),
        )
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(
                state_delta={_CONV_STATE_KEY: decisao.novo_estado},
                escalate=decisao.parar,
            ),
        )


agent = ConvergenceChecker(name="cr_convergence_checker")
