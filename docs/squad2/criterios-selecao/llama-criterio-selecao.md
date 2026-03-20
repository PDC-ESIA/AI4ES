# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | Meta Llama |
| **Versão (se aplicável):** | Llama 3.2 3B |
| **URL oficial para acesso à ferramenta/documentação:** | https://www.llama.com/, https://www.llama.com/models/llama-3/ |
| **Data da avaliação:** | 22/01/2026 |
| **Avaliador:** | Karlla Loane |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática  

> O Llama 3.2 é um modelo de linguagem de propósito geral desenvolvido pela Meta, destinado ao apoio a múltiplas atividades de Engenharia de Software por meio de interação baseada em prompts textuais. A ferramenta é voltada a desenvolvedores, pesquisadores e equipes técnicas, oferecendo suporte à geração e análise de artefatos como requisitos, código, testes, documentação e decisões arquiteturais. Na avaliação prática, o modelo foi testado em ambiente local, sendo utilizado para tarefas de requisitos, arquitetura, construção e testes, com foco em geração e análise de artefatos a partir de descrições em linguagem natural.

---

## **3) Avaliação por Critérios de Inclusão**

Para cada critério, marque **Sim / Parcial / Não**, responda às perguntas-chave fornecendo as evidências necessárias.

---

### **C1 — Cobertura do SDLC**

Descrição: A ferramenta apoia explicitamente pelo menos uma fase do SDLC (ex.: requisitos, projeto, implementação, testes, manutenção).

**Fase(s) do SDLC apoiadas (marque todas):**  
- ☑ Requisitos  
- ☑ Projeto/Arquitetura  
- ☑ Implementação  
- ☑ Testes  
- ☐ Integração/CI-CD  
- ☑ Manutenção/Evolução  
- ☐ Outra: ___________

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita?  
- A atuação cobre atividades centrais da fase? Quais?

> O Llama atua explicitamente nas fases de requisitos (elicitação, análise e documentação), projeto/arquitetura (modelagem, decisões e trade-offs), implementação (geração e refatoração de código), testes (geração de casos de teste) e manutenção (análise e correção de bugs). A atuação cobre atividades centrais dessas fases por meio da geração e análise de artefatos técnicos.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C2 — Apoio ativo por IA**

Descrição: A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA (não apenas edição ou automação tradicional).  

**Tipo de apoio por IA (marque):**  
- ☑ Geração automática  
- ☑ Sugestão/recomendação  
- ☑ Análise inteligente  
- ☐ Automação baseada em IA  
- ☐ Outro: ___________

**Perguntas orientadoras (responder brevemente):**
- A IA é central para a funcionalidade da ferramenta? 
  - A IA é central para a funcionalidade da ferramenta, uma vez que todas as capacidades avaliadas dependem diretamente do modelo generativo.
- Que capacidades “inteligentes” foram observadas na prática?
  - Foram observadas capacidades de geração de requisitos, código, testes, documentação e análise de trade-offs arquiteturais a partir de prompts textuais.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas?
  - A ferramenta reduziu tarefas repetitivas como a escrita inicial de requisitos, geração de boilerplate de código, criação de testes unitários, documentação técnica e análise preliminar de alternativas de design. 
- O ganho de produtividade foi significativo ou marginal?
  -   O ganho de produtividade foi significativo, prncipalmente nas fases iniciais das atividades.
- Foi necessário muito retrabalho/revisão manual?
  - Foi necessária revisão manual moderada, principalmente para ajustes de contexto, validação de requisitos específicos e correção de detalhes técnicos, mas não retrabalho extensivo.   

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):**  
- ☑ Qualidade dos requisitos
- ☑ Qualidade do design
- ☑ Qualidade do código  
- ☑ Qualidade dos testes  
- ☑ Qualidade da documentação  
- ☑ Consistência/detecção de erros  
- ☐ Outro: ___________

**Perguntas orientadoras:**
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?
  - Sim. A ferramenta auxiliou na identificação de inconsistências, ambiguidades e problemas lógicos em requisitos, código e decisões arquiteturais, especialmente quando solicitada explicitamente a revisar ou validar os artefatos gerados.   
- Houve melhoria perceptível na qualidade do artefato gerado?
  - Sim. Observou-se melhoria perceptível na organização, clareza e aderência a boas práticas dos artefatos produzidos, em comparação com versões elaboradas manualmente sob restrições de tempo.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- ☑ Documentação clara e acessível  
- ☑ Tutoriais/exemplos disponíveis  
- ☑ Integração com ferramentas comuns (via LangChain, Ollama, Groq)  
- ☑ Comunidade ativa / relatos de uso  
- ☑ Estudos acadêmicos ou relatos industriais  

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**
- Que “categoria” de AI4SE esta ferramenta representa?  
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas?  
- Há outras ferramentas muito similares já avaliadas?  

**Atende ao critério?** ☐ Sim ☐ Parcial ☐ Não  

---

### **C7 — Riscos e Limitações** 

**Riscos observados (se houver):**
- ☑ Pode introduzir erros críticos  
- ☑ Pode gerar resultados enganosos  
- ☑ Dependência excessiva de IA  
- ☐ Outros: ___________

**Atende ao critério?** ☐ Sim ☑ Parcial ☐ Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
-  Alta redução de esforço manual em tarefas de ES
-  Boa qualidade técnica dos artefatos gerados
-  Execução local favorece controle experimental e privacidade
-  Forte aderência a prompts estruturados
 
### **Pontos fracos (bullet points)**
- Variabilidade entre respostas para o mesmo prompt
- Necessidade de validação humana constante
- Desempenho inferior a modelos proprietários em tarefas de maior complexidade cognitiva

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☑ Incluir ☐ Incluir com ressalvas ☐ Não incluir  

**Justificativa resumida em caso de não incluir (3–5 linhas):**  
> _[Inserir justificativa]_  

---
