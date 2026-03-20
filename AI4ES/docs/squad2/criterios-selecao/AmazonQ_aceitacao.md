# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | Amazon Q Developer |
| **Versão (se aplicável):** | N/A |
| **URL oficial para acesso à ferramenta/documentação:** | https://aws.amazon.com/q/developer/ |
| **Data da avaliação:** | 17/01/2025 |
| **Avaliador:** | Adriam Felipe Santos da Luz |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática  

> O Amazon Q Developer é um assistente de código baseado em IA que atua como plugin de IDE e agente de software. Destina-se a desenvolvedores e engenheiros que buscam apoio em todo o ciclo de vida de desenvolvimento, desde a concepção de requisitos até a manutenção e operações em nuvem. No contexto prático, a ferramenta foi testada na criação de um sistema de farmácia, demonstrando alta capacidade em tarefas de bootstrapping, refatoração de código, identificação de falhas lógicas através de RAG (Retrieval-Augmented Generation) e produção de requisitos.

---

## **3) Avaliação por Critérios de Inclusão**

Para cada critério, marque **Sim / Parcial / Não**, responda às perguntas-chave fornecendo as evidências necessárias.

---

### **C1 — Cobertura do SDLC**

Descrição: A ferramenta apoia explicitamente pelo menos uma fase do SDLC (ex.: requisitos, projeto, implementação, testes, manutenção).

**Fase(s) do SDLC apoiadas (marque todas):** 
- [x] Requisitos  
- [x] Projeto/Arquitetura  
- [x] Implementação  
- [x] Testes  
- [x] Integração/CI-CD  
- [x] Manutenção/Evolução  
- [x] Outra: Gestão de Projetos e Operações

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita? Atua de forma muito alta na implementação e testes, e alta em requisitos, arquitetura e manutenção.  
- A atuação cobre atividades centrais da fase? Quais? Sim, como elicitação de requisitos, geração de código, criação de suítes de testes unitários e correções automatizadas de bugs. 

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não  

---

### **C2 — Apoio ativo por IA**

Descrição: A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA (não apenas edição ou automação tradicional).  

**Tipo de apoio por IA (marque):** 
- [x] Geração automática  
- [x] Sugestão/recomendação  
- [x] Análise inteligente  
- [x] Automação baseada em IA  
- ☐ Outro: ___________

**Perguntas orientadoras (responder brevemente):**
- A IA é central para a funcionalidade da ferramenta? Sim, utiliza a família de modelos Claude 3.5 para processar contexto e gerar respostas.  
- Que capacidades “inteligentes” foram observadas na prática? Identificação de contradições lógicas em documentos, detecção de bugs, geração de códigos e sugestões de requisitos.  

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas? Criação de estrutura de pastas (bootstrapping), escrita de testes unitários e atualização de imports.  
- O ganho de produtividade foi significativo ou marginal? Significativo, com ótima redução de tempo.  
- Foi necessário muito retrabalho/revisão manual? Baixo, embora exija supervisão para garantir que a IA não altere arquivos não solicitados.  

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):** 
- [x] Qualidade dos requisitos
- [x] Qualidade do design
- [x] Qualidade do código  
- [x] Qualidade dos testes  
- [x] Qualidade da documentação  
- [x] Consistência/detecção de erros  
- ☐ Outro: ___________

**Perguntas orientadoras:**
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada? Sim, corrigiu incoerências críticas em requisitos e identificou erros críticos no código.  
- Houve melhoria perceptível na qualidade do artefato gerado? Sim, tanto na melhoria de códigos (organização e eficiência) quanto na escrita de documentos textuais.  

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- [x] Documentação clara e acessível  
- [x] Tutoriais/exemplos disponíveis  
- [x] Integração com ferramentas comuns (GitHub, GitLab, VS Code, Jira, etc.)  
- [x] Comunidade ativa / relatos de uso  
- [x] Estudos acadêmicos ou relatos industriais  

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**
- Que “categoria” de AI4SE esta ferramenta representa? Representa a categoria de "Assistentes de Código" (AI Coding Companions) e "Agentes de Software".  
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas? Sim, pois cobre muitas etapas do processo de desenvolvimento de software.  
- Há outras ferramentas muito similares já avaliadas? Não.  

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não  

---

### **C7 — Riscos e Limitações** **Riscos observados (se houver):**
- [x] Pode introduzir erros críticos (intervenções não solicitadas em arquivos)  
- ☐ Pode gerar resultados enganosos  
- [x] Dependência excessiva de IA (viés de ecossistema AWS)  
- ☐ Outros: ___________

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
- Capacidade analítica para identificar contradições lógicas.  
- Alta capacidade de suporte a RAG.  
- Suporte eficaz a padrões de design (Strategy, Clean Architecture).  
- Eficaz na elicitação de requisitos.  
 
### **Pontos fracos (bullet points)**
- Viés forte para o ecossistema AWS.  
- Custo recorrente elevado para a versão Profissional.  

---

## **5) Decisão Final de Inclusão**

**Decisão:** [x] Incluir ☐ Incluir com ressalvas ☐ Não incluir  

---

## **6) Evidências Anexas (opcional)**
- Links: https://aws.amazon.com/q/developer/  

---
