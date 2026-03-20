# Critérios de seleção de ferramentas AI4SE

Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.

## 1) Identificação da Ferramenta

| Item | Preenchimento |
| :--- | :--- |
| **Nome da ferramenta:** | **Qodo Gen** (anteriormente CodiumAI) |
| **Versão (se aplicável):** | Plugin VS Code (Latest) |
| **URL oficial:** | [https://www.qodo.ai/](https://www.qodo.ai/) |
| **Data da avaliação:** | 20/01/2026 |
| **Avaliador:** | Gabriel Brandão (Squad 2) |

---

## 2) Visão Geral da Ferramenta

**Descreva brevemente:**
O Qodo Gen é uma extensão de IDE focada em "Code Integrity" e geração de testes automatizados. Diferente de assistentes genéricos de chat, ele se especializa em analisar blocos de código (funções/classes) para gerar suítes de testes unitários robustos, explicar o comportamento do código e sugerir melhorias de segurança e performance. É destinado a desenvolvedores que buscam Test-Driven Development (TDD) e aumento da cobertura de testes. Na avaliação prática, foi testado na geração de testes para funções utilitárias e na explicação de lógica complexa.

---

## 3) Avaliação por Critérios de Inclusão

### C1 — Cobertura do SDLC

**Descrição:** A ferramenta apoia explicitamente pelo menos uma fase do SDLC.

**Fase(s) do SDLC apoiadas:**
- [ ] Requisitos
- [ ] Projeto/Arquitetura
- [x] Implementação (Refatoração e Explicação)
- [x] Testes (Geração e Análise de Cobertura)
- [ ] Integração/CI-CD
- [x] Manutenção/Evolução (Documentação automática de código)
- [ ] Outra: ___________

**Perguntas orientadoras:**
* **Em qual(is) fase(s) a ferramenta atua de forma explícita?**
    * Atua fortemente na fase de **Testes Unitários** e **Implementação/Codificação**.
* **A atuação cobre atividades centrais da fase? Quais?**
    * Sim. Automatiza a criação de casos de teste (incluindo *edge cases* que humanos costumam esquecer) e documentação de código (Docstrings).

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C2 — Apoio ativo por IA

**Descrição:** A ferramenta realiza geração, sugestão, análise ou automação inteligente baseada em IA.

**Tipo de apoio por IA:**
- [x] Geração automática (Testes e Docstrings)
- [x] Sugestão/recomendação (Melhorias de código)
- [x] Análise inteligente (Comportamento do código)
- [ ] Automação baseada em IA
- [ ] Outro: ___________

**Perguntas orientadoras:**
* **A IA é central para a funcionalidade da ferramenta?**
    * Sim. A ferramenta usa LLMs para "entender" a lógica do código e inferir cenários de teste plausíveis.
* **Que capacidades “inteligentes” foram observadas na prática?**
    * A capacidade de *Behavior Analysis* (Análise de Comportamento), onde a IA lista em linguagem natural o que o código faz antes de gerar os testes.

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C3 — Redução de esforço manual

**Descrição:** A ferramenta reduz ou elimina esforço manual recorrente em atividades típicas de ES.

**Perguntas orientadoras:**
* **Quais tarefas repetitivas foram reduzidas ou eliminadas?**
    * A escrita manual de *boilerplate* de testes unitários (setup, mocks, assertions) e a criação de documentação (JSDoc/Docstrings).
* **O ganho de produtividade foi significativo ou marginal?**
    * Significativo. O tempo para cobrir uma função com testes caiu de minutos para segundos.
* **Foi necessário muito retrabalho/revisão manual?**
    * Baixo a Médio. Os testes gerados geralmente rodam, mas às vezes requerem ajustes nos *Mocks* de bibliotecas externas.

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C4 — Impacto na Qualidade

**Descrição:** A ferramenta demonstra potencial para melhorar qualidade técnica ou documental.

**Tipo de impacto observado:**
- [ ] Qualidade dos requisitos
- [ ] Qualidade do design
- [x] Qualidade do código (Sugestões de refatoração)
- [x] Qualidade dos testes (Cobertura de Edge Cases)
- [x] Qualidade da documentação (Explicação de código)
- [x] Consistência/detecção de erros
- [ ] Outro: ___________

**Perguntas orientadoras:**
* **A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?**
    * Sim, encontrou bugs lógicos ao sugerir testes para casos de borda (ex: inputs nulos ou vazios) que não haviam sido tratados.
* **Houve melhoria perceptível na qualidade do artefato gerado?**
    * Sim. A ferramenta incentiva a escrita de código mais testável e modular.

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
- [x] Integração com ferramentas comuns (VS Code, JetBrains, GitHub PRs)
- [x] Comunidade ativa / relatos de uso
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
    * Assistente de Integridade de Código e Geração de Testes (focado em *Quality Assurance* na IDE).
* **Ela adiciona diversidade ao conjunto de ferramentas avaliadas?**
    * Sim. Diferencia-se do *Codeium* ou *Amazon Q* (focados em autocompletar) por ser pró-ativo na busca de erros e criação de testes, não apenas em escrever código novo.
* **Há outras ferramentas muito similares já avaliadas?**
    * O *Testim* (Time 4) foca em testes, mas de interface/E2E. O Qodo é único no foco em Testes Unitários e Integração na IDE.

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

### C7 — Riscos e Limitações

**Riscos observados:**
- [ ] Pode introduzir erros críticos
- [x] Pode gerar resultados enganosos (Testes que passam mas não testam nada - "False Positives")
- [ ] Dependência excessiva de IA
- [x] Outros: Privacidade (envio de snippets de código para nuvem).

**Atende ao critério?**
- [x] Sim
- [ ] Parcial
- [ ] Não

---

## 4) Sobre os testes realizados até o momento

**Pontos fortes:**
* Foco explícito em **Testes** (diferencial de mercado).
* Interface dedicada para revisão de testes (não é apenas um chat).
* Capacidade de auto-correção: se o teste gerado falha, ele tenta corrigir sozinho.

**Pontos fracos:**
* Às vezes gera muitos testes redundantes.
* Dificuldade em configurar mocks complexos para frameworks legados.

---

## 5) Decisão Final de Inclusão

**Decisão:**
- [x] Incluir
- [ ] Incluir com ressalvas
- [ ] Não incluir

**Justificativa resumida em caso de não incluir:**
[N/A]

---

## 6) Evidências Anexas

**Links:**
* [Relatório Técnico Qodo Gen - Squad 2](../avaliacao-codeAssistants/avaliacao-qodo-gen-v2-swebok.md)
* [Qodo Official Documentation](https://docs.qodo.ai/)

**Arquivos gerados:**
* `avaliacao-qodo-gen-v2-swebok.md` (Repositório AI4ES)