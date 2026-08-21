# RELATÓRIO DE DIAGNÓSTICO DOS AGENTES

> **Escopo:** Pipeline de geração automática de relatórios de arquitetura de software
> **Lote avaliado:** HU-001 a HU-006 — Módulo de Autenticação
> **Fontes:** Benchmark de Qualidade dos Relatórios (Etapa 2) + Referência Cruzada Etapa 1 vs. Etapa 2
> **Data:** 2026-05-24

---

## 1. GLOSSÁRIO

| Termo | Definição |
| --- | --- |
| **SOTA** | State of The Art — conjunto de práticas e comportamentos de melhor desempenho observados empiricamente no benchmark |
| **CA** | Critério de Aceite — requisito específico de uma HU que o relatório deve capturar |
| **HU** | História de Usuário |
| **BA** | Business Analyst — perfil de documento orientado a produto/negócio, não a arquitetura técnica |
| **BRD** | Business Requirements Document |
| **BDD** | Behavior-Driven Development — estilo de casos de teste |
| **Gap Analysis** | Seção do relatório de arquitetura que identifica lacunas entre os requisitos das HUs e a cobertura arquitetural proposta |
| **Template canônico** | Estrutura de 7 seções obrigatórias definida pelo relatório-base (GPT-4): Identificação das HUs, Diagramas Mermaid, Decisões de Arquitetura, Tabela de Componentes, Bloqueios e Pendências, Cobertura de HUs, Gap Analysis |
| **Pipeline autônomo** | Execução completa do agente sem intervenção manual entre etapas |

---

## 2. INVENTÁRIO

### Fontes primárias analisadas

| # | Documento | Tipo | Escopo |
| --- | --- | --- | --- |
| 1 | Benchmark de Qualidade — Relatórios Gerados por Modelo | Avaliação empírica interna | 8 modelos × 6 HUs × 6 dimensões de qualidade |
| 2 | Referência Cruzada — Etapa 1 vs. Etapa 2: Design de Software | Análise cruzada interna | Correlação heatmap de arquitetura × qualidade de relatório |

### Modelos avaliados

| Modelo | Status no pipeline | Resultado |
| --- | --- | --- |
| GPT-4 (base) | Referência | 26/30 — 87% |
| GPT-4o | GA | N/A — falha de execução |
| GPT-4.1 | ⚠️ Encerrando 01/06/2026 | 17/30 — 57% |
| GPT-5-mini | GA | 28/30 — 93% |
| GPT-5.2 | ⚠️ Encerrando 01/06/2026 | 28/30 — 93% |
| Claude Haiku 4.5 | GA | N/A — sessão vazia |
| Claude Sonnet 4.5 | GA | 9/30 — 30% (formato divergente) |
| Claude Opus 4.5 | GA | 12/30 — 40% (formato divergente) |

---

## 3. PRÁTICAS SOTA IDENTIFICADAS

> Práticas observadas nos modelos de melhor desempenho (GPT-5-mini, GPT-5.2 e GPT-4 base), derivadas do benchmark empírico.

