# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | Lovable (antigo GPT Engineer) |
| **Versão (se aplicável):** | N/A (SaaS) |
| **URL oficial para acesso à ferramenta/documentação:** | https://lovable.dev |
| **Data da avaliação:** | 18/01/2026 |
| **Avaliador:** | Adriam Felipe Santos da Luz|

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática  

> Lovable é uma plataforma de desenvolvimento Full-Stack impulsionada por IA (AI Software Engineer) que permite criar, implantar e iterar aplicações web completas a partir de linguagem natural. Destina-se a desenvolvedores que buscam alta produtividade e prototipagem rápida, integrando frontend (React), backend (Supabase) e deploy automatizado. Na avaliação prática, a ferramenta foi testada na construção de uma aplicação funcional "do zero ao deploy", incluindo modelagem de banco de dados, regras de negócio e integração de APIs.

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
- Em qual(is) fase(s) a ferramenta atua de forma explícita? Atua em quase todo o ciclo, com ênfase em Implementação, Arquitetura e CI/CD.  
- A atuação cobre atividades centrais da fase? Quais? Sim, como geração de código full-stack, modelagem de banco de dados SQL e deploy automatizado. 

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
- A IA é central para a funcionalidade da ferramenta? Sim, a orquestração de modelos (Claude 3.5/GPT-4o) é o motor da plataforma.  
- Que capacidades “inteligentes” foram observadas na prática? Geração de planos de implementação estruturados e correção autônoma de erros de compilação.  

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas? Setup de infraestrutura, criação de CRUDs, configuração de rotas e criação de banco de dados.  
- O ganho de produtividade foi significativo ou marginal? Muito significativo, reduzindo horas de desenvolvimento para minutos.  
- Foi necessário muito retrabalho/revisão manual? Baixo, a ferramenta é assertiva em componentes visuais e lógicas padrão.  

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
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada? Sim, ao garantir políticas de segurança RLS no banco de dados e boas práticas de programação.  
- Houve melhoria perceptível na qualidade do artefato gerado? Sim, o código gerado segue padrões modernos e eficientes.  

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- [x] Documentação clara e acessível  
- [x] Tutoriais/exemplos disponíveis  
- [x] Integração com ferramentas comuns
- [x] Comunidade ativa / relatos de uso  
- [x] Estudos acadêmicos ou relatos industriais  

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**
- Que “categoria” de AI4SE esta ferramenta representa? AI Software Engineer / Plataforma de Desenvolvimento Full-stack.  
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas? Sim, pois foca na entrega do produto funcional fim-a-fim, não apenas assistência pontual.  
- Há outras ferramentas muito similares já avaliadas? Não. 

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não  

---

### **C7 — Riscos e Limitações** **Riscos observados (se houver):**
- [x] Pode introduzir erros críticos  
- ☐ Pode gerar resultados enganosos  
- [x] Dependência excessiva de IA  
- ☐ Outros: ___________

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
- Ciclo completo e extremamente rápido do prompt ao deploy.
- Integração profunda e inteligente com serviços de backend (Supabase).
- Geração de planos de ação claros antes da escrita do código.
 
### **Pontos fracos (bullet points)**
- O plano gratuito é muito restrito, permitindo poucos prompts por dia, o que interrompe o fluxo de trabalho.
- Dificuldade de migração para outros provedores de banco de dados/auth.
- Consumo rápido de créditos no plano gratuito.
- Falta de contexto para custos reais de infraestrutura em nuvem.

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☐ Incluir [x] Incluir com ressalvas ☐ Não incluir  

**Justificativa resumida em caso de não incluir (3–5 linhas):** > A ferramenta apresenta uma excelente aderência técnica aos objetivos de IA Generativa do projeto, porém sua inclusão é parcial devido às fortes restrições do plano gratuito. Como as cotas diárias de prompts são muito limitadas, o desenvolvimento contínuo e a realização de testes mais extensos ficam prejudicados, tornando o uso viável apenas sob condições específicas de assinatura ou gestão rígida de créditos.

---

## **6) Evidências Anexas (opcional)**
- Links: https://lovable.dev | https://docs.lovable.dev  

---
