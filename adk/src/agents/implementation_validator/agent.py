"""Agente de Validação de Implementação.

Slim: construído via `create_se_agent` SEM `output_schema` (GAP-00: no ADK,
`output_schema` ativa o modo gramática/constrained decoding, que desabilita o
function calling — e a factory sempre injeta ao menos uma tool). O LLM julga os
critérios e emite markdown em formato fixo; um `after_agent_callback`
determinístico parseia a resposta, relê o ExecutionReport do disco e aplica
`montar_veredito` — a política (trava da Camada 1 + agregação conservadora)
nunca fica na mão do LLM.

Além do agente, este módulo expõe `montar_veredito` — a codificação
determinística da política de veredito. É usada pelo callback como enforcement,
nos testes, e fica disponível como gate determinístico para a futura integração
executor → validador.
"""

import json
import logging
import re
from pathlib import Path

from google.adk.tools import FunctionTool
from google.genai import types

from shared.agent_factory import create_se_agent
from shared.tools.coding_tools.filesystem_coding import tool_ler_arquivo
from shared.workspace import get_agent_workspace

from . import prompt
from .schemas import (
    CriterionStatus,
    CriterionVerdict,
    ValidationVerdict,
    VerdictStatus,
)

logger = logging.getLogger(__name__)


def _report_path_valido(caminho: str, task_id: str) -> bool:
    """True se `caminho` é exatamente <task_id>.report.json dentro do
    workspace do cr_executor. Resolve `..` antes de comparar (anti-traversal)."""
    if not task_id:
        return False
    try:
        p = Path(caminho).resolve()
        raiz = get_agent_workspace("cr_executor").resolve()
        return (
            p.name == f"{task_id}.report.json"
            and (p == raiz / p.name or raiz in p.parents)
        )
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Política de veredito — codificação determinística (Camada 1 + agregação)
# ---------------------------------------------------------------------------

# overall_status do ExecutionReport que reprova na Camada 1 (execução não OK).
_EXECUCAO_FALHA = {"erro", "falha"}


def _extrair_criterios(report: dict) -> list[str]:
    """Extrai a lista de critérios de aceite do report.

    Prefere `acceptance_criteria`; se ausente, deriva de `criteria_evidence`.
    """
    criterios = report.get("acceptance_criteria") or []
    if criterios:
        return list(criterios)
    return [e.get("criterion", "") for e in report.get("criteria_evidence", [])]


def agregar_status(criteria_verdicts: list[CriterionVerdict]) -> VerdictStatus:
    """Agrega o status global (conservador): aprovado só se TODOS atendido.

    Qualquer `nao_atendido` ou `inconclusivo` resulta em `reprovado`.
    Lista VAZIA também reprova: sem critérios julgados não há evidência de
    atendimento (`all([])` é True e aprovaria vacuamente).
    """
    if not criteria_verdicts:
        return VerdictStatus.REPROVADO
    if all(v.status == CriterionStatus.ATENDIDO for v in criteria_verdicts):
        return VerdictStatus.APROVADO
    return VerdictStatus.REPROVADO


