# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | ReqView |
| **Versão (se aplicável):** | 2.21.2. |
| **URL oficial para acesso à ferramenta/documentação:** | https://www.reqview.com/doc/welcome/ |
| **Data da avaliação:** | 25/01/2026 |
| **Avaliador:** | Vinicius Espindola |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática  

> _O ReqView é uma ferramenta especializada no gerenciamento de requisitos e rastreabilidade que tem como propósito garantir a integridade e a conformidade técnica ao longo do ciclo de vida de desenvolvimento (SDLC). Destinado a engenheiros de software e analistas de requisitos, ele facilita atividades críticas como a elicitação, análise de impacto e vinculação entre requisitos e casos de teste através de uma interface baseada em tabelas e integração com Git_  
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
- ☐ Implementação  
- ☐ Testes  
- ☐ Integração/CI-CD  
- [x] Manutenção/Evolução  
- [x] Outra: Gerenciamento de Projetos e Riscos

**Perguntas orientadoras (responder brevemente):**
- Em qual(is) fase(s) a ferramenta atua de forma explícita? 

O ReqView atua de forma central na fase de Requisitos, permitindo a elicitação, especificação e rastreabilidade.

- A atuação cobre atividades centrais da fase? Quais?

Sim. Nos Requisitos, cobre a criação de Histórias de Usuário, requisitos funcionais/não funcionais e critérios de aceitação.

**Atende ao critério?** ☐ Sim [x] Parcial ☐ Não  

---

### **C2 — Apoio ativo por IA**

Descrição: A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA (não apenas edição ou automação tradicional).  

**Tipo de apoio por IA (marque):**  
- ☐ Geração automática  
- [x] Sugestão/recomendação  
- [x] Análise inteligente  
- ☐ Automação baseada em IA  
- [x] Outro: Análise de Qualidade de Requisitos

**Perguntas orientadoras (responder brevemente):**
- A IA é central para a funcionalidade da ferramenta?

Não. A funcionalidade central do ReqView é o gerenciamento estruturado de requisitos e rastreabilidade em Git. A IA é um componente auxiliar utilizado para refinar a qualidade

- Que capacidades “inteligentes” foram observadas na prática?  

Observou-se a análise automática de requisitos para detecção de ambiguidades, verificações de gramática técnica e clareza

**Atende ao critério?** ☐ Sim [x] Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

Descrição: A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
- Quais tarefas repetitivas foram reduzidas ou eliminadas?

O ReqView elimina a necessidade de criar manualmente Matrizes de Rastreabilidade (RTM) em Excel ou Word, automatizando a vinculação entre requisitos, testes e riscos.

- O ganho de produtividade foi significativo ou marginal?  

O ganho é significativo para a gestão de requisitos em larga escala. A integração com Git permite que as mudanças nos requisitos sejam versionadas automaticamente junto com o código, eliminando a tarefa manual de sincronização entre diferentes ferramentas ou documentos isolados.

- Foi necessário muito retrabalho/revisão manual?

Baixo. Como a ferramenta foca em consistência estrutural e lógica (rastreabilidade), ela previne erros de "elos perdidos" antes mesmo de serem criados

**Atende ao critério?** ☐ Sim [x] Parcial ☐ Não

---

### **C4 — Impacto na Qualidade**

Descrição: A ferramenta demonstra potencial para melhorar qualidade técnica (código, arquitetura, testes) ou qualidade documental (requisitos, especificações, rastreabilidade, etc.).

**Tipo de impacto observado (marque):**  
- [x] Qualidade dos requisitos
- ☐ Qualidade do design
- ☐ Qualidade do código  
- [x] Qualidade dos testes  
- [x] Qualidade da documentação  
- ☐ Consistência/detecção de erros  
- ☐ Outro: ___________

**Perguntas orientadoras:**
- A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada? 

Sim. O ReqView impede inconsistências ao detectar automaticamente requisitos órfãos (sem rastreabilidade para o nível superior) ou sem cobertura de testes.

- Houve melhoria perceptível na qualidade do artefato gerado?

Sim. A qualidade documental é elevada pela estrutura padronizada e pela clareza na hierarquia dos objetos.

**Atende ao critério?** ☐ Sim [x] Parcial ☐ Não  

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

O ReqView representa a categoria de Gerenciamento de Requisitos e Rastreabilidade (RM & Traceability). No contexto de AI4SE, ela se enquadra como uma ferramenta de apoio à qualidade documental e governança.

- Ela adiciona diversidade ao conjunto de ferramentas avaliadas?

Sim, significativamente. Enquanto a maioria das ferramentas de IA foca na implementação (código), o ReqView traz o foco para as fases iniciais e transversais do SDLC.

- Há outras ferramentas muito similares já avaliadas?

Não, ferramentas como IBM DOORS ou Jama Connect são similares em propósito mas não foram incluídas na pesquisa.

**Atende ao critério?** [x] Sim ☐ Parcial ☐ Não  

---

### **C7 — Riscos e Limitações** 

**Riscos observados (se houver):**
- ☐ Pode introduzir erros críticos  
- [x] Pode gerar resultados enganosos  
- [x] Dependência excessiva de IA  
- [x] Outros: A principal limitação é a dependência de processos locais e a necessidade de configuração manual para integrações avançadas de IA, além de não possuir geração de código nativa. Além da complexidade de configuração.

**Atende ao critério?** ☐ Sim  [x] Parcial ☐ Não 

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**

-   Rastreabilidade Rigorosa: A ferramenta permite criar vínculos entre as necessidades de negócio e as especificações técnicas, garantindo que nenhum requisito fique sem cobertura de teste.

-  Controle de Versão via Git: O uso de arquivos JSON versionados no Git permite que a equipe de requisitos e a de desenvolvimento trabalhem em sintonia, mantendo um histórico claro de quem alterou cada regra de negócio e por quê.

-  Segurança: Por processar os dados localmente, oferece maior proteção para a propriedade intelectual e dados sensíveis do projeto, minimizando riscos de vazamento comuns em ferramentas puramente baseadas em nuvem.  
 
### **Pontos fracos (bullet points)**

-  Falta de Geração de Código Nativa: Diferente de assistentes, o ReqView não gera a implementação das funções, limitando-se ao apoio documental e analítico.

-  IA como Recurso Modular: A assistência inteligente não é central; para análises mais profundas via LLMs, pode ser necessário configurar scripts ou APIs externas, o que aumenta a complexidade.

-  Curva de Aprendizado de Configuração: A configuração inicial de templates e a definição de atributos customizados exigem um planejamento prévio detalhado para que a ferramenta entregue valor.

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☐ Incluir ☐ Incluir com ressalvas [x] Não incluir  

Embora a ferramenta apresente suporte robusto à Engenharia de Requisitos e Rastreabilidade, sua atuação é muito limitada às fases iniciais do SDLC. Por não oferecer capacidades de geração de código, automação de deploys ou suporte ativo à implementação, ela não cobre o ciclo de desenvolvimento completo.  

---

## **6) Evidências Anexas (opcional)**
- Links: [Documentação Oficial](https://www.google.com/search?q=https://www.reqview.com/doc/user-guide.html), [Guia de Análise de Qualidade de Requisitos (ISO 29148)](https://www.google.com/search?q=https://www.reqview.com/blog/how-to-write-good-requirements.html)
---
