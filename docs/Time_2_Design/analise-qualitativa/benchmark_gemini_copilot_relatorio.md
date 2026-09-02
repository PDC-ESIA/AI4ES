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
| 🥇 | **Claude Fable 5** | **28.25/30** | **94.2%** | ±0.5 | 98.67s | 4/4 | 4/4 |
| 🥈 | **Claude Opus 4.8** | **26.6/30** | **88.7%** | ±0.89 | 115.5s | 5/5 | 5/5 |
| 🥉 | **Gemini 3.7 Flash** | **26.4/30** | **88.0%** | ±1.52 | 58.15s | 5/5 | 5/5 |
| 4º | **Gemini 3.6 Flash** | **25.8/30** | **86.0%** | ±1.48 | 51.38s | 5/5 | 5/5 |
| 5º | **Claude Sonnet 5** | **25.8/30** | **86.0%** | ±0.84 | 57.52s | 5/5 | 5/5 |
| 6º | **GPT 5.3 Codex** | **25.6/30** | **85.3%** | ±0.55 | 32.3s | 5/5 | 5/5 |
| 7º | **GPT 5 mini** | **24.4/30** | **81.3%** | ±1.67 | 97.75s | 5/5 | 5/5 |

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
| **Claude Fable 5** | 5/5 | 4/5 | 5/5 | 5/5 | 4.2/5 | 5/5 | **28.25/30 (94.2%)** |
| **Claude Opus 4.8** | 5/5 | 4/5 | 5/5 | 4.8/5 | 3.8/5 | 4/5 | **26.6/30 (88.7%)** |
| **Gemini 3.7 Flash** | 5/5 | 4/5 | 5/5 | 4.4/5 | 3.6/5 | 4.4/5 | **26.4/30 (88.0%)** |
| **Gemini 3.6 Flash** | 5/5 | 3.6/5 | 5/5 | 4/5 | 4/5 | 4.2/5 | **25.8/30 (86.0%)** |
| **Claude Sonnet 5** | 5/5 | 4/5 | 5/5 | 4.4/5 | 3.4/5 | 4/5 | **25.8/30 (86.0%)** |
| **GPT 5.3 Codex** | 5/5 | 3.8/5 | 5/5 | 4/5 | 3.8/5 | 4/5 | **25.6/30 (85.3%)** |
| **GPT 5 mini** | 5/5 | 3/5 | 4.8/5 | 4.2/5 | 3.4/5 | 4/5 | **24.4/30 (81.3%)** |

---

## 3. Detalhamento dos Resultados por Cenário de Teste

### 📦 Cenário P04 — Biblioteca Pessoal de Livros (P04) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 24 | 80.0% | 224.74s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | graphql |
| **GPT 5.3 Codex** | 26 | 86.7% | 27.35s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 26 | 86.7% | 38.63s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 40.13s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 26 | 86.7% | 49.21s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 65.03s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 29 | 96.7% | 62.92s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário P05 — Reservas para Quadras Esportivas (P05) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 27 | 90.0% | 63.33s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 26 | 86.7% | 30.74s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 28 | 93.3% | 48.4s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 24 | 80.0% | 41.96s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 51.84s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 71.67s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 66.67s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário M04 — Sistema de Gestão de Condomínio (M04) (Escopo Médio)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 23 | 76.7% | 65.44s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 25 | 83.3% | 30.11s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 28 | 93.3% | 75.95s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 28 | 93.3% | 54.0s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 26 | 86.7% | 54.36s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 80.73s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 84.87s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G03 — ERP para Indústria Manufatureira (G03) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 25 | 83.3% | 87.32s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 26 | 86.7% | 37.47s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 25 | 83.3% | 61.87s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 61.8s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 25 | 83.3% | 67.22s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 25 | 83.3% | 181.34s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G04 — Plataforma de Logística e Rastreamento de Cargas (G04) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 23 | 76.7% | 47.93s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 25 | 83.3% | 35.81s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 25 | 83.3% | 65.88s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 25 | 83.3% | 58.99s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 25 | 83.3% | 64.97s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 178.74s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 180.23s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


---

## 4. Análise Crítica dos Modelos Testados

### 🔍 Claude Fable 5

- **Desempenho Geral:** 28.25/30 pontos (94.2% de conformidade).
- **Latência Média:** 98.67 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa requisito→decisão→componente com tabela de cobertura
  - Gap analysis profunda e acionável, incluindo crítica realista ao RNF03
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de diagramas de sequência para exportação e filtragem/busca
  - Pouca discussão de trade-offs tecnológicos (estilo arquitetural, cache, modelo de dados para agregados)


### 🔍 Claude Opus 4.8

