# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** |Gemini Code Assist |
| **Versão (se aplicável):** |2.68.0 |
| **URL oficial para acesso à ferramenta/documentação:** |[Documentação](https://developers.google.com/gemini-code-assist/docs/overview?hl=pt-br) |
| **Data da avaliação:** |24/01/2026 |
| **Avaliador:** |Vinícius Espíndola |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**



> _O Gemini Code Assist tem como propósito principal atuar como um colaborador de inteligência artificial integrado ao ciclo de vida de desenvolvimento, utilizando uma janela de contexto de até 1 milhão de tokens para compreender repositórios inteiros e automatizar desde a escrita de códigos simples até a refatoração de sistemas complexos. Em avaliações práticas, a ferramenta é testada sob o rigor do SWE-bench, que mede sua capacidade de resolver problemas reais em bases de código extensas, além de ser validada em cenários operacionais críticos onde deve diagnosticar falhas de infraestrutura e sugerir correções precisas em tempo real._  
> 

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
- ☐ Outra: ___________

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita?

O Gemini Code Assist atua em todas as fases mencionadas, embora seu núcleo seja mais robusto na Implementação e Manutenção. Através do chat e do Agent Mode, ele auxilia desde a decomposição de requisitos em tarefas técnicas até o monitoramento de logs em produção.

- A atuação cobre atividades centrais da fase? Quais? 

Sim. Na Implementação, realiza geração automática de código e preenchimento inline. Nos Testes, gera suítes de testes unitários e de integração automaticamente. No Projeto/Arquitetura, sua janela de 1 milhão de tokens permite analisar a estrutura de pastas e sugerir padrões de design (ex.: Clean Architecture). Na Manutenção, identifica vulnerabilidades e sugere correções de bugs em sistemas legados.

**Atende ao critério?** [X] Sim ☐ Parcial ☐ Não  

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
- A IA é central para a funcionalidade da ferramenta?

Sim. O Gemini Code Assist utiliza Large Language Models (LLMs) como componente central para processar linguagem natural e código em todas as suas interações.

- Que capacidades “inteligentes” foram observadas na prática?  

Observou-se a geração de blocos de código complexos, análise de repositórios inteiros para sugestões contextuais, automação de testes unitários e a capacidade de realizar refatorações em múltiplos arquivos simultaneamente através do "Agent Mode"

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas?  

A ferramenta elimina a escrita manual de código repetitivo (boilerplate), automatiza a criação de suítes de testes unitários e reduz o tempo de busca em documentações extensas graças ao chat contextual que analisa o repositório inteiro. Também automatiza a geração de artefatos documentais, como histórias de usuário e critérios de aceitação.

- O ganho de produtividade foi significativo ou marginal?  

O ganho é significativo, especialmente em tarefas de manutenção e construção. A janela de contexto de 1 milhão de tokens permite que a ferramenta realize refatorações complexas que, manualmente, exigiriam horas de análise de dependências entre múltiplos arquivos.

- Foi necessário muito retrabalho/revisão manual?  

Mesmo que a ferramenta reduza o esforço inicial, a revisão humana ainda é necessária para validar a lógica de negócio e as especificidades do sistema.


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
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?  

Sim. Através da análise estática em tempo real e da integração com ferramentas de segurança (como o Snyk), o Gemini identifica vulnerabilidades e inconsistências lógicas antes da compilação. Além disso, ele mantém a consistência entre os requisitos e a implementação das entidades.

- Houve melhoria perceptível na qualidade do artefato gerado?  

Sim. A ferramenta aplica automaticamente padrões de Clean Code e princípios SOLID quando solicitado, resultando em um código mais modular e legível. Na documentação, gera histórias de usuário estruturadas com critérios de aceitação (Given-When-Then) que frequentemente possuem maior detalhamento técnico do que as escritas manualmente sob pressão de tempo.


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
- Que “categoria” de AI4SE esta ferramenta representa? 

O Gemini Code Assist representa a categoria de Assistentes de IA para o Ciclo de Vida de Software (SDLC AI Assistants) e Agentes de IA para Codificação. Ele vai além da simples geração de código, oferecendo suporte a requisitos, arquitetura, testes automatizados e operações (SRE)

- Ela adiciona diversidade ao conjunto de ferramentas avaliadas?  

Sim. Adiciona diversidade especialmente pelo uso de uma janela de contexto massiva de 1 milhão de tokens, que permite a análise de repositórios inteiros de forma holística, e pela integração profunda com o ecossistema Google Cloud (Firebase, BigQuery, Cloud Run)

- Há outras ferramentas muito similares já avaliadas? 

Sim, ferramentas como GitHub Copilot e Amazon Q Developer são concorrentes diretos que também oferecem assistência baseada em LLMs


**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não  

---

### **C7 — Riscos e Limitações** 

**Riscos observados (se houver):**
- [x] Pode introduzir erros críticos  
- [x] Pode gerar resultados enganosos  
- [x] Dependência excessiva de IA  
- [x] Outros: Vazamento de Dados

**Atende ao critério?** ☐ Sim [x] Parcial ☐ Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
- Janela de Contexto Massiva: A capacidade de processar até 1 milhão de tokens permite que a ferramenta compreenda a relação entre o módulo de "Gestão de Quartos" e o de "Reserva" sem perder o contexto, garantindo consistência na arquitetura.

- Agent Mode para Refatoração: Diferente de assistentes que apenas sugerem código, o modo agente consegue aplicar mudanças em múltiplos arquivos simultaneamente, o que é um diferencial na fase de Manutenção e evolução do sistema.

- Qualidade na Geração de Testes: Demonstra alta precisão na criação de suítes de testes unitários e de integração (Jest/JUnit), cobrindo inclusive casos de borda.
 
### **Pontos fracos (bullet points)**
- Dependência de Ecossistema: Embora seja excelente para Google Cloud, a integração com outros provedores de nuvem (AWS/Azure) ou ferramentas de CI/CD menos comuns pode exigir mais esforço manual e personalização de prompts.

- Risco de Alucinação em Lógicas de Nicho: Em regras de negócio muito específicas, a ferramenta ainda pode gerar lógica plausível, porém incorreta, exigindo revisão técnica.

- Latência em Grandes Contextos: Ao utilizar o limite máximo da janela de tokens para analisar o repositório inteiro, o tempo de resposta do chat pode ser elevado, impactando levemente a fluidez do desenvolvimento em tempo real.

- Custo e Limites de Cota: Para usuários do plano gratuito ou Standard, os limites de requisições por minuto podem interromper o fluxo de trabalho durante sessões intensas de codificação ou refatoração.

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☐ Incluir [x] Incluir com ressalvas ☐ Não incluir  

**Justificativa resumida em caso de não incluir (3–5 linhas):**  
> _A ferramenta demonstra alta maturidade e cobertura completa do SDLC, sendo particularmente superior na análise de contextos extensos (1M tokens). No entanto, a inclusão exige cautela devido à necessidade de revisão humana rigorosa para evitar alucinações em regras de negócio específicas._  

---

## **6) Evidências Anexas (opcional)**
- Links:  [Documentação oficial](https://developers.google.com/gemini-code-assist/docs/overview?hl=pt-br), [Guia de Preços e Versões](https://cloud.google.com/products/gemini/pricing?hl=pt-BR)
---