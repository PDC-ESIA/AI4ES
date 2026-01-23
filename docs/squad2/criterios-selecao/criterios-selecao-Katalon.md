# Critérios de seleção de ferramentas AI4SE 

**Análise de critérios mínimos para que uma ferramenta seja incluída no estudo.**

---

## **1) Identificação da Ferramenta**

| Item | Preenchimento |
|---|---|
| **Nome da ferramenta:** | Katalon Platform (Katalon Studio + TestOps + TrueTest) |
| **Versão (se aplicável):** | Versão 2025 (StudioAssist + TrueTest Agent-Aware Testing - janeiro 2026) |
| **URL oficial para acesso à ferramenta/documentação:** | https://katalon.com / https://docs.katalon.com |
| **Data da avaliação:** | Janeiro 2026 |
| **Avaliador:** | Victor Rangel - Equipe de Pesquisa AI4SE - CEIA-UFG |

---

## **2) Visão Geral da Ferramenta (1 parágrafo)**
Descreva brevemente:
- O propósito principal da ferramenta  
- Para que tipo de usuário/atividade ela é destinada  
- Em que contexto foi testada na avaliação prática  

>Katalon Platform é uma **plataforma de automação de testes augmented-by-AI** abrangente, composta por três produtos principais: **Katalon Studio** (IDE local para criação/execução de testes), **Katalon TestOps** (gerenciamento cloud de testes e analytics) e **Katalon TrueTest** (geração automática de testes E2E de comportamento real capturado em produção). A plataforma destina-se a engenheiros de QA, desenvolvedores e equipes DevOps que necessitam automatizar testes para aplicações web, mobile (iOS/Android), API e desktop. Utiliza **StudioAssist** (GPT-4.1-mini via Katalon AI Service ou modelos externos via BYOK) para geração de código de teste via natural language e **TrueTest** para captura de tráfego real (human e **agentic**) e geração de testes E2E. Recursos chave incluem **self-healing** (correção automática de locators quebrados), **AI Failure Analysis** (explicação de root causes), **Agent-Aware Testing** (suporta tráfego de agentes IA, não apenas humanos - first in market) e integração nativa com CI/CD. O contexto de teste envolveu tarefas de **geração de testes E2E via TrueTest**, **self-healing de testes UI**, **geração de API tests de OpenAPI specs**, **StudioAssist code generation** e **AI Failure Analysis** em aplicações web Java/Groovy e REST APIs.

---

## **3) Avaliação por Critérios de Inclusão**

Para cada critério, marque **Sim / Parcial / Não**, responda às perguntas-chave fornecendo as evidências necessárias.

---

### **C1 — Cobertura do SDLC**

**Fase(s) do SDLC apoiadas (marque todas):**  
- ☑ Requisitos  
- ☐ Projeto/Arquitetura  
- ☐ Implementação (foco em test code, não production code)
- ☑ Testes  
- ☑ Integração/CI-CD  
- ☑ Manutenção/Evolução  
- ☑ Outra: **Operações (Monitoramento via TrueTest Agent)**

**Perguntas orientadoras:**

**Em qual(is) fase(s) a ferramenta atua de forma explícita?**  
>- **Testes** (core strength): Geração de testes E2E (TrueTest), unit/API tests (StudioAssist), execução local e cloud (TestCloud), self-healing, AI Failure Analysis.
>- **Integração/CI-CD**: Integração nativa com Jenkins, Azure DevOps, GitLab CI, GitHub Actions, CircleCI. TestOps gerencia execução paralela e scheduling.
>- **Manutenção**: Self-healing detecta e corrige locators quebrados automaticamente. SmartWait evita flakiness esperando elementos carregarem.
>- **Operações**: TrueTest Agent monitora produção em tempo real para capturar tráfego real (human e agentic) e identificar gaps de cobertura.
>- **Requisitos (parcial)**: TrueTest captura comportamento real de usuários como proxy de requisitos não documentados. Integração com Jira permite sincronização de requirements. Manual Test Case Generator cria test cases de tickets Jira via GPT.

**A atuação cobre atividades centrais da fase? Quais?**  
>Sim, para fases em que atua:
>- **Testes**: Criação, execução, manutenção, análise de falhas (atividades centrais completas).
>- **CI/CD**: Integração, execução automatizada, dashboards de status.
>- **Manutenção**: Correção automática de testes quebrados (self-healing).
>- **Monitoramento**: Captura de tráfego real para validação contínua (TrueTest Agent).

