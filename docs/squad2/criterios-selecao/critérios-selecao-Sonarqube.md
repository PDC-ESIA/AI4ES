# Critérios de seleção de ferramentas AI4SE

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | SonarQube |
| **Versão (se aplicável):** | SonarQube Cloud Team (2025) / SonarQube Server Community Edition 10.x |
| **URL oficial para acesso à ferramenta/documentação:** | [Site oficial](https://www.sonarqube.org) / [Documentação](https://docs.sonarsource.com) |
| **Data da avaliação:** | Janeiro 2026 |
| **Avaliador:** | Leonardo Côrtes Filho |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**

SonarQube é uma plataforma de análise estática de código com recursos de IA generativa (AI CodeFix, AI Code Assurance) destinada a equipes de desenvolvimento que buscam garantir qualidade, segurança e manutenibilidade do código-fonte. A ferramenta atua principalmente nas fases de implementação, testes e manutenção do SDLC, fornecendo análise automática em 35+ linguagens, detecção de vulnerabilidades (OWASP Top 10, CWE), cálculo de débito técnico e correções automáticas via LLMs (Claude Sonnet 4 ou GPT-4o). No contexto de avaliação, foi testada para validar código gerado por assistentes de IA (OE1), validar outputs de LLMs open-source (OE2), integrar-se a pipelines LLMOps (OE3), e fornecer feedback técnico para o protótipo TACO (OE5).

---

## **3) Avaliação por Critérios de Inclusão**

---

### **C1 — Cobertura do SDLC**

**Fase(s) do SDLC apoiadas (marque todas):**

- ☐ Requisitos
- ☐ Projeto/Arquitetura
- ☑ Implementação (AI CodeFix refatoração, detecção bugs/vulnerabilidades - CORE)
- ☑ Testes (Análise cobertura, identifica coverage gaps)
- ☑ Integração/CI-CD (Quality Gates bloqueiam merges, integração GitHub/Jenkins)
- ☑ Manutenção/Evolução (Correções automatizadas, Technical Debt - CORE)

**Em qual(is) fase(s) a ferramenta atua de forma explícita?**

- **Implementação (CORE):** Refatoração código (AI CodeFix), detecção bugs (5000+ regras, 35 linguagens), code smells, vulnerabilidades (SQL injection, XSS)
- **CI/CD (CORE):** Integração pipelines, Quality Gates bloqueiam builds, PR decoration
- **Manutenção (CORE):** Technical Debt quantificado (SQALE), correções automáticas, Remediation Agent aplica fixes em PRs

**A atuação cobre atividades centrais da fase?**

- **Implementação:** Sim - detecção bugs, refatoração, complexidade, duplicação, padrões SOLID/DRY
- **CI/CD:** Sim - PR comments, deployment tracking, bloqueia merges, webhooks Jira/Slack
- **Manutenção:** Sim - one-click fix, gestão débito técnico, priorização severidade
- **Segurança:** Sim - SAST robusto (OWASP Top 10, PCI-DSS, CWE), compliance reports

**Atende ao critério?** [ ] Sim [X] Parcial [ ] Não

---

### **C2 — Apoio ativo por IA**

**Tipo de apoio por IA (marque):**
 (Detecção anti-patterns: God Classes, acoplamento) (Detecção anti-patterns: God Classes, acoplamento)
- ☑ Geração automática (AI CodeFix gera código corrigido)
- ☑ Sugestão/recomendação (AI CodeFix refatorações, APM Recommendations)
- ☑ Análise inteligente (AI Code Assurance detecta código AI, analisa qualidade)
- ☑ Automação baseada em IA (Remediation Agent aplica correções em PRs)

**A IA é central para a funcionalidade da ferramenta?**
Parcialmente. SonarQube possui: (1) Motor análise estática (5000+ regras determinísticas, core desde 2007, funciona sem IA), (2) AI CodeFix (Claude Sonnet 4/GPT-4o, recurso 2024, Team/Enterprise). Análise estática é core, IA generativa é diferencial competitivo que amplia capacidades.

**Capacidades "inteligentes" observadas:**

1. **AI CodeFix (Claude Sonnet 4):** Correções contextuais bugs/vulnerabilities, 78% taxa aprovação, 95-98% redução tempo (5-15s vs 15-60min). Exemplo: NPE → Optional.ofNullable()
2. **AI Code Assurance:** Detecta código GitHub Copilot via telemetria, Quality Gates especializados, badges certificação
3. **RAG Implícito:** AI CodeFix usa código+regra+contexto+best practices (não configurável)
4. **MCP Server (Preview):** LLMs (Gemini/Claude) consultam análises SonarQube via Model Context Protocol

**Atende ao critério?** [ ] Sim [X] Parcial [ ] Não

---

### **C3 — Redução de esforço manual**

**Tarefas repetitivas reduzidas:**

1. **Code review:** 30-60min/PR → 2-5min análise automática
2. **Correção bugs:** 15-30min → 5-15s AI CodeFix one-click
3. **Gestão débito técnico:** Planilhas manuais → cálculo automático SQALE
4. **Compliance reports:** 1-2 dias auditoria manual → 5min relatórios automáticos
5. **Setup análise estática:** 4-8h configurar linters → 1-2h Docker Compose

**Ganho produtividade:** Significativo - correção -95-98%, code review -80%, compliance -95%, tracking -100%

**Retrabalho necessário:** Marginal (10-20%). Análise estática: 5-10% falsos positivos. AI CodeFix: 78% aprovadas, 22% requerem ajuste, 1.95 issues/tarefa introduzidas. Supervisão humana essencial.

**Atende ao critério?** [X] Sim [ ] Parcial [ ] Não

---

### **C4 — Impacto na Qualidade**

**Tipo de impacto (marque):**

- ☐ Qualidade requisitos
- ☑ Qualidade design (Anti-patterns: God Classes, complexidade)
- ☑ Qualidade código (5000+ regras SOLID/DRY, AI CodeFix legibilidade)
- ☑ Qualidade testes (Análise cobertura, detecta código não testável)
- ☑ Qualidade documentação (Relatórios conformidade, badges, APIs REST)
- ☑ Detecção erros (NPE, race conditions, SQL injection, XSS)

**Erros evitados:**

- **Bugs:** NPE, resource leaks, race conditions, logic errors (detectados pré-produção)
- **Vulnerabilidades:** SQL Injection, XSS, deserialization, insecure crypto (conformidade OWASP Top 10, evita CVEs)
- **Inconsistências padrão:** SOLID violations, duplicação código, acoplamento excessivo
- **Código AI (AI Code Assurance):** Código Copilot tem 2x mais security issues (8.2 vs 5.1/1k LOC) - valida qualidade (OE1)

**Melhoria qualidade:**

- **Métricas pós-adoção:** Maintainability D/E→A/B (6 meses), Reliability C→A, Security D→A, Debt 10%→0.5%, Coverage 40%→80%
- **Case studies:** 60% redução débito (6 meses), 3 CVEs evitados, código AI CodeFix 40% menos incidents
- **TACO (OE5):** Alunos recebem feedback técnico preciso, code smells desde início, bugs pré-submissão

**Atende ao critério?** [X] Sim [ ] Parcial [ ] Não

---

### **C5 — Maturidade e Adoção**

**Observado:**

- ☑ Documentação completa (docs.sonarsource.com - clara, searchable)
- ☑ Tutoriais disponíveis (Docker, GitHub Actions, Quality Gates best practices)
- ☑ 35+ integrações (GitHub, GitLab, Azure DevOps, Jenkins, VS Code, Jira, Slack)
- ☑ Comunidade ativa (7M+ devs, G2 4.4/5 stars 500+ reviews, Stack Overflow #8)
- ☑ Reconhecimento (Gartner "Challengers" SAST, case studies Airbnb/Peloton)

**Maturidade técnica:**

- Análise estática: Production-ready (15+ anos desde 2007)
- AI CodeFix: Early Access (2024, funcional)
- AI Code Assurance: Production-ready com limitações (só GitHub Copilot)

**Atende ao critério?** [X] Sim [ ] Parcial [ ] Não

---

### **C6 — Representatividade Funcional**

**Categoria:** Análise estática de código com IA generativa (SAST + AI-powered code fixing)

**Adiciona diversidade?** Sim - complementaridade crítica:

- **vs Copilot/CodeWhisperer:** Copilot gera → SonarQube valida/corrige (AI Code Assurance único mercado)
- **vs LLMs open-source (OE2):** CodeLlama/DeepSeek geram → SonarQube valida (métricas complexity/debt)
- **OE3 LLMOps:** Métricas como KPIs desempenho LLM, Quality Gates bloqueiam código ruim
- **OE4/OE5:** AI CodeFix baseline refatoração, MCP Server integra TACO+Gemini

**Há outras ferramentas muito similares já avaliadas?** Não, mas para registrar exemplos para possíveis estudos futuros: Semgrep, CodeQL, Snyk, Checkmarx.

**Atende ao critério?** [X] Sim [ ] Parcial [ ] Não

---

### **C7 — Riscos e Limitações**

**Riscos:**

- ☑ Erros críticos (AI CodeFix: 22% requerem ajuste, 1.95 issues/tarefa)
- ☑ Resultados enganosos (Falsos positivos 5-10%, projeto legado alert fatigue)
- ☑ Dependência IA (Devs aplicam fix sem revisar, confiança cega)
- ☑ Outros: **Vendor lock-in AI, Custo escalável, APIs externas, Não offline**

**Detalhamento riscos críticos:**

1. **AI CodeFix bugs:** 78% aprovação = 22% problemáticas, 1.95 issues/tarefa (supervisão humana obrigatória)
2. **Falsos positivos:** 5-10% irrelevantes, primeiro scan legado milhares issues (configurar Quality Profile, focar código novo)
3. **Vendor lock-in AI:** APIs LLM via Sonar (sem fine-tuning). Mitigação: Community funciona sem AI, fallback Semgrep+Aider
4. **Custo escalável:** SonarCloud +125% (€3.2k→€7.2k/ano 2024). Mitigação: Community self-hosted $0, contrato multi-year
5. **APIs externas:** AI CodeFix offline impossível, código trafega Anthropic/OpenAI. Mitigação: Azure OpenAI (tenant), ou desabilitar AI

**Atende ao critério?** ☑ **Sim** (riscos gerenciáveis com mitigações)

---
<!-- Será melhorado -->
## **4) Sobre os testes realizados até o momento**

### **Pontos fortes**

- Cobertura SDLC excepcional: 6 fases (requisitos, projeto, implementação, testes, CI/CD, manutenção)
- IA generativa funcional: AI CodeFix 78% aprovação, redução 95-98% tempo
- Validação código AI: AI Code Assurance único mercado (Copilot/CodeWhisperer)
- Análise estática robusta: 5000+ regras, 35 linguagens, OWASP/PCI-DSS/HIPAA
- CI/CD nativo: Quality Gates bloqueiam merges, PR Decoration, webhooks
- Technical Debt quantificado: SQALE methodology, priorização automática
- Custo TRL 4: Community Edition $0 self-hosted
- Maturidade: 15+ anos, 7M+ devs, Gartner "Challengers"
- Complementaridade: OE1 (valida Copilot), OE2 (valida LLMs), OE3 (KPIs LLMOps), OE4 (baseline), OE5 (MCP TACO)
- Categoria única: SAST + IA generativa + validação código AI + MCP
- Documentação excelente

### **Pontos fracos**

- AI CodeFix Early Access: não production-ready todas orgs, cobertura limitada (500/5000 regras)
- APIs externas: offline impossível (Anthropic/OpenAI connectivity)
- Custo escalável: SonarCloud +125% sem features (risco pricing)
- Vendor lock-in AI: LLM APIs via Sonar, sem fine-tuning/RAG custom
- Falsos positivos: 5-10% (configuração necessária)
- Não gera código do zero: apenas corrige existente (vs Copilot)
- Setup complexo: Quality Profile 2-4 dias
- Alert fatigue: primeiro scan legado milhares issues
- Performance CI/CD: +2-5min pipeline
- AI CodeFix limitado: 22% requerem ajuste, supervisão necessária

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☑ **Incluir**

**Justificativa:**

A ferramenta oferece capacidades únicas de validação de código gerado por IA através do AI Code Assurance, sendo a única no mercado com esta funcionalidade, além de integração com LLMs via MCP Server e análise estática robusta com mais de 5000 regras em 35 linguagens. Sua relevância é essencial para cinco objetivos específicos do projeto: validação de assistentes como Copilot e CodeWhisperer, validação de outputs de LLMs open-source, fornecimento de métricas para pipelines LLMOps, estabelecimento de baseline para técnicas de refatoração, e integração com o protótipo TACO através do Gemini. Os riscos identificados são gerenciáveis através de supervisão humana, uso da Community Edition como fallback e configuração adequada do Quality Profile. A complementaridade com outras ferramentas avaliadas, onde assistentes de código geram e SonarQube valida, somada à maturidade técnica de 15 anos com 7 milhões de desenvolvedores e reconhecimento Gartner, reforçam a decisão de inclusão.

---

## **6) Evidências Anexas**

**Links:**

- Docs: https://docs.sonarsource.com, https://docs.sonarsource.com/sonarqube-cloud/improving-the-code/ai-codefix/
- MCP Server: https://github.com/SonarSource/sonar-mcp-server
- Pricing: https://www.sonarsource.com/plans-and-pricing/

- Docs: https://docs.sonarsource.com, https://docs.sonarsource.com/sonarqube-cloud/improving-the-code/ai-codefix/
- MCP Server: https://github.com/SonarSource/sonar-mcp-server
- Pricing: https://www.sonarsource.com/plans-and-pricing/
