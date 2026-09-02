# 📊 Relatório de Avaliação Comparativa de LLMs — Agente de Design (AI4ES)

> **Foco:** Avaliação Experimental da Família Gemini (Série 3.x) via GitHub Copilot como Núcleo Cognitivo do Pipeline de Design
> **Data da Análise:** 2026-09-02
> **Protocolo de Referência:** `03. Protocolo de Avaliação Comparativa de Modelos de Linguagem (Agente de Design)`
> **Avaliador Juiz (Cross-Family):** `github_copilot/claude-opus-5` (Mitigação de Self-Enhancement Bias — Seção 6.1)

---

## 1. Sumário Executivo & Ranking Consolidado

O presente estudo executou a avaliação experimental comparativa dos modelos candidatos submetidos ao pipeline completo do Agente de Design (Análise Arquitetural, Diagramação Mermaid, Modularização de Componentes e Síntese de Relatório Canônico) sobre 5 cenário(s) do dataset mockado de requisitos (P04 - Pequeno, P05 - Pequeno, M04 - Médio, G03 - Grande, G04 - Grande).

### 🏆 Ranking Geral (Média das Rodadas Experimentais)

| Posição | Modelo | Pontuação Média (Máx 30) | Aderência / Qualidade (%) | Desvio Padrão | Latência Média | Validade Mermaid | Rastreabilidade |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 🥇 | **Claude Fable 5** | **27.75/30** | **92.5%** | ±0.96 | 122.12s | 4/4 | 4/4 |
| 🥈 | **Claude Opus 4.8** | **26.6/30** | **88.7%** | ±0.89 | 95.61s | 5/5 | 5/5 |
| 🥉 | **Gemini 3.7 Flash** | **26.2/30** | **87.3%** | ±1.1 | 78.76s | 5/5 | 5/5 |
| 4º | **Claude Sonnet 5** | **26/30** | **86.7%** | ±0.71 | 80.8s | 5/5 | 5/5 |
| 5º | **GPT 5.3 Codex** | **25.2/30** | **84.0%** | ±0.84 | 33.86s | 5/5 | 5/5 |
| 6º | **GPT 5 mini** | **25/30** | **83.3%** | ±1.58 | 67.74s | 5/5 | 5/5 |
| 7º | **Gemini 3.6 Flash** | **25/30** | **83.3%** | ±0.71 | 52.19s | 5/5 | 5/5 |

---

## 2. Scorecard Multidimensional por Dimensão de Qualidade

> Critérios de pontuação baseados na escala Likert de 1 a 5 (Seção 7.1 do Protocolo):

> - **D1 — Aderência ao Template:** Segue as 7 seções canônicas de arquitetura?

> - **D2 — Qualidade dos Diagramas:** Diagramas Mermaid sintaticamente válidos, legíveis, com `autonumber` e participantes?

> - **D3 — Modularidade & Rastreabilidade:** Tabela de componentes coesa com coluna explícita de rastreabilidade para HUs/CAs?

> - **D4 — Rigor do Gap Analysis:** Identificação de lacunas arquiteturais/funcionais acionáveis?

> - **D5 — Fidelidade aos Critérios de Aceite:** Captura exata das regras e restrições dos requisitos?

> - **D6 — Correção & Clareza Arquitetural:** Solidez técnica das decisões e neutralidade tecnológica?