**Observação importante**: Katalon é **ferramenta de teste**, não de desenvolvimento de software de produção. Não atua em implementação de código de produção, arquitetura de sistemas ou design de aplicações. Seu escopo é **exclusivamente teste e qualidade**.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C2 — Apoio ativo por IA**

**Tipo de apoio por IA (marque):**  
- ☑ Geração automática  
- ☑ Sugestão/recomendação  
- ☑ Análise inteligente  
- ☑ Automação baseada em IA  
- ☑ Outro: **Self-healing, AI Failure Analysis, Agent-Aware Testing, visual regression testing por IA**

**Perguntas orientadoras:**

**A IA é central para a funcionalidade da ferramenta?**  
>**Sim**, mas de forma **complementar**. Katalon Studio roda sem IA (record & playback tradicional), mas recursos de IA são **diferenciais competitivos** chave:
>- **StudioAssist** (GPT-4.1-mini): Central para geração de código de teste via natural language.
>- **TrueTest**: IA é central para análise comportamental de tráfego real e geração de User Journey Maps + test cases.
>- **Self-healing**: ML/IA para detectar locators quebrados e aplicar fixes automaticamente.
>- **AI Failure Analysis**: Central para explicar root causes de falhas automaticamente.
>- **Visual Testing**: IA para detecção de regressões visuais via TestOps.

**Que capacidades "inteligentes" foram observadas na prática?**  
>- **TrueTest Behavior Analysis**: Captura tráfego real (human e **agentic**), identifica padrões e agrupa interações em jornadas lógicas (ex.: "Purchase Flow", "Search Flow").
>- **Agent-Aware Testing**: **First in market** (jan 2026) - suporta tráfego de agentes IA, não apenas humanos (captura interações de bots, LLMs, RPAs).
>- **Self-healing**: Detecta automaticamente quando locators (XPath, CSS selectors) quebram após mudanças de UI e aplica correções (tenta alternativas como ID, name, text).
>- **SmartWait**: Aguarda elementos carregarem dinamicamente (evita flakiness de timing).
>- **AI Failure Analysis**: Analisa stack traces, screenshots e logs para explicar root causes em linguagem simples.
>- **StudioAssist Agent Mode com MCP**: Permite automação multi-step com contexto do projeto (janeiro 2026).
>- **Gap Analysis**: Compara fluxos em QA vs produção, identifica áreas não cobertas por testes (risco de defeitos).
>- **Visual Regression AI**: Detecta mudanças visuais inesperadas via comparação de screenshots com IA.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C3 — Redução de esforço manual**

**Perguntas orientadoras:**

**Quais tarefas repetitivas foram reduzidas ou eliminadas?**  
>- **Criação de test cases**: Até **60% mais rápido** com StudioAssist e TrueTest (claim oficial Katalon).
>- **Manutenção de testes**: **Self-healing reduz tempo de manutenção em 40-60%** (literatura de AI testing 2025). Elimina ciclos manuais de "teste quebrou → identificar locator → corrigir → re-executar".
>- **Debug de falhas**: **AI Failure Analysis reduz tempo de diagnóstico em ~50%** (claim oficial). Desenvolvedor não precisa analisar stack traces manualmente.
>- **Geração de testes de comportamento real**: TrueTest elimina necessidade de "imaginar" casos de uso - gera automaticamente de tráfego capturado em produção.
>- **Testes de regressão visual**: Visual Testing AI automatiza comparação de screenshots (anteriormente manual).

**O ganho de produtividade foi significativo ou marginal?**  
>**Significativo**. Claims oficiais e literatura independente indicam:
>- **60% faster test creation** (oficial).
>- **40-60% reduction em test maintenance** devido a self-healing (literatura).
>- Payback típico: **3-6 meses** para equipes médias/grandes com testes E2E complexos.

**Foi necessário muito retrabalho/revisão manual?**  
>**Parcial**. 
>- **Testes gerados são "production-ready"** mas requerem revisão humana (StudioAssist pode alucinar keywords inexistentes - limitação documentada).
>- **Self-healing** reduz drasticamente retrabalho (correções automáticas), mas pode gerar falsos positivos se aplicar fix incorreto.
>- **TrueTest**: Journey Maps precisam de revisão para validar agrupamento lógico de interações.
>- **Gap Analysis** requer interpretação humana para priorizar áreas descobertas.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C4 — Impacto na Qualidade**

