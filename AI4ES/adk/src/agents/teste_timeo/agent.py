
from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.agents import ParallelAgent, SequentialAgent
from google.adk.tools.agent_tool import AgentTool
from datetime import datetime
from zoneinfo import ZoneInfo
from .tools.coder_agent import tool_get_weather
from .prompts import weather_agent_description, weather_agent_instruction
from google.adk.tools import ToolContext


def better_system_instruction_callback(callback_context: CallbackContext, llm_request: LlmRequest):

    callback_context.state["teste_state"] = "teste"
    llm_request.config.system_instruction += f"Hoje é dia {datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y')} e agora são {datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%H:%M:%S')} e o dia da semana é {datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%A')}"
    return None

def before_agent_callback(callback_context: CallbackContext, llm_request: LlmRequest):

    better_system_instruction_callback(callback_context, llm_request)

    context_str = ""
    
    # Inject Financial Context
    llm_request.config.system_instruction += f"\n\n{context_str}"

    return None

# Define the weather_agent 1
weather_agent = LlmAgent(
    model="gemini-3-flash-preview", # Using a capable model for multimodal/reasoning
    name="weather_agent",
    description=weather_agent_description,
    instruction=weather_agent_instruction,
    generate_content_config=GenerateContentConfig(
        temperature=0.4, # Lower temperature for more consistent data extraction
    ),
    tools=[tool_get_weather],
    before_model_callback=before_agent_callback,
)

# Define the weather_agent 2
weather_agent_2 = LlmAgent(
    model="gemini-3-flash-preview", # Using a capable model for multimodal/reasoning
    name="weather_agent_2",
    description=weather_agent_description,
    instruction=weather_agent_instruction,
    generate_content_config=GenerateContentConfig(
        temperature=0.4, # Lower temperature for more consistent data extraction
    ),
    tools=[tool_get_weather],
    before_model_callback=before_agent_callback,
)

workflow_weather = ParallelAgent(
    name="workflow_weather",
    description="Executa agentes em paralelo para obter o tempo em uma cidade.",
    sub_agents=[weather_agent, weather_agent_2],
)

router_agent = LlmAgent(
    model="gemini-3-flash-preview", # Using a capable model for multimodal/reasoning
    name="router_agent",
    description="Roteia para o agente correto.",
    instruction="""
    Você é um agente que vai rotear para o agente correto.
    """,
    generate_content_config=GenerateContentConfig(
        temperature=0.4, # Lower temperature for more consistent data extraction
    ),
    tools=[AgentTool(agent=workflow_weather)],
    before_model_callback=before_agent_callback,
)

agent_validator = LlmAgent(
    model="gemini-3-flash-preview", # Using a capable model for multimodal/reasoning
    name="agent_validator",
    description="Valida se o agente respondeu corretamente.",
    instruction="""
    Você é um agente que vai validar se o agente respondeu corretamente.
    """,
    generate_content_config=GenerateContentConfig(
        temperature=0.4, # Lower temperature for more consistent data extraction
    ),
    before_model_callback=before_agent_callback,
)

root_agent = SequentialAgent(
    name="teste_timeo",
    description="Executa agente de roteador e depois o agente principal.",
    sub_agents=[router_agent,agent_validator],
)