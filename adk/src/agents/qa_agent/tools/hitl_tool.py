"""Tool de pausa HITL para o qa_pipeline.

Empacotada como LongRunningFunctionTool no workflow_qa/agent.py. Quando o
LLM chama esta função, o ADK emite um function_call event sem auto-resposta
e o runner devolve controle. A resposta vem da próxima invocação do
orchestrator como um function_response, montado a partir do texto livre do
usuário ("aprovar" / "rejeitar" / "solicitar_ajustes ...").
"""

from typing import Any, Optional


async def aguardar_aprovacao_humana(
    checkpoint_id: str,
    approval_question: str,
    allowed_decisions: list[str],
    pause_reason: Optional[str] = None,
) -> dict[str, Any]:
    """Pausa o agente até receber decisão humana explícita.

    Quando usar:
        Apenas quando o action_planner retornou um plano com
        `hitl_checkpoint.required=true`. Chame ANTES de prosseguir para
        a etapa de geração de testes. Após a tool retornar, leia o campo
        `decision` para decidir o próximo passo.

    Args:
        checkpoint_id: Identificador do checkpoint criado por
            create_hitl_checkpoint.
        approval_question: Texto literal da pergunta a ser exibida ao humano.
        allowed_decisions: Lista de decisões aceitáveis
            (ex.: ["aprovar", "rejeitar", "solicitar_ajustes"]).
        pause_reason: Motivo opcional da pausa (mostrado ao humano).

    Returns:
        dict com chaves: decision, comments, reviewer, validated_at,
        checkpoint_id, approval_question, allowed_decisions, pause_reason.
        `decision` é uma das opções de `allowed_decisions` quando a
        execução real acontece (via ADK + orchestrator); em chamada direta
        retorna "pending".
    """
    return {
        "decision": "pending",
        "comments": "",
        "reviewer": "usuario",
        "validated_at": None,
        "checkpoint_id": checkpoint_id,
        "approval_question": approval_question,
        "allowed_decisions": allowed_decisions,
        "pause_reason": pause_reason,
    }
