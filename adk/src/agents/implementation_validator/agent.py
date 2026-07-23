"""Agente de Validação de Implementação.

Slim: construído via `create_se_agent` com `output_schema=ValidationVerdict`.
Julga o Work Item exclusivamente sobre a evidência estruturada do
ExecutionReport (produzido pelo harness) — não executa nada e não relê o
código-fonte. Emite um veredito estruturado (aprovado/reprovado).

Além do agente (LLM), este módulo expõe `montar_veredito` — a codificação
determinística da política de veredito (trava da Camada 1 + agregação
conservadora). É usada nos testes e fica disponível como gate determinístico
para a futura integração executor → validador.
"""

from google.adk.tools import FunctionTool

from shared.agent_factory import create_se_agent
from shared.tools.filesystem import tool_ler_arquivo

from . import prompt
from .schemas import (
    CriterionStatus,
    CriterionVerdict,
    ValidationVerdict,
    VerdictStatus,
)

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
    output_key="validation",
    output_schema=ValidationVerdict,
    tools=[FunctionTool(tool_ler_arquivo)],
)

# ADK CLI busca por `root_agent` ao carregar um app diretamente.
root_agent = agent


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
    critérios marcados como `inconclusivo`, `blocking_reason` preenchido, e a
    Camada 2 não é executada.

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
        return ValidationVerdict(
            work_item_id=work_item_id,
            status=VerdictStatus.REPROVADO,
            criteria_verdicts=verdicts,
            blocking_reason=(
                f"Execução do harness terminou com status '{overall}'. "
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