| # | Prática | Evidência | Fonte |
| --- | --- | --- | --- |
| P1 | Aderência total ao template canônico de 7 seções sem desvio de formato | Empírica — GPT-5-mini e GPT-5.2 atingiram 100% de aderência; Claude Sonnet e Opus divergiram para formatos BA/BRD | Benchmark, Seção 3 |
| P2 | Fidelidade completa aos critérios de aceite específicos das HUs, incluindo valores numéricos exatos e regras de negócio precisas | Empírica — GPT-5-mini, GPT-5.2, Sonnet 4.5 e Opus 4.5 capturaram 11/11 CAs; BASE e GPT-4.1 capturaram 8/11 e 6/11 respectivamente | Benchmark, Seção 4 |
| P3 | Gap analysis com lacunas reais, categorizadas (arquitetural/funcional), com impacto descrito e ação recomendada | Empírica — GPT-5-mini identificou 6 lacunas acionáveis; GPT-4.1 declarou ausência de lacunas apesar de existirem | Benchmark, Seção 8 |
| P4 | Geração de diagramas Mermaid com `autonumber` e declaração explícita de bloco `participant` | Empírica — GPT-5.2 único com participants explícitos (5/5); GPT-5-mini e GPT-5.2 usam autonumber | Benchmark, Seção 6 |
| P5 | Tabela de componentes com rastreabilidade explícita Componente → HU/CA de origem | Empírica — apenas GPT-4 base inclui coluna "Origem"; GPT-5.2 compensa com maior volume (38 componentes) | Benchmark, Seção 7 |
| P6 | Execução autônoma completa do pipeline sem solicitar confirmações intermediárias | Empírica — Claude Sonnet 4.5 interrompeu o fluxo repetidamente; GPT-5-mini e GPT-5.2 completaram sem intervenção | Benchmark, Seção 9; Referência Cruzada, Seção 5.3 |
| P7 | Consistência entre capacidade de design estático (heatmap) e execução em pipeline de geração de documentação | Empírica — GPT-5-mini e GPT-5.2 confirmaram cobertura T1–T14 com execução de alta qualidade na etapa 2; GPT-4.1 falhou em profundidade apesar de cobertura total | Referência Cruzada, Seção 5.1 |

---

## 4. GAP ANALYSIS

> Comparação entre as práticas SOTA identificadas e o estado atual do pipeline.

| Prática SOTA | Status no protótipo | Observação |
| --- | --- | --- |
| P1 — Aderência ao template canônico (7 seções) | **Parcial** | GPT-5-mini e GPT-5.2 atingem 100%; modelos Claude divergem para formatos BA/BRD. O pipeline não garante uniformidade entre modelos |
| P2 — Fidelidade completa aos 11 CAs específicos | **Parcial** | GPT-5-mini, GPT-5.2 e modelos Claude atingem 11/11; GPT-4 base (8/11) e GPT-4.1 (6/11) ficam abaixo. Ausência de validação pós-geração de CAs |
| P3 — Gap analysis com lacunas categorizadas e acionáveis | **Parcial** | GPT-5-mini entrega o melhor gap analysis (6 lacunas); GPT-4.1 declara ausência de lacunas sem justificativa. Sem validação de presença e profundidade do gap analysis no pipeline |
| P4 — Diagramas Mermaid com `autonumber` e `participant` explícito | **Parcial** | Apenas GPT-5.2 atinge 5/5; GPT-5-mini usa autonumber mas sem participant; modelos Claude não geram diagramas. Sem instrução de qualidade de diagrama no prompt |
| P5 — Rastreabilidade Componente → HU/CA na tabela de componentes | **Ausente** | Apenas o GPT-4 base inclui coluna "Origem". Nenhum outro modelo replicou esse comportamento espontaneamente. Não está especificado no prompt como requisito |
| P6 — Execução autônoma sem confirmações intermediárias | **Parcial** | GPT-5-mini e GPT-5.2 executam autonomamente; Claude Sonnet 4.5 interrompe repetidamente. A instrução de autonomia existe no pipeline mas sem autoridade suficiente para garantir o comportamento dos modelos Claude |
| P7 — Consistência capacidade estática × execução em pipeline | **Parcial** | GPT-5-mini e GPT-5.2 confirmam consistência; GPT-4.1 apresenta contradição analítica (cobertura total T1–T14, mas gap analysis vazio). O heatmap da etapa 1 não prediz profundidade analítica |

---

## 5. CLASSIFICAÇÃO DE GAPS

### Gaps endereçáveis

> Existem técnicas conhecidas — falta implementar.