**Tipo de impacto observado (marque):**  
- ☑ Qualidade dos requisitos (TrueTest captura requisitos implícitos)
- ☐ Qualidade do design (não aplicável - ferramenta de teste)
- ☐ Qualidade do código de produção (não aplicável)
- ☑ Qualidade dos testes (core strength)
- ☑ Qualidade da documentação (test cases documentados, AI explica test code)
- ☑ Consistência/detecção de erros (self-healing, visual testing, AI Failure Analysis)
- ☑ Outro: **Cobertura de testes (TrueTest Gap Analysis)**

**Perguntas orientadoras:**

**A ferramenta ajudou a evitar erros ou inconsistências na tarefa realizada?**  
>Sim, de múltiplas formas:
>- **Self-healing**: Evita falsos positivos (testes quebrados por mudanças de UI, não por bugs reais). Mantém suite de testes **estável**.
>- **SmartWait**: Evita flakiness de timing (erros intermitentes que não refletem bugs reais).
>- **TrueTest**: Elimina "assumptions" humanas incorretas - testes refletem comportamento **real** de usuários, não casos imaginados.
>- **Gap Analysis**: Identifica áreas não testadas (evita erros em produção por falta de cobertura).
>- **AI Failure Analysis**: Ajuda a distinguir entre bugs reais e falhas de ambiente/configuração (acelera triagem).

**Houve melhoria perceptível na qualidade do artefato gerado?**  
>Sim. Evidências:
>- **Testes**: Test cases gerados são claros, legíveis e seguem padrões (Page Object Model). StudioAssist gera código Groovy/Java válido (mas requer revisão para alucinações).
>- **Cobertura**: TrueTest garante cobertura de fluxos **reais**, não apenas casos imaginados (aumenta cobertura efetiva vs QA tradicional).
>- **Estabilidade**: Self-healing reduz significativamente falsos positivos em suites de testes (suites mais estáveis = maior confiança).
>- **Documentação**: Test cases são auto-documentados; AI Failure Analysis explica falhas em linguagem simples.
>- **Consistência**: Visual Testing AI detecta regressões visuais inesperadas (garante consistência de UI).

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C5 — Maturidade e Adoção**

**Marque o que foi observado:**
- ☑ Documentação clara e acessível  
- ☑ Tutoriais/exemplos disponíveis  
- ☑ Integração com ferramentas comuns (GitHub, GitLab, VS Code, Jira, etc.)  
- ☑ Comunidade ativa / relatos de uso  
- ☑ Estudos acadêmicos ou relatos industriais  

**Evidências:**
>- **Documentação oficial**: Docs completos em https://docs.katalon.com com guias, API reference, tutoriais e best practices.
>- **Tutoriais**: Katalon Academy (cursos gratuitos), YouTube oficial (centenas de vídeos), webinars mensais.

**Integrações**: 
  >- CI/CD: Jenkins, Azure DevOps, GitLab CI, GitHub Actions, CircleCI, TeamCity.
  >- Issue tracking: Jira, Azure Boards.
  >- Cloud: AWS Device Farm, BrowserStack, Sauce Labs, LambdaTest.
  >- ALM: qTest, TestRail, Zephyr.
>- **Comunidade**: Katalon Community Forum (ativo desde 2016), 65k+ usuários, Slack community, presença forte em Stack Overflow.

**Adoção**: 
  >- **Gartner Peer Insights**: 4.4/5 (70+ reviews).
  >- **G2 Crowd**: 4.4/5 (300+ reviews, Leader em Software Test Automation Winter 2025).
  >- **Capterra**: 4.4/5 (40+ reviews).

>- **Estudos acadêmicos**: Múltiplos papers em conferências IEEE/ACM sobre test automation, self-healing, AI-driven testing (2022-2025).
>- **Cases industriais**: Publicados em site oficial (Fortune 500 companies: Deloitte, Fujitsu, Orange, etc.).