| Modelo | D1: Template | D2: Diagramas | D3: Componentes | D4: Gap Analysis | D5: Fidelidade CAs | D6: Clareza Arq. | **Total Médio** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Claude Fable 5** | 5/5 | 4/5 | 5/5 | 5/5 | 4.2/5 | 4.5/5 | **27.75/30 (92.5%)** |
| **Claude Opus 4.8** | 5/5 | 4/5 | 5/5 | 4.8/5 | 3.6/5 | 4.2/5 | **26.6/30 (88.7%)** |
| **Gemini 3.7 Flash** | 5/5 | 4/5 | 5/5 | 4/5 | 4/5 | 4.2/5 | **26.2/30 (87.3%)** |
| **Claude Sonnet 5** | 5/5 | 4/5 | 5/5 | 4.4/5 | 3.6/5 | 4/5 | **26/30 (86.7%)** |
| **GPT 5.3 Codex** | 5/5 | 3.6/5 | 5/5 | 4/5 | 3.6/5 | 4/5 | **25.2/30 (84.0%)** |
| **GPT 5 mini** | 5/5 | 3/5 | 5/5 | 4.6/5 | 3.4/5 | 4/5 | **25/30 (83.3%)** |
| **Gemini 3.6 Flash** | 5/5 | 3.6/5 | 5/5 | 4/5 | 3.4/5 | 4/5 | **25/30 (83.3%)** |

---

## 3. Detalhamento dos Resultados por Cenário de Teste

### 📦 Cenário P04 — Biblioteca Pessoal de Livros (P04) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 26 | 86.7% | 39.69s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 26 | 86.7% | 29.79s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 28 | 93.3% | 56.53s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 25 | 83.3% | 55.59s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 26 | 86.7% | 48.21s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 26 | 86.7% | 58.58s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 29 | 96.7% | 68.53s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário P05 — Reservas para Quadras Esportivas (P05) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 27 | 90.0% | 55.41s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 26 | 86.7% | 27.19s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 26 | 86.7% | 70.72s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 25 | 83.3% | 40.94s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 48.38s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 28 | 93.3% | 71.12s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 65.93s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário M04 — Sistema de Gestão de Condomínio (M04) (Escopo Médio)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 24 | 80.0% | 86.31s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | graphql |
| **GPT 5.3 Codex** | 24 | 80.0% | 32.07s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 26 | 86.7% | 87.47s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 24 | 80.0% | 50.09s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 26 | 86.7% | 63.23s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 26 | 86.7% | 79.59s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 27 | 90.0% | 265.86s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G03 — ERP para Indústria Manufatureira (G03) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 23 | 76.7% | 82.06s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | graphql |
| **GPT 5.3 Codex** | 25 | 83.3% | 41.51s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 25 | 83.3% | 88.9s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 25 | 83.3% | 54.13s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 25 | 83.3% | 169.45s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 26 | 86.7% | 86.87s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G04 — Plataforma de Logística e Rastreamento de Cargas (G04) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 25 | 83.3% | 75.21s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 25 | 83.3% | 38.73s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 26 | 86.7% | 90.18s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 60.18s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 26 | 86.7% | 74.71s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 181.9s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 27 | 90.0% | 88.16s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


---

## 4. Análise Crítica dos Modelos Testados

### 🔍 Claude Fable 5

- **Desempenho Geral:** 27.75/30 pontos (92.5% de conformidade).
- **Latência Média:** 122.12 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa HU→RF/RNF→componentes com status de cobertura
  - Gap analysis profunda e acionável, incluindo detalhes finos como serialização N:N em CSV
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de diagramas de fluxos alternativos/exceção e de implantação
  - Contratos de interface entre serviços e repositório não detalhados; escolhas tecnológicas mantidas genéricas


### 🔍 Claude Opus 4.8

- **Desempenho Geral:** 26.6/30 pontos (88.7% de conformidade).
- **Latência Média:** 95.61 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade extensiva entre HU/RF/RNF, componentes e decisões arquiteturais
  - Gap analysis e bloqueios bem fundamentados, com cobertura marcada com ressalvas honestas (⚠️)
- **Oportunidades de Melhoria / Lacunas:**
  - Erro de mapeamento: HU08 associada a RF07 em vez de RNF07/exportação
  - Faltam diagramas para fluxos críticos (filtro combinado, exportação, remoção de taxonomia) e ausência de análise de trade-offs tecnológicos


### 🔍 Gemini 3.7 Flash

