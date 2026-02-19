# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | Atlassian Intelligence (Jira Software) |
| **Versão (se aplicável):** | - |
| **URL oficial para acesso à ferramenta/documentação:** | https://www.atlassian.com/trust/atlassian-intelligence |
| **Data da avaliação:** | 20/01/2026 |
| **Avaliador:** | Danilo Sucupira Galvão |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

A ferramenta funciona como um assistente virtual embutido na suíte Atlassian (Jira, Confluence), utilizando modelos da OpenAI para tarefas de processamento de linguagem natural. É destinada primariamente a Gerentes de Projetos, Product Owners e Scrum Masters para agilizar a gestão de tickets, resumir contextos de discussão e facilitar consultas (JQL). Pode ser utilizada para resumir threads de comentários, gerar User Stories a partir de frases curtas e criar filtros de busca via linguagem natural.

> _[Ferramenta focada em gestão e produtividade dentro de um ecossistema fechado]_  
> 

---

## **3) Avaliação por Critérios de Inclusão**

Para cada critério, marque **Sim / Parcial / Não**, responda às perguntas-chave fornecendo as evidências necessárias.

---

### **C1 — Cobertura do SDLC**

Descrição: A ferramenta apoia explicitamente pelo menos uma fase do SDLC (ex.: requisitos, projeto, implementação, testes, manutenção).

**Fase(s) do SDLC apoiadas (marque todas):** - ☑ Requisitos  
- ☐ Projeto/Arquitetura  
- ☐ Implementação  
- ☐ Testes  
- ☐ Integração/CI-CD  
- ☑ Manutenção/Evolução  
- ☑ Outra: Gestão de Projetos

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita?  
  *Atua fortemente na Elicitação/Gestão de Requisitos e na Manutenção.*
- A atuação cobre atividades centrais da fase? Quais? 
  *Sim, cobre a escrita de User Stories e o refinamento de backlog.*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C2 — Apoio ativo por IA**

Descrição: A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA (não apenas edição ou automação tradicional).  

**Tipo de apoio por IA (marque):** - ☑ Geração automática  
- ☑ Sugestão/recomendação  
- ☑ Análise inteligente  
- ☑ Automação baseada em IA  
- ☐ Outro: ___________

**Perguntas orientadoras (responder brevemente):**
- A IA é central para a funcionalidade da ferramenta?  
  *Não, o Jira funciona sem ela. A IA é um "add-on" de produtividade.*
- Que capacidades “inteligentes” foram observadas na prática?  
  *Conversão de linguagem natural para JQL (Query Language) e resumos de contexto (RAG sobre tickets).*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas?  
  *Leitura de longas threads de comentários (substituída por resumos) e criação manual de consultas de banco de dados.*
- O ganho de produtividade foi significativo ou marginal?  
  *Significativo para gestão, marginal para engenharia de código.*
- Foi necessário muito retrabalho/revisão manual?    
  *Pouco retrabalho, a ferramenta é precisa no contexto textual.*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):** - ☑ Qualidade dos requisitos
- ☐ Qualidade do design
- ☐ Qualidade do código  
- ☐ Qualidade dos testes  
- ☑ Qualidade da documentação  
- ☐ Consistência/detecção de erros  
- ☐ Outro: ___________

**Perguntas orientadoras:**
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?  
  *Ajuda a padronizar a escrita de requisitos, evitando ambiguidades.*
- Houve melhoria perceptível na qualidade do artefato gerado?  
  *Sim, User Stories mais completas e detalhadas.*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- ☐ Documentação clara e acessível  
- ☑ Tutoriais/exemplos disponíveis  
- ☑ Integração com ferramentas comuns (GitHub, GitLab, VS Code, Jira, etc.)  
- ☐ Comunidade ativa / relatos de uso  
- ☐ Estudos acadêmicos ou relatos industriais  

**Atende ao critério?**  ☐ Sim ☑ Parcial ☐ Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**
- Que “categoria” de AI4SE esta ferramenta representa?  
  *Assistentes de Gestão e Requisitos.*
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas?  
  *Sim, pois foca em texto e processo, não em código.*
- Há outras ferramentas muito similares já avaliadas?  
  *Não neste conjunto.*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C7 — Riscos e Limitações** **Riscos observados (se houver):**
- ☐ Pode introduzir erros críticos  
- ☐ Pode gerar resultados enganosos  
- ☐ Dependência excessiva de IA  
- ☑ Outros: *Vendor Lock-in severo (funciona apenas dentro do Jira).*

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
- Excelente conversão de Linguagem Natural para JQL (reduz barreira técnica).
- Capacidade de RAG (Retrieval-Augmented Generation) eficiente sobre o contexto histórico do projeto.
- Integração fluida sem necessidade de configuração de API externa.
 
### **Pontos fracos (bullet points)**
- **Escopo Limitado:** Não interage com o código-fonte, IDEs ou arquitetura fora do ambiente Atlassian.
- Custo elevado (funcionalidades limitadas para planos Premium/Enterprise).
- Não gera artefatos exportáveis universais (apenas tickets internos).

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☐ Incluir  ☑ Incluir com ressalvas ☐ Não incluir  

**Justificativa resumida em caso de não incluir (3–5 linhas):** > A ferramenta deve ser incluída com ressalvas devido à sua limitação de escopo. Embora seja excelente para gestão, ela opera estritamente como uma *feature* interna do ecossistema Atlassian, não configurando uma ferramenta de Engenharia de Software independente. Sua incapacidade de atuar fora do ambiente Jira limita a generalização dos resultados para o estudo proposto. Além disso, não há uma documentação clara a seu respeito.

---

## **6) Evidências Anexas (opcional)**
- Links: [Atlassian Intelligence Overview](https://www.atlassian.com/trust/atlassian-intelligence)
- Arquivos gerados: N/A