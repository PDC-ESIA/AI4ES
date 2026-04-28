import os
import json
from pathlib import Path

# Ajuste o import conforme a estrutura do seu projeto
from adk.agents.roles.qa_agent.subagents.receive_requirements import receber_requisitos

# Garanta que a variável de ambiente do LLM esteja setada para o teste
os.environ["ADK_LLM_MODEL"] = "github_copilot/gpt-4"

def rodar_testes():
    print("=== INICIANDO TESTES DO RECEIVE REQUIREMENTS ===\n")

    # ---------------------------------------------------------
    # CENÁRIO 1: O Caminho Feliz (JSON estrito que já funcionava)
    # ---------------------------------------------------------
    json_valido = json.dumps([{
        "id_artefato": "RF-001",
        "tipo": "RF",
        "conteudo": "O sistema deve calcular o frete com base no CEP.",
        "modulo": "checkout",
        "criticidade": "alta"
    }])
    
    print("▶ Teste 1: Enviando JSON estruturado...")
    resultado_json = receber_requisitos(json_valido)
    print(f"Status: {resultado_json['status']}")
    print(f"Resumo: {resultado_json.get('resumo', 'N/A')}\n")

    # ---------------------------------------------------------
    # CENÁRIO 2: Texto Fragmentado / Sujo (Alvo da Subtask 1)
    # ---------------------------------------------------------
    texto_fragmentado = """
    Fala equipe, temos as seguintes demandas pra sprint:
    HU: Como usuário deslogado, quero poder ver o catálogo de produtos para saber o que a loja vende.
    E também tem uma Regra de Negócio importante: Se o usuário tentar comprar sem logar, deve redirecionar pra tela de login. Essa regra é de prioridade média.
    """
    
    print("▶ Teste 2: Enviando texto solto (acionando o LLM fallback)...")
    resultado_texto = receber_requisitos(texto_fragmentado)
    print(f"Status: {resultado_texto['status']}")
    print(f"Resumo: {resultado_texto.get('resumo', 'N/A')}\n")

if __name__ == "__main__":
    rodar_testes()