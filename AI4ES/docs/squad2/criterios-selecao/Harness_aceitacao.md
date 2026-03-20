# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | Harness AI (Harness AIDA - AI Development Assistant) |
| **Versão (se aplicável):** | Plataforma SaaS (Rolling Release) / Módulos Code & DevOps |
| **URL oficial para acesso à ferramenta/documentação:** | https://harness.io / https://developer.harness.io |
| **Data da avaliação:** | 20/01/2026 |
| **Avaliador:** | Walisson |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática  

> A Harness AI posiciona-se como uma plataforma completa de SDLC (Software Development Life Cycle). Destina-se primariamente a equipes de Engenharia de Plataforma e DevOps em ambientes corporativos (Enterprise), utilizando agentes de IA para orquestrar CI/CD, QA, Governança e Segurança. A avaliação prática ocorreu em contexto de infraestrutura de nuvem (SaaS) com foco nas capacidades de automação de pipelines e revisão de código.
> 

---

## **3) Avaliação por Critérios de Inclusão**

Para cada critério, marque **Sim / Parcial / Não**, responda às perguntas-chave fornecendo as evidências necessárias.

---

### **C1 — Cobertura do SDLC**

Descrição: A ferramenta apoia explicitamente pelo menos uma fase do SDLC (ex.: requisitos, projeto, implementação, testes, manutenção).

**Fase(s) do SDLC apoiadas (marque todas):** 
- [ ] Requisitos  
- [x] Projeto/Arquitetura  
- [x] Implementação  
- [x] Testes  
- [x] Integração/CI-CD  
- [x] Manutenção/Evolução  
- [ ] Outra: ___________

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita?  
Atuação predominante em **Integração/CI-CD**, **Testes** e **Operações/Manutenção**.
- A atuação cobre atividades centrais da fase? Quais? 
Sim, cobre orquestração de deploys, execução de testes automatizados baseados em intenção e análise de erros de build.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não  

---

### **C2 — Apoio ativo por IA**

Descrição: A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA (não apenas edição ou automação tradicional).  

**Tipo de apoio por IA (marque):** 
- [x] Geração automática  
- [ ] Sugestão/recomendação  
- [x] Análise inteligente  
- [x] Automação baseada em IA  
- [ ] Outro: ___________

**Perguntas orientadoras (responder brevemente):**
- A IA é central para a funcionalidade da ferramenta?  
Sim, a arquitetura AIDA (AI Development Assistant) permeia os módulos, desde a geração de pipelines YAML até a análise de logs de erro (RCA).
- Que capacidades “inteligentes” foram observadas na prática?  
Diagnóstico de falhas de pipeline, sugestão de correção de vulnerabilidades e geração de testes baseados em intenção.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas?  
Configuração de pipelines de CI/CD, triagem de logs de erro em builds falhos, criação de testes de regressão, review de Pull Requests.
- O ganho de produtividade foi significativo ou marginal?  
Potencialmente significativo em escala Enterprise, mas com alto custo de configuração inicial para projetos menores.
- Foi necessário muito retrabalho/revisão manual?    
Devido à complexidade da ferramenta, a intervenção manual para configuração da infraestrutura (Delegates/Connectors) é alta, embora a operação subsequente seja autônoma.

**Atende ao critério?** [ ] Sim [x] Parcial [ ] Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):** 
- [ ] Qualidade dos requisitos
- [ ] Qualidade do design
- [x] Qualidade do código  
- [x] Qualidade dos testes  
- [x] Qualidade da documentação  
- [x] Consistência/detecção de erros  
- [ ] Outro: ___________

**Perguntas orientadoras:**
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?  
Sim, através de mecanismos de "Governance as Code" e detecção proativa de quebras de build.
- Houve melhoria perceptível na qualidade do artefato gerado?  
A ferramenta foca na estabilidade do processo de entrega e segurança, garantindo conformidade.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- [x] Documentação clara e acessível  
- [ ] Tutoriais/exemplos disponíveis  
- [x] Integração com ferramentas comuns (GitHub, GitLab, VS Code, Jira, etc.)  
- [ ] Comunidade ativa / relatos de uso  
- [ ] Estudos acadêmicos ou relatos industriais  

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**
- Que “categoria” de AI4SE esta ferramenta representa?  
Representa a categoria de **Plataformas de Engenharia de Plataforma/DevOps AI-Native** e **Agentes Autônomos de SDLC**.
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas?  
Sim, diferencia-se drasticamente dos assistentes focados apenas em IDE (como Copilot/Codeium) por abordar o ciclo de vida e infraestrutura.
- Há outras ferramentas muito similares já avaliadas?  
Não, ela cobre lacunas de Operações e Governança não atendidas por assistentes de código puros.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não  

---

### **C7 — Riscos e Limitações** **Riscos observados (se houver):**
- [ ] Pode introduzir erros críticos  
- [ ] Pode gerar resultados enganosos  
- [ ] Dependência excessiva de IA  
- [x] Outros: Alta complexidade de setup, Barreiras financeiras/Trial limitado.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
- **Abordagem Holística:** Cobre todo o ciclo de vida (Code, Build, Test, Deploy, Verify), não apenas a escrita de código.
- **Governança e Segurança:** Integração nativa de verificação de segurança e políticas de conformidade orquestradas por IA.
- **Contexto Operacional:** Capacidade de analisar logs e métricas de infraestrutura, algo que assistentes de IDE não conseguem fazer.

### **Pontos fracos (bullet points)**
- **Alta Barreira de Entrada:** Exige infraestrutura complexa (Kubernetes/Docker Delegates) apenas para testes básicos.
- **Acessibilidade:** Funcionalidades de IA generativa (Code Assistant) apresentaram instabilidade ou indisponibilidade em contas de avaliação (Free Tier).
- **UX Fragmentada:** Curva de aprendizado íngreme devido à mistura de conceitos densos de DevOps com funcionalidades de IA.

---

## **5) Decisão Final de Inclusão**

**Decisão:** [ ] Incluir [x] Incluir com ressalvas [ ] Não incluir  

**Justificativa resumida em caso de não incluir (3–5 linhas):** A ferramenta é incluída pela sua alta relevância na categoria de **Agentes Autônomos e DevOps**, alinhando-se aos objetivos de pesquisa de agentes do projeto. No entanto, as **ressalvas** aplicam-se à dificuldade de testar suas capacidades de geração de código (Code Assistant) na Macroentrega 1 devido a barreiras de licenciamento e complexidade de infraestrutura observadas no levantamento.

---

## **6) Evidências Anexas (opcional)**
- Links:  
- Arquivos gerados:  

---
