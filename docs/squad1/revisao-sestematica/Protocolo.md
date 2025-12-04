# **Protocolo de Revisão Sistemática da Literatura (RSL)**

**Tema:** *IA Generativa na Engenharia de Software*  
 **Versão:** 1.0  
 **Autores:** *PDC*  
 **Data:** *24/11/25*

**1\. Introdução**

Este protocolo documenta todas as etapas e procedimentos necessários para conduzir uma Revisão Sistemática da Literatura (RSL) sobre o uso de **IA Generativa (GenAI)** nas atividades da **Engenharia de Software (ES)**.

## **2\. Objetivos**

### **Objetivo Geral**

Investigar o estado da arte e da prática sobre o uso de IA Generativa nas diversas atividades da Engenharia de Software.

### **Objetivos Específicos**

* Identificar em quais atividades da ES a GenAI está mais madura.

* Catalogar técnicas, modelos e métodos usados.

* Mapear métricas de avaliação.

* Identificar riscos, limitações e desafios.

* Avaliar o nível de consolidação da área.

* Identificar lacunas e oportunidades de pesquisa.

## **3\. Questões de Pesquisa (RQs)**

**RQ1.** Quais atividades da Engenharia de Software têm maior maturidade no uso de IA Generativa?  
 **RQ2.** Quais modelos e técnicas de IA Generativa são utilizados nas atividades de ES?  
 **RQ3.** Quais métricas são utilizadas para avaliar GenAI em Engenharia de Software?  
 **RQ4.** Quais riscos, limitações e desafios são reportados no uso de GenAI em ES?  
 **RQ5.** Quais lacunas de pesquisa existem na aplicação de GenAI em ES?  
 **RQ6.** Qual é o nível de consolidação da área (experimental vs madura)?

## **4\. PICOC**

| Elemento | Definição |
| ----- | ----- |
| **P (Population)** | Estudos primários sobre uso de IA Generativa em ES |
| **I (Intervention)** | Aplicação de GenAI (LLMs, multimodais, difusão etc.) |
| **C (Comparison)** | Não se aplica |
| **O (Outcome)** | Desempenho, qualidade, produtividade, riscos, maturidade |
| **C (Context)** | Atividades da Engenharia de Software (SWEBOK) |

## **5\. Estratégia de Busca**

### **5.1 Bases de Dados**

* Scopus

* IEEE Xplore

* ACM Digital Library

* Engineering Village

* Web of Science

* arXiv

### **5.2 Termos de Busca**

**Termos relacionados a GenAI:**

* "generative AI"

* "genAI"

* "large language model" OR "LLM"

* "foundation model"

* "multimodal model"

* "diffusion model"

* "AI-assisted"

**Termos relacionados a Engenharia de Software:**

* "software engineering"

* "requirements engineering"

* "software architecture"

* "software design"

* "software testing"

* "devops"

* "software maintenance"

* "software project management"

* "code generation"

* "test generation"

### **5.3 String de Busca (versão inicial)**

`("generative AI" OR "genAI" OR "large language model" OR "LLM" OR`   
 `"foundation model" OR "AI-assisted" OR "AI-assisted software")`   
`AND`   
`("software engineering" OR "requirements engineering" OR "software architecture"`   
 `OR "software design" OR "software testing" OR "devops" OR "software maintenance"`   
 `OR "software project management" OR "code generation" OR "test generation")`

Strings serão adaptadas conforme as regras e sintaxes de cada base.

## **6\. Critérios de Inclusão e Exclusão**

### **6.1 Critérios de Inclusão (CI)**

* CI1: Estudos que utilizam IA Generativa em atividades de ES.

* CI2: Estudos que apresentem avaliação, proposta, método, ferramenta ou aplicação prática.

* CI3: Estudos completos (journal, conference, workshop, arXiv relevante).

* CI4: Publicados em inglês ou português.

### **6.2 Critérios de Exclusão (CE)**

* CE1: Estudos que **não utilizam IA Generativa**.

