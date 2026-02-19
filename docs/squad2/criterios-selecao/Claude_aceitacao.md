# Critérios de seleção de ferramentas AI4SE

Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.

## 1) Identificação da Ferramenta

| Item | Preenchimento |
| :--- | :--- |
| **Nome da ferramenta:** | **Claude 3.5 Sonnet** |
| **Versão (se aplicável):** | 3.5 Sonnet (Web/API) |
| **URL oficial:** | [https://claude.ai/](https://claude.ai/) |
| **Data da avaliação:** | 20/01/2026 |
| **Avaliador:** | Gabriel Brandão (Squad 2) |

---

## 2) Visão Geral da Ferramenta

**Descreva brevemente:**
O Claude 3.5 Sonnet é um LLM (Large Language Model) de propósito geral desenvolvido pela Anthropic, reconhecido atualmente como o "Estado da Arte" (SOTA) para tarefas de codificação e raciocínio lógico. Diferencia-se pela funcionalidade "Artifacts", que permite gerar e renderizar interfaces (React, HTML/CSS) e diagramas (SVG, Mermaid) em uma janela lateral dedicada em tempo real. É destinado a desenvolvedores, arquitetos de software e engenheiros de dados para apoio em todo o ciclo de desenvolvimento, desde a ideação visual até a refatoração de código complexo.

---

## 3) Avaliação por Critérios de Inclusão

### C1 — Cobertura do SDLC

**Descrição:** A ferramenta apoia explicitamente pelo menos uma fase do SDLC.

**Fase(s) do SDLC apoiadas:**
- [x] Requisitos (Análise e refinamento)
- [x] Projeto/Arquitetura (Geração de diagramas e decisões técnicas)
- [x] Implementação (Geração de código fonte)
- [x] Testes (Geração de casos de teste unitários/integração)
- [ ] Integração/CI-CD
- [x] Manutenção/Evolução (Refatoração e explicação de legado)
- [ ] Outra: ___________

**Perguntas orientadoras:**
* **Em qual(is) fase(s) a ferramenta atua de forma explícita?**
    * Atua fortemente na **Implementação** (codificação) e **Projeto** (prototipagem visual e arquitetura).
* **A atuação cobre atividades centrais da fase? Quais?**
    * Sim. Cobre a escrita de código, a criação de interfaces de usuário (UI) instantâneas e a modelagem de sistemas via diagramas.

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C2 — Apoio ativo por IA

**Descrição:** A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA.

**Tipo de apoio por IA:**
- [x] Geração automática
- [x] Sugestão/recomendação
- [x] Análise inteligente
- [ ] Automação baseada em IA (Agente autônomo completo)
- [ ] Outro: ___________

**Perguntas orientadoras:**
* **A IA é central para a funcionalidade da ferramenta?**
    * Sim, a ferramenta é um modelo de IA Generativa puro acessível via chat.
* **Que capacidades “inteligentes” foram observadas na prática?**
    * Capacidade de raciocínio complexo para depuração (encontrar bugs lógicos e não apenas de sintaxe) e capacidade de "imaginar" interfaces visuais completas a partir de descrições textuais breves.

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C3 — Redução de esforço manual

**Descrição:** A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
* **Quais tarefas repetitivas foram reduzidas ou eliminadas?**
    * Configuração inicial de projetos (boilerplate), criação de componentes de UI padrão (tabelas, dashboards) e escrita manual de testes unitários repetitivos.
* **O ganho de produtividade foi significativo ou marginal?**
    * Significativo na prototipagem. O que levaria horas para configurar (React + Tailwind) foi gerado em segundos via Artifacts.
* **Foi necessário muito retrabalho/revisão manual?**
    * Nível médio. O código visual geralmente funciona de primeira, mas a lógica de backend simulada precisa ser substituída por implementações reais.

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C4 — Impacto na Qualidade

**Descrição:** A ferramenta demonstra potencial para melhorar qualidade técnica ou documental.

**Tipo de impacto observado:**
- [ ] Qualidade dos requisitos
- [x] Qualidade do design (Arquitetura)
- [x] Qualidade do código (Clean Code)
- [x] Qualidade dos testes
- [x] Qualidade da documentação
- [ ] Consistência/detecção de erros
- [ ] Outro: ___________

**Perguntas orientadoras:**
* **A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?**
    * Sim, durante o teste de refatoração, a ferramenta identificou um erro de escopo de variável (*shadowing*) que um linter comum poderia ignorar.
* **Houve melhoria perceptível na qualidade do artefato gerado?**
    * Sim, o código gerado segue padrões modernos (ex: Hooks no React, Type Hints no Python) por padrão.

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
- [x] Integração com ferramentas comuns (Via API e extensões de terceiros)
- [x] Comunidade ativa / relatos de uso
- [x] Estudos acadêmicos ou relatos industriais (SWE-bench benchmarks)

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C6 — Representatividade Funcional

**Descrição:** A ferramenta representa uma categoria relevante de ferramentas AI4SE.

**Perguntas orientadoras:**
* **Que “categoria” de AI4SE esta ferramenta representa?**
    * LLM Generalista SOTA (State-of-the-Art) com capacidades visuais (*Artifacts*). Atua como um "Pair Programmer Sênior".
* **Ela adiciona diversidade ao conjunto de ferramentas avaliadas?**
    * Sim. Diferencia-se dos "Code Assistants" (como Qodo) por não ser preso à IDE e possuir uma janela de contexto massiva (200k tokens) para análise de arquitetura.
* **Há outras ferramentas muito similares já avaliadas?**
    * O *GPT-4o* (Time 1) e *Gemini 1.5 Pro* (Time 3) são concorrentes diretos, mas o Claude se destaca especificamente na qualidade de geração de código e na feature de Artifacts.

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C7 — Riscos e Limitações

**Riscos observados:**
- [ ] Pode introduzir erros críticos
- [x] Pode gerar resultados enganosos (Alucinações em bibliotecas obscuras)
- [ ] Dependência excessiva de IA
- [x] Outros: Limite de mensagens na versão gratuita; Privacidade (não recomendado enviar código proprietário na versão free).

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

## 4) Sobre os testes realizados até o momento

**Pontos fortes:**
* **Artifacts:** Visualização instantânea de código Frontend e Diagramas (Mermaid) é um diferencial único de produtividade.
* **Raciocínio Lógico:** Demonstrou capacidade superior de debug e refatoração comparado a modelos anteriores.
* **Contexto:** Capacidade de entender instruções longas e complexas sem "se perder".

**Pontos fracos:**
* **Ambiente de Execução:** Diferente do ChatGPT (Code Interpreter), ele não roda Python/Backend real no navegador, apenas simula.
* **Custo/Limites:** A versão gratuita bloqueia o usuário rapidamente após algumas interações longas.

---

## 5) Decisão Final de Inclusão

**Decisão:**
- [x] Incluir
- [ ] Incluir com ressalvas
- [ ] Não incluir

**Justificativa resumida em caso de não incluir:**
A ferramenta é muito útil no que faz - análise de documentação de requisitos e gestão - porém, ela é paga e seus testes são difíceis para comprovar sua reprodutibilidade de maneira unitária.

---

## 6) Evidências Anexas

**Links:**
* [Relatório Técnico Claude 3.5 - Squad 2](../avaliacao-codeAssistants/avaliacao-claude.md)
* [Anthropic Artifacts Launch](https://www.anthropic.com/news/artifacts)

**Arquivos gerados:**
* `avaliacao-claude.md` (Repositório AI4ES)
* Prints do Kanban e Diagramas (via Artifacts)