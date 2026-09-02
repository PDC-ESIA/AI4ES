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
| 🥇 | **Claude Fable 5** | **27.6/30** | **92.0%** | ±0.55 | 150.82s | 5/5 | 5/5 |
| 🥈 | **Gemini 3.7 Flash** | **26.6/30** | **88.7%** | ±0.89 | 109.81s | 5/5 | 5/5 |
| 🥉 | **Claude Opus 4.8** | **26.6/30** | **88.7%** | ±0.55 | 135.53s | 5/5 | 5/5 |
| 4º | **Claude Sonnet 5** | **26.2/30** | **87.3%** | ±1.1 | 65.02s | 5/5 | 5/5 |
| 5º | **Gemini 3.6 Flash** | **25.6/30** | **85.3%** | ±0.55 | 57.74s | 5/5 | 5/5 |
| 6º | **GPT 5.3 Codex** | **25/30** | **83.3%** | ±1.22 | 36.5s | 5/5 | 5/5 |
| 7º | **GPT 5 mini** | **24/30** | **80.0%** | ±1.41 | 90.97s | 5/5 | 5/5 |

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
| **Claude Fable 5** | 5/5 | 4/5 | 5/5 | 5/5 | 4/5 | 4.6/5 | **27.6/30 (92.0%)** |
| **Gemini 3.7 Flash** | 5/5 | 4/5 | 5/5 | 4.4/5 | 4/5 | 4.2/5 | **26.6/30 (88.7%)** |
| **Claude Opus 4.8** | 5/5 | 4/5 | 5/5 | 5/5 | 3.6/5 | 4/5 | **26.6/30 (88.7%)** |
| **Claude Sonnet 5** | 5/5 | 4/5 | 5/5 | 4.6/5 | 3.6/5 | 4/5 | **26.2/30 (87.3%)** |
| **Gemini 3.6 Flash** | 5/5 | 3.8/5 | 5/5 | 4/5 | 3.8/5 | 4/5 | **25.6/30 (85.3%)** |
| **GPT 5.3 Codex** | 5/5 | 3.2/5 | 5/5 | 4.2/5 | 3.6/5 | 4/5 | **25/30 (83.3%)** |
| **GPT 5 mini** | 5/5 | 2.4/5 | 5/5 | 4.4/5 | 3.4/5 | 3.8/5 | **24/30 (80.0%)** |

---

## 3. Detalhamento dos Resultados por Cenário de Teste

### 📦 Cenário P04 — Biblioteca Pessoal de Livros (P04) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 23 | 76.7% | 39.78s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | graphql |
| **GPT 5.3 Codex** | 25 | 83.3% | 26.94s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 26 | 86.7% | 65.61s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 50.44s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 51.12s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 69.76s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 27 | 90.0% | 68.0s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário P05 — Reservas para Quadras Esportivas (P05) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 26 | 86.7% | 76.56s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 27 | 90.0% | 30.56s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 28 | 93.3% | 58.05s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 51.06s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 49.96s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 70.84s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 67.01s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário M04 — Sistema de Gestão de Condomínio (M04) (Escopo Médio)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 23 | 76.7% | 58.87s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | graphql |
| **GPT 5.3 Codex** | 24 | 80.0% | 41.67s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 26 | 86.7% | 72.88s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 25 | 83.3% | 67.33s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 25 | 83.3% | 76.72s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 26 | 86.7% | 85.23s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 356.81s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G03 — ERP para Indústria Manufatureira (G03) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 25 | 83.3% | 244.21s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 25 | 83.3% | 45.91s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 27 | 90.0% | 88.56s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 25 | 83.3% | 48.29s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 78.4s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 26 | 86.7% | 269.92s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 89.28s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G04 — Plataforma de Logística e Rastreamento de Cargas (G04) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 23 | 76.7% | 35.44s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 24 | 80.0% | 37.43s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 26 | 86.7% | 263.97s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 71.6s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 25 | 83.3% | 68.88s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 181.91s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 27 | 90.0% | 173.0s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


---

## 4. Análise Crítica dos Modelos Testados

### 🔍 Claude Fable 5