| Gap | Descrição | Técnica disponível |
| --- | --- | --- |
| **G1 — Divergência de formato dos modelos Claude** | Sonnet 4.5 e Opus 4.5 produzem documentos BA/BRD em vez de relatório de arquitetura | Template fixo no system prompt + instrução `"Siga EXATAMENTE esta estrutura"` + restrição explícita de escopo (sem DDL, REST, test cases) |
| **G2 — Ausência de rastreabilidade Componente → CA** | Nenhum modelo além do BASE inclui coluna "Origem" na tabela de componentes | Especificação explícita da coluna no prompt: `"A tabela de componentes deve incluir obrigatoriamente a coluna Origem, indicando a HU ou CA que motivou o componente"` |
| **G3 — Qualidade insuficiente dos diagramas Mermaid** | Maioria dos modelos não usa `autonumber` nem declara `participant` explicitamente | Instrução específica de qualidade de diagrama no prompt + validação de sintaxe pós-geração |
| **G4 — Gap analysis vazio ou ausente em alguns modelos** | GPT-4.1 declara ausência de lacunas sem evidência; modelos Claude não geram gap analysis arquitetural | Validação pós-geração da presença e do número mínimo de lacunas identificadas |
| **G5 — Fidelidade parcial a CAs no BASE e GPT-4.1** | GPT-4 base perde 3/11 CAs específicos; GPT-4.1 perde 5/11 | Inclusão dos CAs críticos como exemplos negativos no prompt (`"Atenção especial para: flag_suspeito = 5+ consecutivas, não apenas '5 ou mais'"`) |

### Gaps de pesquisa

> Não há solução clara — oportunidade de contribuição.

| Gap | Descrição | Natureza da abertura |
| --- | --- | --- |
| **G6 — Autonomia de execução vs. qualidade técnica nos modelos Claude** | Modelos Claude demonstram maior densidade técnica (11/11 CAs, DDL SQL, análise de completude) mas interrompem pipelines para solicitar confirmação. A instrução de autonomia existe mas não tem autoridade suficiente | Não há técnica estabelecida para calibrar o trade-off entre autonomia de execução e profundidade analítica em modelos com forte "instinto de alinhamento". Requer investigação sobre mecanismos de system prompt com maior peso de instrução |
| **G7 — Previsibilidade de profundidade analítica via heatmap estático** | A etapa 1 (heatmap) mede cobertura funcional, mas não prediz profundidade analítica na etapa 2. GPT-4.1 tem cobertura total T1–T14 e gap analysis vazio | Não há metodologia estabelecida para avaliar "rigor crítico" vs. "cobertura funcional" em benchmarks estáticos de design. Oportunidade de contribuição: dimensão de avaliação de profundidade analítica |
| **G8 — Fragmentação de artefatos no Claude Opus 4.5** | O Opus produz múltiplos artefatos especializados por HU (spec, ACs, test cases, análise técnica) em vez de um relatório consolidado — formato potencialmente mais útil para algumas equipes, mas incompatível com o pipeline atual | Não há consenso sobre o formato ótimo de output para pipelines de documentação de arquitetura. A fragmentação pode ser uma prática emergente superior para equipes ágeis |

---

## 6. RECOMENDAÇÕES (priorizadas)

### Quick wins — implementáveis nesta/próxima sprint

| # | Recomendação | Gap endereçado | Esforço estimado |
| --- | --- | --- | --- |
| R1 | Adicionar validação pós-geração das 7 seções canônicas antes de aceitar o output | G1, G4 | Baixo — checklist de presença de seções via regex/parsing |
| R2 | Incluir instrução de `autonumber` e `participant` explícito nos diagramas Mermaid diretamente no prompt | G3 | Baixo — adição de 2 linhas ao prompt |
| R3 | Especificar a coluna "Origem" como campo obrigatório na tabela de componentes no prompt | G2 | Baixo — adição de instrução ao prompt |
| R4 | Incluir os 3 CAs mais perdidos como exemplos negativos no prompt (`flag_suspeito = 5+ consecutivas`, erro genérico HU-001, IP considera TODO histórico) | G5 | Baixo — adição de exemplos ao prompt |

### Médio prazo — requerem refatoração

