# 📊 Benchmark de Qualidade — Relatórios Gerados por Modelo

> **Escopo:** Avaliação dos relatórios de arquitetura do lote HU-001 a HU-006 (Módulo de Autenticação)
> **Data da análise:** 2026-05-24

---

## 1. Inventário de Entregas

> Resumo dos modelos testados e disponíveis no GitHub Copilot.
> Modelos com encerramento programado marcados com ⚠️. Referência: <https://docs.github.com/en/copilot/reference/ai-models/supported-models>

| # | Modelo | Status no GitHub Copilot | Arquivo de Relatório | Tamanho |
| --- | --- | --- | --- | --- |
| BASE | GPT-4 (base) | — | `relatorio_HU-001_..._HU-006.md` | 20.035 bytes / 239 linhas |
| 1 | GPT-4o | GA | ❌ **Não gerado** | — |
| 2 | GPT-4.1 | ⚠️ Encerrando em 01/06/2026 | `relatorio_HU-001_..._HU-006.md` | 16.230 bytes / 264 linhas |
| 3 | GPT-5 mini | GA | `relatorio_HU-001_..._HU-006.md` | 20.593 bytes / 304 linhas |
| 4 | GPT-5.2 | ⚠️ Encerrando em 01/06/2026 | `relatorio_HU-001_..._HU-006.md` | 30.185 bytes / 472 linhas |
| 5 | Claude Haiku 4.5 | GA | ❌ **Sessão vazia** | — |
| — | Claude Sonnet 4 | ~~Descontinuado em 01/05/2026~~ → **Claude Sonnet 4.6** | — | — |
| 6 | Claude Sonnet 4.5 | GA | `ANÁLISE_LOTE_HU_AUTENTICACAO_v1.md` | 31.829 bytes / 1057 linhas |
| — | Claude Sonnet 4.6 | GA | — | — |
| 7 | Claude Opus 4.5 | GA | `analise_completude_lote_hus_autenticacao.md` + múltiplos | ~60 KB total |
| — | Claude Opus 4.6 | GA | — | — |
| — | Claude Opus 4.7 | GA | — | — |

> **Notas de estrutura:**
>
> - GPT-4o gerou apenas prototype, sem relatório markdown.
> - Claude Haiku 4.5 produziu pasta vazia

---

## 2. Ranking e Scorecard

> Visão consolidada de todos os modelos. Detalhamento por dimensão nas seções seguintes.

### Ranking Final

```text
🥇 GPT-5-mini  & GPT-5.2     —   28/30 (93%) — Empate técnico (GPT-5-mini é mais rápido e conciso; GPT-5.2 é mais denso e completo)
🥈 BASE (GPT-4)              —   26/30 (87%) — O mais equilibrado em velocidade/qualidade (5m48s)
🥉 GPT-4.1                   —   17/30 (57%) — Rápido (8m02s), mas com baixo rigor técnico
   Claude Opus 4.5           —   12/30 (40%) ⚠️ formato divergente — produziu análise BA, não relatório de arquitetura
   Claude Sonnet 4.5         —    9/30 (30%) ⚠️ formato divergente + interrupções manuais constantes no fluxo
   GPT-4o                    —   N/A         ❌ sem relatório (modelo interrompeu a execução espontaneamente)
   Claude Haiku 4.5          —   N/A         ❌ sessão vazia (falha — nenhum arquivo gerado)
```

### Scorecard

> **Critérios de pontuação (1–5 por dimensão):**
>
> - **Aderência ao template:** segue as 7 seções canônicas?
> - **Qualidade dos diagramas:** Mermaid correto, autonumber, participants?
> - **Tabela de componentes:** volume, rastreabilidade, dependências?
> - **Gap Analysis:** lacunas reais, categorizadas e acionáveis?
> - **Fidelidade aos critérios de aceite:** captura requisitos específicos?
> - **Clareza e legibilidade:** estrutura do documento, proporção sinal/ruído?

