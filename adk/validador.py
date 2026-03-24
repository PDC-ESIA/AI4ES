import sys
import os
import subprocess
import asyncio

# as duas linhas abaixo adicionam a pasta adk/ do repositório à lista de pastas conhecidas do python. Em seguida, ele importa o agente dessa pasta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from google.adk.models.llm_request import LlmRequest
from src.agents.pr_revisor_agent.agent import root_agent


def extrair_diff_codigo():

    print("Extraindo diferença...\n")

    branch_destino = os.environ.get("GITHUB_BASE_REF", "main")
    alvo = f"origin/{branch_destino}"

    # captura as linhas de código que estão tentando entrar na main
    resultado = subprocess.run(["git", "diff", alvo], capture_output=True, text=True)

    if resultado.returncode != 0:
        print("Erro ao extrair diff contra {alvo}")
        sys.exit(1)

    return resultado.stdout


async def main():
    diff = extrair_diff_codigo()

    # Se o texto estiver vazio, ignora.
    if not diff.strip():
        print("Sem alterações. Pulando validação.")
        sys.exit(0)

    prompt = f"Analise o seguinte git diff e diga se o código segue as boas práticas. Termine a sua resposta dizendo 'APROVADO' ou 'REPROVADO'. Diff:\n{diff}"

    requisicao = LlmRequest(prompt=prompt, session_id="sessao_validador_pr")
    try:
        # chama o agente

        print("\n ----- Relatório do Agente ----- ")

        tex_resposta = ""

        async for pedaco in root_agent.run_live(requisicao):
            print(pedaco, end="", flush=True)
            tex_resposta += str(pedaco)

        print("---------------------------------\n")
        relatorio = tex_resposta.upper()
        if "REPROVADO" in relatorio or "ERRO" in relatorio:
            print("Erros encontrados no código ou no agente. Bloqueado")
            sys.exit(1)
        elif "APROVADO" in relatorio:
            print("APROVADO")
            sys.exit(0)
        else:
            print(
                "O agente retornou uma resposta inconclusiva. Bloqueado por segurança"
            )
            sys.exit(1)

    # Segurança. Se houver algum erro e o script não chamar o agente, vai retornar esse erro ao invés de quebrar o código.
    except Exception as e:
        print(f"Erro provavelmente desconhecido ao se comunicar com a IA: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
