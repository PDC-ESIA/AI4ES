import asyncio
from dotenv import load_dotenv
from pathlib import Path
from src.agents.pr_revisor_agent.agent import pr_revisor_agent

# NOVA IMPORTAÇÃO: O "envelope" oficial do ADK
from google.adk.models.llm_request import LlmRequest

# 1. Carrega as variáveis de ambiente
caminho_env = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(caminho_env)

async def executar_teste_local():
    print("🚀 Acordando o Agente Revisor de PRs...")
    
    instrucao_inicial = """
    Inicie o processo de auditoria de código.
    1. Utilize sua ferramenta para ler o 'git diff' da branch atual contra a 'main'.
    2. Analise os resultados com base nas suas diretrizes de qualidade.
    3. Utilize a ferramenta de salvar relatório para gerar o arquivo 'doubt_artifact_revisao.md'.
    """
    
    # 2. Colocamos o texto dentro do envelope LlmRequest
    # (Usamos 'prompt' aqui. Se o Pydantic chiar, ele nos avisará qual é a palavra exata)
    requisicao = LlmRequest(
        prompt=instrucao_inicial,
        session_id="sessao_teste_01"
    )
    
    try:
        print("\n=== RESPOSTA DO AGENTE (AO VIVO) ===\n")
        
        # 3. Passamos o envelope (requisicao) em vez do texto solto
        async for pedaco in pr_revisor_agent.run_live(requisicao):
            print(pedaco, end="", flush=True)
            
        print("\n\n✅ Teste finalizado!")
        
    except Exception as e:
        print(f"\n❌ Erro durante a execução do agente: {e}")

if __name__ == "__main__":
    asyncio.run(executar_teste_local())