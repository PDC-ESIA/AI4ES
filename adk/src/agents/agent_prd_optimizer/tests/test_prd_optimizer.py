"""
Script de teste — Agente PRD Optimizer
 
Como executar (a partir da pasta adk/ do repositório):
    python -m src.agents.agent_prd_optimizer.tests.test_prd_optimizer
"""
 
import asyncio
import sys
from pathlib import Path
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent.parent.resolve() / ".env")
print("[DEBUG] MISTRAL_API_KEY carregada:", "SIM" if os.getenv("MISTRAL_API_KEY") else "NAO")
# Aponta o Python para adk/ para resolver os imports corretamente
_ADK_ROOT = Path(__file__).parent.parent.parent.parent.parent.resolve()
sys.path.insert(0, str(_ADK_ROOT))
 
from dotenv import load_dotenv
 
# O .env fica dentro de adk/ (mesmo nível do .env.example)
load_dotenv(_ADK_ROOT / ".env")
 
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
 
from src.agents.agent_prd_optimizer.agent import root_agent
 
# -------------------------------------------------------------------
# CAMINHO DO PRD DE EXEMPLO
# -------------------------------------------------------------------
CAMINHO_PRD_EXEMPLO = str(
    (Path(__file__).parent.parent / "PRD" / "prd_taco_exemplo.md").resolve()
)
 
print("[DEBUG] ADK root:       " + str(_ADK_ROOT))
print("[DEBUG] Caminho do PRD: " + CAMINHO_PRD_EXEMPLO)
print("[DEBUG] Arquivo existe: " + str(Path(CAMINHO_PRD_EXEMPLO).exists()))
 
# -------------------------------------------------------------------
# CENÁRIOS DE TESTE
# -------------------------------------------------------------------
 
CENARIO_1_ARQUIVO = (
    "Voce deve processar o PRD do TACO IDE.\n"
    "\n"
    "O arquivo esta salvo neste caminho absoluto: " + CAMINHO_PRD_EXEMPLO + "\n"
    "\n"
    "Siga exatamente estes passos na ordem:\n"
    "Passo 1: chame a tool tool_ler_prd_arquivo passando o caminho acima.\n"
    "Passo 2: analise o conteudo retornado e fracione em paineis logicos.\n"
    "Passo 3: chame tool_salvar_context_window_json com nome_arquivo_base igual a: context_windows/cw_taco_completo_v1\n"
    "Passo 4: chame tool_salvar_context_window_markdown com nome_arquivo_base igual a: context_windows/cw_taco_completo_v1\n"
    "Passo 5: informe o resumo do que foi gerado.\n"
    "\n"
    "O nome base DEVE ser exatamente: context_windows/cw_taco_completo_v1\n"
)
 
CENARIO_2_TEXTO_DIRETO = (
    "Fracione o seguinte modulo de PRD e gere as Context Windows.\n"
    "\n"
    "Modulo: Sistema de Notificacoes\n"
    "\n"
    "O sistema deve enviar notificacoes por e-mail quando:\n"
    "- Um professor atribuir um novo exercicio a turma.\n"
    "- O prazo de um exercicio estiver proximo (24h antes).\n"
    "- O aluno concluir um exercicio.\n"
    "As notificacoes devem ser configuráveis pelo usuario.\n"
    "O envio deve ser assíncrono via fila Redis Pub/Sub.\n"
    "Registrar log de cada notificacao enviada.\n"
    "\n"
    "Siga exatamente estes passos:\n"
    "Passo 1: fracione o modulo acima em paineis logicos.\n"
    "Passo 2: chame tool_salvar_context_window_json com nome_arquivo_base igual a: context_windows/cw_notificacoes_v1\n"
    "Passo 3: chame tool_salvar_context_window_markdown com nome_arquivo_base igual a: context_windows/cw_notificacoes_v1\n"
    "Passo 4: informe o resumo.\n"
    "\n"
    "O nome base DEVE ser exatamente: context_windows/cw_notificacoes_v1\n"
)
 
