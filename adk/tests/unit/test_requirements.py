"""
Script de teste — Agente Requirements (PRD Optimizer)

Como executar (a partir da pasta adk/ do repositorio):
    python -m agents.roles.requirements.tests.test_requirements
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# O .env fica dentro de adk/
_ADK_ROOT = Path(__file__).parent.parent.parent.parent.parent.resolve()
load_dotenv(_ADK_ROOT / ".env")

print("[DEBUG] ADK root: " + str(_ADK_ROOT))
print("[DEBUG] ADK_LLM_MODEL: " + os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4 (padrao)"))

sys.path.insert(0, str(_ADK_ROOT))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.roles.requirements.agent import agent

# -------------------------------------------------------------------
# OPTEI POR NESSE TESTE COLOCAR APENAS A CHAMADA POR PROMPOT, POSTERIORMENTE PODEMOS VER A NECESSIDADE DE COLOCAR A ENTRADA VIA ARQUIVO
# CENARIO UNICO — PRD via texto direto no prompt
# -------------------------------------------------------------------

CENARIO_PRD_TEXTO = (
    "Fracione o seguinte modulo de PRD e gere as Context Windows.\n"
    "\n"
    "Modulo: Autenticacao de Usuarios\n"
    "\n"
    "O sistema deve suportar dois perfis: Aluno e Professor.\n"
    "O cadastro sera feito via e-mail e senha.\n"
    "Deve haver validacao de e-mail com link de confirmacao.\n"
    "O login deve gerar um token JWT com expiracao de 8 horas.\n"
    "O token deve ser renovavel via refresh token.\n"
    "Professores tem permissoes adicionais: criar turmas, adicionar alunos\n"
    "e visualizar relatorios de progresso.\n"
    "O sistema deve bloquear o acesso apos 5 tentativas de login falhas\n"
    "consecutivas por 15 minutos.\n"
    "\n"
    "Siga exatamente estes passos:\n"
    "Passo 1: fracione o modulo acima em paineis logicos.\n"
    "Passo 2: chame tool_salvar_context_window_json com nome_arquivo_base: context_windows/cw_auth_v1\n"
    "Passo 3: chame tool_salvar_context_window_markdown com nome_arquivo_base: context_windows/cw_auth_v1\n"
    "Passo 4: informe o resumo do que foi gerado.\n"
    "\n"
    "O nome base DEVE ser exatamente: context_windows/cw_auth_v1\n"
)

# -------------------------------------------------------------------
# EXECUTOR
# -------------------------------------------------------------------

async def executar_cenario(prompt: str, nome: str) -> bool:
    print("\n" + "="*60)
    print("CENARIO: " + nome)
    print("="*60 + "\n")

    session_service = InMemorySessionService()

    APP_NAME   = "requirements_agent"
    USER_ID    = "taco_ide"
    SESSION_ID = "teste_" + nome.lower().replace(" ", "_")

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    mensagem = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )

    try:
        async for evento in runner.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=mensagem,
        ):
            if evento.is_final_response() and evento.content:
                for part in evento.content.parts:
                    if hasattr(part, "text") and part.text:
                        print(part.text)

        print("\nCenario finalizado: " + nome + "\n")
        return True

    except Exception as e:
        print("\nErro no cenario '" + nome + "': " + str(e))
        return False

# -------------------------------------------------------------------
# VERIFICACAO DE ARTEFATOS
# -------------------------------------------------------------------

def verificar_artefatos() -> list:
    base = Path.cwd()
    return [
        ("context_windows/cw_auth_v1.json", (base / "context_windows/cw_auth_v1.json").exists()),
        ("context_windows/cw_auth_v1.md",   (base / "context_windows/cw_auth_v1.md").exists()),
    ]

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

async def main():
    print("Testes — Agente Requirements\n")

    r1 = await executar_cenario(CENARIO_PRD_TEXTO, "PRD via Texto Direto")

    artefatos = verificar_artefatos()

    print("\n" + "="*60)
    print("RELATORIO FINAL")
    print("="*60)

    todos_ok = True

    print("\nExecucao:")
    icone = "OK" if r1 else "FALHOU"
    print("  [" + icone + "] Cenario: PRD via texto direto")
    if not r1:
        todos_ok = False

    print("\nArtefatos gerados em disco:")
    for nome_artefato, existe in artefatos:
        icone = "OK" if existe else "NAO ENCONTRADO"
        print("  [" + icone + "] " + nome_artefato)
        if not existe:
            todos_ok = False

    print("="*60)

    if todos_ok:
        print("\nTudo certo! Context Window gerada e pronta para revisao.\n")
        sys.exit(0)
    else:
        print("\nAlgo falhou. Verifique os logs acima.\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
