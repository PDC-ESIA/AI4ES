import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.adk.models.llm_request import LlmRequest
from src.agents.pr_revisor_agent.agent import root_agent

# aqui ele vai carregar as variáveis de ambiente (API Key) no arquivo .env que deve estar localizado na raiz do projeto.
caminho_env = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(caminho_env)


async def executar_auditoria_automatizada():
    # apenas para garantir que o script seja executado no terminal, sem interface gráfica, e que o agente possa imprimir seus pensamentos em tempo real.
    print("Iniciando Agente Revisor de PRs em modo Headless (sem interface)...")

    instrucao_inicial = """
    Inicie o processo de auditoria de código.
    1. Utilize sua ferramenta para ler o 'git diff' da branch atual contra a 'main'.
    2. Analise os resultados com base nas suas diretrizes de qualidade.
    3. Utilize a ferramenta de salvar relatório para gerar o arquivo 'doubt_artifact_revisao.md'.
    """

    requisicao = LlmRequest(
        prompt=instrucao_inicial, session_id="sessao_pipeline_automatizado"
    )

    try:
        # vai executar o agente
        async for pedaco in root_agent.run_live(requisicao):
            # imprimir o pensamento do agente no terminal em tempo real
            print(pedaco, end="", flush=True)

        print("\n\nExecução do agente finalizada. Analisando o veredito...\n")

        # vai ler a saída para decidir o status da máquina (Exit Code)
        caminho_relatorio = Path("doubt_artifact_revisao.md")

        if caminho_relatorio.exists():
            conteudo = caminho_relatorio.read_text(encoding="utf-8")

            if "STATUS: APROVADO" in conteudo:
                print("RESULTADO: PR Aprovado pelo Agente!")
                sys.exit(0)  # retorna 0 para sucesso - PR aprovado
            else:
                print("RESULTADO: PR Rejeitado pelo Agente (ou requer ajustes).")
                sys.exit(1)  # retorna 1 para falha) - PR bloqueado
        else:
            print("ERRO: O agente não conseguiu gerar o arquivo de relatório.")
            sys.exit(1)  # também considera falha se o arquivo não foi criado

    except Exception as e:
        print(f"\nErro crítico durante a execução: {e}")
        sys.exit(1)  # e também considera falha se houve uma exceção não tratada.


if __name__ == "__main__":
    asyncio.run(executar_auditoria_automatizada())
