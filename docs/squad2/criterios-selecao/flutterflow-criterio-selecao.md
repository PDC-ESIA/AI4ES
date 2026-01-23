# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | FlutterFlow AI App Generator |
| **Versão (se aplicável):** | |
| **URL oficial para acesso à ferramenta/documentação:** | FlutterFlow AI App Generator |
| **Data da avaliação:** | 22/01/2026 |
| **Avaliador:** | Karlla Loane |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática  

> O FlutterFlow AI App Generator é uma ferramenta low-code que utiliza IA generativa baseada em LLMs para auxiliar na construção de interfaces gráficas de aplicações Flutter, a partir de prompts em linguagem natural, imagens ou integrações com Figma. É destinada principalmente a desenvolvedores, designers e equipes de produto que desejam acelerar a prototipagem e a construção inicial de aplicações mobile e web. Na avaliação prática, a ferramenta foi utilizada para gerar telas e modais a partir de descrições textuais e Data Types previamente definidos, observando sua aderência ao modelo de dados e consistência com o estado atual do projeto. 


---

## **3) Avaliação por Critérios de Inclusão**

Para cada critério, marque **Sim / Parcial / Não**, responda às perguntas-chave fornecendo as evidências necessárias.

---

### **C1 — Cobertura do SDLC**

Descrição: A ferramenta apoia explicitamente pelo menos uma fase do SDLC (ex.: requisitos, projeto, implementação, testes, manutenção).

**Fase(s) do SDLC apoiadas (marque todas):**  
- ☐ Requisitos  
- ☐ Projeto/Arquitetura  
- ☑ Implementação  
- ☐ Testes  
- ☐ Integração/CI-CD  
- ☐ Manutenção/Evolução  
- ☐ Outra: ___________

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita?  
  - Atua explicitamente na fase de implementação, com foco na geração de código de interface (UI) e lógica básica em Flutter/Dart.
- A atuação cobre atividades centrais da fase? Quais?
  - Cobre parcialmente atividades centrais, como geração de telas, layouts, componentes visuais e funções iniciais, mas não cobre aspectos mais profundos como arquitetura, validações de domínio ou integração robusta com backend.

**Atende ao critério?** ☐ Sim ☑ Parcial ☐ Não  

---

### **C2 — Apoio ativo por IA**

Descrição: A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA (não apenas edição ou automação tradicional).  

**Tipo de apoio por IA (marque):**  
- ☑ Geração automática  
- ☐ Sugestão/recomendação  
- ☐ Análise inteligente  
- ☐ Automação baseada em IA  
- ☐ Outro: ___________

**Perguntas orientadoras (responder brevemente):**
- A IA é central para a funcionalidade da ferramenta?
  - Parcialmente. A ferramenta pode ser usada sem IA (drag-and-drop manual), porém a IA é central para acelerar a geração inicial de telas e código. 
- Que capacidades “inteligentes” foram observadas na prática?
  - Geração automática de layouts, widgets e funções Dart a partir de prompts textuais ou imagens, sem análise semântica profunda do estado atual do projeto.

**Atende ao critério?** ☐ Sim ☑ Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas?
  - Criação manual de boilerplate visual, estrutura básica de telas, widgets e navegação inicial.  
- O ganho de produtividade foi significativo ou marginal?
  - O ganho foi significativo para prototipagem e scaffolding inicial, mas marginal em tarefas incrementais ou dependentes de consistência com modelos de dados existentes.   
- Foi necessário muito retrabalho/revisão manual?
  - Sim. Houve necessidade frequente de retrabalho para remover campos inventados, ajustar bindings e alinhar a UI ao modelo de dados real.     

**Atende ao critério?** ☐ Sim ☑ Parcial ☐ Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):**  
- ☐ Qualidade dos requisitos
- ☐ Qualidade do design
- ☑ Qualidade do código  
- ☐ Qualidade dos testes  
- ☐ Qualidade da documentação  
- ☐ Consistência/detecção de erros  
- ☐ Outro: ___________

**Perguntas orientadoras:**
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?
  - Não de forma consistente. Em vários casos, a IA introduziu inconsistências ao ignorar Data Types e alterações manuais pré-existentes.
- Houve melhoria perceptível na qualidade do artefato gerado?
  - Houve melhoria apenas no aspecto visual inicial e a padronização do código Flutter gerado.. A qualidade lógica e a aderência ao domínio não apresentaram melhora consistente. 

**Atende ao critério?** ☐ Sim ☑ Parcial ☐ Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- ☑ Documentação clara e acessível  
- ☑ Tutoriais/exemplos disponíveis  
- ☐ Integração com ferramentas comuns (GitHub, GitLab, VS Code, Jira, etc.)  
- ☑ Comunidade ativa / relatos de uso  
- ☐ Estudos acadêmicos ou relatos industriais  

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**
- Que “categoria” de AI4SE esta ferramenta representa?
  - Desenvolvimento Low-Code assistido por IA
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas?
  -  Sim. Representa uma categoria distinta de ferramentas baseadas em interface visual e geração assistida de UI, diferente de LLMs textuais puros.
- Há outras ferramentas muito similares já avaliadas?
  - Não

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C7 — Riscos e Limitações** 

**Riscos observados (se houver):**
- ☑ Pode introduzir erros críticos  
- ☑ Pode gerar resultados enganosos  
- ☐ Dependência excessiva de IA  
- ☐ Outros: ___________

**Atende ao critério?** ☐ Sim ☑ Parcial ☐ Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
-  Geração rápida de interfaces completas.
-  Acelera significativamente a prototipagem visual.
-  Integração imediata do código gerado ao projeto.
 
### **Pontos fracos (bullet points)**
- Ignora o estado atual do projeto (Data Types, variáveis).
- Introduz campos e estruturas não solicitadas.
- Exige alto esforço de supervisão manual.
- Geração de telas limitadas no plano gratuito.

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☐ Incluir ☑ Incluir com ressalvas ☐ Não incluir  

> A ferramenta será incluída no experimento por representar uma categoria relevante de ferramentas AI4SE voltadas à construção visual e geração assistida de interfaces. Contudo, sua avaliação será realizada com ressalvas devido à baixa consciência de contexto do projeto, dependência de prompts altamente específicos e dificuldades de padronização dos resultados, especialmente em cenários incrementais. Além disso, o uso da ferramenta de IA para gerar componentes é limitado no plano gratuito. 

---
