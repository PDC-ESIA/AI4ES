# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | Dynatrace (Davis AI / Davis CoPilot) |
| **Versão (se aplicável):** | SaaS (Plataforma DPS) |
| **URL oficial para acesso à ferramenta/documentação:** | https://www.dynatrace.com/ |
| **Data da avaliação:** | 20/01/2026 |
| **Avaliador:** | Walisson |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática  

> A Dynatrace é uma plataforma de observabilidade unificada e segurança que utiliza uma IA Hipermodal (Davis AI) combinando IA Causal, Preditiva e Generativa. É destinada a equipes de SRE (Site Reliability Engineering), DevOps e Arquitetura em ambientes corporativos complexos para monitoramento, detecção de falhas e automação. Na avaliação prática, foi testada em ambiente Linux para validar capacidades de descoberta automática de topologia e análise de causa raiz em tempo real.
> 

---

## **3) Avaliação por Critérios de Inclusão**

Para cada critério, marque **Sim / Parcial / Não**, responda às perguntas-chave fornecendo as evidências necessárias.

---

### **C1 — Cobertura do SDLC**

Descrição: A ferramenta apoia explicitamente pelo menos uma fase do SDLC (ex.: requisitos, projeto, implementação, testes, manutenção).

**Fase(s) do SDLC apoiadas (marque todas):*
- [ ] Requisitos  
- [x] Projeto/Arquitetura  
- [ ] Implementação  
- [x] Testes  
- [ ] Integração/CI-CD  
- [x] Manutenção/Evolução  
- [x] Outra: Operações (SRE/Observabilidade)

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita?  
Atua fortemente em **Operações/Manutenção** (Monitoramento e Correção) e **Arquitetura** (Mapeamento de Topologia).
- A atuação cobre atividades centrais da fase? Quais? 
Sim, cobre detecção de falhas, análise de causa raiz e validação de requisitos não-funcionais (performance).

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
Sim, a Davis AI é o motor central para correlação de eventos e análise causal.
- Que capacidades “inteligentes” foram observadas na prática?  
Análise Causal (RCA) determinística que aponta a linha de código exata de uma falha e o Davis CoPilot para geração de queries (DQL) via linguagem natural.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas?  
Elimina a necessidade de instrumentação manual de código (via OneAgent) e a configuração manual de dashboards e alertas.
- O ganho de produtividade foi significativo ou marginal?  
Significativo na etapa de diagnóstico de erros, reduzindo horas de investigação para minutos.
- Foi necessário muito retrabalho/revisão manual?    
Não para a detecção, mas a configuração de permissões e ambiente exige esforço manual inicial elevado.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):** - [ ] Qualidade dos requisitos
- [ ] Qualidade do design
- [x] Qualidade do código  
- [ ] Qualidade dos testes  
- [ ] Qualidade da documentação  
- [x] Consistência/detecção de erros  
- [ ] Outro: ___________

**Perguntas orientadoras:**
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?  
Sim, através de *Profiling* contínuo que identifica gargalos de performance no código em produção.
- Houve melhoria perceptível na qualidade do artefato gerado?  
Melhora a estabilidade e performance do software em execução, mas não auxilia na escrita do código fonte (features) em si.

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
Representa **AIOps (Artificial Intelligence for IT Operations)** e Observabilidade Inteligente.
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas?  
Sim, traz uma abordagem de IA Causal (determinística) diferente da IA Generativa (probabilística) comum em assistentes de código.
- Há outras ferramentas muito similares já avaliadas?  
Não no escopo atual.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não  

---

### **C7 — Riscos e Limitações** **Riscos observados (se houver):**
- [ ] Pode introduzir erros críticos  
- [ ] Pode gerar resultados enganosos  
- [ ] Dependência excessiva de IA  
- [x] Outros: Custo proibitivo (Enterprise), Vendor Lock-in (Agente proprietário), Necessidade de Root.

**Atende ao critério?** [x] Sim [ ] Parcial [ ] Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
- **Instrumentação Automática:** O OneAgent descobre e monitora processos sem alteração no código fonte.
- **Precisão Causal:** Aponta a causa raiz exata (RCA) de problemas de performance (ex: loop infinito), não apenas correlações.
- **Topologia em Tempo Real:** Mapeia dependências de infraestrutura e serviços automaticamente.

### **Pontos fracos (bullet points)**
- **Escopo Funcional:** Não gera código de aplicação (Java, Python, etc.), apenas scripts de automação e queries internas.
- **Barreira de Entrada:** Exige privilégios de `root` e infraestrutura complexa, dificultando testes rápidos.
- **Pontos Cegos:** Ignora processos simples ou CLI que não abrem portas de rede, limitando o uso em scripts de automação locais.

---

## **5) Decisão Final de Inclusão**

**Decisão:** [ ] Incluir [ ] Incluir com ressalvas [x] Não incluir  

**Justificativa resumida em caso de não incluir (3–5 linhas):** A ferramenta é classificada como uma plataforma de **AIOps/Observabilidade**, e não como um "Assistente de Código" ou ferramenta de apoio direto ao desenvolvimento (escrita de software), que é o foco central da **Macroentrega 1 (ME1)**. Além disso, as barreiras de custo e infraestrutura tornam inviável sua utilização no benchmarking comparativo proposto para o laboratório TRL 4 neste momento.

---

## **6) Evidências Anexas (opcional)**
- Links:  
- Arquivos gerados:  

---
