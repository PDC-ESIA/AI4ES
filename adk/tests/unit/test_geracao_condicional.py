import os
import json
from pathlib import Path

# Ajuste o import conforme o ambiente
from adk.agents.roles.qa_agent.subagents.receive_requirements import receber_requisitos

def rodar_teste_subtask2():
    print("=== INICIANDO TESTE DA SUBTASK 2: GERAÇÃO CONDICIONAL ===\n")

    # ---------------------------------------------------------
    # CENÁRIO 1: Apenas Requisito (Espera-se um Esqueleto)
    # ---------------------------------------------------------
    cenario_sem_codigo = [{
        "id_artefato": "RF-SKELETON",
        "tipo": "RF",
        "conteudo": "O sistema deve verificar se o e-mail informado contém '@' e '.com'.",
        "modulo": "validacao_email",
        "criticidade": "media"
        # Repare: não estamos enviando a chave "arquivos_apoio"
    }]

    print("▶ Teste 1: Gerando teste SEM código fonte anexado...")
    res1 = receber_requisitos(json.dumps(cenario_sem_codigo))
    print(f"Status: {res1['status']}\n")

    # ---------------------------------------------------------
    # CENÁRIO 2: Requisito + Código-fonte (Espera-se Teste Completo)
    # ---------------------------------------------------------
    cenario_com_codigo = [{
        "id_artefato": "RF-COMPLETO",
        "tipo": "RF",
        "conteudo": "A função somar_valores deve retornar a soma matemática de dois números.",
        "modulo": "matematica",
        "criticidade": "alta",
        "arquivos_apoio": [
            {
                "nome": "matematica.py",  # O .py no final é o que ativa o nosso "tem_codigo = True"
                "conteudo": "def somar_valores(a, b):\n    return a + b\n"
            }
        ]
    }]

    print("▶ Teste 2: Gerando teste COM código fonte (matematica.py) anexado...")
    res2 = receber_requisitos(json.dumps(cenario_com_codigo))
    print(f"Status: {res2['status']}\n")

    print("✅ Execução concluída! Vá verificar os arquivos na pasta 'artefactsTests'.")

if __name__ == "__main__":
    rodar_teste_subtask2()