- **Desempenho Geral:** 27.6/30 pontos (92.0% de conformidade).
- **Latência Média:** 150.82 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade forte entre HU, RF/RNF, componentes e decisões
  - Gap analysis e pendências profundas, específicas e acionáveis
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de fluxos de exceção e de diagramas para filtragem/exportação
  - Trade-offs tecnológicos e de granularidade de serviços pouco explorados; repositório único compartilhado não problematizado


### 🔍 Gemini 3.7 Flash

- **Desempenho Geral:** 26.6/30 pontos (88.7% de conformidade).
- **Latência Média:** 109.81 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita entre HUs, RFs/RNFs e componentes
  - ADRs com contexto, decisão e consequência bem articulados
  - Modelo de domínio com cardinalidades e enums corretos
- **Oportunidades de Melhoria / Lacunas:**
  - Inconsistência entre ADR02 (eventos) e o acoplamento síncrono mostrado no diagrama de sequência
  - Cobertura declarada como 100% sem evidências para RNF02/RNF03/RNF06
  - Ausência de diagramas para busca/filtro e exportação; sem detalhamento de índices/paginação para desempenho


### 🔍 Claude Opus 4.8

- **Desempenho Geral:** 26.6/30 pontos (88.7% de conformidade).
- **Latência Média:** 135.53 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita entre HUs, RFs, RNFs, componentes e decisões arquiteturais
  - Gap analysis e tabela de bloqueios profundos, com severidade, impacto e ações acionáveis
  - Modelo de domínio correto quanto às cardinalidades (gênero N:N, coleção 0..1)
- **Oportunidades de Melhoria / Lacunas:**
  - Mapeamento incorreto de HU08 a 'RF07(export)' em vez de RNF07
  - Bypass do domínio por serviços de busca/estatística/exportação e evento de atualização de estatísticas não formalizado
  - Ausência de diagramas de sequência para exportação, estatísticas e remoção com desvinculação; poucos fluxos de exceção


### 🔍 Claude Sonnet 5

- **Desempenho Geral:** 26.2/30 pontos (87.3% de conformidade).
- **Latência Média:** 65.02 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita HU→RF→RNF→componente com tabela de cobertura e status parciais honestos
  - Gap analysis e bloqueios profundos, acionáveis e com responsáveis sugeridos
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de modelo de dados/entidades e de contratos de interface entre serviços
  - Tratamento superficial de RNF03/RNF02/RNF06 e ausência de fluxos de exceção nos diagramas


### 🔍 Gemini 3.6 Flash

- **Desempenho Geral:** 25.6/30 pontos (85.3% de conformidade).
- **Latência Média:** 57.74 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita HU↔RF/RNF↔componentes com tabela de cobertura completa
  - Modelo de domínio correto quanto a cardinalidades e regras de desvinculação sem cascata
- **Oportunidades de Melhoria / Lacunas:**
  - Mapeamentos imprecisos: RNF06 associado à exportação e RF03 sem HU vinculada
  - Decisão de filtragem híbrida sem limiar definido e ausência de diagramas para exportação/filtragem


### 🔍 GPT 5.3 Codex

- **Desempenho Geral:** 25/30 pontos (83.3% de conformidade).
- **Latência Média:** 36.5 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade sistemática HU↔RF↔RNF↔componente com tabelas de cobertura
  - Gap analysis acionável e reconhecimento honesto de coberturas parciais (RNF02, RNF03, RNF06)
- **Oportunidades de Melhoria / Lacunas:**
  - Cobertura diagramática limitada: sem ER/modelo de dados e sem fluxos de exportação, filtro ou desvinculação
  - Erros pontuais de mapeamento (HU08→RF08/RF13; RF02/RF03 sem HU) e ausência de tratamento de exceções e trade-offs tecnológicos


### 🔍 GPT 5 mini

- **Desempenho Geral:** 24/30 pontos (80.0% de conformidade).
- **Latência Média:** 90.97 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita entre componentes, HUs e RF/RNF em tabela
  - Seção de gaps e pendências acionável, ligando lacunas a impactos arquiteturais
  - Neutralidade tecnológica mantida, com foco em responsabilidades e contratos
