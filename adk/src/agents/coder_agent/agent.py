from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.agents import ParallelAgent, SequentialAgent
from google.adk.tools.agent_tool import AgentTool
from datetime import datetime
from zoneinfo import ZoneInfo
from .tools.coder_agent import tool_git_add, tool_git_checkout, tool_git_commit
from .prompts import coder_agent_description, coder_agent_instruction
from google.adk.tools import ToolContext
from google.adk.models.lite_llm import LiteLlm


root_agent = LlmAgent(
    model=LiteLlm("mistral/mistral-small-latest"),
    name="root_agent",
    description=coder_agent_description,
    instruction=coder_agent_instruction,
    tools=[tool_git_commit, tool_git_checkout, tool_git_add]
)

