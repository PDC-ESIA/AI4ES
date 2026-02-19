# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | Applitools |
| **Versão (se aplicável):** | Visual AI (Modelo Proprietário) |
| **URL oficial para acesso à ferramenta/documentação:** | https://applitools.com/docs/ |
| **Data da avaliação:** | 19/01/2026 |
| **Avaliador:** | Adriam Felipe Santos da Luz |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática  

> A Applitools é uma plataforma de testes visuais automatizados que utiliza inteligência artificial baseada em visão computacional para verificar interfaces de usuário de forma autônoma. Destina-se a engenheiros de QA (Garantia de Qualidade) e desenvolvedores frontend que buscam garantir a fidelidade visual e detectar regressões de layout em diversas plataformas. Na avaliação prática, a ferramenta foi testada em experimentos de detecção de regressão estrutural, mudanças milimétricas de layout e análise de conformidade com normas de acessibilidade visual (WCAG).

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
- [x] Testes  
- [x] Integração/CI-CD  
- [x] Manutenção/Evolução  
- ☐ Outra: ___________

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita? Atua principalmente em Testes, Manutenção e Integração.
- A atuação cobre atividades centrais da fase? Quais? Sim, como execução de testes de regressão visual, dando suporte a manutenção do software.

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não  

---

### **C2 — Apoio ativo por IA**

Descrição: A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA (não apenas edição ou automação tradicional).  

**Tipo de apoio por IA (marque):**  
- ☐ Geração automática  
- ☐ Sugestão/recomendação  
- [x] Análise inteligente  
- [x] Automação baseada em IA  
- ☐ Outro: ___________

**Perguntas orientadoras (responder brevemente):**
- A IA é central para a funcionalidade da ferramenta? Sim, o algoritmo de Visual AI é o motor que permite a comparação inteligente de telas sem depender de comparação de pixels simples.
- Que capacidades “inteligentes” foram observadas na prática? Detecção de mudanças imperceptíveis ao olho humano, identificação de elementos estruturais e propagação automática de aceite de mudanças (Auto-Maintenance).

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas? Elimina a necessidade de inspeção visual manual exaustiva e simplifica scripts de teste ao substituir múltiplas asserções de CSS por um único comando visual.
- O ganho de produtividade foi significativo ou marginal? Significativo, acelerando o ciclo de feedback visual e o processo de Code Review.
- Foi necessário muito retrabalho/revisão manual? Baixo, embora exija a validação humana para aprovar ou rejeitar novas Baselines.

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):**  
- ☐ Qualidade dos requisitos
- ☐ Qualidade do design
- ☐ Qualidade do código  
- [x] Qualidade dos testes  
- [x] Qualidade da documentação (Histórico visual)
- [x] Consistência/detecção de erros  
- ☐ Outro: ___________

**Perguntas orientadoras:**
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada? Sim, detectou com precisão as mudanças estruturais e nas cores em relação à referência.
- Houve melhoria perceptível na qualidade do artefato gerado? Sim, garante a manutenção do padrão visual e integridade da marca ao longo das iterações.

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- [x] Documentação clara e acessível  
- [x] Tutoriais/exemplos disponíveis  
- [x] Integração com ferramentas comuns (Cypress, Playwright, Selenium, GitHub)  
- [x] Comunidade ativa / relatos de uso  
- [x] Estudos acadêmicos ou relatos industriais  

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**
- Que “categoria” de AI4SE esta ferramenta representa? Plataforma de Testes Visuais Automatizados.
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas? Sim, pois introduz a análise por visão computacional, diferindo de assistentes de código textuais.
- Há outras ferramentas muito similares já avaliadas? Não.

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não  

---

### **C7 — Riscos e Limitações** 

**Riscos observados (se houver):**
- [x] Pode introduzir erros críticos (Aceite de Baselines incorretas)
- ☐ Pode gerar resultados enganosos  
- [x] Dependência excessiva de IA (Aceitação amoral no primeiro teste)
- ☐ Outros: ___________

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
- Extrema precisão na detecção de mudanças visuais e estruturais.
- Redução drástica na manutenção de scripts de testes de interface.
- Resultados determinísticos com baixa ocorrência de falsos positivos.
- Dashboard robusto que facilita a gestão de logs visuais e incidentes.
 
### **Pontos fracos (bullet points)**
- Dependência absoluta da Baseline; se a primeira imagem estiver errada, a IA a protegerá como correta.
- Custo elevado para grandes volumes de testes na versão comercial.
- Relatórios de acessibilidade limitados a planos superiores (Starter).

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☐ Incluir ☐ Incluir com ressalvas [x] Não incluir  

**Justificativa resumida em caso de não incluir (3–5 linhas):**  > Embora a ferramenta apresente alta maturidade em testes visuais, ela foi excluída por não se enquadrar como uma **IA Generativa**. O foco central do projeto TACO é a aplicação de LLMs e modelos generativos para automação e assistência direta no ciclo de desenvolvimento (SDLC). Como o Applitools foca na camada de apresentação (UI) através de visão computacional, e não na lógica de software ou qualidade do código-fonte, ele acaba sendo periférico demais aos objetivos da nossa pesquisa.

---

## **6) Evidências Anexas (opcional)**
- Links: https://applitools.com/docs/
---
