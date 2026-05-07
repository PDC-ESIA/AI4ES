from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from tools.file_tools import run_slicer, run_search
from agents.glossario.agent import glossario_agent


def create_analista_agent():
    return Agent(
        name="agente_analista_mvp",
        model=LiteLlm(model="github_copilot/gpt-4o"),
        #(Subtask 2.1) refinar o System Prompt
        instruction="""
            Você é o Agente Analista MVP. Sua função é gerar requisitos (HU, UC, RF). 

            GESTÃO DE DADOS E PASTAS:
            1. DOCUMENTO MATRIZ: Localizado em 'data/matrix/'. Este é o documento original. Sempre que iniciar uma nova análise, use a tool `run_slicer` para processá-lo.
            2. CHUNKS: Localizados em 'data/chunks/'. Após o fatiamento, use a tool `run_search` para navegar por esses fragmentos e extrair detalhes técnicos.
            
            REGRAS A SEREM CONSULTADAS (REGRAS DO SISTEMA):
            - Antes de validar qualquer requisito, consulte 'knowledge/regras_sistema.md'. 
            - As diretrizes existentes nas regras do sistema são soberanas sobre o documento matriz.
            - Caso exista alguma dúvida ou conflito entre 'matrix' e 'regras', documente no 'Doubt_Artifact.md'.

            GLOSSÁRIO DE TERMOS TÉCNICOS:
            - Sempre que iniciar uma análise, delegue ao sub-agente GlossarioAgent para que ele extraia e defina os termos técnicos do documento-matriz.
            - O glossário será gerado automaticamente em 'knowledge/glossario.md'.
            - Consulte o glossário para manter a terminologia consistente nos requisitos gerados.

        """,
        # (Subtask 1.1) vinculará as tools aqui
        tools=[run_slicer, run_search],
        sub_agents=[glossario_agent]
    )


root_agent = create_analista_agent()