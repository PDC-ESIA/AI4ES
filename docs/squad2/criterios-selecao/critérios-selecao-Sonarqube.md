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

SonarQube é uma plataforma **híbrida** que combina análise estática de código (baseada em algoritmos determinísticos) com recursos opcionais de IA generativa (AI CodeFix, AI Code Assurance), destinada a equipes de desenvolvimento que buscam garantir qualidade, segurança e manutenibilidade do código-fonte. A ferramenta atua principalmente nas fases de implementação, testes e manutenção do SDLC, fornecendo análise automática em 35+ linguagens, detecção de vulnerabilidades (OWASP Top 10, CWE), cálculo de débito técnico e correções automáticas via LLMs (Claude Sonnet 4 ou GPT-4o). O motor de análise estática (5000+ regras) opera independentemente de LLMs, enquanto as funcionalidades de IA são complementares e disponíveis apenas em planos específicos. No contexto de avaliação, foi testada para validar código gerado por assistentes de IA (OE1), validar outputs de LLMs open-source (OE2), integrar-se a pipelines LLMOps (OE3), e fornecer feedback técnico para o protótipo TACO (OE5).

---

## **3) Avaliação por Critérios de Inclusão**

---

### **C1 — Cobertura do SDLC**

**Fase(s) do SDLC apoiadas (marque todas):**

- ☐ Requisitos
- ☐ Projeto/Arquitetura
- ☑ Implementação (Análise estática + AI CodeFix refatoração, detecção bugs/vulnerabilidades - CORE)
- ☑ Testes (Análise cobertura, identifica coverage gaps)
- ☑ Integração/CI-CD (Quality Gates bloqueiam merges, integração GitHub/Jenkins)
- ☑ Manutenção/Evolução (Análise estática + Correções automatizadas, Technical Debt - CORE)

**Em qual(is) fase(s) a ferramenta atua de forma explícita?**

- **Implementação (CORE):**
  - Análise estática: detecção bugs (5000+ regras algorítmicas, 35 linguagens), code smells, vulnerabilidades (SQL injection, XSS)
  - AI CodeFix (opcional): refatoração código assistida por LLM
- **CI/CD (CORE):** Integração pipelines, Quality Gates bloqueiam builds, PR decoration
- **Manutenção (CORE):**
  - Análise estática: Technical Debt quantificado (SQALE)
  - AI (opcional): Remediation Agent aplica fixes em PRs, correções automáticas

**A atuação cobre atividades centrais da fase?**

- **Implementação:** Sim - detecção bugs, refatoração, complexidade, duplicação, padrões SOLID/DRY (algoritmos + IA opcional)
- **CI/CD:** Sim - PR comments, deployment tracking, bloqueia merges, webhooks Jira/Slack
- **Manutenção:** Sim - gestão débito técnico, priorização severidade (algoritmos), one-click fix (IA opcional)
- **Segurança:** Sim - SAST robusto algorítmico (OWASP Top 10, PCI-DSS, CWE), compliance reports

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C2 — Apoio ativo por IA**

**Tipo de apoio por IA (marque):**

- ☑ Geração automática (AI CodeFix gera código corrigido - opcional)
- ☑ Sugestão/recomendação (AI CodeFix refatorações, APM Recommendations - opcional)
- ☑ Análise inteligente (AI Code Assurance detecta código AI, analisa qualidade - opcional)
- ☑ Automação baseada em IA (Remediation Agent aplica correções em PRs - opcional)

**A IA é central para a funcionalidade da ferramenta?**

Parcialmente, SonarQube é uma **ferramenta híbrida** com dois componentes distintos:

1. **Motor de análise estática (CORE, desde 2007):**
   - Baseado em 5000+ regras algorítmicas determinísticas
   - Funciona completamente sem LLMs
   - Production-ready, estável
   - Disponível em todas as edições (incluindo Community gratuita)

