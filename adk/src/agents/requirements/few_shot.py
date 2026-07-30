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
### EXEMPLO DE MATRIZ DE RASTREABILIDADE BIDIRECIONAL (PADRÃO TIME 1 - TACO-IDE)

**CONTEXTO DE ENTRADA:**
"O professor precisa criar um exercício novo para os alunos resolverem, colocando o enunciado e como vai testar se o código está certo. O sistema deve executar o código do aluno em sandbox isolada. Além disso, o sistema deve ter um limite de 5 segundos por execução de teste."

**ARTEFATOS GERADOS NA ANÁLISE:**
- HU-001: Criação de Exercícios de Programação
- RF-005: Execução em Sandbox (deriva de HU-001)
- RN-001: O exercício deve possuir enunciado antes de ser publicado (relacionada a HU-001)
- RNF-001: O ambiente de execução deve isolar processos e arquivos temporários (sustenta RF-005)
- RF-009: Limite de tempo de execução de 5 segundos por teste — **gerado sem menção explícita a uma HU de origem no texto**

**PASSO DA MATRIZ (RACIOCÍNIO):**
1. Backward: HU-001 -> origem explícita de RF-005 e RN-001 (ambos citam o mesmo cenário do professor).
2. Backward: RF-005 -> origem de RNF-001 (isolamento sustenta a execução em sandbox).
3. Backward: RF-009 -> **nenhuma HU de origem explícita no texto**. LACUNA detectada.
4. Forward: HU-001 -> origina RF-005 e RN-001. OK, sem lacuna.
5. Como RF-009 não tem origem rastreável, gera-se `lacuna_detectada=true` para RF-009 e um Doubt_Artifact correspondente (não se infere uma HU fictícia para "fechar" a lacuna).

**SAÍDA ESPERADA (JSON — campo `traceability_matrix` de `AnalystOutput`):**
{
  "id": "MTR-001",
  "itens": [
    {
      "id_artefato": "HU-001",
      "tipo": "HU",
      "descricao": "Criação de Exercícios de Programação",
      "origem": "Descrição inicial do professor",
      "motivo_inclusao": "Necessidade relatada de disponibilizar exercícios com enunciado e testes",
      "prioridade": "Alta",
      "rastreabilidade_backward": [],
      "rastreabilidade_forward": [
        {"id_artefato_relacionado": "RF-005", "tipo_artefato_relacionado": "RF", "tipo_relacao": "origina"},
        {"id_artefato_relacionado": "RN-001", "tipo_artefato_relacionado": "RN", "tipo_relacao": "origina"}
      ],
      "criterios_aceitacao": ["CA-1", "CA-2", "CA-3"],
      "casos_teste": "A definir",
      "id_agente_origem": "requirements_agent",
      "lacuna_detectada": false,
      "lacuna_descricao": null
    },
    {
      "id_artefato": "RF-005",
      "tipo": "RF",
      "descricao": "Execução em Sandbox",
      "origem": "Necessidade de execução segura do código do aluno",
      "motivo_inclusao": "Mitigar risco de comprometimento do servidor ao rodar código de terceiros",
      "prioridade": "Alta",
      "rastreabilidade_backward": [
        {"id_artefato_relacionado": "HU-001", "tipo_artefato_relacionado": "HU", "tipo_relacao": "deriva_de"}
      ],
      "rastreabilidade_forward": [
        {"id_artefato_relacionado": "RNF-001", "tipo_artefato_relacionado": "RNF", "tipo_relacao": "sustentado_por"}
      ],
      "criterios_aceitacao": ["Não aplicável"],
      "casos_teste": "A definir",
      "id_agente_origem": "requirements_agent",
      "lacuna_detectada": false,
      "lacuna_descricao": null
    },
    {
      "id_artefato": "RF-009",
      "tipo": "RF",
      "descricao": "Limite de tempo de execução de 5 segundos por teste",
      "origem": "Trecho: 'sistema deve ter um limite de 5 segundos por execução de teste'",
      "motivo_inclusao": "Restrição operacional explícita no texto",
      "prioridade": "Não identificado",
      "rastreabilidade_backward": [],
      "rastreabilidade_forward": [],
      "criterios_aceitacao": ["Não aplicável"],
      "casos_teste": "A definir",
      "id_agente_origem": "requirements_agent",
      "lacuna_detectada": true,
      "lacuna_descricao": "RF-009 não possui HU de origem explícita no texto de entrada (lacuna de rastreabilidade backward)."
    }
  ],
  "lacunas_candidatas_doubt": [
    "RF-009 sem HU de origem identificável no texto — candidato a Doubt_Artifact."
  ],
  "markdown": "# Matriz de Rastreabilidade\\n\\n| ID do Artefato | Tipo | Descrição/Título | Origem | Motivo de Inclusão | Prioridade | Rastreabilidade Backward | Rastreabilidade Forward | Critérios de Aceitação | Caso(s) de Teste |\\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\\n| HU-001 | HU | Criação de Exercícios de Programação | Descrição inicial do professor | Necessidade relatada de disponibilizar exercícios com enunciado e testes | Alta | Não identificado | RF-005, RN-001 | CA-1, CA-2, CA-3 | A definir |\\n| RF-005 | RF | Execução em Sandbox | Necessidade de execução segura do código do aluno | Mitigar risco de comprometimento do servidor ao rodar código de terceiros | Alta | HU-001 | RNF-001 | Não aplicável | A definir |\\n| RN-001 | RN | Exercício deve possuir enunciado antes da publicação | Regra operacional do processo de cadastro | Garantir que o exercício seja compreensível ao aluno antes de disponibilizado | Média | HU-001 | Nenhum | Não aplicável | A definir |\\n| RNF-001 | RNF | Isolamento de processos e arquivos temporários | Restrição técnica de segurança do ambiente | Sustentar a execução segura exigida por RF-005 | Alta | RF-005 | Nenhum | Não aplicável | A definir |\\n| RF-009 | RF | Limite de tempo de execução de 5 segundos por teste | Trecho: 'limite de 5 segundos por execução de teste' | Restrição operacional explícita no texto | Não identificado | Não identificado (LACUNA) | Nenhum | Não aplicável | A definir |\\n"
}

