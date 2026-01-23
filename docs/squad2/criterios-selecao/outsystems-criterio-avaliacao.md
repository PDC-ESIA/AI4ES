# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | OutSystems Mentor |
| **Versão (se aplicável):** | |
| **URL oficial para acesso à ferramenta/documentação:** | https://www.outsystems.com/low-code-platform/mentor-ai-app-generation/ |
| **Data da avaliação:** | 22/01/2025 |
| **Avaliador:** | Karlla Loane |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática  

> O OutSystems Mentor é uma solução de "Agentic AI" integrada à plataforma low-code OutSystems Developer Cloud, projetada para gerar e refinar aplicações full-stack a partir de descrições em linguagem natural ou documentos de requisitos. Destina-se a desenvolvedores corporativos que buscam acelerar o ciclo de vida de desenvolvimento, automatizando a criação de modelos de dados, lógica de negócio e interfaces de usuário dentro de um ecossistema governado. No contexto da avaliação prática, a ferramenta foi utilizada para gerar uma aplicação completa a partir de um documento de requisitos, demonstrando alta autonomia na orquestração de componentes de software.

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
- ☑ Manutenção/Evolução  
- ☐ Outra: ___________

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita?
  - Atua explicitamente na fase de implementação, com geração full-stack de aplicações. 
- A atuação cobre atividades centrais da fase? Quais?
  - Sim. Cobre atividades centrais como modelagem de dados, geração de lógica de negócio, construção de interfaces

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C2 — Apoio ativo por IA**

Descrição: A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA (não apenas edição ou automação tradicional).  

**Tipo de apoio por IA (marque):**  
- ☑ Geração automática  
- ☑ Sugestão/recomendação  
- ☐ Análise inteligente  
- ☐ Automação baseada em IA  
- ☐ Outro: ___________

**Perguntas orientadoras (responder brevemente):**
- A IA é central para a funcionalidade da ferramenta?
  - Sim. O Mentor é concebido como um agente de IA que interpreta descrições em linguagem natural e executa ações complexas na plataforma, sendo o principal diferencial da ferramenta. 
- Que capacidades “inteligentes” foram observadas na prática?
  - Interpretação de prompts e documentos de requisitos, geração coordenada de múltiplos artefatos (dados, lógica e UI), análise automática de qualidade e aplicação de correções assistidas.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas?
  - Criação manual de CRUDs, telas padrão, configuração inicial de banco de dados, lógica básica de negócio, verificações iniciais de qualidade e publicação da aplicação.  
- O ganho de produtividade foi significativo ou marginal?
  - Ganho significativo; reduziu o tempo de criação de um sistema web funcional de semanas (desenvolvimento tradicional) para minutos. 
- Foi necessário muito retrabalho/revisão manual?
  - Baixo a moderado, concentrado em ajustes finos de regras de negócio e customizações específicas.    

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

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
  - Sim. O uso de metamodelos internos e análises automáticas reduziu inconsistências estruturais e erros comuns.
- Houve melhoria perceptível na qualidade do artefato gerado?
  - Sim, especialmente em termos de consistência arquitetural, segurança e aderência a padrões da plataforma.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C5 — Maturidade e Adoção**

Descrição: Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- ☑ Documentação clara e acessível  
- ☑ Tutoriais/exemplos disponíveis  
- ☐ Integração com ferramentas comuns (GitHub, GitLab, VS Code, Jira, etc.)  
- ☐ Comunidade ativa / relatos de uso  
- ☐ Estudos acadêmicos ou relatos industriais  

**Atende ao critério?** ☐ Sim ☑ Parcial ☐ Não

---

### **C6 — Representatividade Funcional**

Descrição: A ferramenta representa uma categoria relevante de ferramentas AI4SE (ex.: geração de código, apoio a requisitos, teste automatizado, análise estática com IA, etc.).

**Perguntas orientadoras:**
- Que “categoria” de AI4SE esta ferramenta representa?
  - Geração full-stack orientada por agentes em plataforma low-code.  
- Ela adiciona diversidade ao conjunto de ferramentas avaliadas?
  - Adiciona diversidade ao estudo por ser uma ferramenta orientada à plataforma. 
- Há outras ferramentas muito similares já avaliadas?
  - Não diretamente; difere de geradores de UI ou assistentes de código isolados

**Atende ao critério?** ☐ Sim ☑ Parcial ☐ Não  

---

### **C7 — Riscos e Limitações** 

**Riscos observados (se houver):**
- ☐ Pode introduzir erros críticos  
- ☐ Pode gerar resultados enganosos  
- ☑ Dependência excessiva de IA  
- ☑ Outros: forte dependência de ecossistema proprietário

**Atende ao critério?** ☐ Sim ☑ Parcial ☐ Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
- Geração rápida de aplicações full-stack funcionais
- Alta consistência interna dos artefatos
- Análises automáticas de qualidade integradas 
 
### **Pontos fracos (bullet points)**
- Baixa explicabilidade das decisões da IA
- Forte dependência do ambiente proprietário OutSystems  

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☐ Incluir ☑ Incluir com ressalvas ☐ Não incluir  
 
> Apesar do alto nível de automação, a ferramenta é fortemente dependente de um ecossistema proprietário, o que limita a generalização e a comparabilidade dos resultados no contexto do experimento.

---

## **6) Evidências Anexas (opcional)**
- Links:  
- Arquivos gerados:  

---
