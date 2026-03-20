# Critérios de seleção de ferramentas AI4SE

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | Cursor |
| **Versão (se aplicável):** | Cursor 0.42+ (2025) |
| **URL oficial para acesso à ferramenta/documentação:** | [Site oficial](https://cursor.com) e [Documentação](https://docs.cursor.com) |
| **Data da avaliação:** | Janeiro 2026 |
| **Avaliador:** | Leonardo Côrtes Filho |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

Cursor é um IDE (fork do VS Code) com IA generativa integrada destinado a desenvolvedores que buscam acelerar a escrita de código através de sugestões contextuais, chat com base de código e edição em múltiplos arquivos simultaneamente. A ferramenta atua principalmente na fase de implementação do SDLC, fornecendo autocompletion avançado via Tab, chat conversacional sobre o código (Cmd+K), geração de código a partir de prompts em linguagem natural, e refatoração assistida por IA usando modelos Claude Sonnet 3.5, GPT-4, ou modelos customizados.

---

## **3) Avaliação por Critérios de Inclusão**

---

### **C1 — Cobertura do SDLC**

**Fase(s) do SDLC apoiadas:**

- ☐ Requisitos
- ☑ Projeto/Arquitetura
- ☑ Implementação (Geração código, refatoração, debugging - CORE)
- ☑ Testes (Geração unit tests, test-driven development)
- ☐ Integração/CI-CD
- ☐ Manutenção/Evolução

**Em qual(is) fase(s) a ferramenta atua de forma explícita?**

- **Implementação (CORE):** Geração código via chat/Tab, refatoração multi-arquivo, debugging com IA, code completion contextual
- **Testes (Limitado):** Geração unit tests sob demanda, sugestões test cases

**A atuação cobre atividades centrais da fase?**

- **Implementação:** Sim - escrita código, refatoração, debugging, documentação inline
- **Testes:** Parcial - gera testes mas não executa ou valida

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C2 — Apoio ativo por IA**

**Tipo de apoio por IA:**

- ☑ Geração automática (Code generation via Tab, Cmd+K)
- ☑ Sugestão/recomendação (Inline suggestions, multi-line completions)
- ☑ Análise inteligente (Codebase indexing, semantic search)
- ☑ Automação baseada em IA (Multi-file editing, apply changes across files)

**A IA é central para a funcionalidade da ferramenta?**
Sim. Cursor é IDE construído em torno de IA generativa. Funcionalidades core: (1) Tab completion (multi-line predictions), (2) Cmd+K (chat inline no código), (3) Composer (edição multi-arquivo via chat), (4) Codebase context (indexação semântica automática).

**Capacidades "inteligentes" observadas:**

1. **Tab completion:** Predição multi-linha contextual (superior a Copilot segundo benchmarks comunidade)
2. **Cmd+K:** Chat inline para editar código no cursor, aceitar/rejeitar mudanças
3. **Composer:** Edição simultânea múltiplos arquivos via prompt único
4. **Codebase awareness:** Indexação automática repositório, busca semântica, referências inteligentes
5. **Model flexibility:** Suporta Claude, GPT-4, modelos custom via API

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

**Tarefas repetitivas reduzidas:**

1. **Boilerplate code:** Geração automática classes, métodos, testes (redução estimada 60-80%)
2. **Refatoração multi-arquivo:** Renomear variáveis, extrair métodos em múltiplos arquivos simultaneamente
3. **Navegação codebase:** Busca semântica vs grep/find (redução 50% tempo)
4. **Documentação:** Geração docstrings, comentários, READMEs
5. **Conversão entre linguagens:** Tradução código Python→TypeScript, etc

**Ganho produtividade:** Significativo - comunidade reporta 30-50% aumento velocidade desenvolvimento

**Retrabalho necessário:** Moderado (20-30%). Sugestões IA requerem revisão, código gerado pode ter bugs lógicos, hallucinations ocasionais.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C4 — Impacto na Qualidade**

**Tipo de impacto:**

- ☐ Qualidade requisitos
- ☑ Qualidade design (Sugere padrões arquiteturais, refatorações)
- ☑ Qualidade código (Code completion reduz syntax errors, sugere idioms)
- ☑ Qualidade testes (Gera unit tests, test cases)
- ☑ Qualidade documentação (Gera docstrings, READMEs)
- ☑ Detecção erros (Identifica bugs, sugere fixes)

**Erros evitados:**

- Syntax errors reduzidos (autocompletion correto)
- Logic bugs (IA sugere validações, edge cases)
- Inconsistências estilo (IA segue padrões codebase)

**Melhoria qualidade:**

- Código mais idiomático (IA conhece best practices)
- Melhor documentação (geração automática)
- Testes mais abrangentes (IA sugere edge cases)

**Limitação:** IA pode introduzir bugs sutis, anti-patterns. Requer validação humana + ferramentas complementares (SonarQube).

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C5 — Maturidade e Adoção**

**Observado:**

- ☑ Documentação completa (docs.cursor.sh)
- ☑ Tutoriais disponíveis (YouTube, docs oficiais, comunidade)
- ☑ Integração limitada (VS Code extensions compatíveis, APIs LLM)
- ☑ Comunidade ativa (Discord, Twitter/X, Reddit /r/cursor)
- ☐ Estudos acadêmicos (ferramenta recente, poucos estudos formais)

**Maturidade técnica:**

- Produto relativamente novo (lançado 2023)
- Adoção crescente (100k+ usuários reportados)
- Empresa startup com funding (não empresa pública como Microsoft/Amazon)

**Atende ao critério?** ☐ Sim ☑ Parcial ☐ Não

---

### **C6 — Representatividade Funcional**

**Categoria:** Assistente de código IA integrado (IDE-native AI coding assistant)

**Adiciona diversidade?** Sim:

- **vs Copilot:** Copilot é extension, Cursor é IDE completo com IA nativa
- **vs CodeWhisperer:** Cursor suporta múltiplos LLMs (Claude, GPT-4, custom)
- **vs SonarQube:** Cursor gera código, SonarQube valida (complementares)
- **Diferencial:** Composer (multi-file editing), codebase indexing, model flexibility

**Ferramentas similares:** Copilot

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C7 — Riscos e Limitações**

**Riscos:**

- ☑ Erros críticos (IA pode gerar código com bugs lógicos, vulnerabilidades)
- ☑ Resultados enganosos (Hallucinations, código plausível mas incorreto)
- ☑ Dependência IA (Desenvolvedores podem perder proficiência em código manual)
- ☑ Outros: **Custo alto, Vendor lock-in, Privacidade código, Requer conectividade**

**Mitigações:** Supervisão humana, combinar com SonarQube, code review rigoroso, treinar equipe em prompt engineering

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes**

- Geração código contextual superior (codebase indexing automático)
- Competência com linguagens menos usadas
- Composer permite edição multi-arquivo simultânea
- Model flexibility (Claude, GPT-4, modelos custom via API)
- Tab completion multi-linha (predições longas e precisas)
- Chat inline (Cmd+K) permite iteração rápida
- Busca semântica codebase (superior a grep/find)

### **Pontos fracos**

- Custo alto ($20-40/usuário/mês, escala com equipe)
- Privacidade: código trafega para APIs externas (Claude/OpenAI)
- Vendor lock-in (dependência IDE Cursor, migração difícil)
- Requer internet constante (offline mode limitado)
- Qualidade variável (depende prompt quality, pode gerar bugs)
- Poucos estudos acadêmicos (validação formal limitada)

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☑ Incluir ☐ Incluir com ressalvas ☐ Não incluir

**Justificativa resumida:**

A ferramenta demonstra redução significativa de esforço manual com ganhos reportados de 30-50% em velocidade de desenvolvimento pela comunidade. Os riscos identificados como custo escalável e privacidade de código são comuns a assistentes de IA e mitigáveis através de supervisão humana e validação com ferramentas complementares.

---

## **6) Evidências Anexas**

**Links:**

- Site oficial: https://cursor.sh
- Documentação: https://docs.cursor.sh
- Comunidade: Discord, Reddit /r/cursor
- Pricing: https://cursor.sh/pricing