**DOUBT ARTIFACT GERADO A PARTIR DA LACUNA:**
{
  "id_duvida": "D-003",
  "trecho": "RF-009 (limite de 5 segundos por execução de teste)",
  "duvida": "Não há HU explícita ou diretamente inferível associada a este RF; a origem/valor de negócio do requisito não está rastreável.",
  "impacto": "Sem rastreabilidade backward, o requisito fica sem justificativa de negócio auditável e sem cobertura de teste vinculada a uma necessidade do usuário.",
  "sugestao": "Confirmar se este limite decorre de uma HU já registrada (ex: HU-001) ou se deve ser tratado como RNF autônomo com justificativa própria."
}

**REGRAS OBSERVADAS NO EXEMPLO:**
1. A matriz é bidirecional: cada item registra explicitamente `rastreabilidade_backward` (origem) e `rastreabilidade_forward` (derivados), alinhado às práticas de RTM da ISO/IEC/IEEE 29148 e do BABOK/PMBOK.
2. O mesmo conteúdo é entregue em dois formatos consistentes: objeto estruturado (`itens`, campo JSON) e tabela (`markdown`).
3. Os campos `id_agente_origem` e `tipo_relacao` são genéricos o suficiente para consumo por agentes futuros (Design, Codificação, Testes), sem acoplamento ao domínio do TACO-IDE.
4. A coluna/campo `Caso(s) de Teste` existe, mas nunca é preenchida com casos de teste inventados.
5. Lacunas de rastreabilidade (RF sem HU de origem, HU sem derivados) são marcadas em `lacuna_detectada`/`lacuna_descricao`, agregadas em `lacunas_candidatas_doubt` e resultam em um Doubt_Artifact — nunca são preenchidas com vínculos inferidos artificialmente.
6. A matriz (JSON + Markdown) é persistida junto aos demais artefatos e sua geração — incluindo a existência de lacunas — é citada no `summary` do `AnalystOutput`.
"""