CENARIO_3_INCONSISTENCIA = (
    "Analise o seguinte modulo de PRD e execute o protocolo correto para a situacao encontrada:\n"
    "\n"
    "Modulo: Avaliacao Automatica de Codigo\n"
    "\n"
    "Requisito A: O agente deve avaliar o codigo e atribuir nota de 0 a 10.\n"
    "Requisito B: O agente nao deve atribuir notas, apenas dar feedback qualitativo.\n"
    "Requisito C: A avaliacao deve ocorrer em tempo real durante a digitacao.\n"
    "Requisito D: A avaliacao deve ocorrer somente apos o aluno clicar em Submeter.\n"
    "Requisito E: O modelo de avaliacao sera definido futuramente.\n"
    "\n"
    "Este modulo possui contradicoes diretas entre os requisitos.\n"
    "Voce NAO deve tentar fracionar — siga o protocolo de bloqueio:\n"
    "Passo 1: identifique as contradicoes.\n"
    "Passo 2: chame tool_gerar_doubt_artifact_prd com as informacoes do problema.\n"
    "Passo 3: informe que a execucao foi pausada.\n"
    "\n"
    "O nome do arquivo de saida DEVE ser: Doubt_Artifact_PRD.md\n"
)
 
# -------------------------------------------------------------------
# EXECUTOR DE CENÁRIO
# -------------------------------------------------------------------
 
async def executar_cenario(prompt: str, nome: str) -> bool:
    print("\n" + "="*60)
    print("CENARIO: " + nome)
    print("="*60 + "\n")
 
    session_service = InMemorySessionService()
 
    APP_NAME   = "prd_optimizer"
    USER_ID    = "projeto"
    SESSION_ID = "teste_" + nome.lower().replace(" ", "_").replace(":", "")
 
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )
 
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
# VERIFICAÇÃO DE ARTEFATOS
# -------------------------------------------------------------------
 
def verificar_artefatos() -> list:
    # Artefatos são salvos relativos ao diretório onde o comando é executado (adk/)
    base = Path.cwd()
    return [
        ("context_windows/cw_taco_completo_v1.json", (base / "context_windows/cw_taco_completo_v1.json").exists()),
        ("context_windows/cw_taco_completo_v1.md",   (base / "context_windows/cw_taco_completo_v1.md").exists()),
        ("context_windows/cw_notificacoes_v1.json",  (base / "context_windows/cw_notificacoes_v1.json").exists()),
        ("context_windows/cw_notificacoes_v1.md",    (base / "context_windows/cw_notificacoes_v1.md").exists()),
        ("Doubt_Artifact_PRD.md",                    (base / "Doubt_Artifact_PRD.md").exists()),
    ]
 
# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
 
async def main():
    print("Testes — Agente PRD Optimizer\n")
 
    r1 = await executar_cenario(CENARIO_1_ARQUIVO,        "PRD via Arquivo")
    r2 = await executar_cenario(CENARIO_2_TEXTO_DIRETO,   "PRD via Texto Direto")
    r3 = await executar_cenario(CENARIO_3_INCONSISTENCIA, "Inconsistencia")
 
    artefatos = verificar_artefatos()
 
    print("\n" + "="*60)
    print("RELATORIO FINAL")
    print("="*60)
 
    todos_ok = True
 
    print("\nExecucao dos cenarios:")
    for nome, ok in [
        ("Cenario 1: PRD via arquivo",      r1),
        ("Cenario 2: PRD via texto direto", r2),
        ("Cenario 3: Inconsistencia",       r3),
    ]:
        icone = "OK" if ok else "FALHOU"
        print("  [" + icone + "] " + nome)
        if not ok:
            todos_ok = False
 
    print("\nArtefatos gerados em disco:")
    for nome_artefato, existe in artefatos:
        icone = "OK" if existe else "NAO ENCONTRADO"
        print("  [" + icone + "] " + nome_artefato)
        if not existe:
            todos_ok = False
 
    print("="*60)
 
    if todos_ok:
        print("\nTudo certo! Proximo passo: liberar ao Coder.\n")
        sys.exit(0)
    else:
        print("\nAlgo falhou. Verifique os logs acima.\n")
        sys.exit(1)
 
 
if __name__ == "__main__":
    asyncio.run(main())