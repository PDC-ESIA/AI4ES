> ### 🔍 Checklist de Validação Rápida (Anti-Alucinação)
> **1. Importações:** Os pacotes e classes existem na doc oficial e no `requirements.txt`?
> **2. Assinaturas:** Os nomes das funções da equipe estão certos? A IA inventou parâmetros (ex: `auto_clean`, `force`)?
> **3. Lógica:** A IA usou caminhos absurdos (ex: recursão infinita) ou mascarou erros (usando `try...except` que força o sucesso)?
> **4. Validação (Asserts):** O `assert` está validando o resultado real do sistema ou apenas testando variáveis fixas/vazias (ex: `assert True`)?

# Artefato de Dúvidas (Doubt Artifact)
**Documentação de anomalias, erros, alucinações e comportamentos suspeitos da IA.**

---

* **ID do Artefato:** [ Ex: RF-001 ou ID do teste ]
* **Data/Hora do Erro:** {{timestamp}}
* **Arquivo Analisado:** {{test_name}}
* **Agente:** qa_agente
* **Status:** 🔴 Alucinação Confirmada

**Trecho Suspeito:**
O agente deve colar o código suspeito aqui

**Motivo da Dúvida/Invalidação:**
O motivo da invalidacao/suvida

**Contexto**
Artefato recebido: [ Ex: RF-001 - Teste de geração de vetor ]

Módulo: [ Ex: Processamento de Dados ]

Etapa onde o bloqueio ocorreu: Validação manual do código gerado (Monitoramento QA).

**O que foi tentado**
O agente tentou fazer a validacao atraves de uma API que não foi respondida


**O que é necessário para continuar**
Revalidar a API usada e substituir


**Artefatos relacionados**
Artefatos que tenham relacao com o que esta sendo relatadp