"""
validador.py
============
Script de validação automatizada de Pull Requests via Agente ADK.

Fluxo de execução:
  1. Extrai o git diff entre a branch atual e a branch de destino (definida por
     GITHUB_BASE_REF, padrão: 'main').
  2. Envia o diff como mensagem para o agente revisor (pr_revisor_agent) usando
     o padrão Runner + InMemorySessionService do Google ADK.
  3. Avalia a resposta final do agente:
       - Contém 'APROVADO'  → exit(0)  — PR liberado.
       - Contém 'REPROVADO' ou 'ERRO' → exit(1) — PR bloqueado.
       - Resposta inconclusiva         → exit(1) — bloqueado por segurança.

Variáveis de ambiente esperadas:
  GITHUB_BASE_REF  – branch de destino do PR (ex.: 'main', 'develop').
  MISTRAL_API_KEY  – chave de autenticação da API Mistral (obrigatória).
"""

import sys
import os
import subprocess
import asyncio

# Adiciona a pasta adk/ ao PYTHONPATH para que os módulos src.* sejam encontrados
# independentemente do diretório de trabalho do processo.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from src.agents.pr_revisor_agent.agent import root_agent

# O ADK infere o app_name a partir do caminho de instalação do pacote google.adk.agents.
# Para evitar o aviso "App name mismatch", usamos o mesmo valor que ele infere: "agents".
APP_NAME = "agents"
USER_ID = "ci_pipeline"


def extrair_diff_codigo() -> str:
    """Executa 'git diff origin/<branch_destino>' e retorna o texto do diff.

    A branch de destino é lida da variável de ambiente GITHUB_BASE_REF,
    que o GitHub Actions preenche automaticamente em eventos de pull_request.
    Se a variável não estiver definida (ex.: execução local), usa 'main'.

    Returns:
        str: Conteúdo completo do diff em texto plano.

    Raises:
        SystemExit(1): Se o comando git falhar (returncode != 0).
    """
    print("Extraindo diferença...\n")

    branch_destino = os.environ.get("GITHUB_BASE_REF", "main")
    alvo = f"origin/{branch_destino}"

    # Captura as linhas de código que estão tentando entrar na branch de destino.
    resultado = subprocess.run(["git", "diff", alvo], capture_output=True, text=True)

    if resultado.returncode != 0:
        # Inclui o alvo na mensagem de erro para facilitar o diagnóstico no log do CI.
        print(f"Erro ao extrair diff contra {alvo}: {resultado.stderr}")
        sys.exit(1)

    return resultado.stdout


async def main() -> None:
    """Ponto de entrada assíncrono: orquestra a extração do diff e a invocação do agente.

    O agente é acionado via Runner.run_async(), que gerencia internamente o ciclo de
    vida da sessão ADK. Apenas eventos marcados como resposta final (is_final_response)
    são considerados para o veredito.
    """
    diff = extrair_diff_codigo()

    # Se não houver alterações (ex.: PR sem commits novos), ignora a validação.
    if not diff.strip():
        print("Sem alterações. Pulando validação.")
        sys.exit(0)

    prompt = (
        "Analise o seguinte git diff e diga se o código segue as boas práticas. "
        "Termine a sua resposta dizendo 'APROVADO' ou 'REPROVADO'.\n"
        f"Diff:\n{diff}"
    )

    # InMemorySessionService mantém o estado da sessão apenas em memória,
    # suficiente para execuções de curta duração como pipelines de CI.
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID)

    # O Runner é responsável por despachar a mensagem ao agente e iterar
    # sobre os eventos gerados (pensamentos, chamadas de ferramentas, resposta final).
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    mensagem = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )

    try:
        print("\n ----- Relatório do Agente ----- ")

        tex_resposta = ""

        async for evento in runner.run_async(
            user_id=USER_ID,
            session_id=session.id,
            new_message=mensagem,
        ):
            # Filtra apenas eventos de resposta final com conteúdo textual.
            # Eventos intermediários (tool_use, tool_result, etc.) são ignorados.
            if evento.is_final_response() and evento.content and evento.content.parts:
                for part in evento.content.parts:
                    if hasattr(part, "text") and part.text:
                        print(part.text, end="", flush=True)
                        tex_resposta += part.text

        print("\n---------------------------------\n")

        # Avalia o veredito de forma case-insensitive.
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

    except Exception as e:
        # Captura qualquer exceção inesperada (ex.: falha de rede, timeout da API)
        # e encerra o processo com código de erro para que o pipeline falhe explicitamente.
        print(f"Erro provavelmente desconhecido ao se comunicar com a IA: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
