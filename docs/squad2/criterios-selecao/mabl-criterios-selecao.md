# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | mabl |
| **Versão (se aplicável):** |  |
| **URL oficial para acesso à ferramenta/documentação:** | https://www.mabl.com/ e [Documentação](https://help.mabl.com/hc/en-us) |
| **Data da avaliação:** | 22/01/2026 |
| **Avaliador:** | Karlla Loane |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática  

> O mabl é uma plataforma de automação de testes inteligente (SaaS) que oferece uma solução de automação de testes nativa de IA para criar, executar e manter testes de ponta a ponta (E2E) em interfaces web e APIs. Destina-se a profissionais de QA e desenvolvedores que buscam automatizar validações funcionais sem a necessidade de codificação manual complexa. Nos testes práticos, a ferramenta foi utilizada para converter prompts em linguagem natural em fluxos de teste funcionais e para validar a resiliência do sistema diante de mudanças na interface.
> 

---

## **3) Avaliação por Critérios de Inclusão**

Para cada critério, marque **Sim / Parcial / Não**, responda às perguntas-chave fornecendo as evidências necessárias.

---

### **C1 — Cobertura do SDLC**

Descrição: A ferramenta apoia explicitamente pelo menos uma fase do SDLC (ex.: requisitos, projeto, implementação, testes, manutenção).

**Fase(s) do SDLC apoiadas (marque todas):**  
- ☐ Requisitos  
- ☐ Projeto/Arquitetura  
- ☐ Implementação  
- ☑ Testes  
- ☐ Integração/CI-CD  
- ☐ Manutenção/Evolução  
- ☐ Outra: ___________

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita?
  - Atua explicitamente na fase de Testes de Software, com foco em testes funcionais end-to-end e testes de API.
- A atuação cobre atividades centrais da fase? Quais?
  - Sim. A ferramenta cobre atividades centrais da fase de testes, incluindo geração automática de casos de teste, execução automatizada, validação de resultados e adaptação de testes a mudanças na interface.

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
  - A IA não é central para a funcionalidade da ferramenta, uma vez que é possível criar testes manualmente, atuando então como uma plataforma de automação low-code. Entretanto, a IA atua como um facilitador para geração, adaptação e manutenção dos testes.
- Que capacidades “inteligentes” foram observadas na prática?
  - Geração automática de testes a partir de prompts, análise do DOM e de respostas de APIs, detecção de inconsistências entre instruções e restrições reais do sistema, além de auto-healing de seletores.

**Atende ao critério?** ☐ Sim ☑ Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas?
  - Elimina a criação manual de scripts de teste(Selenium/XPath) e a manutenção e validação repetitivas de seletores e API.
- O ganho de produtividade foi significativo ou marginal?
  -  Significativo, com redução expressiva do tempo de criação e manutenção de testes automatizados.
- Foi necessário muito retrabalho/revisão manual?
  - Baixo, pois a IA valida as ações em tempo real contra o DOM da aplicação. A ferramenta solicitou intervenção humana apenas em casos de ambiguidade ou contradição lógica.    

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):**  
- ☐ Qualidade dos requisitos
- ☐ Qualidade do design
- ☐ Qualidade do código  
- ☑ Qualidade dos testes  
- ☐ Qualidade da documentação  
- ☑ Consistência/detecção de erros  
- ☐ Outro: ___________

**Perguntas orientadoras:**
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?
  - Sim. A IA interrompeu fluxos inválidos e apontou inconsistências entre o objetivo do teste e as validações reais da aplicação.
- Houve melhoria perceptível na qualidade do artefato gerado?
  - Gera testes mais estáveis e menos propensos a falsos positivos.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- ☑ Documentação clara e acessível  
- ☑ Tutoriais/exemplos disponíveis  
- ☑ Integração com ferramentas comuns (GitHub, GitLab, VS Code, Jira, etc.)  
- ☐ Comunidade ativa / relatos de uso  
- ☐ Estudos acadêmicos ou relatos industriais  

**Atende ao critério?** ☐ Sim ☑ Parcial ☐ Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**
- Que “categoria” de AI4SE esta ferramenta representa?
  - Ferramenta de automação de testes baseada em IA. 
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas?
  - Sim. Representa uma categoria distinta de ferramentas focadas em QA dinâmico e testes baseados em sistemas reais.
- Há outras ferramentas muito similares já avaliadas?
  - Não. 

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C7 — Riscos e Limitações** 

**Riscos observados (se houver):**
- ☐ Pode introduzir erros críticos  
- ☑ Pode gerar resultados enganosos  
- ☐ Dependência excessiva de IA  
- ☑ Outros: **Dependência de ambiente em execução e infraestrutura SaaS**

**Atende ao critério?** ☐ Sim ☑ Parcial ☐ Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
-  Geração automática de testes E2E e de API a partir de linguagem natural
-  Detecção de inconsistências entre objetivos de teste e restrições reais do sistema
-  Redução significativa de esforço manual e manutenção de testes
 
### **Pontos fracos (bullet points)**
- Dependência de sistema real em execução
- Impossibilidade de execução em ambientes locais sem acesso externo.

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☐ Incluir ☐ Incluir com ressalvas ☑ Não incluir  

**Justificativa**  
> A ferramenta apresenta alto potencial agêntico para a fase de testes, porém sua inclusão no experimento é limitada pela dependência de um ambiente real em execução (URL ativa). Portanto, a adoção da ferramenta no protocolo de avaliação estará condicionada à disponibilidade de um ambiente em produção e à elaboração de prompts textuais para a criação dos testes. Essa dependência pode dificultar a padronização dos cenários e a comparação dos resultados.

---