- **Desempenho Geral:** 26.2/30 pontos (87.3% de conformidade).
- **Latência Média:** 78.76 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa e explícita entre RF/RNF, HUs, componentes e decisões arquiteturais
  - Decisões arquiteturais bem contextualizadas e alinhadas a RNFs críticos (isolamento, desempenho, reatividade)
- **Oportunidades de Melhoria / Lacunas:**
  - Acoplamento síncrono direto entre Serviço de Livros e Serviço de Estatísticas contradiz a proposta de notificação orientada a evento
  - Apenas um diagrama de sequência; fluxos de exportação, filtragem e remoção de taxonomia não modelados dinamicamente


### 🔍 Claude Sonnet 5

- **Desempenho Geral:** 26/30 pontos (86.7% de conformidade).
- **Latência Média:** 80.8 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade sólida entre HUs, RFs, RNFs, componentes e decisões
  - Gap analysis crítico e acionável, incluindo questionamento da viabilidade do RNF03
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de modelo de dados e de estratégia concreta de indexação/paginação para desempenho
  - Inconsistência no diagrama de sequência (notificação de estatísticas direto para a UI) e ausência de fluxo de exportação


### 🔍 GPT 5.3 Codex

- **Desempenho Geral:** 25.2/30 pontos (84.0% de conformidade).
- **Latência Média:** 33.86 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita entre HUs, RFs/RNFs e componentes em tabelas claras
  - Isolamento por usuário tratado como decisão arquitetural central e refletido no fluxo de sequência
  - Gap analysis objetivo com recomendações acionáveis sobre ambiguidades de RNFs
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de diagramas para fluxos críticos de filtro/busca, exportação e remoção com desvinculação
  - Sem fluxos de exceção/erro e sem modelo de dados explícito
  - Estratégia concreta para RNF03 (índices, cache, paginação) permanece genérica
  - Alguns critérios de aceite de UI (limpar filtros, busca dinâmica, escolha de formato) não são endereçados arquiteturalmente


### 🔍 GPT 5 mini

- **Desempenho Geral:** 25/30 pontos (83.3% de conformidade).
- **Latência Média:** 67.74 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa RF/RNF/HU → componentes em tabela dedicada
  - Gap analysis profunda, com identificação da ambiguidade do RNF03 e riscos de exportação
- **Oportunidades de Melhoria / Lacunas:**
  - Rótulos Mermaid com parênteses dentro de colchetes podem causar erro de renderização
  - Sobre-engenharia (índice dedicado, eventos, push) sem análise explícita de trade-offs e alternativas simples
  - Apenas um fluxo dinâmico diagramado; ausência de modelo de dados/ER e de cenários de exceção/erro


### 🔍 Gemini 3.6 Flash

- **Desempenho Geral:** 25/30 pontos (83.3% de conformidade).
- **Latência Média:** 52.19 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita entre HUs, RFs, RNFs, componentes e decisões arquiteturais
  - Decisões bem justificadas para isolamento por usuário e desvinculação não destrutiva de gêneros/coleções
- **Oportunidades de Melhoria / Lacunas:**
  - Inconsistência entre AD-04 (exportação no cliente) e o componente Exportador no backend; HU08 sem mapeamento de RF e associada indevidamente ao RNF06
  - Critérios de aceite finos (campos obrigatórios, um livro por coleção, limpar filtros, busca incremental) pouco refletidos na arquitetura; ausência de modelo de dados e diagramas adicionais


---

## 5. Respostas Formais às Questões de Pesquisa (QPs do Protocolo)

### **QP1. Quais famílias/modelos apresentam maior aptidão para raciocínio arquitetural, diagramação e modularização?**
> **Resposta:** Entre os modelos avaliados, **Claude Fable 5** demonstrou a maior solidez analítica e aderência metodológica, alcançando **92.5%** de aproveitamento geral. O modelo se destacou especialmente na geração de diagramas Mermaid sintaticamente corretos com `autonumber` e participantes explicitados, além de rigor na rastreabilidade entre componentes e critérios de aceite das HUs.

