import json
from datetime import datetime, timezone
from typing import Any


QA_AGENT_TOOLS = [
    {
        "name": "receber_requisitos",
        "agent": "qa_agent",
        "category": "requirements_to_pytest",
        "summary": "Recebe artefatos RF, HU, UC, RNF ou RN em JSON e gera suites pytest.",
        "input_contract": (
            "String JSON com um artefato ou lista de artefatos contendo "
            "id_artefato, tipo, conteudo, modulo e criticidade."
        ),
        "output_contract": (
            "Relatorio consolidado com status, resumo de sucessos/bloqueios/falhas "
            "e detalhes por artefato."
        ),
        "use_when": [
            "A entrada principal e um requisito ou artefato de requisito.",
            "O objetivo e gerar testes pytest a partir de comportamento esperado.",
            "Ha codigo acompanhado de requisito que precisa virar criterio testavel.",
        ],
        "avoid_when": [
            "O usuario pediu apenas execucao de um arquivo de teste ja existente.",
            "A entrada nao possui comportamento verificavel nem codigo inferivel.",
        ],
    },
    {
        "name": "executar_pytest_tool",
        "agent": "qa_agent",
        "category": "pytest_execution",
        "summary": "Executa pytest em um arquivo especifico e retorna resultado estruturado.",
        "input_contract": "Caminho do arquivo de teste pytest a ser executado.",
        "output_contract": (
            "Status geral, testes executados, cobertura inicial e lista de erros "
            "quando a execucao falha."
        ),
        "use_when": [
            "Ja existe um arquivo de teste pytest para executar.",
            "O checklist precisa validar se os testes passam ou falham.",
            "O plano exige observar erro, timeout ou loop de execucao.",
        ],
        "avoid_when": [
            "Ainda nao existe arquivo pytest definido.",
            "A entrada e codigo/requisito bruto e primeiro precisa gerar testes.",
        ],
    },
]


def list_available_tools(agent_name: str = "qa_agent") -> dict[str, Any]:
    """Lista tools disponíveis para um agente específico.

    Args:
        agent_name: Nome do agente (padrão: "qa_agent").

    Returns:
        dict[str, Any]: Dicionário com agente, total e lista de tools.
    """
    normalized_agent = (agent_name or "qa_agent").strip()
    tools = [
        {
            "name": tool["name"],
            "agent": tool["agent"],
            "category": tool["category"],
            "summary": tool["summary"],
        }
        for tool in QA_AGENT_TOOLS
        if tool["agent"] == normalized_agent
    ]

    return {
        "agent": normalized_agent,
        "total": len(tools),
        "tools": tools,
    }


def describe_tools(tool_names: str = "", agent_name: str = "qa_agent") -> dict[str, Any]:
    """Descreve uma ou mais tools do QA Agent.

    Args:
        tool_names: Nomes separados por vírgula. Vazio descreve todas as tools.
        agent_name: Agente dono das tools (padrão: "qa_agent").

    Returns:
        dict[str, Any]: Dicionário com agente, tools descritas e unknown_tools (se houver).
    """
    normalized_agent = (agent_name or "qa_agent").strip()
    requested = {
        item.strip()
        for item in (tool_names or "").split(",")
        if item.strip()
    }

    descriptions = []
    unknown_tools = []

    for tool in QA_AGENT_TOOLS:
        if tool["agent"] != normalized_agent:
            continue
        if requested and tool["name"] not in requested:
            continue
        descriptions.append(tool)

    available_names = {
        tool["name"] for tool in QA_AGENT_TOOLS if tool["agent"] == normalized_agent
    }
    unknown_tools = sorted(requested - available_names)

    return {
        "agent": normalized_agent,
        "tools": descriptions,
        "unknown_tools": unknown_tools,
    }


