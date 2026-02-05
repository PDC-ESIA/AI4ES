# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | Codeium / Windsurf (IDE AI-Native) |
| **Versão (se aplicável):** | Cascade 2.0 / SWE 1.5 |
| **URL oficial para acesso à ferramenta/documentação:** | https://codeium.com / https://windsurf.com |
| **Data da avaliação:** | 19/01/2026 |
| **Avaliador:** | Walisson |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática  

> A Codeium apresenta-se como uma solução híbrida que opera tanto como plugin assistente de código quanto como uma IDE completa (Windsurf) baseada em agentes (Cascade). Destina-se a engenheiros de software para aumentar a produtividade em codificação, refatoração e documentação. Na avaliação prática, foi testada em um ambiente Linux (Ubuntu) cobrindo todo o ciclo SWEBOK, desde a elicitação de requisitos e modelagem UML (PlantUML) até a implementação de pipelines de CI/CD (via código gerado pelo chat) e testes unitários em Python e C++.
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
- [ ] Outra: ___________

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita?  
Atua fortemente na **Implementação** (geração e refatoração), **Documentação/Requisitos** (geração de texto e diagramas) e **Operações** (criação de pipelines CI/CD) via prompts com o chat integrado à IDE.
- A atuação cobre atividades centrais da fase? Quais? 
Sim. Na fase de requisitos, apoiou na elicitação e priorização. Na implementação, realizou otimização de complexidade algorítmica ($O(2^n) \to O(n)$).

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não  

---

### **C2 — Apoio ativo por IA**

Descrição: A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA (não apenas edição ou automação tradicional).  

**Tipo de apoio por IA (marque):** - [x] Geração automática  
- [x] Sugestão/recomendação  
- [x] Análise inteligente  
- [x] Automação baseada em IA  
- [ ] Outro: ___________

**Perguntas orientadoras (responder brevemente):**
- A IA é central para a funcionalidade da ferramenta?  
Sim, utiliza um modelo híbrido (Proprietário para autocomplete + Agentes Cascade/Claude/GPT para raciocínio complexo).
- Que capacidades “inteligentes” foram observadas na prática?  
Capacidade de **Context Awareness (RAG)** profundo, lendo todo o projeto para sugerir código.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas?  
Escrita de *boilerplate* para testes unitários, criação de arquivos de configuração (Dockerfile, YAML para GitHub Actions) e diagramação (PlantUML).
- O ganho de produtividade foi significativo ou marginal?  
Significativo na codificação e na documentação.
- Foi necessário muito retrabalho/revisão manual?    
Revisão necessária em testes (correção de alucinações) e segurança, mas o esboço inicial economizou tempo.

**Atende ao critério?** [ ] Sim [x] Parcial [ ] Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):** - [x] Qualidade dos requisitos
- [ ] Qualidade do design
- [x] Qualidade do código  
- [ ] Qualidade dos testes  
- [x] Qualidade da documentação  
- [ ] Consistência/detecção de erros  
- [ ] Outro: ___________

**Perguntas orientadoras:**
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?  
Sim, identificou conflitos de requisitos.
- Houve melhoria perceptível na qualidade do artefato gerado?  
Melhorou a complexidade de tempo e espaço de algoritmos (Fibonacci) e gerou documentação técnica clara.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- [x] Documentação clara e acessível  
- [ ] Tutoriais/exemplos disponíveis  
- [x] Integração com ferramentas comuns (GitHub, GitLab, VS Code, Jira, etc.)  
- [x] Comunidade ativa / relatos de uso  
- [ ] Estudos acadêmicos ou relatos industriais  

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**
- Que “categoria” de AI4SE esta ferramenta representa?  
Representa a categoria de **Assistentes de Código Comerciais** e **IDEs AI-Native**, competindo diretamente com GitHub Copilot e Cursor.
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas?  
Sim, introduz o conceito de "Agentes" (Cascade) integrados à IDE, diferindo do modelo de apenas "chat/autocomplete".
- Há outras ferramentas muito similares já avaliadas?  
Ainda não avaliadas no projeto atual, sendo esta uma das candidatas principais para a ME1.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não  

---

### **C7 — Riscos e Limitações** **Riscos observados (se houver):**
- [x] Pode introduzir erros críticos 
- [x] Pode gerar resultados enganosos
- [ ] Dependência excessiva de IA  
- [x] Outros: Privacidade (SaaS envia código para nuvem)

**Atende ao critério?** [ ] Sim [x] Parcial [ ] Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
- **Context Awareness (RAG):** Alta capacidade de indexar e compreender o projeto inteiro para gerar sugestões assertivas.
- **Velocidade:** Baixa latência no autocomplete e na geração de respostas.
- **Versatilidade SWEBOK:** Atendeu bem desde a engenharia de requisitos até operações (DevOps), gerando artefatos úteis em todas as etapas.
- **Explainability:** Excelente capacidade didática para explicar códigos e decisões.

### **Pontos fracos (bullet points)**
- **Alucinação em Testes:** Gera testes unitários que passam em cenários ideais, mas falham no código real (inventa métodos ou erros).
- **Segurança:** Tende a gerar configurações de infraestrutura funcionais, mas inseguras.
- **Precisão Semântica:** Pode inverter conceitos técnicos complexos, cometendo erros semânticos ao gerar resposta.

---

## **5) Decisão Final de Inclusão**

**Decisão:** [x] Incluir [ ] Incluir com ressalvas [ ] Não incluir  

**Justificativa resumida em caso de não incluir (3–5 linhas):**
> _[Inserir justificativa]_  

---

## **6) Evidências Anexas (opcional)**


---