2. **Funcionalidades de IA (OPCIONAIS, desde 2024):**
   - AI CodeFix: Claude Sonnet 4/GPT-4o para correções
   - AI Code Assurance: validação código gerado por IA
   - MCP Server: integração com assistentes LLM
   - Disponível apenas em planos Team/Enterprise
   - Early Access, cobertura limitada

**Capacidades "inteligentes" observadas:**

1. **AI CodeFix (Claude Sonnet 4):** Correções contextuais bugs/vulnerabilities, 78% taxa aprovação, 95-98% redução tempo (5-15s vs 15-60min). Exemplo: NPE → Optional.ofNullable()
2. **AI Code Assurance:** Detecta código GitHub Copilot via telemetria, Quality Gates especializados, badges certificação
3. **RAG Implícito:** AI CodeFix usa código+regra+contexto+best practices (não configurável pelo usuário)
4. **MCP Server (Preview):** LLMs (Gemini/Claude) consultam análises SonarQube via Model Context Protocol

**Atende ao critério?** ☑ **Sim com ressalvas** (IA é opcional, análise estática é algorítmica)

---

### **C3 — Redução de esforço manual**

**Tarefas repetitivas reduzidas:**

1. **Code review:** 30-60min/PR → 2-5min análise automática (análise estática algorítmica)
2. **Correção bugs:** 15-30min → 5-15s AI CodeFix one-click (requer funcionalidade de IA)
3. **Gestão débito técnico:** Planilhas manuais → cálculo automático SQALE (algorítmico)
4. **Compliance reports:** 1-2 dias auditoria manual → 5min relatórios automáticos (algorítmico)
5. **Setup análise estática:** 4-8h configurar linters → 1-2h Docker Compose

**Ganho produtividade:**

- **Análise estática (algorítmica):** Code review -80%, compliance -95%, tracking -100%
- **AI CodeFix (opcional):** Correção bugs -95-98% quando disponível

**Retrabalho necessário:** Marginal (10-20%).
- Análise estática algorítmica: 5-10% falsos positivos
- AI CodeFix: 78% aprovadas, 22% requerem ajuste, 1.95 issues/tarefa introduzidas
- Supervisão humana essencial em ambos os casos

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C4 — Impacto na Qualidade**

**Tipo de impacto (marque):**

- ☐ Qualidade requisitos
- ☑ Qualidade design (Anti-patterns: God Classes, complexidade - algorítmico)
- ☑ Qualidade código (5000+ regras SOLID/DRY algorítmicas + AI CodeFix legibilidade opcional)
- ☑ Qualidade testes (Análise cobertura algorítmica, detecta código não testável)
- ☑ Qualidade documentação (Relatórios conformidade, badges, APIs REST)
- ☑ Detecção erros (NPE, race conditions, SQL injection, XSS - algorítmico)

**Erros evitados:**

- **Bugs:** NPE, resource leaks, race conditions, logic errors (detectados pré-produção)
- **Vulnerabilidades:** SQL Injection, XSS, deserialization, insecure crypto (conformidade OWASP Top 10, evita CVEs)
- **Inconsistências padrão:** SOLID violations, duplicação código, acoplamento excessivo
- **Código AI (AI Code Assurance):** Código Copilot tem 2x mais security issues (8.2 vs 5.1/1k LOC) - valida qualidade (OE1)

**Melhoria qualidade:**

- **Métricas pós-adoção:** Maintainability D/E→A/B (6 meses), Reliability C→A, Security D→A, Debt 10%→0.5%, Coverage 40%→80%
- **Case studies:** 60% redução débito (6 meses), 3 CVEs evitados, código AI CodeFix 40% menos incidents
- **TACO (OE5):** Alunos recebem feedback técnico preciso, code smells desde início, bugs pré-submissão

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C5 — Maturidade e Adoção**

**Observado:**