* CE2: Estudos fora do escopo da Engenharia de Software.

* CE3: Duplicatas.

* CE4: Estudos sem acesso ao texto completo.

* CE5: Versões preliminares quando a versão completa existir.

## **7\. Processo de Seleção dos Estudos (PRISMA)**

As etapas serão:

1. **Identificação**

   * Busca automática nas bases

   * Importação para gerenciador (Zotero, Rayyan, Parsifal etc.)

2. **Triagem**

   * Remoção de duplicatas

   * Leitura de títulos

   * Leitura de resumos

3. **Elegibilidade**

   * Leitura completa

   * Aplicação dos critérios de inclusão/exclusão

4. **Inclusão**

   * Lista final de estudos aceitos

   * Consolidação de dados

O diagrama PRISMA será produzido ao final.

## **8\. Avaliação de Qualidade**

Os estudos serão avaliados usando uma pontuação de 0–2:

* **0** \= Não descrito

* **1** \= Parcialmente descrito

* **2** \= Totalmente descrito

### **Critérios:**

| ID | Critério | Relacionado a |
| ----- | ----- | ----- |
| CQ1 | Método descrito | RQ1/RQ2 |
| CQ2 | Avaliação descrita | RQ3 |
| CQ3 | Limitações/riscos descritos | RQ4 |
| CQ4 | Disponibilização de artefatos (código, dados, prompts) | Reprodutibilidade |
| CQ5 | Evidência prática | RQ1/RQ6 |
| CQ6 | Objetivo claro | Qualidade geral |
| CQ7 | Contribuições explícitas | Qualidade geral |
| CQ8 | Limitações explícitas | Validade |

A pontuação de cada estudo será usada na interpretação final.

## **9\. Formulário de Extração de Dados**

### **9.1 Metadados Gerais**

* Título

* Autores

* Afiliação

* Ano

* País

* Veículo de publicação

* Tipo (journal, conference, workshop, arXiv etc.)

* Fonte de busca

### **9.2 Qualidade do Estudo**

* Tipo de evidência (experimento, survey, estudo de caso etc.)

* Amostra (n)

* Reprodutibilidade (código/prompts/dados disponíveis?)

### **9.3 Atividade de ES (base SWEBOK)**

* Requisitos

* Arquitetura

* Design

* Construção

* Testes

* Operações / DevOps

* Manutenção

* Gestão de Projeto

### **9.4 Tipo de IA Generativa**

* Modelo (GPT-x, Llama, Claude, StarCoder etc.)

* Tipo (LLM, multimodal, difusão etc.)

* Tamanho do modelo (se informado)

* Acesso (open-source vs comercial)

* Técnica utilizada:

  * Prompt Engineering

  * Chain-of-Thought

  * Program-of-Thought

  * ReAct

  * Self-Refine

  * Multi-agent

  * RAG

### **9.5 Métricas Utilizadas**

* Precisão / correção

* Coerência

* Produtividade

* Redução de esforço

* Carga cognitiva

* Segurança

* Custos

### **9.6 Resultados**

* Benefícios

* Limitações

* Desafios

* Lacunas

* Recomendações

## **10\. Procedimento de Síntese**

### **10.1 Síntese Quantitativa (se aplicável)**

* Frequência por atividade do SWEBOK

* Frequência por tipo de modelo

* Distribuição temporal

* Métricas mais utilizadas

### **10.2 Síntese Qualitativa**

* Análise temática

* Classificação dos tipos de uso

* Framework conceitual

* Identificação de lacunas

* Recomendações para pesquisa futura

## **11\. Ameaças à Validade**

* Ameaças à seleção (viés de busca)

* Ameaças à extração (interpretação)

* Ameaças à análise (viés do pesquisador)

* Ameaças de publicação (preprints e indústria)

* Rapidez da evolução na área de IA Generativa

## **12\. Plano de Atualização**

Devido à velocidade de evolução da IA Generativa, recomenda-se atualização **anual** da revisão.