**Maturidade do produto:**
>- **Katalon Studio**: Lançado em 2016, **9 anos no mercado** (produto maduro).
>- **TestOps**: Lançado em 2019, **7 anos no mercado**.
>- **TrueTest**: Lançado em 2023, **3 anos no mercado** (mais recente, mas estável).
>- **StudioAssist**: Beta lançado em 2024, GA em 2025 (1 ano no mercado).
>- **Agent-Aware Testing**: Lançado em janeiro 2026 (muito recente).

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

### **C6 — Representatividade Funcional**

**Perguntas orientadoras:**

**Que "categoria" de AI4SE esta ferramenta representa?**  
>**Categoria: Plataforma de Automação de Testes Augmented-by-AI**

>Katalon representa categoria de **ferramentas AI4SE focadas em teste e qualidade** que combinam:
>- Automação tradicional de testes (record & playback, scripting).
>- **AI-augmented testing**: StudioAssist para code generation, self-healing, AI >Failure Analysis.
>- **Behavior-driven testing**: TrueTest captura tráfego real e gera testes automaticamente.
>- **Agent-Aware Testing**: Suporta testes de aplicações que interagem com agentes IA (primeiro no mercado).
>- **Cloud test orchestration**: TestOps para gerenciamento centralizado.

**Ela adiciona diversidade ao conjunto de ferramentas avaliadas?**  
>**Sim**. Diversidade significativa:
>- **Escopo diferente**: Katalon foca em **teste**, não em desenvolvimento de código de produção (vs Zencoder, Google Antigravity que focam em codificação).
>- **Agent-Aware Testing**: Única ferramenta avaliada que suporta **tráfego de agentes IA** (tendência emergente crítica para era de agentic applications).
>- **Behavior-driven approach**: TrueTest captura tráfego **real** de produção (vs testes gerados de specs/requisitos).
>- **Self-healing especializado**: Focado exclusivamente em testes UI (vs self-healing genérico de código).
>- **Visual Testing AI**: Regressão visual automatizada (não coberto por outras ferramentas avaliadas).

**Há outras ferramentas muito similares já avaliadas?**  
>Não no contexto deste estudo. Ferramentas similares no mercado (Selenium + plugins, Cypress, Playwright) mas Katalon é única em:
>- **All-in-one platform**: Studio + TestOps + TrueTest integrados nativamente.
>- **Agent-Aware Testing**: First in market (janeiro 2026).
>- **TrueTest**: Geração de testes de tráfego real (vs geração de specs).
>- **Self-healing nativo**: Sem necessidade de plugins externos.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não  

---

### **C7 — Riscos e Limitações**

**Riscos observados (se houver):**
- ☑ Pode introduzir erros críticos  
- ☑ Pode gerar resultados enganosos  
- ☑ Dependência excessiva de IA  
- ☑ Outros: **Dependência de cloud, custos recorrentes, vendor lock-in, curva de aprendizado**

**Detalhamento dos riscos:**

>1. **Erros críticos**: 
   **Self-healing pode mascarar bugs reais**: Corrige locator quebrado mas não detecta mudança de comportamento da aplicação.
   **StudioAssist pode alucinar**: Gera keywords inexistentes (documentado oficialmente como limitação conhecida).

>2. **Resultados enganosos**: 
   **Falsos negativos**: Self-healing pode aplicar fix incorreto (teste passa mas não valida comportamento correto).
   **TrueTest Journey Maps**: Agrupamento automático pode ser incorreto (requer validação humana).

>3. **Dependência excessiva**: 
   **Skill degradation**: QA engineers podem perder proficiência em debugging manual e análise de root cause.
   **Confiança cega**: Equipes podem confiar excessivamente em AI Failure Analysis sem investigação profunda.

>4. **Dependência de cloud**: 
   **TestOps é cloud-only**: Não há opção self-hosted para TestOps (apenas Studio roda local).
   **TrueTest requer cloud**: Não funciona sem conectividade.

>5. **Custos recorrentes**: 
   **Free tier muito limitado**: Studio free sem StudioAssist/TrueTest/TestOps.
   **Premium**: \$208/mês por usuário (Ultimate Plan com todos recursos AI).
   **TestCloud**: \$69-\$399/mês por sessão paralela (execução cloud).
   **TrueTest**: \$125/mês (Standard) ou \$250/mês (Advanced).

