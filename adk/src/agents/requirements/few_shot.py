"""
Este arquivo contém exemplos de Few-Shot baseados no sistema TACO-IDE para calibrar
o comportamento do Agente Analista de Requisitos Crítico.

Cada few-shot de artefato persistível (HU, RF, RNF, RN) expõe DUAS saídas:
- SAÍDA 1 — JSON: alimenta o campo correspondente do schema `AnalystOutput`.
- SAÍDA 2 — Markdown: alimenta o argumento `conteudo_md` de
  `tool_salvar_artefato_requisito`, que grava o arquivo no workspace.

PADRÃO DE FORMATAÇÃO DO MARKDOWN (obrigatório e idêntico para todos os tipos):
1. Título H1 no formato `# <ID>: <Título>`.
2. Seção `## Metadados` com tabela de duas colunas `| Campo | Valor |`.
   As duas primeiras linhas são sempre `ID` e `Tipo`; as demais variam por tipo.
3. Conteúdo em seções `##` — nunca em campos inline do tipo `**Rótulo:** valor`.
4. Somente campos que existem no schema entram na tabela — nada é inventado.
"""

FEW_SHOT_HU = """
### EXEMPLO DE HISTÓRIA DE USUÁRIO (PADRÃO TIME 1 - TACO-IDE)

**CONTEXTO DE ENTRADA:**
"O professor precisa criar um exercício novo para os alunos resolverem, colocando o enunciado e como vai testar se o código está certo."

**PROCESSO ANALÍTICO (CHAIN OF THOUGHT):**
1. Identificado Ator: Professor.
2. Identificada Ação: Criar exercício.
3. Identificados Componentes: Enunciado e Casos de Teste.
4. Derivados os critérios de aceitação verificáveis a partir dos componentes.

**SAÍDA 1 — JSON (campo `user_stories` do AnalystOutput):**
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

**SAÍDA 2 — Markdown (argumento `conteudo_md` de `tool_salvar_artefato_requisito` com tipo='HU'):**
# HU-001: Criação de Exercícios de Programação

## Metadados

| Campo   | Valor               |
|---------|---------------------|
| ID      | HU-001              |
| Tipo    | História de Usuário |
| Persona | Professor           |

## História

> Como **Professor**,
> quero **criar exercícios de programação definindo enunciado e casos de teste**,
> para que **possa disponibilizar atividades práticas de codificação aos meus estudantes**.

## Critérios de Aceitação

- [ ] **CA-1:** O sistema deve permitir a inserção de um enunciado em formato Markdown.
- [ ] **CA-2:** O sistema deve permitir a configuração de múltiplos casos de teste (entrada e saída esperada).
- [ ] **CA-3:** O sistema deve validar se todos os campos obrigatórios foram preenchidos antes de salvar.

**REGRAS OBSERVADAS:**
1. A seção `## História` usa blockquote e compõe os campos `persona`, `action` e `value` do JSON na forma "Como / quero / para que".
2. Os itens de `## Critérios de Aceitação` são exatamente os mesmos do array `acceptance_criteria` do JSON, na mesma ordem.
3. HU é o único tipo de artefato que possui critérios de aceitação.
"""

FEW_SHOT_RF = """
### EXEMPLO DE REQUISITO FUNCIONAL (PADRÃO TIME 1 - TACO-IDE)

**CONTEXTO DE ENTRADA:**
"O sistema tem que rodar o código do aluno num lugar seguro pra não quebrar o servidor."

**SAÍDA 1 — JSON (campo `functional_requirements` do AnalystOutput):**
{
  "id": "RF-005",
  "title": "Execução em Sandbox",
  "description": "O sistema deve executar o código submetido pelo estudante em um ambiente de sandbox isolado, garantindo a integridade do servidor principal.",
  "priority": "Alta",
  "hu_parent": "HU-001"
}

**SAÍDA 2 — Markdown (argumento `conteudo_md` de `tool_salvar_artefato_requisito` com tipo='RF'):**
# RF-005: Execução em Sandbox

## Metadados

| Campo      | Valor               |
|------------|---------------------|
| ID         | RF-005              |
| Tipo       | Requisito Funcional |
| Prioridade | Alta                |
| Deriva de  | HU-001              |

## Descrição

O sistema deve executar o código submetido pelo estudante em um ambiente de sandbox isolado, garantindo a integridade do servidor principal.

**REGRAS OBSERVADAS:**
1. O campo `description` do JSON e a seção `## Descrição` do Markdown devem conter o mesmo texto.
2. A linha `Deriva de` da tabela corresponde ao campo `hu_parent` do JSON. Quando não houver HU de origem, use `Não identificado` e trate como lacuna de rastreabilidade.
3. **REGRA CRÍTICA:** RFs NÃO possuem seção de Critérios de Aceitação. Critérios de aceitação pertencem exclusivamente às HUs. Um RF que inclua `## Critérios de Aceitação` está incorreto e deve ser corrigido antes de persistir.
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

FEW_SHOT_RNF = """
### EXEMPLO DE REQUISITO NÃO FUNCIONAL (PADRÃO TIME 1 - TACO-IDE)

**CONTEXTO DE ENTRADA:**
"O sistema tem que ser rápido e responder rápido pra não frustrar o aluno esperando o resultado da submissão."

