"""Tools de pausa HITL do Time 2 (Design).

Cada função aqui é um stub que retorna sempre None. Quando empacotada como
LongRunningFunctionTool, o ADK emite um function_call sem auto-resposta e o
runner devolve controle ao chamador — o orchestrator (adk/src/agents/
orchestrator/agent.py) já sabe pausar e retomar qualquer pipeline que emita
esse tipo de function_call, então nenhuma mudança é necessária lá.

Referência: adk/shared/tools/hitl_tool.py (mesmo padrão, usado pelo Time 3/QA).
"""

from typing import Any, Optional


async def aguardar_resolucao_doubt(
    checkpoint_id: str,
    approval_question: str,
    allowed_decisions: list[str],
    pause_reason: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Pausa o design_pipeline até humano resolver Doubt_Artifacts bloqueados.

    Quando usar (pipeline_controller, ETAPA 3):
        Apenas quando check_active_blocks (via Agente IO) retornar
        has_blocks=true. Chame ANTES de emitir qualquer texto de bloqueio.

    Args:
        checkpoint_id: identificador do lote de doubts (ex.: hu_ids
            bloqueados, unidos por vírgula).
        approval_question: pergunta literal a exibir ao humano, citando os
            Doubt_Artifacts bloqueados (filename + hu_id).
        allowed_decisions: ["retomar", "cancelar"].
        pause_reason: motivo opcional (ex.: lista de arquivos bloqueados).

    Returns:
        None — ver docstring de shared/tools/hitl_tool.py para o porquê.
    """
    _ = (checkpoint_id, approval_question, allowed_decisions, pause_reason)
    return None


async def aguardar_decisao_validacao(
    checkpoint_id: str,
    approval_question: str,
    allowed_decisions: list[str],
    pause_reason: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Pausa quando o validator esgota as 2 tentativas de correção.

    Quando usar (validator):
        Apenas após a 2ª tentativa de correção falhar (sintática ou
        semântica). Chame em vez de só declarar texto de escalonamento.

    Args:
        checkpoint_id: identificador do artefato em validação (ex.: o `id`
            do artefato, tipo `HU-001` ou nome do arquivo .mmd/.md).
        approval_question: pergunta literal a exibir ao humano, resumindo o
            motivo da falha de validação (sintática/semântica) e as 2
            tentativas já feitas.
        allowed_decisions: ["resolvido", "abandonar_artefato"]
            — DECIDIDO: sem opção de "prosseguir mesmo assim". A IA nunca
            deve autocorrigir sozinha além do limite de 2 tentativas nem
            deixar o erro passar silenciosamente; a pausa serve só para
            bloquear e avisar um humano. "resolvido" (humano/especialista
            corrigiu fora do ciclo automático → validator revalida do
            zero) ou "abandonar_artefato" (remove este artefato específico
            do lote, sem forçar o pipeline adiante — registra como doubt
            não resolvido). Vocabulário alinhado ao padrão já existente de
            Doubt_Artifact (Bloqueado/Resolvido) em
            shared/tools/design_filesystem.py.
        pause_reason: motivo opcional (ex.: qual camada falhou: sintática
            ou semântica).

    Returns:
        None — ver docstring de shared/tools/hitl_tool.py para o porquê.
    """
    _ = (checkpoint_id, approval_question, allowed_decisions, pause_reason)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Clarificação genérica da fábrica — removida dos agentes de design
# ──────────────────────────────────────────────────────────────────────────────

CLARIFICATION_TOOL_NAME = "tool_ask_clarification"


def remover_clarificacao_generica(agent):
    """Retira do agente de design a via genérica de "parar e perguntar".

    Chamada logo após create_se_agent (shared/agent_factory.py, que não é
    alterado). A fábrica injeta tool_ask_clarification (FunctionTool comum:
    não pausa de verdade e grava um Doubt_Artifact com "EXECUÇÃO PAUSADA",
    que bloqueia check_active_blocks) e anexa _SE_AGENT_POLICY ao prompt.
    O design tem protocolo próprio de Aviso/Doubt e de pausa (as tools
    acima), então as duas coisas são removidas aqui, sem texto substituto.

    Depende do nome _SE_AGENT_POLICY; test_design_agent_policy.py falha se
    ele mudar ou se a política voltar a aparecer.
    """
    from shared.agent_factory import _SE_AGENT_POLICY

    agent.tools = [
        t for t in agent.tools
        if (getattr(t, "name", None) or getattr(t, "__name__", "")) != CLARIFICATION_TOOL_NAME
    ]
    if isinstance(agent.instruction, str):
        agent.instruction = agent.instruction.replace(_SE_AGENT_POLICY, "")
    return agent