- ☑ Documentação completa (docs.sonarsource.com - clara, searchable)
- ☑ Tutoriais disponíveis (Docker, GitHub Actions, Quality Gates best practices)
- ☑ 35+ integrações (GitHub, GitLab, Azure DevOps, Jenkins, VS Code, Jira, Slack)
- ☑ Comunidade ativa (7M+ devs, G2 4.4/5 stars 500+ reviews, Stack Overflow ativo)
- ☑ Reconhecimento (Gartner "Challengers" SAST, case studies Airbnb/Peloton)

**Maturidade técnica:**

- Análise estática: Production-ready (15+ anos desde 2007)
- AI CodeFix: Early Access (2024, funcional)
- AI Code Assurance: Production-ready com limitações (só GitHub Copilot)

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C6 — Representatividade Funcional**

**Categoria:** Análise estática de código (algorítmica) com recursos opcionais de IA generativa (SAST híbrido)

**Adiciona diversidade?** Sim - complementaridade crítica:

- **vs Copilot/CodeWhisperer:** Copilot gera → SonarQube valida/corrige (AI Code Assurance único mercado)
- **vs LLMs open-source (OE2):** CodeLlama/DeepSeek geram → SonarQube valida (métricas complexity/debt)
- **OE3 LLMOps:** Métricas como KPIs desempenho LLM, Quality Gates bloqueiam código ruim
- **OE4/OE5:** AI CodeFix baseline refatoração, MCP Server integra TACO+Gemini

**Há outras ferramentas muito similares já avaliadas?** Não, mas para registrar exemplos para possíveis estudos futuros: Semgrep, CodeQL, Snyk, Checkmarx.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C7 — Riscos e Limitações**

**Riscos:**

- ☑ Erros críticos (AI CodeFix: 22% requerem ajuste, 1.95 issues/tarefa quando usado)
- ☑ Resultados enganosos (Falsos positivos 5-10% na análise algorítmica, projeto legado alert fatigue)
- ☑ Dependência IA (Devs podem aplicar AI CodeFix sem revisar, confiança cega em correções automáticas)
- ☑ Outros: **Vendor lock-in para IA, Custo escalável, APIs externas (IA), Não offline (IA)**

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

- Análise estática robusta: 5000+ regras, 35 linguagens, OWASP/PCI-DSS/HIPAA
- CI/CD nativo: Quality Gates bloqueiam merges, PR Decoration, webhooks
- Capacidade de quantificar débito técnico de forma objetiva, facilitando priorização em sprints
- Documentação clara permitiu configuração inicial sem necessidade de treinamento especializado
- Eficaz na detecção precoce de vulnerabilidades de segurança antes da integração em produção

### **Pontos fracos**

- Geração excessiva de alertas em projetos legados, exigindo configuração inicial trabalhosa
- AI CodeFix Early Access: não production-ready todas orgs, cobertura limitada (500/5000 regras)
- APIs externas: offline impossível (Anthropic/OpenAI connectivity)
- Custo escalável: SonarCloud +125% sem features (risco pricing)
- Não gera código do zero: apenas corrige existente (vs Copilot)
- Performance CI/CD: +2-5min pipeline

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☐ Incluir ☑ **Incluir com ressalvas** ☐ Não incluir

**Justificativa:**

O SonarQube é uma ferramenta híbrida que combina análise estática tradicional (baseada em algoritmos, não em LLMs) com funcionalidades emergentes de IA. A análise estática robusta é executada por algoritmos determinísticos, enquanto as funcionalidades de LLM são complementares e opcionais.

---

## **6) Evidências Anexas**

**Links:**

- Docs: https://docs.sonarsource.com, https://docs.sonarsource.com/sonarqube-cloud/improving-the-code/ai-codefix/
- MCP Server: https://github.com/SonarSource/sonar-mcp-server
- Pricing: https://www.sonarsource.com/plans-and-pricing/

- Docs: https://docs.sonarsource.com, https://docs.sonarsource.com/sonarqube-cloud/improving-the-code/ai-codefix/
- MCP Server: https://github.com/SonarSource/sonar-mcp-server
- Pricing: https://www.sonarsource.com/plans-and-pricing/