**COMO DISTINGUIR RNF DE RN:**
- RNF: propriedade de qualidade do sistema — DESEMPENHO, SEGURANÇA, DISPONIBILIDADE, USABILIDADE, MANUTENIBILIDADE. Responde a 'quão bem o sistema faz algo'.
- RN: restrição ou política de domínio — o que é permitido/proibido/obrigatório. Responde a 'o que o sistema DEVE ou NÃO DEVE permitir'.

**SAÍDA 1 — JSON (campo `non_functional_requirements` do AnalystOutput):**
{
  "id": "RNF-001",
  "title": "Tempo de Resposta da Execução",
  "description": "O sistema deve retornar o resultado de uma submissão de código em até 5 segundos para 95% das execuções em condições normais de carga.",
  "category": "Desempenho"
}

**SAÍDA 2 — Markdown (argumento `conteudo_md` de `tool_salvar_artefato_requisito` com tipo='RNF'):**
# RNF-001: Tempo de Resposta da Execução

## Metadados

| Campo     | Valor                   |
|-----------|-------------------------|
| ID        | RNF-001                 |
| Tipo      | Requisito Não Funcional |
| Categoria | Desempenho              |

## Descrição

O sistema deve retornar o resultado de uma submissão de código em até 5 segundos para 95% das execuções em condições normais de carga.

## Métrica de Verificação

Tempo de resposta ≤ 5s medido no percentil 95 em ambiente de produção.

**REGRAS OBSERVADAS:**
1. A categoria deve ser EXATAMENTE um destes valores: Desempenho, Segurança, Disponibilidade, Usabilidade, Manutenibilidade, Escalabilidade, Confiabilidade, Portabilidade, Compatibilidade, Interoperabilidade, Implantação, Adequação Funcional. Não invente categorias fora desta lista.
2. O campo `description` do JSON e a seção `## Descrição` do Markdown devem conter o mesmo texto.
3. RNFs NÃO possuem `hu_parent` (diferente dos RFs) nem critérios de aceitação.
4. A `## Métrica de Verificação` deve ser mensurável e objetiva — nunca vaga (ex: 'deve ser rápido' não é válido).
"""

FEW_SHOT_RN = """
### EXEMPLO DE REGRA DE NEGÓCIO (PADRÃO TIME 1 - TACO-IDE)

**CONTEXTO DE ENTRADA:**
"O sistema de submissão de exercícios só aceita arquivos .py. O aluno não pode resubmeter depois que o prazo do exercício expirar. O professor é o único que pode encerrar o prazo."

**COMO DISTINGUIR RN DE RNF:**
- RNF (Requisito Não Funcional): propriedade de qualidade do sistema — desempenho, disponibilidade, segurança, usabilidade, etc. Responde a 'quão bem o sistema faz algo'.
- RN (Regra de Negócio): restrição ou política do domínio que define o que é permitido/proibido/obrigatório do ponto de vista das regras do negócio. Responde a 'o que o sistema DEVE ou NÃO DEVE permitir, independentemente de como é implementado'.

**PROCESSO ANALÍTICO:**
1. "Só aceita .py" → restrição de domínio (qual tipo de arquivo é válido). NÃO é performance nem usabilidade → RN.
2. "Não pode resubmeter após prazo expirado" → regra de negócio do processo de avaliação → RN.
3. "Só o professor pode encerrar o prazo" → regra de autorização de domínio → RN.

**SAÍDA 1 — JSON (campo `business_rules` do AnalystOutput — cada item é uma entrada separada na lista):**
[
  {
    "id": "RN-001",
    "description": "O sistema deve aceitar exclusivamente arquivos com extensão .py nas submissões de exercícios. Outros formatos devem ser rejeitados com mensagem de erro clara."
  },
  {
    "id": "RN-002",
    "description": "Após a expiração do prazo de um exercício, o sistema deve impedir qualquer nova submissão por parte do aluno, mesmo que o aluno ainda tenha o exercício aberto."
  },
  {
    "id": "RN-003",
    "description": "Somente o professor responsável pelo exercício pode encerrar manualmente o prazo de submissão antes da data configurada."
  }
]

**SAÍDA 2 — Markdown (argumento `conteudo_md` de `tool_salvar_artefato_requisito` com tipo='RN'):**
Cada RN gera um arquivo separado. Exemplo para RN-001:

# RN-001: Formato de Arquivo Aceito em Submissões

## Metadados

| Campo | Valor            |
|-------|------------------|
| ID    | RN-001           |
| Tipo  | Regra de Negócio |

## Regra

O sistema deve aceitar exclusivamente arquivos com extensão .py nas submissões de exercícios. Outros formatos devem ser rejeitados com mensagem de erro clara.

**REGRAS OBSERVADAS NO EXEMPLO:**
1. RNs são restrições ou políticas do domínio — o que é permitido, proibido ou obrigatório.
2. RNs NÃO são atributos de qualidade do sistema (desempenho, segurança, disponibilidade) — esses são RNFs.
3. Cada RN é atômica: uma única regra por artefato.
4. O campo `description` do JSON e a seção `## Regra` do Markdown devem conter o mesmo texto.
5. RNs frequentemente surgem de restrições explícitas no texto ("só aceita", "não pode", "apenas", "obrigatoriamente") ou de regras implícitas do domínio que o analista deve detectar.
6. Cada RN deve ser persistida individualmente com `tool_salvar_artefato_requisito(tipo='RN', id_req='RN-001', ...)`.
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

