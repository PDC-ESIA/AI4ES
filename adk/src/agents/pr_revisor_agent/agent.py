from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from .prompts.pr_revisor import revisor_agent_description, revisor_agent_instruction
from .tools.tools_revisao import tool_ler_diff_adk, tool_salvar_relatorio_adk

root_agent = LlmAgent(
    model=LiteLlm("mistral/mistral-small-latest"), 
    name="pr_revisor_agent",
    description=revisor_agent_description,
    instruction=revisor_agent_instruction,
    tools=[
        tool_ler_diff_adk,
        tool_salvar_relatorio_adk
    ]
)