def plan_validator(plan_json: str) -> dict[str, Any]:
    """Valida plano do action_planner verificando completude e coerência.

    Args:
        plan_json: JSON string contendo o plano a validar.

    Returns:
        dict[str, Any]: Dicionário com valid (bool), errors (list) e warnings (list).
    """
    try:
        plan = json.loads(plan_json)
    except json.JSONDecodeError as exc:
        return {
            "valid": False,
            "errors": [f"JSON invalido: {exc}"],
            "warnings": [],
        }

    errors = []
    warnings = []
    required_fields = [
        "tipo_entrada",
        "modo",
        "tools",
        "lifecycle",
        "hitl_checkpoint",
        "analise_inicial",
        "analise_progressiva",
        "criterios_verificaveis",
        "objetivo_qa",
        "estrategia",
        "checklist_inicial",
        "relatorio_conformidade_esperado",
        "doubt",
    ]

    for field in required_fields:
        if field not in plan:
            errors.append(f"Campo obrigatorio ausente: {field}")

    tipo_entrada = plan.get("tipo_entrada")
    modo = plan.get("modo")
    selected_tools = plan.get("tools", [])
    checklist = plan.get("checklist_inicial", [])
    doubt = plan.get("doubt")
    lifecycle = plan.get("lifecycle", {})
    hitl_checkpoint = plan.get("hitl_checkpoint", {})
    relatorio_conformidade = plan.get("relatorio_conformidade_esperado", {})

    if tipo_entrada not in {"requisito", "codigo", "misto", "desconhecido"}:
        errors.append("tipo_entrada deve ser requisito, codigo, misto ou desconhecido.")

    if modo not in {"requisito", "codigo", "misto"}:
        errors.append("modo deve ser requisito, codigo ou misto.")

    if not isinstance(selected_tools, list):
        errors.append("tools deve ser uma lista.")
        selected_tools = []

    available_tool_names = {tool["name"] for tool in QA_AGENT_TOOLS}
    unknown_selected_tools = sorted(set(selected_tools) - available_tool_names)
    if unknown_selected_tools:
        errors.append(
            "Tools selecionadas nao existem no qa_agent: "
            + ", ".join(unknown_selected_tools)
        )

    if doubt and selected_tools:
        errors.append("Planos com doubt nao devem selecionar tools.")

    if not doubt and not selected_tools:
        warnings.append("Plano sem doubt deveria selecionar pelo menos uma tool executavel.")

    if doubt and lifecycle is None:
        lifecycle = {}
    elif not isinstance(lifecycle, dict):
        errors.append("lifecycle deve ser um objeto.")
        lifecycle = {}

    if not doubt:
        if lifecycle.get("status") != "aguardando_validacao_humana":
            errors.append(
                "lifecycle.status deve ser aguardando_validacao_humana antes da execucao."
            )
        if lifecycle.get("execution_allowed") is not False:
            errors.append(
                "lifecycle.execution_allowed deve ser false ate aprovacao humana."
            )
        if lifecycle.get("next_step_after_approval") not in {
            "executar_plano",
            "revisar_plano",
        }:
            errors.append(
                "lifecycle.next_step_after_approval deve ser executar_plano ou revisar_plano."
            )

    if doubt and hitl_checkpoint is None:
        hitl_checkpoint = {}
    elif not isinstance(hitl_checkpoint, dict):
        errors.append("hitl_checkpoint deve ser um objeto.")
        hitl_checkpoint = {}

    if not doubt:
        if hitl_checkpoint.get("required") is not True:
            errors.append("hitl_checkpoint.required deve ser true.")
        if not hitl_checkpoint.get("checkpoint_id"):
            errors.append("hitl_checkpoint.checkpoint_id e obrigatorio.")
        if not hitl_checkpoint.get("approval_question"):
            errors.append("hitl_checkpoint.approval_question e obrigatorio.")
        if not hitl_checkpoint.get("pause_reason"):
            errors.append("hitl_checkpoint.pause_reason e obrigatorio.")
        allowed_decisions = hitl_checkpoint.get("allowed_decisions", [])
        if not isinstance(allowed_decisions, list):
            errors.append("hitl_checkpoint.allowed_decisions deve ser lista.")
        else:
            required_decisions = {"aprovar", "rejeitar", "solicitar_ajustes"}
            missing_decisions = required_decisions - set(allowed_decisions)
            if missing_decisions:
                errors.append(
                    "hitl_checkpoint.allowed_decisions deve conter: "
                    + ", ".join(sorted(required_decisions))
                )

    if not isinstance(checklist, list):
        errors.append("checklist_inicial deve ser uma lista.")
    elif not doubt and not checklist:
        errors.append("checklist_inicial deve ser uma lista nao vazia.")
    elif checklist:
        for index, item in enumerate(checklist, start=1):
            if not isinstance(item, dict):
                errors.append(f"Checklist item {index} deve ser objeto.")
                continue
            if not item.get("id"):
                errors.append(f"Checklist item {index} sem id.")
            if not item.get("descricao"):
                errors.append(f"Checklist item {index} sem descricao.")
            if item.get("status") != "pendente":
                errors.append(
                    f"Checklist item {index} deve iniciar com status pendente."
                )

    criterios = plan.get("criterios_verificaveis", [])
    if not doubt and (not isinstance(criterios, list) or not criterios):
        errors.append("Plano sem doubt precisa ter criterios_verificaveis.")

    if doubt and relatorio_conformidade is None:
        relatorio_conformidade = {}
    elif not isinstance(relatorio_conformidade, dict):
        errors.append("relatorio_conformidade_esperado deve ser um objeto.")
    elif not doubt:
        required_report_fields = {
            "comparar_planejado_vs_executado",
            "incluir_evidencias",
            "incluir_divergencias",
            "status_possiveis",
        }
        missing_report_fields = required_report_fields - set(relatorio_conformidade)
        if missing_report_fields:
            errors.append(
                "relatorio_conformidade_esperado incompleto: "
                + ", ".join(sorted(missing_report_fields))
            )
        if relatorio_conformidade.get("comparar_planejado_vs_executado") is not True:
            errors.append(
                "relatorio_conformidade_esperado.comparar_planejado_vs_executado "
                "deve ser true."
            )
        if relatorio_conformidade.get("incluir_evidencias") is not True:
            errors.append(
                "relatorio_conformidade_esperado.incluir_evidencias deve ser true."
            )
        if relatorio_conformidade.get("incluir_divergencias") is not True:
            errors.append(
                "relatorio_conformidade_esperado.incluir_divergencias deve ser true."
            )
        status_possiveis = relatorio_conformidade.get("status_possiveis", [])
        if not isinstance(status_possiveis, list):
            errors.append(
                "relatorio_conformidade_esperado.status_possiveis deve ser lista."
            )
        else:
            required_statuses = {"conforme", "parcialmente_conforme", "nao_conforme"}
            missing_statuses = required_statuses - set(status_possiveis)
            if missing_statuses:
                errors.append(
                    "relatorio_conformidade_esperado.status_possiveis deve conter: "
                    + ", ".join(sorted(required_statuses))
                )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "selected_tools": selected_tools,
    }