| Dimensão | BASE | GPT-4.1 | GPT-5-mini | GPT-5.2 | Sonnet 4.5 | Opus 4.5 |
| --- | --- | --- | --- | --- | --- | --- |
| Aderência ao template | 5 | 4 | 5 | 5 | 1 | 2 |
| Qualidade dos diagramas | 4 | 3 | 4 | **5** | 0 | 0 |
| Tabela de componentes | **5** | 3 | 4 | 5 | 0 | 0 |
| Gap Analysis | 4 | 1 | **5** | 4 | 0 | 2 |
| Fidelidade aos CAs | 3 | 2 | **5** | **5** | **5** | **5** |
| Clareza e legibilidade | 5 | 4 | 5 | 4 | 3 | 3 |
| **TOTAL (máx. 30)** | **26** | **17** | **28** | **28** | **9** | **12** |
| **Percentual** | 87% | 57% | 93% | 93% | 30% | 40% |

---

## 3. Aderência ao Template

> Presença das seções canônicas por modelo e fidelidade geral ao formato esperado.

O relatório-base possui 7 seções canônicas:

| Seção | BASE | GPT-4.1 | GPT-5-mini | GPT-5.2 | Sonnet 4.5 | Opus 4.5 |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Identificação das HUs | ✅ | ✅ | ✅ | ✅ | ✅ (integrada) | ✅ (integrada) |
| 2. Diagramas de Arquitetura (Mermaid) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 3. Decisões de Arquitetura | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 4. Componentes | ✅ | ✅ | ✅ | ✅ | ❌ (substituída por stack) | ❌ (substituída por checklist) |
| 5. Bloqueios e Pendências | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 6. Cobertura de HUs | ✅ | ✅ | ✅ | ✅ | ❌ (parcial, via status) | ✅ (via tabela de resumo) |
| 7. Gap Analysis | ✅ | ⚠️ (ausente) | ✅ | ✅ | ❌ (substituída por gaps de produto) | ✅ (via perguntas de clarificação) |
| **Percentual** | 100% | ≈ 85% | ≈ 100% | 100% | ≈ 30% | ≈ 40% |

---

## 4. Aderência aos Critérios de Aceite

> Fidelidade de cada modelo aos requisitos específicos do lote.

| Critério de aceite específico | BASE | GPT-4.1 | GPT-5-mini | GPT-5.2 | Sonnet 4.5 | Opus 4.5 |
| --- | --- | --- | --- | --- | --- | --- |
| Bloqueio 15min após 3 falhas (HU-001) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Erro genérico sem indicar campo (HU-001) | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Token reset com TTL 30min + timestamp (HU-002) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Token marcado como consumido após uso (HU-002) | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Log auditoria com 4 campos obrigatórios (HU-002) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| IP inédito considera **TODO** histórico, não só 10 (HU-003) | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| 3 eventos de WS distintos: login/logout/remoto (HU-003) | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Conta inativa até confirmação de e-mail (HU-004) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Invalidar **todos** tokens após troca de senha (HU-005) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CSV com campos: timestamp/tipo/ip/usuario/flag_suspeito (HU-006) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `flag_suspeito` = 5+ falhas **consecutivas** (HU-006) | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Score** | **8/11** | **6/11** | **11/11** | **11/11** | **11/11** | **11/11** |

---

## 5. Cobertura de HUs

> Verificação de que cada HU do lote foi coberta no relatório gerado.

| Modelo | HU-001 | HU-002 | HU-003 | HU-004 | HU-005 | HU-006 | Total Cobertas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BASE | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **6/6** |
| GPT-4.1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **6/6** |
| GPT-5-mini | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **6/6** |
| GPT-5.2 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **6/6** |
| Sonnet 4.5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **6/6** *(via análise de produto)* |
| Opus 4.5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **6/6** *(via completude/BA)* |

GPT-4o e Claude Haiku 4.5 não produziram relatório utilizável, portanto sem cobertura registrada.

---

## 6. Qualidade dos Diagramas Mermaid

> Avaliação dos diagramas técnicos exigidos pelo template.

| Modelo | Diagramas Gerados | Tipos Usados | `autonumber` | Participantes explícitos | Qualidade |
| --- | --- | --- | --- | --- | --- |
| BASE | 6 (1 por HU) | `sequenceDiagram` (5) + `flowchart TD` (HU-006) | ❌ | ❌ (implícito) | ⭐⭐⭐⭐ |
| GPT-4.1 | 6 (1 por HU) | `sequenceDiagram` (6) | ❌ | ❌ | ⭐⭐⭐ |
| GPT-5-mini | 6 (1 por HU) | `sequenceDiagram` (6) | ✅ | ❌ | ⭐⭐⭐⭐ |
| GPT-5.2 | 6 (1 por HU) | `sequenceDiagram` (6) | ✅ | ✅ (bloco `participant`) | ⭐⭐⭐⭐⭐ |
| Sonnet 4.5 | ❌ | — | — | — | ❌ |
| Opus 4.5 | ❌ | — | — | — | ❌ |

