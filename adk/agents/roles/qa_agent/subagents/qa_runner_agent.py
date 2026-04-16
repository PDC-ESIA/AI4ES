import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool

from ..tools.pytest_runner import executar_pytest_tool, gerar_teste_via_hu

agent = LlmAgent(
    name="qa_runner_agent",
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4")),
    instruction=(
        "Você é o subagente de QA responsável por garantir a cobertura e o sucesso de testes automatizados. "
        "Seu fluxo de trabalho rigoroso é:\n"
        "1. Receber uma História de Usuário (HU) ou requisito funcional.\n"
        "2. Usar a ferramenta para gerar a estrutura do teste em código.\n"
        "3. Executar os testes utilizando o Pytest para validar o sucesso e a cobertura de código.\n"
        "Regras estritas:\n"
        "- Se a execução do teste retornar 'status': 'sucesso', finalize a tarefa.\n"
        "- Se a execução do teste retornar 'status': 'falha' e solicitar roteamento (proxima_acao_orquestrador: trigger_correcao_matunag), "
        "NÃO tente corrigir o código ou adivinhar o erro. O seu papel encerra aqui. Devolva o payload de erro imediatamente "
        "para que o supervisor possa acionar o subagente de correção (code_fix_agent)."
    ),
    description="Subagente responsável por gerar testes unitários a partir de HUs e auditá-los via Pytest.",
    tools=[
        FunctionTool(
            func=gerar_teste_via_hu
        ),
        FunctionTool(
            func=executar_pytest_tool
        ),
    ]
)