def create_hitl_checkpoint(plan_json: str) -> dict[str, Any]:
    """Registra checkpoint HITL (Human-In-The-Loop) antes da execução do plano.

    Args:
        plan_json: JSON string contendo o plano aprovado.

    Returns:
        dict[str, Any]: Status do checkpoint e informações para aprovação humana.
    """
    try:
        plan = json.loads(plan_json)
    except json.JSONDecodeError as exc:
        return {
            "status": "invalid_plan",
            "errors": [f"JSON invalido: {exc}"],
        }

    validation = plan_validator(plan_json)
    if not validation["valid"]:
        return {
            "status": "invalid_plan",
            "errors": validation["errors"],
            "warnings": validation["warnings"],
        }

    checkpoint = plan.get("hitl_checkpoint", {})
    lifecycle = plan.get("lifecycle", {})

    return {
        "status": "awaiting_human_validation",
        "checkpoint_id": checkpoint.get("checkpoint_id"),
        "approval_question": checkpoint.get("approval_question"),
        "pause_reason": checkpoint.get("pause_reason"),
        "allowed_decisions": checkpoint.get("allowed_decisions", []),
        "execution_allowed": lifecycle.get("execution_allowed", False),
        "message": (
            "Pausa HITL criada. O plano nao deve ser executado antes de uma "
            "decisao humana explicita."
        ),
    }