**Observações:**

- GPT-5.2 é o único que declara todos os `participant` explicitamente, tornando os diagramas mais legíveis e evitando nomes automáticos.
- GPT-5-mini e GPT-5.2 usam `autonumber`, facilitando referência cruzada com critérios de aceite.

---

## 7. Profundidade da Tabela de Componentes

> Volume, colunas e rastreabilidade do artefato de mapeamento de componentes.

| Modelo | Qtd. Componentes | Colunas | Rastreabilidade (Origem → HU/CA) | Dependências mapeadas |
| --- | --- | --- | --- | --- |
| BASE | 25 | Componente / Responsabilidade / **Origem** / Dependências | ✅ Explícita | ✅ |
| GPT-4.1 | 17 | Componente / Responsabilidade / Dependências | ❌ | ✅ |
| GPT-5-mini | 30 | Componente / Responsabilidade / Dependências | ❌ | ✅ |
| GPT-5.2 | 38 | Componente / Responsabilidade / Dependências | ❌ | ✅ |
| Sonnet 4.5 | — | Stack tecnológica + SQL DDL | — | — |
| Opus 4.5 | — | Checklist de completude | — | — |

**Destaque:** Somente o BASE inclui a coluna **Origem**, rastreando cada componente diretamente ao texto da HU ou ao critério de aceite que o motivou. GPT-5.2 compensa com o maior volume de componentes (38 vs. 25), cobrindo até a camada de UI (`LoginUI`, `SignUpUI`, `ChangePasswordUI`) e repositórios de dados separados.

---

## 8. Qualidade do Gap Analysis

> Profundidade da análise crítica de lacunas arquiteturais exigida pelo template.

| Modelo | Gaps Identificados | Categoria (Arq./Func.) | Impacto Descrito | Ação Recomendada |
| --- | --- | --- | --- | --- |
| BASE | 4 | ✅ | ✅ | ✅ |
| GPT-4.1 | 0 | — | — | — |
| GPT-5-mini | 6 | ✅ | ✅ | ✅ |
| GPT-5.2 | 5 | ✅ | ✅ | ✅ |
| Sonnet 4.5 | — | ❌ (análise de produto, não arquitetural) | — | — |
| Opus 4.5 | 1–2 por HU | ✅ (checklist estilo BA) | Parcial | Parcial |

**GPT-4.1** declara explicitamente `"GAP ANALYSIS — Nenhuma lacuna implícita identificada neste lote."` — o que é tecnicamente questionável dado que os demais modelos encontram lacunas reais (SLA não definido, autenticação de websocket, política de revogação de token, etc.).

**GPT-5-mini** apresenta o gap analysis mais completo e acionável: 6 lacunas classificadas, com impacto arquitetural e ação clara (assumir padrão vs. escalar para Time 1).

---

## 9. Diferencial de Conteúdo por Modelo

### 🔵 BASE (GPT-4)

- Único com coluna **Origem** na tabela de componentes (rastreabilidade total HU/CA → componente).
- Boa profundidade arquitetural sem verbosidade excessiva.
- Usa `flowchart TD` para HU-006, diferente dos `sequenceDiagram` dos demais.
- **Limitação:** Não captura `flag_suspeito = 5+ consecutivas` (usa "mais de 5 tentativas falhas") nem o critério de erro genérico do HU-001. Score de fidelidade a CAs: 8/11.

### 🟢 GPT-4.1

- Relatório mais compacto (16KB); boa estrutura formal, **mas sem profundidade analítica**.
- Gap Analysis vazio (`"Nenhuma lacuna identificada"`), o que é uma falha crítica de análise.
- Não captura 5 dos 11 critérios de aceite mais específicos.
- Menor volume de componentes dentre os modelos com template regular (17 itens).
- **Limitação:** Apesar da velocidade (8m02s), a superficialidade do gap analysis e a baixa fidelidade a CAs comprometem a utilidade do output.

### 🟡 GPT-5-mini

