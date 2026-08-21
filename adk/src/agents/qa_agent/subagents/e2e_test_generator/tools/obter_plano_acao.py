"""Recupera o plano de ação já validado, direto do estado da sessão."""

from google.adk.tools import ToolContext


def obter_plano_acao(tool_context: ToolContext) -> str:
    """Retorna o JSON do último plano gerado pelo action_planner nesta sessão.

    Isso evita depender de o LLM copiar manualmente o JSON completo do
    action_planner através da conversa — o valor é lido diretamente do
    estado da sessão, preenchido automaticamente via output_key.

    Returns:
        O JSON (como string) do último plano de ação, ou uma string vazia
        se nenhum plano foi gerado ainda nesta sessão.
    """
    return tool_context.state.get("last_action_plan", "")