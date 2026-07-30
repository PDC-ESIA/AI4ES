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

FEW_SHOT_TRACEABILITY_MATRIX = """
### EXEMPLO DE MATRIZ DE RASTREABILIDADE (PADRÃO TIME 1 - TACO-IDE)

**CONTEXTO DE ENTRADA:**
"O professor precisa criar um exercício novo para os alunos resolverem, colocando o enunciado e como vai testar se o código está certo. O sistema deve executar o código do aluno em sandbox isolada."

**ARTEFATOS GERADOS NA ANÁLISE:**
- HU-001: Criação de Exercícios de Programação
- RF-005: Execução em Sandbox
- RN-001: O exercício deve possuir enunciado antes de ser publicado.
- RNF-001: O ambiente de execução deve isolar processos e arquivos temporários.

**SAÍDA ESPERADA (ARTEFATO MARKDOWN):**

Persistir como artefato auxiliar, por exemplo com ID `MTR-001`, em `Outros/MTR-001.md`.

```md
# Matriz de Rastreabilidade

| ID do Artefato | Tipo | Descrição/Título | Origem | Motivo de Inclusão | Prioridade | Relacionamentos | Critérios de Aceitação | Caso(s) de Teste |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HU-001 | HU | Criação de Exercícios de Programação | Descrição inicial do professor | Necessidade relatada de disponibilizar exercícios com enunciado e testes | Alta | Relaciona-se a RF-005, RN-001 | CA-1, CA-2, CA-3 | A definir |
| RF-005 | RF | Execução em Sandbox | Necessidade de execução segura do código do aluno | Mitigar risco de comprometimento do servidor ao rodar código de terceiros | Alta | Deriva de HU-001; relaciona-se a RNF-001 | Não aplicável | A definir |
| RN-001 | RN | Exercício deve possuir enunciado antes da publicação | Regra operacional do processo de cadastro | Garantir que o exercício seja compreensível ao aluno antes de disponibilizado | Média | Relaciona-se a HU-001 | Não aplicável | A definir |
| RNF-001 | RNF | Isolamento de processos e arquivos temporários | Restrição técnica de segurança do ambiente | Sustentar a execução segura exigida por RF-005 | Alta | Sustenta RF-005 | Não aplicável | A definir |
```

**REGRAS OBSERVADAS NO EXEMPLO:**
1. A coluna `Caso(s) de Teste` existe, mas não contém casos de teste inventados.
2. As colunas `Motivo de Inclusão` e `Prioridade` seguem os atributos típicos de uma matriz de rastreabilidade de requisitos (ISO/IEC 29110 Perfil Básico / PMBOK) e são preenchidas apenas com base no que é extraído ou diretamente inferível da entrada e do CoT já documentado.
3. `Critérios de Aceitação` referencia os CAs já especificados para HUs; para tipos sem critério de aceite próprio (RF, RN, RNF), usa-se `Não aplicável`.
4. Os relacionamentos registram apenas vínculos explícitos ou diretamente derivados dos artefatos já produzidos.
5. Quando faltar vínculo ou prioridade explícita, use `Não identificado` em vez de inferir.
6. A matriz é persistida como artefato complementar e sua existência deve ser citada no `summary` do `AnalystOutput`.
"""