- **Equilíbrio sólido**: aderência total ao template e fidelidade a todos os 11 critérios de aceite.
- Gap Analysis de melhor qualidade absoluta: 6 lacunas, com categoria, impacto e ação recomendada.
- 30 componentes bem definidos, incluindo `IPHistoryAnalyzer` — componente específico nomeado apenas aqui e no GPT-5.2.
- Usa `autonumber` nos diagramas, facilitando rastreamento cruzado com CAs.
- **Limitação:** Fidelidade ao template é alta, mas sem rastreabilidade explícita Componente→CA na tabela de componentes.

### 🔵 GPT-5.2

- Relatório mais volumoso (30KB, 472 linhas) e tecnicamente mais rico.
- **Melhor cobertura de componentes:** 38 itens, incluindo camada de UI e repositórios separados.
- **4 Decisões de Arquitetura** com tabela de alternativas (os demais têm 1).
- Diagramas com blocos `participant` explícitos — maior clareza visual.
- Fluxo HU-002 mais detalhado: dois participantes de UI separados (`AdminResetPasswordUI` / `ResetLinkLandingUI`), distingue erros 404 vs 410.
- **Limitação:** Verbosidade pode dificultar leitura rápida; é o modelo com maior latência (16m29s).

### 🔴 Claude Sonnet 4.5 *(formato divergente)*

- Não seguiu o template de relatório de arquitetura; produziu um documento híbrido entre BRD, backlog refinado e guia de implementação.
- Inclui: modelo de dados SQL (DDL completo), endpoints REST com exemplos JSON, casos de teste BDD, stack tecnológica recomendada, considerações LGPD/GDPR, orientações de performance e observabilidade.
- Captura todos os 11 critérios de aceite com alta fidelidade.
- **Ausência total** de diagramas Mermaid, tabela de componentes arquiteturais, decisões de arquitetura e gap analysis arquitetural.
- **Comportamento de interrupção de fluxo:** ao longo da execução, o modelo pausou repetidamente para solicitar confirmação ou feedback do usuário antes de prosseguir — incompatível com execução autônoma e representando risco operacional em pipelines sem supervisão.
- **Nota de aproveitamento:** O desalinhamento é de formato e autonomia de execução, não de capacidade. Com template fixo no system prompt, exemplo few-shot, restrição de escopo e instrução explícita de não solicitar confirmações intermediárias, este modelo tem potencial de alcançar alta qualidade.

### 🟠 Claude Opus 4.5 *(formato divergente)*

- Produziu múltiplos artefatos fragmentados por HU (spec, acceptance criteria, test cases, auth module doc) em vez de um relatório consolidado.
- O arquivo `analise_completude_lote_hus_autenticacao.md` segue estilo BA: completude por HU em %, status aprovado/clarificação, gaps de produto.
- Captura todos os 11 critérios de aceite com alta fidelidade.
- **Ausência total** de diagramas Mermaid, tabela de componentes arquiteturais e decisões de arquitetura.
- **Ponto forte:** Identificou que HU-004 precisa de clarificações (70% completo) — avaliação crítica útil ignorada pelos demais modelos.
- **Nota de aproveitamento:** A análise de completude por HU com percentuais e perguntas de clarificação evidencia capacidade analítica sofisticada. Assim como o Sonnet, o desvio é de formato. Prompts com template fixo e exemplos few-shot devem corrigir o alinhamento sem perda de profundidade.

---

## 10. Análise Especial — Modelos Claude: Complexidade Técnica vs. Aderência ao Template

> **Síntese:** Os modelos Claude avaliados (Sonnet 4.5 e Opus 4.5) demonstraram **complexidade técnica considerável** — em muitos aspectos superior à dos modelos GPT de geração anterior — mas **não seguiram a estrutura esperada** do relatório de arquitetura. Esse desalinhamento não é uma limitação de capacidade, e sim um problema de **engenharia de prompts**.

### O que esses modelos entregaram de diferencial técnico

| Capacidade | Sonnet 4.5 | Opus 4.5 |
| --- | --- | --- |
| Fidelidade total aos 11 critérios de aceite específicos | ✅ | ✅ |
| Modelo de dados SQL (DDL com índices) | ✅ | ❌ |
| Endpoints REST com exemplos de request/response | ✅ | ❌ |
| Casos de teste BDD por HU | ✅ | ❌ |
| Análise de completude por HU (com %) | ❌ | ✅ |
| Identificação de gaps de produto (clarificações) | Parcial | ✅ |
| Considerações de compliance (LGPD/GDPR) | ✅ | ❌ |
| Recomendações de performance e observabilidade | ✅ | ❌ |
| Stack tecnológica detalhada | ✅ | ❌ |

