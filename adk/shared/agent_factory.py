"""Factory para os agentes de Engenharia de Software."""

import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from shared.tools.clarification import tool_ask_clarification_adk

_DEFAULT_MODEL = "github_copilot/gpt-4"

_SE_AGENT_POLICY = """

---
CRITICAL POLICY (DEFENSIVE PROMPTING):
Você é um agente de Engenharia de Software. Se você encontrar ambiguidades, falta de requisitos, 
código ausente, ou qualquer impeditivo irrecuperável, você NÃO deve inventar ou alucinar informações.
Você DEVE usar a ferramenta 'tool_ask_clarification' para registrar a dúvida e interromper a execução, 
devolvendo o controle ao usuário.
"""

def create_se_agent(name: str, description: str, instruction: str, tools: list = None, **kwargs) -> LlmAgent:
    """Cria um LlmAgent com a base comum aplicada (Tool de Dúvidas + Defensive Prompting)."""
    
    model = LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL))
    
    all_tools = [tool_ask_clarification_adk]
    if tools:
        all_tools.extend(tools)
        
    full_instruction = instruction + _SE_AGENT_POLICY
    
    return LlmAgent(
        model=model,
        name=name,
        description=description,
        instruction=full_instruction,
        tools=all_tools,
        **kwargs
    )