def montar_veredito(
    report: dict,
    criteria_verdicts: list[CriterionVerdict] | None = None,
) -> ValidationVerdict:
    """Aplica a política de veredito de forma determinística.

    Camada 1 (trava determinística, verdade absoluta): se o `overall_status` do
    ExecutionReport é `erro` ou `falha`, REPROVA imediatamente — todos os
    critérios marcados como `inconclusivo`, `blocking_reason` preenchido (com o
    estágio que falhou), e a Camada 2 não é executada.

    Camada 2 (agregação): quando a execução teve sucesso, agrega os
    `criteria_verdicts` julgados semanticamente — `aprovado` só se TODOS forem
    `atendido`; qualquer `nao_atendido`/`inconclusivo` → `reprovado`.

    Args:
        report: ExecutionReport como dict (saída do harness).
        criteria_verdicts: Vereditos por critério da Camada 2 (julgados a partir
            da evidência). Ignorados quando a Camada 1 reprova.

    Returns:
        ValidationVerdict consolidado (o único portador de veredito do fluxo).
    """
    work_item_id = report.get("work_item_id", "")
    overall = report.get("overall_status")

    # ---- Camada 1 — execução precede julgamento ----
    if overall in _EXECUCAO_FALHA:
        verdicts = [
            CriterionVerdict(
                criterion=c,
                status=CriterionStatus.INCONCLUSIVO,
                reasoning=(
                    f"Execução terminou com status '{overall}'; o critério não "
                    f"pôde ser comprovado."
                ),
            )
            for c in _extrair_criterios(report)
        ]

        # Primeiro estágio com falha/erro: os estágios estão em ordem de
        # pipeline, então o primeiro que quebra é a causa (os seguintes são
        # consequência — pulados ou falhando em cascata).
        estagio_falho = next(
            (s for s in report.get("stages", []) if s.get("status") in ("falha", "erro")),
            None,
        )
        detalhe_estagio = (
            f" Estágio que falhou: '{estagio_falho['stage']}'"
            f" (error_code={estagio_falho.get('error_code')})."
            if estagio_falho else ""
        )

        return ValidationVerdict(
            work_item_id=work_item_id,
            status=VerdictStatus.REPROVADO,
            criteria_verdicts=verdicts,
            blocking_reason=(
                f"Execução do harness terminou com status '{overall}'."
                f"{detalhe_estagio} "
                f"A Camada 2 (semântica) não foi executada."
            ),
            summary="Reprovado na Camada 1: a execução não foi bem-sucedida.",
        )

    # ---- Camada 2 — agregação conservadora ----
    cv = criteria_verdicts or []
    status = agregar_status(cv)
    if not cv:
        blocking_reason = (
            "Nenhum critério de aceite foi julgado — não há evidência de que o "
            "Work Item atenda aos seus critérios."
        )
        summary = "Reprovado: nenhum critério de aceite foi avaliado."
    elif status == VerdictStatus.APROVADO:
        blocking_reason = None
        summary = "Aprovado: todos os critérios de aceite foram atendidos."
    else:
        blocking_reason = "Ao menos um critério ficou nao_atendido ou inconclusivo."
        summary = "Reprovado: nem todos os critérios de aceite foram atendidos."

    return ValidationVerdict(
        work_item_id=work_item_id,
        status=status,
        criteria_verdicts=cv,
        blocking_reason=blocking_reason,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Callback — parse da resposta do LLM + enforcement da política (GAP-00)
# ---------------------------------------------------------------------------

_BLOCO_RE = re.compile(
    r"### CRITERIO\s*\n"
    r"TEXTO:\s*(?P<texto>.+?)\s*\n"
    r"STATUS:\s*(?P<status>atendido|nao_atendido|inconclusivo)\s*\n"
    r"JUSTIFICATIVA:\s*(?P<just>.+?)\s*\n"
    r"(?:EVIDENCIA_REF:\s*(?P<ref>.+?)\s*\n?)?",
    re.IGNORECASE,
)
_PATH_RE = re.compile(r"REPORT_PATH:\s*(?P<path>\S+)")


def _como_content(verdict: ValidationVerdict) -> types.Content:
    """Serializa o veredito enforçado como saída final do agente.

    Retornar um Content do `after_agent_callback` substitui a resposta do
    agente — assim o executor (que invoca o validador via AgentTool) recebe o
    JSON do ValidationVerdict aplicado pela política, não o markdown cru.
    """
    return types.Content(
        role="model",
        parts=[types.Part(text=json.dumps(verdict.model_dump(), ensure_ascii=False))],
    )


def _parse_e_aplicar_politica(callback_context):
    """Parseia o markdown do LLM e aplica `montar_veredito` (enforcement).

    Garantias, independentes do que o LLM escrever:
    - report ilegível/ausente → REPROVADO (fail-safe: veredito sem evidência
      não é permitido);
    - critério do report não julgado (ou renomeado) → `inconclusivo`, e a
      agregação conservadora reprova;
    - execução com falha → Camada 1 reprova, mesmo que o texto "aprove".
    """
    raw = callback_context.state.get("validation_raw", "") or ""

    # 1) Localiza e lê o report (o JSON canônico do harness).
    #    Resolução do caminho em duas fontes, nesta ordem:
    #      (a) session state `report_path`, gravado deterministicamente pela tool
    #          do harness (não depende do LLM);
    #      (b) fallback: o regex `_PATH_RE` sobre a resposta do LLM (eco).
    #    Cada caminho SÓ é lido se apontar exatamente para o report esperado
    #    deste work item dentro do workspace do cr_executor — venha do state ou
    #    do eco. Caminho do eco (fonte b) que não valida é descartado COM AVISO
    #    de segurança (um LLM manipulado poderia apontar para /etc/passwd ou um
    #    report forjado).
    task_id = callback_context.state.get("task_id") or ""

    caminhos: list[tuple[str, bool]] = []  # (caminho, veio_do_eco)
    do_state = callback_context.state.get("report_path")
    if do_state:
        caminhos.append((str(do_state), False))
    m = _PATH_RE.search(raw)
    if m:
        caminhos.append((m.group("path"), True))

    report = None
    for caminho, veio_do_eco in caminhos:
        if not _report_path_valido(caminho, task_id):
            if veio_do_eco:
                logger.warning(
                    "Segurança: REPORT_PATH ecoado pelo validador foi rejeitado "
                    "por apontar fora do report esperado no workspace do "
                    "cr_executor: %r (task_id=%r).",
                    caminho,
                    task_id,
                )
            continue
        try:
            report = json.loads(Path(caminho).read_text(encoding="utf-8"))
            break
        except Exception:
            report = None
    if report is None:
        # Fail-safe conservador: sem report lido não há evidência → reprovado
        verdict = ValidationVerdict(
            work_item_id="desconhecido",
            status=VerdictStatus.REPROVADO,
            criteria_verdicts=[],
            blocking_reason=(
                "ExecutionReport não pôde ser lido pelo validador "
                "(report_path ausente no state e REPORT_PATH ausente/ilegível "
                "na resposta)."
            ),
            summary="Reprovado: veredito sem leitura de evidência não é permitido.",
        )
        callback_context.state["validation"] = verdict.model_dump()
        return _como_content(verdict)

    # 2) Parseia os julgamentos do LLM (um bloco por critério)
    julgados: dict[str, CriterionVerdict] = {}
    for b in _BLOCO_RE.finditer(raw):
        texto = b.group("texto").strip()
        julgados[texto] = CriterionVerdict(
            criterion=texto,
            status=CriterionStatus(b.group("status").lower()),
            reasoning=b.group("just").strip(),
            evidence_ref=(b.group("ref") or "").strip() or None,
        )

    # 3) Alinha com os critérios REAIS do report: o que o LLM não julgou
    #    (ou renomeou) entra como inconclusivo — a agregação reprova.
    cvs = []
    for criterio in _extrair_criterios(report):
        cvs.append(
            julgados.get(criterio)
            or CriterionVerdict(
                criterion=criterio,
                status=CriterionStatus.INCONCLUSIVO,
                reasoning=(
                    "Critério não julgado (ou não identificável) na resposta "
                    "do validador."
                ),
            )
        )

    # 4) Enforcement: a política é do montar_veredito, nunca do texto do LLM
    verdict = montar_veredito(report, cvs)
    callback_context.state["validation"] = verdict.model_dump()
    return _como_content(verdict)


# ---------------------------------------------------------------------------
# Agente — por último no módulo: o callback já existe quando é referenciado
# ---------------------------------------------------------------------------

# Abordagem (b): SEM `agent_subdir`. O validador lê o ExecutionReport a partir
# do `report_path` CONCRETO (absoluto) que o executor lhe entrega, gravado pelo
# harness em coder/execution/{task_id}.report.json. `tool_ler_arquivo` só aceita
# caminho absoluto quando `base_dir` é None (com `base_dir` setado,
# `_resolver_caminho` REJEITA caminhos absolutos). Por isso NÃO passamos
# agent_subdir: assim o report absoluto é lido diretamente do disco, sem o
# validador precisar conhecer o task_id nem remontar o caminho. O validador é
# read-only (só lê o report), então não precisa de workspace bound para escrita.
agent = create_se_agent(
    name="implementation_validator",
    description=prompt.description,
    instruction=prompt.instruction,
    output_key="validation_raw",
    tools=[FunctionTool(tool_ler_arquivo)],
    # SEM output_schema — GAP-00: schema + tools são mutuamente exclusivos.
)
agent.after_agent_callback = _parse_e_aplicar_politica

# ADK CLI busca por `root_agent` ao carregar um app diretamente.
root_agent = agent