| # | Recomendação | Gap endereçado | Esforço estimado |
| --- | --- | --- | --- |
| R6 | Adicionar validação de profundidade do gap analysis: verificar se o número de lacunas identificadas é ≥ 3 e se cada lacuna tem categoria, impacto e ação — rejeitar outputs com gap analysis vazio | G4 | Médio — lógica de validação semântica pós-geração |
| R7 | Refatorar o system prompt dos modelos Claude com template fixo de 7 seções, restrição explícita de escopo (sem DDL, REST, test cases) e instrução de autonomia com maior peso | G1, G6 | Médio — reescrita de system prompt + testes de regressão |
| R8 | Implementar avaliação de fidelidade a CAs como etapa automatizada do pipeline: comparar critérios específicos do lote contra o output gerado antes de aceitar o relatório | G5 | Médio — parser de CAs + lógica de comparação |

### Longo prazo / pesquisa — requerem investigação adicional

| # | Recomendação | Gap endereçado | Natureza |
| --- | --- | --- | --- |
| R9 | Investigar mecanismos de system prompt com maior autoridade de instrução para modelos Claude — calibrar trade-off entre autonomia de execução e profundidade analítica | G6 | Pesquisa de prompt engineering — sem solução estabelecida |
| R10 | Desenvolver dimensão de "profundidade analítica" para o heatmap da etapa 1, complementando a cobertura funcional T1–T14 com avaliação de rigor crítico (ex: qualidade de gap analysis, rastreabilidade de requisitos) | G7 | Pesquisa metodológica — requer design de nova dimensão de avaliação |
| R11 | Avaliar se o formato de artefatos fragmentados por HU do Claude Opus 4.5 tem valor para casos de uso específicos (ex: onboarding de equipe, revisão de sprint) — potencial de pipeline paralelo para documentação de produto vs. arquitetura | G8 | Pesquisa aplicada — requer validação com equipes usuárias |

---

## 7. POSICIONAMENTO

> Avaliação do estado atual do pipeline em relação às práticas SOTA identificadas.

**Nosso agente está: abaixo do SOTA — com trajetória clara de convergência.**

### Detalhamento por dimensão

| Dimensão | Melhor resultado observado (SOTA) | Resultado atual do pipeline* | Posição |
| --- | --- | --- | --- |
| Aderência ao template | 100% (GPT-5-mini, GPT-5.2) | ~87% (média ponderada modelos ativos) | Abaixo do SOTA |
| Fidelidade aos CAs | 11/11 (GPT-5-mini, GPT-5.2, Claude Sonnet/Opus) | 8–11/11 dependendo do modelo | No SOTA (modelos líderes) / Abaixo (modelos legados) |
| Qualidade do gap analysis | 6 lacunas acionáveis (GPT-5-mini) | 0–6 dependendo do modelo | Abaixo do SOTA (sem garantia de qualidade mínima) |
| Qualidade dos diagramas | ⭐⭐⭐⭐⭐ (GPT-5.2) | ⭐⭐⭐–⭐⭐⭐⭐ (maioria dos modelos) | Abaixo do SOTA |
| Rastreabilidade Componente → CA | Presente (GPT-4 base) | Ausente nos demais modelos | Abaixo do SOTA |
| Autonomia de execução | Total (GPT-5-mini, GPT-5.2) | Parcial — Claude Sonnet interrompe pipeline | Abaixo do SOTA |

*\*Pipeline atual considerando o conjunto de modelos ativos no GitHub Copilot (GA).*

### Observação estratégica

O pipeline demonstra capacidade técnica de atingir o SOTA — os modelos GPT-5-mini e GPT-5.2 já operam nesse nível quando executados corretamente. O gap principal não é de capacidade dos modelos, mas de **engenharia de prompts, validação pós-geração e gestão de modelos ativos**. Com as quick wins da Seção 6 implementadas, o pipeline tem condições de operar consistentemente no SOTA na próxima sprint. Os modelos Claude representam o maior potencial de salto de qualidade no médio prazo, desde que o problema de alinhamento de formato e autonomia de execução seja endereçado.
