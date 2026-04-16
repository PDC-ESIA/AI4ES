from google.adk.agents import Agent

def create_analista_agent():
    """
    Configura o Agente Analista com as diretrizes do Time 1.
    """
    return agent.Agent(
        name="Agente Analista MVP",
        #(Subtask 2.1) refinar o System Prompt
        instructions="""
            Você é o Agente Analista...
        """,
        # (Subtask 1.1) vinculará as tools aqui
        tools=["file_tools"] 
    )