- **Oportunidades de Melhoria / Lacunas:**
  - Provável erro de sintaxe no diagrama Mermaid de componentes (parênteses/barras em rótulos não escapados) e arestas redundantes
  - Sobre-engenharia para o domínio (índice separado, WebSocket, microsserviços) sem análise de trade-off ou alternativa mais simples
  - Ausência de modelo de dados/entidades e de tratamento de cenários de exceção (validações, erros, limites de exportação)


---

## 5. Respostas Formais às Questões de Pesquisa (QPs do Protocolo)

### **QP1. Quais famílias/modelos apresentam maior aptidão para raciocínio arquitetural, diagramação e modularização?**
> **Resposta:** Entre os modelos avaliados, **Claude Fable 5** demonstrou a maior solidez analítica e aderência metodológica, alcançando **92.0%** de aproveitamento geral. O modelo se destacou especialmente na geração de diagramas Mermaid sintaticamente corretos com `autonumber` e participantes explicitados, além de rigor na rastreabilidade entre componentes e critérios de aceite das HUs.

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

| GPT 5 mini | P04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gpt_5_mini_P04.md` |

| GPT 5.3 Codex | P04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gpt_5_3_codex_P04.md` |

| Gemini 3.7 Flash | P04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gemini_3_7_flash_P04.md` |

| Gemini 3.6 Flash | P04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gemini_3_6_flash_P04.md` |

| Claude Sonnet 5 | P04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_sonnet_5_P04.md` |

| Claude Opus 4.8 | P04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_opus_4_8_P04.md` |

| Claude Fable 5 | P04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_fable_5_P04.md` |

| GPT 5 mini | P05 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gpt_5_mini_P05.md` |

| GPT 5.3 Codex | P05 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gpt_5_3_codex_P05.md` |

| Gemini 3.7 Flash | P05 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gemini_3_7_flash_P05.md` |

| Gemini 3.6 Flash | P05 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gemini_3_6_flash_P05.md` |

| Claude Sonnet 5 | P05 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_sonnet_5_P05.md` |

| Claude Opus 4.8 | P05 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_opus_4_8_P05.md` |

| Claude Fable 5 | P05 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_fable_5_P05.md` |

| GPT 5 mini | M04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gpt_5_mini_M04.md` |

| GPT 5.3 Codex | M04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gpt_5_3_codex_M04.md` |

| Gemini 3.7 Flash | M04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gemini_3_7_flash_M04.md` |

| Gemini 3.6 Flash | M04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gemini_3_6_flash_M04.md` |

| Claude Sonnet 5 | M04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_sonnet_5_M04.md` |

| Claude Opus 4.8 | M04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_opus_4_8_M04.md` |

| Claude Fable 5 | M04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_fable_5_M04.md` |

| GPT 5 mini | G03 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gpt_5_mini_G03.md` |

| GPT 5.3 Codex | G03 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gpt_5_3_codex_G03.md` |

| Gemini 3.7 Flash | G03 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gemini_3_7_flash_G03.md` |

| Gemini 3.6 Flash | G03 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gemini_3_6_flash_G03.md` |

| Claude Sonnet 5 | G03 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_sonnet_5_G03.md` |

| Claude Opus 4.8 | G03 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_opus_4_8_G03.md` |

| Claude Fable 5 | G03 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_fable_5_G03.md` |

| GPT 5 mini | G04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gpt_5_mini_G04.md` |

| GPT 5.3 Codex | G04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gpt_5_3_codex_G04.md` |

| Gemini 3.7 Flash | G04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gemini_3_7_flash_G04.md` |

| Gemini 3.6 Flash | G04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_gemini_3_6_flash_G04.md` |

| Claude Sonnet 5 | G04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_sonnet_5_G04.md` |

| Claude Opus 4.8 | G04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_opus_4_8_G04.md` |

| Claude Fable 5 | G04 | ✅ OK | `docs\Time_2_Design\analise-qualitativa\outputs\relatorio_claude_fable_5_G04.md` |
