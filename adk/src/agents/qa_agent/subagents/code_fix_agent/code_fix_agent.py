from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from Tools.build_fix_prompt import build_fix_prompt_from_error, build_fix_prompt_from_pytest

root_agent = Agent(
    name="code_fix_agent",
    model="gemini-2.0-flash",
    instruction=(
                "Você é um subagente de um agente de teste"
                "Seu papel é receber logs de funcionamento de programas, entender o que ele significa, e, se ver algum erro, fazer um prompt de correção para um outro agente que irá realizar a codificação."
                "Para isso, você tem as ferramentas de parsing de logs, que irão resumir o log para você, e as ferramentas de construir o prompt"
                ),
    description="",
    tools=[
        FunctionTool(
            func=build_fix_prompt_from_error
        ),
        FunctionTool(
            func=build_fix_prompt_from_pytest
        ),
    ]
)