def register_human_validation(
    checkpoint_id: str,
    decision: str,
    reviewer: str = "usuario",
    comments: str = "",
) -> dict[str, Any]:
    """Registra decisão humana para checkpoint HITL.

    Args:
        checkpoint_id: Identificador do checkpoint.
        decision: Decisão tomada ("aprovar", "rejeitar", "solicitar_ajustes").
        reviewer: Nome do revisor (padrão: "usuario").
        comments: Comentários adicionais (opcional).

    Returns:
        dict[str, Any]: Status, decisão registrada e próximos passos.
    """
    normalized_decision = (decision or "").strip().lower()
    allowed_decisions = {"aprovar", "rejeitar", "solicitar_ajustes"}

    if normalized_decision not in allowed_decisions:
        return {
            "status": "invalid_decision",
            "execution_allowed": False,
            "errors": [
                "decision deve ser uma destas opcoes: "
                + ", ".join(sorted(allowed_decisions))
            ],
        }

    execution_allowed = normalized_decision == "aprovar"
    next_step = "executar_plano" if execution_allowed else "revisar_plano"

    return {
        "status": "human_validation_recorded",
        "checkpoint_id": checkpoint_id,
        "decision": normalized_decision,
        "reviewer": reviewer or "usuario",
        "comments": comments or "",
        "validated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "execution_allowed": execution_allowed,
        "next_step": next_step,
    }


def generate_compliance_report(
    planned_json: str,
    executed_json: str,
) -> dict[str, Any]:
    """Gera relatório de conformidade comparando planejado vs executado.

    Args:
        planned_json: JSON string do plano original.
        executed_json: JSON string dos resultados da execução.

    Returns:
        dict[str, Any]: Relatório com status, divergências, evidências e resumo.
    """
    try:
        planned = json.loads(planned_json)
    except json.JSONDecodeError as exc:
        return {
            "status": "invalid_planned_json",
            "errors": [f"planned_json invalido: {exc}"],
        }

    try:
        executed = json.loads(executed_json)
    except json.JSONDecodeError as exc:
        return {
            "status": "invalid_executed_json",
            "errors": [f"executed_json invalido: {exc}"],
        }

    planned_tools = planned.get("tools", [])
    executed_tools = executed.get("tools_executadas", executed.get("tools", []))
    missing_tools = [tool for tool in planned_tools if tool not in executed_tools]
    extra_tools = [tool for tool in executed_tools if tool not in planned_tools]

    planned_checklist = planned.get("checklist_inicial", [])
    executed_checklist = executed.get("checklist_final", executed.get("checklist", []))
    executed_by_id = {
        item.get("id"): item for item in executed_checklist if isinstance(item, dict)
    }

    checklist_report = []
    divergences = []

    for item in planned_checklist:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        executed_item = executed_by_id.get(item_id)
        if not executed_item:
            checklist_report.append(
                {
                    "id": item_id,
                    "planejado": item.get("descricao"),
                    "executado": None,
                    "status": "nao_executado",
                    "evidencia": None,
                }
            )
            divergences.append(f"Checklist planejado nao executado: {item_id}")
            continue

        executed_status = executed_item.get("status", "desconhecido")
        checklist_report.append(
            {
                "id": item_id,
                "planejado": item.get("descricao"),
                "executado": executed_item.get("descricao", item.get("descricao")),
                "status": executed_status,
                "evidencia": executed_item.get("evidencia"),
            }
        )
        if executed_status not in {"concluido", "aprovado", "ok"}:
            divergences.append(
                f"Checklist {item_id} finalizou com status {executed_status}."
            )

    if missing_tools:
        divergences.append("Tools planejadas nao executadas: " + ", ".join(missing_tools))
    if extra_tools:
        divergences.append("Tools executadas sem planejamento: " + ", ".join(extra_tools))

    execution_status = executed.get("status", "desconhecido")
    if execution_status in {"falha", "erro", "failed"}:
        divergences.append("Execucao finalizou com falha.")

    if not divergences:
        compliance_status = "conforme"
    elif len(divergences) <= 2:
        compliance_status = "parcialmente_conforme"
    else:
        compliance_status = "nao_conforme"

    return {
        "status": compliance_status,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "planned_vs_executed": {
            "tools_planejadas": planned_tools,
            "tools_executadas": executed_tools,
            "checklist": checklist_report,
        },
        "divergencias": divergences,
        "evidencias": executed.get("evidencias", []),
        "resultado_execucao": execution_status,
        "summary": (
            "Execucao conforme ao plano."
            if compliance_status == "conforme"
            else "Execucao possui divergencias em relacao ao plano."
        ),
    }