### Por que o formato divergiu?

Os modelos Claude tendem a interpretar tarefas de documentação de forma mais autônoma, priorizando utilidade percebida sobre conformidade estrutural. Sem uma âncora explícita de template no prompt do sistema, o modelo escolhe o formato que considera mais completo para o contexto — resultando em documentos ricos, mas incompatíveis com o pipeline esperado.

### O que seria necessário para aproveitá-los no pipeline atual

| Ação | Descrição |
| --- | --- |
| **Proibição de confirmações intermediárias** | Incluir instrução: `"Execute todas as etapas de forma autônoma, sem solicitar aprovação ou feedback do usuário entre as etapas"` — crítico especialmente para Claude Sonnet |
| **Validação de seções no pipeline** | Adicionar etapa pós-geração que verifique presença das 7 seções antes de aceitar o output |

> **Observação:** Isso já está implementado no pipeline, mas através dos testes descobrimos que não está com autoridade o bastante para garantir o comportamento correto dos modelos Claude. Isso será considerado em sprints futuros e como parte da evolução constante do sistema.

---

## 11. Conclusões

### Contexto do Benchmark

Este documento avalia **8 modelos de linguagem** (GPT-4 como base, GPT-4o, GPT-4.1, GPT-5-mini, GPT-5.2, Claude Haiku 4.5, Claude Sonnet 4.5 e Claude Opus 4.5) na tarefa de gerar automaticamente **relatórios de arquitetura de software** a partir de um lote de 6 Histórias de Usuário (HU-001 a HU-006) do Módulo de Autenticação.

O relatório esperado segue um **template canônico de 7 seções**: identificação das HUs, diagramas Mermaid, decisões de arquitetura, tabela de componentes, bloqueios e pendências, cobertura de HUs e gap analysis. Os modelos GPT foram executados via payload direto na API; os modelos Claude foram testados via interface web — os tempos de execução entre os dois grupos, portanto, **não são diretamente comparáveis**.

A pontuação final combina 6 dimensões (máx. 5 pontos cada, total 30): aderência ao template, qualidade dos diagramas Mermaid, profundidade da tabela de componentes, qualidade do gap analysis, fidelidade aos critérios de aceite das HUs e clareza/legibilidade do documento.

### O que cada modelo entregou — resumo executivo

**GPT-5-mini e GPT-5.2** lideram com 93% e foram os únicos, além do BASE, a capturar todos os 11 critérios de aceite específicos das HUs e a seguir o template completo. O GPT-5-mini se destaca pelo gap analysis mais rico (6 lacunas identificadas, categorizadas e com ação recomendada) em tempo razoável (12m48s). O GPT-5.2 é o mais denso tecnicamente — 38 componentes mapeados, 4 decisões de arquitetura com tabela de alternativas e diagramas Mermaid com participants explícitos — mas é o mais lento (16m29s) e verboso.

**BASE (GPT-4)** é o único modelo com rastreabilidade explícita Componente→Origem (coluna "Origem" na tabela de componentes), identificando diretamente qual HU ou critério de aceite motivou cada componente arquitetural. Combina alta qualidade com o menor tempo de execução entre os bem-sucedidos (5m48s).

**GPT-4.1** entrega rapidez (8m02s) e boa estrutura formal, mas apresenta falha crítica de análise: declara explicitamente que não há lacunas no gap analysis — quando os demais modelos identificam entre 4 e 6 lacunas reais. Captura apenas 6 dos 11 critérios de aceite específicos.

**Claude Sonnet 4.5 e Opus 4.5** produziram documentos tecnicamente sofisticados, mas de natureza completamente diferente do esperado. O Sonnet gerou um híbrido entre BRD, guia de implementação e especificação técnica. O Opus gerou múltiplos artefatos fragmentados por HU com análise de completude percentual estilo Business Analyst. Ambos capturam todos os 11 critérios de aceite com alta fidelidade, mas nenhum gerou diagramas Mermaid, tabela de componentes arquiteturais ou decisões de arquitetura. O Sonnet agravou o problema interrompendo o fluxo repetidamente para solicitar confirmação do usuário.

