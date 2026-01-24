# Critérios de seleção de ferramentas AI4SE

Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.

## 1) Identificação da Ferramenta

| Item | Preenchimento |
| :--- | :--- |
| **Nome da ferramenta:** | **Visure Requirements ALM Platform** (Módulo: AI Quality Analyzer) |
| **Versão (se aplicável):** | Visure ALM 7.x (Cloud/Desktop) |
| **URL oficial:** | [https://visuresolutions.com/](https://visuresolutions.com/) |
| **Data da avaliação:** | 20/01/2026 |
| **Avaliador:** | Gabriel Brandão (Squad 2) |

---

## 2) Visão Geral da Ferramenta

**Descreva brevemente:**
O Visure é uma plataforma de ALM (Application Lifecycle Management) focada na Engenharia de Requisitos. Seu módulo de IA ("Quality Analyzer") utiliza Processamento de Linguagem Natural (NLP) para analisar a qualidade semântica dos requisitos em tempo real. A ferramenta é destinada a engenheiros de requisitos, analistas de negócios e gerentes de conformidade, especialmente em indústrias reguladas (automotiva, aeroespacial, médica). Na avaliação prática, foi testada sua capacidade de detectar ambiguidades e termos vagos em especificações textuais baseando-se em normas internacionais (como INCOSE).

---

## 3) Avaliação por Critérios de Inclusão

### C1 — Cobertura do SDLC

**Descrição:** A ferramenta apoia explicitamente pelo menos uma fase do SDLC.

**Fase(s) do SDLC apoiadas:**
- [x] Requisitos
- [ ] Projeto/Arquitetura
- [ ] Implementação
- [x] Testes (Gestão e Rastreabilidade)
- [ ] Integração/CI-CD
- [ ] Manutenção/Evolução
- [ ] Outra: ___________

**Perguntas orientadoras:**
* **Em qual(is) fase(s) a ferramenta atua de forma explícita?**
    * Atua primariamente na Engenharia de Requisitos e secundariamente na Gestão de Testes (rastreabilidade).
* **A atuação cobre atividades centrais da fase? Quais?**
    * Sim. Cobre elicitação, análise de qualidade, validação de conformidade e especificação de requisitos.

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C2 — Apoio ativo por IA

**Descrição:** A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA.

**Tipo de apoio por IA:**
- [ ] Geração automática
- [ ] Sugestão/recomendação
- [x] Análise inteligente
- [ ] Automação baseada em IA
- [ ] Outro: ___________

**Perguntas orientadoras:**
* **A IA é central para a funcionalidade da ferramenta?**
    * Sim, para o módulo "Quality Analyzer", a IA é o motor central que permite a verificação instantânea de regras semânticas.
* **Que capacidades “inteligentes” foram observadas na prática?**
    * Capacidade de identificar adjetivos e advérbios subjetivos (ex: "sistema rápido", "interface amigável") e classificar a qualidade do requisito com um *score* (1 a 5 estrelas).

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C3 — Redução de esforço manual

**Descrição:** A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
* **Quais tarefas repetitivas foram reduzidas ou eliminadas?**
    * A revisão manual de sintaxe e conformidade de requisitos ("Peer Review" textual), que geralmente consome horas de engenheiros seniores.
* **O ganho de produtividade foi significativo ou marginal?**
    * Significativo na etapa de pré-aprovação de documentos, filtrando erros óbvios antes da revisão humana final.
* **Foi necessário muito retrabalho/revisão manual?**
    * Pouco. A ferramenta aponta o erro e sugere a categoria da falha, exigindo apenas a reescrita pontual pelo usuário.

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C4 — Impacto na Qualidade

**Descrição:** A ferramenta demonstra potencial para melhorar qualidade técnica ou documental.

**Tipo de impacto observado:**
- [x] Qualidade dos requisitos
- [ ] Qualidade do design
- [ ] Qualidade do código
- [x] Qualidade dos testes (Rastreabilidade)
- [x] Qualidade da documentação
- [x] Consistência/detecção de erros
- [ ] Outro: ___________

**Perguntas orientadoras:**
* **A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?**
    * Sim, evitou a aprovação de requisitos ambíguos que poderiam gerar erros de interpretação no desenvolvimento.
* **Houve melhoria perceptível na qualidade do artefato gerado?**
    * Sim, os requisitos reescritos após o feedback da IA tornaram-se mensuráveis e verificáveis.

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C5 — Maturidade e Adoção

**Descrição:** Há evidências de uso prático, integração com outras ferramentas, documentação disponível e/ou casos de uso reportados.

**Marque o que foi observado:**
- [x] Documentação clara e acessível
- [x] Tutoriais/exemplos disponíveis
- [x] Integração com ferramentas comuns (Jira, GitLab, Word/Excel)
- [ ] Comunidade ativa / relatos de uso (Focado em nicho Enterprise)
- [x] Estudos acadêmicos ou relatos industriais

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C6 — Representatividade Funcional

**Descrição:** A ferramenta representa uma categoria relevante de ferramentas AI4SE.

**Perguntas orientadoras:**
* **Que “categoria” de AI4SE esta ferramenta representa?**
    * Análise de Qualidade de Requisitos e Conformidade (Compliance) baseada em NLP.
* **Ela adiciona diversidade ao conjunto de ferramentas avaliadas?**
    * Sim. Diferente de geradores de texto (GPT/Claude) ou ferramentas de gestão geral (Jira), o Visure é especializado em garantir a *qualidade técnica do texto* segundo normas de engenharia.
* **Há outras ferramentas muito similares já avaliadas?**
    * A ferramenta *ReqView* (Time 3) e *Copilot 4 DevOps* (Time 4) tocam em requisitos, mas o Visure se distingue pelo foco profundo em análise de qualidade normativa (INCOSE).

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C7 — Riscos e Limitações

**Riscos observados:**
- [ ] Pode introduzir erros críticos
- [ ] Pode gerar resultados enganosos
- [ ] Dependência excessiva de IA
- [x] Outros: Custo elevado e Curva de aprendizado.

**Atende ao critério?** (A ferramenta é segura o suficiente para ser incluída?)
- [x] Sim
- [ ] Parcial
- [ ] Não

---

## 4) Sobre os testes realizados até o momento

**Pontos fortes:**
* Feedback instantâneo sobre a qualidade do texto (tempo real).
* Explicação educativa do erro (ex: explica por que "rápido" é um termo ambíguo).
* Integração total entre Requisito, Risco e Teste.
* Baseado em normas industriais consolidadas (não alucina regras).

**Pontos fracos:**
* Ferramenta Enterprise "pesada", com interface complexa para iniciantes.
* Não possui versão gratuita permanente (apenas Trial).
* Foca apenas no texto, não auxiliando na geração de diagramas ou código a partir dos requisitos.

---

## 5) Decisão Final de Inclusão

**Decisão:**
- [ ] Incluir
- [x] Incluir com ressalvas
- [ ] Não incluir

**Justificativa resumida em caso de não incluir:**
[N/A]

---

## 6) Evidências Anexas

**Links:**
* [Relatório Técnico Visure - Squad 2](../avaliacao-codeAssistants/avaliacao-visure.md)
* [Documentação Oficial Visure - Quality Analyzer](https://visuresolutions.com/features/ai-requirements-management/)

**Arquivos gerados:**
* `avaliacao-visure.md` (Repositório AI4ES)