>6. **Vendor lock-in**: 
   **Formato proprietário**: Test cases em formato Katalon (.tc, .ts) não são 100% portáveis.
   **Migração complexa**: Sair de Katalon requer rewrite significativo de testes.

>7. **Curva de aprendizado**: 
   **Groovy/Java**: Requer conhecimento de linguagem específica (vs Selenium com múltiplas linguagens).
   **Plataforma complexa**: 3 produtos integrados (Studio, TestOps, TrueTest) requerem tempo para domínio.

>8. **Compliance/Privacidade**: 
   **TrueTest Agent em produção**: Captura tráfego real pode incluir dados sensíveis (PII, PHI).
   **Cloud processing**: Dados enviados para cloud Katalon (pode violar GDPR, HIPAA, regulamentações governamentais).

>9. **Limitações técnicas**: 
   **Não suporta desktop apps complexos**: Foco em web/mobile/API (desktop é limitado).
   **Self-healing apenas UI**: Não corrige lógica de teste ou assertions.
   **StudioAssist limitado a contexto de projeto**: Não tem Repo Grokking™ como Zencoder.

>10. **Produto em evolução (Agent-Aware Testing)**:
    Lançado em janeiro 2026 (muito recente).
    - Pode ter bugs, limitações ou mudanças breaking.

**Atende ao critério?** ☑ Sim ☐ Parcial ☐ Não

---

## **4) Sobre os testes realizados até o momento**

### **Pontos fortes (bullet points)**
- **Agent-Aware Testing**: **First in market** - suporta tráfego de agentes IA, crítico para era de agentic applications (tendência emergente).
- **TrueTest**: Geração de testes de comportamento **real** capturado em produção (elimina "assumptions" incorretas de QA tradicional).
- **Self-healing robusto**: Reduz manutenção de testes em 40-60%; mantém suites estáveis após mudanças de UI.
- **AI Failure Analysis**: Explica root causes em linguagem simples, acelerando diagnóstico em ~50%.
- **Gap Analysis**: Identifica áreas não cobertas por testes (risk-based testing).
- **All-in-one platform**: Studio + TestOps + TrueTest integrados nativamente (reduz fragmentação de ferramentas).
- **Multi-plataforma**: Web, mobile (iOS/Android), API, desktop em uma única ferramenta.
- **Integrações robustas**: CI/CD (Jenkins, Azure DevOps, GitHub Actions), cloud testing (AWS, BrowserStack), ALM (Jira, TestRail).
- **Maturidade comprovada**: 9 anos no mercado (Studio), comunidade ativa 65k+ usuários, casos Fortune 500.
- **Estudos acadêmicos**: Múltiplos papers IEEE/ACM validam abordagens de self-healing e AI testing (2022-2025).
- **Visual Testing AI**: Detecção automatizada de regressões visuais (não depende de assertions manuais).
- **SmartWait**: Elimina flakiness de timing (testes mais confiáveis).

### **Pontos fracos (bullet points)**
- **Interface não intuitiva**: Plataforma com 3 produtos integrados (Studio, TestOps, TrueTest) apresenta curva de aprendizado acentuada; navegação entre módulos não é sempre óbvia para novos usuários; documentação fragmentada entre produtos.
- **Escopo limitado a testes**: Não atua em desenvolvimento de código de produção (vs ferramentas agentic como Zencoder/Antigravity).
- **Custos elevados**: \$208/mês por usuário (Ultimate) + \$69-\$399/mês TestCloud + \$125-\$250/mês TrueTest (pode ser barreira para startups/pequenas equipes).
- **Vendor lock-in**: Formato proprietário dificulta migração para outras ferramentas.
- **Dependência de cloud**: TestOps e TrueTest são cloud-only (sem opção self-hosted).
- **Compliance/Privacidade**: TrueTest Agent captura tráfego real de produção (pode incluir dados sensíveis); cloud processing pode violar regulamentações estritas.
- **Curva de aprendizado**: Groovy/Java requerido; plataforma complexa (3 produtos) requer tempo para domínio.
- **StudioAssist limitado**: Pode alucinar keywords inexistentes (limitação documentada oficialmente); não tem Repo Grokking™.
- **Self-healing pode mascarar bugs**: Corrige locators mas não detecta mudanças de comportamento da aplicação.
- **Agent-Aware Testing muito recente**: Lançado janeiro 2026 (pode ter bugs/limitações).
- **Desktop testing limitado**: Foco principal em web/mobile/API; desktop é funcionalidade secundária.
- **Free tier muito limitado**: Studio free sem StudioAssist/TrueTest/TestOps (força upgrade para uso produtivo).

