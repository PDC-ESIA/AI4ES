"""
Este arquivo contém exemplos de Few-Shot baseados no sistema TACO-IDE para calibrar 
o comportamento do Agente Analista de Requisitos Crítico.
"""

FEW_SHOT_HU = """
### EXEMPLO DE HISTÓRIA DE USUÁRIO (PADRÃO TIME 1 - TACO-IDE)

**CONTEXTO DE ENTRADA:**
"O professor precisa criar um exercício novo para os alunos resolverem, colocando o enunciado e como vai testar se o código está certo."

**PROCESSO ANALÍTICO (CHAIN OF THOUGHT):**
1. Identificado Ator: Professor.
2. Identificada Ação: Criar exercício.
3. Identificados Componentes: Enunciado e Casos de Teste.
4. Mapeamento de Metadados: Status 'Rascunho', Origem 'Contexto Estruturado'.

**SAÍDA ESPERADA (JSON):**
{
  "id": "HU-001",
  "title": "Criação de Exercícios de Programação",
  "persona": "Professor",
  "action": "Criar exercícios de programação definindo enunciado e casos de teste",
  "value": "Disponibilizar atividades práticas de codificação aos meus estudantes",
  "acceptance_criteria": [
    "CA-1: O sistema deve permitir a inserção de um enunciado em formato Markdown.",
    "CA-2: O sistema deve permitir a configuração de múltiplos casos de teste (entrada e saída esperada).",
    "CA-3: O sistema deve validar se todos os campos obrigatórios foram preenchidos antes de salvar."
  ]
}
"""

FEW_SHOT_RF = """
### EXEMPLO DE REQUISITO FUNCIONAL (PADRÃO TIME 1 - TACO-IDE)

**CONTEXTO DE ENTRADA:**
"O sistema tem que rodar o código do aluno num lugar seguro pra não quebrar o servidor."

**SAÍDA ESPERADA (JSON):**
{
  "id": "RF-005",
  "title": "Execução em Sandbox",
  "description": "O sistema deve executar o código submetido pelo estudante em um ambiente de sandbox isolado, garantindo a integridade do servidor principal.",
  "priority": "Alta",
  "hu_parent": "HU-001"
}
"""

FEW_SHOT_DOUBT = """
### EXEMPLO DE DÚVIDA CRÍTICA (AMBIGUIDADE NO TACO)

**CONTEXTO DE ENTRADA:**
"A inteligência artificial do sistema deve ajudar o aluno quando ele estiver travado."

**PROCESSO ANALÍTICO:**
1. O termo "ajudar" é vago. 
2. A ajuda pode ser: explicar o erro, dar a resposta pronta, dar uma dica progressiva ou sugerir documentação.
3. Decisão: Bloquear a especificação dessa funcionalidade e questionar a regra pedagógica.

**SAÍDA ESPERADA (DOUBT ARTEFACT):**
{
  "id_duvida": "D-002",
  "trecho": "IA deve ajudar o aluno",
  "duvida": "O termo 'ajudar' não define o nível de interferência pedagógica da IA.",
  "impacto": "Risco de a IA fornecer a resposta completa, invalidando o aprendizado (plágio/cola).",
  "sugestao": "Definir se a IA deve atuar como um tutor Socrático (apenas dicas) ou como um assistente de correção (aponta o erro exato)."
}
"""

FEW_SHOT_GLOSSARY = """
### EXEMPLO DE TERMO TÉCNICO (GLOSSÁRIO TACO)

**CONTEXTO DE ENTRADA:**
"O aluno faz a submissão e a IA usa um LLM para analisar o código."

**SAÍDA ESPERADA (GLOSSÁRIO):**
{
  "term": "LLM",
  "definition": "Large Language Model. Modelo de inteligência artificial treinado em vastas quantidades de texto, capaz de compreender e gerar linguagem humana ou código de programação.",
  "source": "Documento de Especificação de Requisitos - Seção 1.3"
}
"""