**GPT-4o e Claude Haiku 4.5** não produziram relatório utilizável.

### Observações Finais por Modelo

| Modelo | Ponto |
| --- | --- |
| **GPT-5-mini** | Gap Analysis mais completo (6 lacunas) e fidelidade total aos 11 CAs com menor verbosidade que o GPT-5.2. **Melhor custo-benefício entre os líderes (12m48s).** |
| **GPT-5.2** | Superior em volume técnico (4 decisões de arquitetura, 38 componentes, participants explícitos nos diagramas), mas a verbosidade pode prejudicar revisões rápidas. **Lento, mas exaustivo (16m29s).** |
| **BASE (GPT-4)** | Único com rastreabilidade explícita Componente→Origem (HU/CA). **Altíssima eficiência temporal (5m48s)** com excelente relação custo-benefício. |
| **GPT-4.1** | Regressão crítica no Gap Analysis (declara ausência de lacunas sem justificativa) e captura apenas 6/11 CAs específicos. Rápido (8m02s), mas superficial. |
| **Claude Sonnet 4.5 e Opus 4.5** | Produziram documentos de alto valor técnico como BRD/BA, mas não são substitutos do relatório de arquitetura esperado. O desvio é de formato e autonomia de execução, não de capacidade. Com template fixo, few-shot, restrição de escopo e proibição de confirmações intermediárias, têm potencial de alcançar ou superar os líderes GPT. |
| **GPT-4o e Claude Haiku 4.5** | Não produziram relatório utilizável: GPT-4o interrompeu a execução espontaneamente; Claude Haiku 4.5 resultou em sessão vazia sem registro de atividade. |
| **Modelos Claude em geral** | Requerem **engenharia de prompts específica** para seguir a estrutura de 7 seções: template fixo no system prompt, exemplo few-shot, restrição explícita de escopo (sem DDL, REST ou test cases) e proibição de confirmações intermediárias. |

---

## 12. Comparativo de Tempos de Execução

> ⚠️ **Nota metodológica:** Os modelos Claude foram testados via interface web, enquanto os modelos GPT foram executados via payload direto na API. Essa diferença de ambiente altera consideravelmente os tempos de execução, portanto **os tempos de Claude e GPT não são diretamente comparáveis** entre si.

### Tabela Geral de Latência e Throughput

| Modelo | Duração Total | Arquivos Úteis Gerados | Throughput Médio (Segundos por Arquivo) | Status do Pipeline |
| --- | --- | --- | --- | --- |
| **BASE (GPT-4)** | **5 min 48s** (348s) | 15 | **23.2s / arquivo** | Complete (Sucesso) |
| **GPT-4o** | **2 min 46s** (166s) | 1 | **166.0s / arquivo** | Interrompido pelo modelo (Incompleto) |
| **GPT-4.1** | **8 min 02s** (482s) | 19 | **25.3s / arquivo** | Complete (Sucesso) |
| **GPT-5-mini** | **12 min 48s** (768s) | 16 | **48.0s / arquivo** | Complete (Sucesso) |
| **GPT-5.2** | **16 min 29s** (989s) | 20 | **49.5s / arquivo** | Complete (Sucesso) |

### Análise Crítica dos Tempos de Execução

1. **Eficiência e Velocidade:**
   - O **BASE (GPT-4)** e o **GPT-4.1** demonstraram altíssima velocidade operacional, completando o pipeline inteiro em menos de 8 minutos com média de ~23 a 25 segundos por arquivo útil.

2. **Equilíbrio Custo-Benefício:**
   - O **GPT-5-mini** levou 12m48s — praticamente o dobro do BASE — mas obteve pontuação líder no scorecard (93%), com fidelidade total aos critérios de aceite e o gap analysis mais completo. A latência incremental é amplamente compensada pelo rigor técnico.

3. **Thoroughness vs. Latency:**
   - O **GPT-5.2** registrou a maior latência (16m29s), refletindo diretamente sua profundidade: 20 arquivos gerados, 38 componentes mapeados e 4 decisões completas de arquitetura. Para projetos críticos que demandam máxima profundidade, essa latência é justificada.

4. **Falhas Operacionais:**
   - **GPT-4o** interrompeu a execução por conta própria na etapa inicial (2m46s ativos, 1 arquivo salvo).
   - **Claude Haiku 4.5** não chegou a iniciar o processamento (pasta vazia, sem registro de log).