---

## **5) Decisão Final de Inclusão**

**Decisão:** ☐ Incluir ☑ Incluir com ressalvas ☐ Não incluir  

**Justificativa resumida em caso de não incluir (3–5 linhas):**  

**Katalon Platform atende todos os 7 critérios de inclusão.** Incluída com ressalvas por: 
- (1) escopo exclusivo em testes, não codificação de produção; 
- (2) custos elevados (\$208-\$650+/mês); 
- (3) vendor lock-in proprietário; 
- (4) dependência de cloud para TestOps/TrueTest; 
- (5) riscos de compliance ao capturar dados reais de produção. 

**Recomendação: Incluir** — diferencial único de Agent-Aware Testing (first in market, jan 2026) é crítico para pesquisa de agentes inteligentes, alinhado com objetivos de pesquisa do TACO.

---

## **6) Evidências Anexas (opcional)**

**Links consultados:**
- Katalon Official: https://katalon.com
- Katalon Docs: https://docs.katalon.com
- Katalon Academy: https://academy.katalon.com
- Katalon TrueTest: https://katalon.com/truetest
- Katalon StudioAssist: https://docs.katalon.com/docs/studioassist/studioassist-overview
- Katalon Agent-Aware Testing: https://katalon.com/resources/center/blog/agent-aware-testing
- Gartner Peer Insights: https://www.gartner.com/reviews/market/software-test-automation/vendor/katalon
- G2 Crowd: https://www.g2.com/products/katalon-platform/reviews
- Pricing: https://katalon.com/pricing

**Papers acadêmicos consultados:**
- IEEE/ACM papers sobre self-healing em test automation (2022-2025)
- Papers sobre AI-driven testing e behavior-driven testing (2023-2025)

**Arquivos gerados:**
- Relatório técnico completo: [Levantamento Katalon](docs/squad2/levantamento-ferramentas-IA4ES/avaliacao-google-antigravity.md)

---

**Observações Finais:**

Katalon Platform representa uma **categoria única** entre as ferramentas avaliadas: **automação de testes augmented-by-AI** com foco exclusivo em qualidade e teste (não em desenvolvimento de código de produção). Atende todos os critérios de inclusão de forma robusta: **cobertura do SDLC** (testes, CI/CD, manutenção, operações), **apoio ativo por IA** (StudioAssist, TrueTest, self-healing, AI Failure Analysis), **redução significativa de esforço manual** (60% faster test creation, 40-60% menos manutenção), **impacto positivo na qualidade** (cobertura de fluxos reais, estabilidade de testes, gap analysis) e **excelente maturidade** (9 anos no mercado, comunidade 65k+, casos Fortune 500, papers acadêmicos).

**Diferencial único**: **Agent-Aware Testing** (first in market, janeiro 2026) é **extremamente relevante** para o contexto do projeto de pesquisa (desenvolvimento de agentes inteligentes, plataforma TACO). Representa tendência emergente crítica: **testar aplicações que interagem com agentes IA**, não apenas humanos.

Os principais riscos são: **(1) escopo limitado a testes** (não atua em codificação de produção), **(2) custos elevados** (\$208-\$650+/mês por usuário para stack completo), **(3) vendor lock-in** (formato proprietário), **(4) dependência de cloud** (TestOps/TrueTest), e **(5) compliance** (TrueTest captura tráfego real de produção com possíveis dados sensíveis).

**Recomendação técnica**: Ferramenta **altamente relevante** para o estudo, representando categoria de **AI4SE focada em teste e qualidade** (complementar às ferramentas de codificação como Zencoder/Antigravity). **Agent-Aware Testing** oferece oportunidade única de investigar **como testar agentes inteligentes** (diretamente relevante para OE5 - prototipação de agentes inteligentes no TACO). Adequada para experimentação em ambiente controlado (TRL 4), especialmente para pesquisa aplicada em geração de testes (OE4). Custos devem ser avaliados cuidadosamente (considerar planos acadêmicos ou trials estendidos).