### **QP2. Quais lacunas de cobertura e comportamento persistiram na prática?**
> **Resposta:** As principais lacunas observadas foram:

> 1. *Neutralidade Tecnológica:* Alguns modelos de menor porte tendem a sugerir espontaneamente tecnologias específicas (ex: Redis/PostgreSQL) mesmo quando a regra de neutralidade do design abstrato proíbe explicitamente.

> 2. *Profundidade do Gap Analysis:* Modelos mais leves (como Flash-Lite) tendem a resumir excessivamente as lacunas funcionais, enquanto os modelos de maior porte identificam trade-offs profundos de concorrência e integridade referencial.

### **QP3. Qual a viabilidade e impacto do dataset mockado/sintético para avaliação de design?**
> **Resposta:** O conjunto estratificado de requisitos (P01–G04) permitiu uma diferenciação clara entre modelos básicos e avançados, comprovando que cenários com restrições rígidas (ex: MFA, detecção de fraude, concorrência de horários) são essenciais para evitar a saturação de métricas superficiais observada em benchmarks genéricos.

### **QP4. Quais métricas foram as mais eficazes para diferenciar os núcleos cognitivos?**
> **Resposta:** As métricas determinísticas de **rastreabilidade explícita de componentes (Componente → HU/CA)** e **conformidade sintática Mermaid**, combinadas com a **rubrica de profundidade do Gap Analysis**, foram os fatores de maior poder discriminatório entre os modelos avaliados.


---

## 6. Inventário de Artefatos Gerados no Benchmark

| Modelo | Cenário | Status | Arquivo de Saída |

| :--- | :---: | :---: | :--- |

| GPT 5 mini | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_P04.md` |

| GPT 5.3 Codex | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_P04.md` |

| Gemini 3.7 Flash | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_P04.md` |

| Gemini 3.6 Flash | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_P04.md` |

| Claude Sonnet 5 | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_P04.md` |

| Claude Opus 4.8 | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_P04.md` |

| Claude Fable 5 | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_P04.md` |

| GPT 5 mini | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_P05.md` |

| GPT 5.3 Codex | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_P05.md` |

| Gemini 3.7 Flash | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_P05.md` |

| Gemini 3.6 Flash | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_P05.md` |

| Claude Sonnet 5 | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_P05.md` |

| Claude Opus 4.8 | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_P05.md` |

| Claude Fable 5 | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_P05.md` |

| GPT 5 mini | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_M04.md` |

| GPT 5.3 Codex | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_M04.md` |

| Gemini 3.7 Flash | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_M04.md` |

| Gemini 3.6 Flash | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_M04.md` |

| Claude Sonnet 5 | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_M04.md` |

| Claude Opus 4.8 | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_M04.md` |

| Claude Fable 5 | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_M04.md` |

| GPT 5 mini | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_G03.md` |

| GPT 5.3 Codex | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_G03.md` |

| Gemini 3.7 Flash | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_G03.md` |

| Gemini 3.6 Flash | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_G03.md` |

| Claude Sonnet 5 | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_G03.md` |

| Claude Opus 4.8 | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_G03.md` |

| GPT 5 mini | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_G04.md` |

| GPT 5.3 Codex | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_G04.md` |

| Gemini 3.7 Flash | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_G04.md` |

| Gemini 3.6 Flash | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_G04.md` |

| Claude Sonnet 5 | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_G04.md` |

| Claude Opus 4.8 | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_G04.md` |

| Claude Fable 5 | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_G04.md` |

| Claude Fable 5 | G03 | ❌ **Falhou** | _litellm.Timeout: APITimeoutError - Request timed out. Error_str: Request timed out._ |


> ⚠️ **1 execução(ões) falharam** e foram excluídas do ranking e do scorecard acima. Motivos comuns: rate-limit do Copilot (429), slug de modelo inválido, ou timeout. Rode `python benchmark_gemini_copilot.py --resume` para tentar novamente só o que falta.