- **Desempenho Geral:** 26.6/30 pontos (88.7% de conformidade).
- **Latência Média:** 115.5 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa HU→RF→RNF→componentes com tabela de cobertura
  - Gap analysis profundo e acionável, incluindo lacunas não óbvias (histórico de status, importação, duplicidade)
- **Oportunidades de Melhoria / Lacunas:**
  - Dependências invertidas no diagrama de componentes (domínio→repositório) e acoplamento cruzado entre serviços de Gênero/Coleção e domínio Livro
  - Ausência de decisões técnicas concretas e trade-offs quantitativos (indexação, paginação, cache) para atender RNF03


### 🔍 Gemini 3.7 Flash

- **Desempenho Geral:** 26.4/30 pontos (88.0% de conformidade).
- **Latência Média:** 58.15 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa RF/RNF/HU→componentes em tabelas claras
  - Decisões arquiteturais justificadas, com destaque para isolamento por usuário e não-cascata de taxonomias
- **Oportunidades de Melhoria / Lacunas:**
  - Multiplicidade Livro–Gênero como 1..* contradiz o critério de desvinculação (livro pode ficar sem gênero)
  - Estratégia de desempenho (RNF03) genérica, sem índices, paginação ou debounce; apenas um diagrama de sequência cobrindo poucos fluxos


### 🔍 Gemini 3.6 Flash

- **Desempenho Geral:** 25.8/30 pontos (86.0% de conformidade).
- **Latência Média:** 51.38 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa HU-RF-RNF-componentes com tabelas de cobertura
  - Decisões arquiteturais justificadas e alinhadas a critérios de aceite (SET NULL, multi-tenancy lógico)
  - Gap analysis acionável com recomendações técnicas concretas
- **Oportunidades de Melhoria / Lacunas:**
  - Contradição entre decisão 'event-driven desacoplado' e fluxo síncrono do diagrama de sequência
  - Mapeamentos imprecisos (HU08 associada a RNF06; ausência de RF02/RF03 em HUs)
  - Ausência de diagrama de dados/entidades e de fluxos de exceção; erro de digitação no título do diagrama


### 🔍 Claude Sonnet 5

- **Desempenho Geral:** 25.8/30 pontos (86.0% de conformidade).
- **Latência Média:** 57.52 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade forte entre HU, RF, RNF, componentes e decisões
  - Modelo de domínio fiel às regras (multi-gênero, coleção única, desvinculação em remoção)
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de diagramas para exportação e edição/remoção; RF02/RF03 pouco explorados
  - UI orquestrando estatísticas e falta de trade-offs técnicos concretos (paginação, indexação, cache)


### 🔍 GPT 5.3 Codex

- **Desempenho Geral:** 25.6/30 pontos (85.3% de conformidade).
- **Latência Média:** 32.3 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita HU → RF/RNF → componentes, com tabela de cobertura e classificação parcial/completa honesta
  - Diagrama de sequência com caminho de exceção (validação) e atualização de resumo, aderente aos critérios de aceite
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de modelo de dados/diagrama de entidades e de estratégias concretas para RNF03 (índices, paginação, debounce na busca)
  - Trade-offs arquiteturais pouco explorados (recomputação vs. contadores incrementais, repositório único vs. repositórios por agregado); diagrama de componentes com retornos inconsistentes


### 🔍 GPT 5 mini

- **Desempenho Geral:** 24.4/30 pontos (81.3% de conformidade).
- **Latência Média:** 97.75 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita HU→RF→Componentes em tabelas claras
  - Gap analysis extensa, priorizada e acionável
  - Modelo de dados fiel às cardinalidades exigidas (N:N gêneros, 0..1 coleção)
- **Oportunidades de Melhoria / Lacunas:**
  - Erros de sintaxe Mermaid no diagrama de componentes que impedem renderização
  - Ausência de fluxos de exceção/erro e de diagrama de implantação
  - Possível sobre-engenharia (índice de busca dedicado, WebSocket) sem análise de trade-off frente a alternativas simples


---

## 5. Respostas Formais às Questões de Pesquisa (QPs do Protocolo)

### **QP1. Quais famílias/modelos apresentam maior aptidão para raciocínio arquitetural, diagramação e modularização?**
> **Resposta:** Entre os modelos avaliados, **Claude Fable 5** demonstrou a maior solidez analítica e aderência metodológica, alcançando **94.2%** de aproveitamento geral. O modelo se destacou especialmente na geração de diagramas Mermaid sintaticamente corretos com `autonumber` e participantes explicitados, além de rigor na rastreabilidade entre componentes e critérios de aceite das HUs.

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
