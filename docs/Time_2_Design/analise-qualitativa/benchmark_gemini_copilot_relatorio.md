# 📊 Relatório de Avaliação Comparativa de LLMs — Agente de Design (AI4ES)

> **Foco:** Avaliação Experimental da Família Gemini (Série 3.x) via GitHub Copilot como Núcleo Cognitivo do Pipeline de Design
> **Data da Análise:** 2026-09-10
> **Protocolo de Referência:** `03. Protocolo de Avaliação Comparativa de Modelos de Linguagem (Agente de Design)`
> **Avaliador Juiz (Cross-Family):** `github_copilot/claude-opus-5` (Mitigação de Self-Enhancement Bias — Seção 6.1)

---

## 1. Sumário Executivo & Ranking Consolidado

O presente estudo executou a avaliação experimental comparativa dos modelos candidatos submetidos ao pipeline completo do Agente de Design (Análise Arquitetural, Diagramação Mermaid, Modularização de Componentes e Síntese de Relatório Canônico) sobre 13 cenário(s) do dataset mockado de requisitos (P01 - Pequeno, P02 - Pequeno, P03 - Pequeno, P04 - Pequeno, P05 - Pequeno, M01 - Médio, M02 - Médio, M03 - Médio, M04 - Médio, G01 - Grande, G02 - Grande, G03 - Grande, G04 - Grande).

### 🏆 Ranking Geral (Média das Rodadas Experimentais)

| Posição | Modelo | Pontuação Média (Máx 30) | Aderência / Qualidade (%) | Desvio Padrão | Latência Média | Validade Mermaid | Rastreabilidade |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 🥇 | **GPT 6 Astra** | **28.77/30** | **95.9%** | ±0.83 | 177.49s | 12/13 | 13/13 |
| 🥈 | **Claude Fable 5** | **27.23/30** | **90.7%** | ±1.96 | 79.42s | 12/13 | 13/13 |
| 🥉 | **Claude Opus 4.8** | **26.92/30** | **89.7%** | ±0.76 | 77.23s | 13/13 | 13/13 |
| 4º | **Gemini 3.7 Flash** | **26.77/30** | **89.2%** | ±1.59 | 46.36s | 12/13 | 13/13 |
| 5º | **Claude Sonnet 5** | **26.08/30** | **86.9%** | ±0.95 | 60.76s | 13/13 | 13/13 |
| 6º | **GPT 5.3 Codex** | **26/30** | **86.7%** | ±1.35 | 34.4s | 13/13 | 13/13 |
| 7º | **Gemini 3.6 Flash** | **24.85/30** | **82.8%** | ±1.14 | 47.4s | 12/13 | 13/13 |
| 8º | **GPT 5 mini** | **24.38/30** | **81.3%** | ±1.56 | 74.65s | 13/13 | 13/13 |

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
| **GPT 6 Astra** | 5/5 | 3.8/5 | 5/5 | 5/5 | 5/5 | 5/5 | **28.77/30 (95.9%)** |
| **Claude Fable 5** | 5/5 | 3.7/5 | 4.9/5 | 4.8/5 | 4/5 | 4.8/5 | **27.23/30 (90.7%)** |
| **Claude Opus 4.8** | 5/5 | 4/5 | 5/5 | 4.9/5 | 3.9/5 | 4.1/5 | **26.92/30 (89.7%)** |
| **Gemini 3.7 Flash** | 5/5 | 3.9/5 | 5/5 | 4.5/5 | 3.9/5 | 4.5/5 | **26.77/30 (89.2%)** |
| **Claude Sonnet 5** | 5/5 | 3.9/5 | 5/5 | 4.7/5 | 3.5/5 | 4/5 | **26.08/30 (86.9%)** |
| **GPT 5.3 Codex** | 5/5 | 3.6/5 | 5/5 | 4.5/5 | 3.8/5 | 4.2/5 | **26/30 (86.7%)** |
| **Gemini 3.6 Flash** | 5/5 | 3.2/5 | 5/5 | 4.1/5 | 3.5/5 | 4/5 | **24.85/30 (82.8%)** |
| **GPT 5 mini** | 5/5 | 2.5/5 | 4.9/5 | 4.5/5 | 3.5/5 | 3.9/5 | **24.38/30 (81.3%)** |

---

## 3. Detalhamento dos Resultados por Cenário de Teste

### 📦 Cenário P01 — Cardápio Digital para Restaurante (P01) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 26 | 86.7% | 84.86s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 25 | 83.3% | 28.02s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 6 Astra** | 29 | 96.7% | 145.72s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 28 | 93.3% | 41.3s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 31.3s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 45.85s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 28 | 93.3% | 68.17s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 27 | 90.0% | 52.32s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário P02 — Agendador de Consultas para Clínica Pequena (P02) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 26 | 86.7% | 62.12s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 28 | 93.3% | 34.55s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 6 Astra** | 29 | 96.7% | 123.11s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 28 | 93.3% | 37.4s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 23 | 76.7% | 165.66s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 49.13s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 72.22s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 21 | 70.0% | 61.32s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário P03 — Controle de Estoque para Loja Física (P03) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 26 | 86.7% | 41.1s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 28 | 93.3% | 31.08s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 6 Astra** | 29 | 96.7% | 153.32s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 28 | 93.3% | 41.16s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 24 | 80.0% | 29.49s | 7/7 (100.0%) | ❌ Inválido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 48.39s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 28 | 93.3% | 80.17s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 26 | 86.7% | 84.17s | 7/7 (100.0%) | ❌ Inválido | ✅ Presente | 0 |


### 📦 Cenário P04 — Biblioteca Pessoal de Livros (P04) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 25 | 83.3% | 42.81s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 25 | 83.3% | 32.85s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 6 Astra** | 29 | 96.7% | 134.23s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 28 | 93.3% | 47.36s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 28.98s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 26 | 86.7% | 56.86s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 71.29s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 59.17s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário P05 — Reservas para Quadras Esportivas (P05) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 26 | 86.7% | 37.37s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 26 | 86.7% | 30.06s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 6 Astra** | 29 | 96.7% | 166.78s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 29 | 96.7% | 46.91s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 40.42s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 51.16s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 63.93s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 64.1s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário M01 — Plataforma de Cursos Online (M01) (Escopo Médio)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 24 | 80.0% | 82.63s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 27 | 90.0% | 27.0s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 6 Astra** | 29 | 96.7% | 145.43s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 27 | 90.0% | 36.03s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 33.16s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 57.12s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 61.5s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 67.17s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário M02 — Gestão para Clínica Odontológica (M02) (Escopo Médio)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 23 | 76.7% | 78.7s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 27 | 90.0% | 34.55s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 6 Astra** | 29 | 96.7% | 178.53s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 27 | 90.0% | 36.62s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 24 | 80.0% | 37.22s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 26 | 86.7% | 58.03s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 86.83s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 75.39s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário M03 — Marketplace de Produtos Artesanais (M03) (Escopo Médio)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 25 | 83.3% | 84.98s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 27 | 90.0% | 37.17s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 6 Astra** | 29 | 96.7% | 183.39s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 26 | 86.7% | 56.46s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 25 | 83.3% | 38.76s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 26 | 86.7% | 60.15s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 26 | 86.7% | 67.23s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 70.26s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário M04 — Sistema de Gestão de Condomínio (M04) (Escopo Médio)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 23 | 76.7% | 62.83s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | graphql |
| **GPT 5.3 Codex** | 24 | 80.0% | 35.61s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 6 Astra** | 29 | 96.7% | 197.74s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 27 | 90.0% | 74.13s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 23 | 76.7% | 43.76s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 26 | 86.7% | 69.53s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 84.36s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 88.59s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G01 — Sistema Bancário Digital (G01) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 23 | 76.7% | 74.77s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 26 | 86.7% | 36.8s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 6 Astra** | 26 | 86.7% | 188.5s | 7/7 (100.0%) | ❌ Inválido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 26 | 86.7% | 39.72s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 45.14s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 25 | 83.3% | 67.25s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 80.42s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 107.84s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G02 — Plataforma de Telemedicina (G02) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 21 | 70.0% | 47.7s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 24 | 80.0% | 36.67s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 6 Astra** | 29 | 96.7% | 218.19s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 26 | 86.7% | 46.01s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 24 | 80.0% | 39.38s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 25 | 83.3% | 83.05s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 85.19s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 105.99s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G03 — ERP para Indústria Manufatureira (G03) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 24 | 80.0% | 186.34s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 25 | 83.3% | 40.95s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 6 Astra** | 29 | 96.7% | 258.01s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 25 | 83.3% | 45.69s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 25 | 83.3% | 40.82s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 24 | 80.0% | 67.66s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 99.03s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 96.55s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G04 — Plataforma de Logística e Rastreamento de Cargas (G04) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 25 | 83.3% | 84.18s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 26 | 86.7% | 41.88s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 6 Astra** | 29 | 96.7% | 214.42s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 23 | 76.7% | 53.94s | 7/7 (100.0%) | ❌ Inválido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 25 | 83.3% | 42.08s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 26 | 86.7% | 75.66s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 25 | 83.3% | 83.69s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 99.65s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


---

## 4. Análise Crítica dos Modelos Testados

### 🔍 GPT 6 Astra

- **Desempenho Geral:** 28.77/30 pontos (95.9% de conformidade).
- **Latência Média:** 177.49 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa e explícita de RF/RNF/HU para componentes com situação de cobertura honesta
  - Gap analysis acionável com priorização, responsáveis e critérios de verificação mensuráveis (ex.: fórmula de disponibilidade)
  - Modularidade com portas explícitas e separação clara público/administrativo
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de diagramas adicionais (dados/implantação) e sequência única muito densa
  - Alto volume de pendências pode postergar decisões triviais que poderiam ser propostas como default reversível
  - Nenhuma proposta tecnológica ou de deployment, limitando a acionabilidade imediata para o time


### 🔍 Claude Fable 5

- **Desempenho Geral:** 27.23/30 pontos (90.7% de conformidade).
- **Latência Média:** 79.42 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa HU→RF→componente com tabela de cobertura
  - Gap analysis profunda e acionável, incluindo trade-off cache vs consistência imediata
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de fluxos de exceção/erro nos diagramas e nas decisões
  - Aresta AUTH→Serviços no diagrama de componentes é logicamente ambígua; estratégias de RNF02/RNF04 pouco concretas


### 🔍 Claude Opus 4.8

- **Desempenho Geral:** 26.92/30 pontos (89.7% de conformidade).
- **Latência Média:** 77.23 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa e explícita entre HU, RF, RNF, decisões e componentes
  - Gap analysis profunda e acionável, incluindo concorrência e invalidação de cache
  - Separação clara entre zona pública sem autenticação e zona administrativa protegida
  - Diagrama de estados captura corretamente o ciclo de disponibilidade
- **Oportunidades de Melhoria / Lacunas:**
  - Inconsistência de camadas: Domínio chamando Repositório e Publicação acessando Repositório diretamente
  - RNF02 e RNF04 sem estratégia arquitetural concreta (apenas adiados para infraestrutura)
  - Ausência de diagramas de sequência para remoção com confirmação e falha de autenticação
  - Modelo de dados/entidades não detalhado (atributos, restrições) além de menção textual


### 🔍 Gemini 3.7 Flash

- **Desempenho Geral:** 26.77/30 pontos (89.2% de conformidade).
- **Latência Média:** 46.36 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa HU→RF/RNF→componente com matriz de cobertura integral
  - Gap analysis perspicaz, especialmente o conflito cache×atualização imediata e opacidade×WCAG
  - Separação limpa entre fronteira pública e administrativa, adequada ao porte do sistema
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de cenários de exceção/erro nos diagramas de sequência
  - RNF04 (disponibilidade 99%) tratado de forma genérica, sem estratégia concreta de redundância ou observabilidade
  - Leve sobreposição de responsabilidades entre serviços de catálogo e de categorias quanto a RF05


### 🔍 Claude Sonnet 5

- **Desempenho Geral:** 26.08/30 pontos (86.9% de conformidade).
- **Latência Média:** 60.76 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita e consistente entre HU, RF, RNF, decisões e componentes
  - Gap analysis e pendências profundos, acionáveis e com responsáveis sugeridos
  - Honestidade ao marcar RNF02/RNF04 como cobertura parcial dependente de infraestrutura
  - Diagrama de sequência com caminho de exceção (validação inválida)
- **Oportunidades de Melhoria / Lacunas:**
  - Serviço de Disponibilidade como componente separado é granularidade excessiva para um atributo de estado
  - Notificação ao Serviço de Consulta Pública sugere cache/CQRS não explicitado, com risco de conflito com o critério de atualização imediata
  - Ausência de diagrama de fluxos de exclusão/indisponibilidade e de modelo de dados
  - Critério de confirmação antes da exclusão (HU05) e regras de remoção de categoria com itens associados não tratados


### 🔍 GPT 5.3 Codex

- **Desempenho Geral:** 26/30 pontos (86.7% de conformidade).
- **Latência Média:** 34.4 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita e completa entre HUs, RFs, RNFs e componentes
  - Separação clara entre domínio administrativo autenticado e consulta pública anônima
  - Pendências e gaps acionáveis, com status 'Parcial' honesto para RNFs dependentes de operação
- **Oportunidades de Melhoria / Lacunas:**
  - Erro de sintaxe Mermaid (parênteses em rótulo de nó) que pode impedir renderização
  - Ausência de fluxos de exceção nos diagramas de sequência e de segundo cenário (exclusão/login)
  - Trade-offs arquiteturais superficiais; sem discussão de cache, HA, ou impacto do banco compartilhado entre serviços


### 🔍 Gemini 3.6 Flash

- **Desempenho Geral:** 24.85/30 pontos (82.8% de conformidade).
- **Latência Média:** 47.4 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade forte e bidirecional entre HU, RF, RNF e componentes, com cobertura tabulada completa
  - Separação arquitetural pertinente entre fluxo público de leitura e fluxo administrativo autenticado, com ADRs justificadas
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de cenários de exceção nos diagramas e de discussão do trade-off cache vs. atualização imediata do cardápio
  - Estratégias para RNF02/RNF04 declaradas de forma genérica, sem mecanismos concretos (invalidação de cache, redundância, monitoramento)


### 🔍 GPT 5 mini

- **Desempenho Geral:** 24.38/30 pontos (81.3% de conformidade).
- **Latência Média:** 74.65 segundos por pipeline completo.
- **Pontos Fortes:**
  - Gap analysis priorizada, com impacto e ação recomendada por lacuna
  - Rastreabilidade completa RF/RNF/HU → componentes e trade-offs explícitos por decisão
- **Oportunidades de Melhoria / Lacunas:**
  - Prováveis erros de sintaxe Mermaid (parênteses em rótulos, subgraphs sem aspas) e ausência de fluxo do cliente
  - Inconsistências de camada (AdminAPI→Repo), sobreposição Menu/CategoryService e ausência de modelo de dados/regra de cardinalidade item-categoria


---

## 5. Respostas Formais às Questões de Pesquisa (QPs do Protocolo)

### **QP1. Quais famílias/modelos apresentam maior aptidão para raciocínio arquitetural, diagramação e modularização?**
> **Resposta:** Entre os modelos avaliados, **GPT 6 Astra** demonstrou a maior solidez analítica e aderência metodológica, alcançando **95.9%** de aproveitamento geral. O modelo se destacou especialmente na geração de diagramas Mermaid sintaticamente corretos com `autonumber` e participantes explicitados, além de rigor na rastreabilidade entre componentes e critérios de aceite das HUs.

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

| GPT 5 mini | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_P01.md` |

| GPT 5.3 Codex | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_P01.md` |

| GPT 6 Astra | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_6_astra_P01.md` |

| Gemini 3.7 Flash | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_P01.md` |

| Gemini 3.6 Flash | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_P01.md` |

| Claude Sonnet 5 | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_P01.md` |

| Claude Opus 4.8 | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_P01.md` |

| Claude Fable 5 | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_P01.md` |

| GPT 5 mini | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_P02.md` |

| GPT 5.3 Codex | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_P02.md` |

| GPT 6 Astra | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_6_astra_P02.md` |

| Gemini 3.7 Flash | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_P02.md` |

| Gemini 3.6 Flash | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_P02.md` |

| Claude Sonnet 5 | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_P02.md` |

| Claude Opus 4.8 | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_P02.md` |

| Claude Fable 5 | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_P02.md` |

| GPT 5 mini | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_P03.md` |

| GPT 5.3 Codex | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_P03.md` |

| GPT 6 Astra | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_6_astra_P03.md` |

| Gemini 3.7 Flash | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_P03.md` |

| Gemini 3.6 Flash | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_P03.md` |

| Claude Sonnet 5 | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_P03.md` |

| Claude Opus 4.8 | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_P03.md` |

| Claude Fable 5 | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_P03.md` |

| GPT 5 mini | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_P04.md` |

| GPT 5.3 Codex | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_P04.md` |

| GPT 6 Astra | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_6_astra_P04.md` |

| Gemini 3.7 Flash | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_P04.md` |

| Gemini 3.6 Flash | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_P04.md` |

| Claude Sonnet 5 | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_P04.md` |

| Claude Opus 4.8 | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_P04.md` |

| Claude Fable 5 | P04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_P04.md` |

| GPT 5 mini | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_P05.md` |

| GPT 5.3 Codex | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_P05.md` |

| GPT 6 Astra | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_6_astra_P05.md` |

| Gemini 3.7 Flash | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_P05.md` |

| Gemini 3.6 Flash | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_P05.md` |

| Claude Sonnet 5 | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_P05.md` |

| Claude Opus 4.8 | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_P05.md` |

| Claude Fable 5 | P05 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_P05.md` |

| GPT 5 mini | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_M01.md` |

| GPT 5.3 Codex | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_M01.md` |

| GPT 6 Astra | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_6_astra_M01.md` |

| Gemini 3.7 Flash | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_M01.md` |

| Gemini 3.6 Flash | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_M01.md` |

| Claude Sonnet 5 | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_M01.md` |

| Claude Opus 4.8 | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_M01.md` |

| Claude Fable 5 | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_M01.md` |

| GPT 5 mini | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_M02.md` |

| GPT 5.3 Codex | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_M02.md` |

| GPT 6 Astra | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_6_astra_M02.md` |

| Gemini 3.7 Flash | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_M02.md` |

| Gemini 3.6 Flash | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_M02.md` |

| Claude Sonnet 5 | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_M02.md` |

| Claude Opus 4.8 | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_M02.md` |

| Claude Fable 5 | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_M02.md` |

| GPT 5 mini | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_M03.md` |

| GPT 5.3 Codex | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_M03.md` |

| GPT 6 Astra | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_6_astra_M03.md` |

| Gemini 3.7 Flash | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_M03.md` |

| Gemini 3.6 Flash | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_M03.md` |

| Claude Sonnet 5 | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_M03.md` |

| Claude Opus 4.8 | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_M03.md` |

| Claude Fable 5 | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_M03.md` |

| GPT 5 mini | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_M04.md` |

| GPT 5.3 Codex | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_M04.md` |

| GPT 6 Astra | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_6_astra_M04.md` |

| Gemini 3.7 Flash | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_M04.md` |

| Gemini 3.6 Flash | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_M04.md` |

| Claude Sonnet 5 | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_M04.md` |

| Claude Opus 4.8 | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_M04.md` |

| Claude Fable 5 | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_M04.md` |

| GPT 5 mini | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_G01.md` |

| GPT 5.3 Codex | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_G01.md` |

| GPT 6 Astra | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_6_astra_G01.md` |

| Gemini 3.7 Flash | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_G01.md` |

| Gemini 3.6 Flash | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_G01.md` |

| Claude Sonnet 5 | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_G01.md` |

| Claude Opus 4.8 | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_G01.md` |

| Claude Fable 5 | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_G01.md` |

| GPT 5 mini | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_G02.md` |

| GPT 5.3 Codex | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_G02.md` |

| GPT 6 Astra | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_6_astra_G02.md` |

| Gemini 3.7 Flash | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_G02.md` |

| Gemini 3.6 Flash | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_G02.md` |

| Claude Sonnet 5 | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_G02.md` |

| Claude Opus 4.8 | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_G02.md` |

| Claude Fable 5 | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_G02.md` |

| GPT 5 mini | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_G03.md` |

| GPT 5.3 Codex | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_G03.md` |

| GPT 6 Astra | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_6_astra_G03.md` |

| Gemini 3.7 Flash | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_G03.md` |

| Gemini 3.6 Flash | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_G03.md` |

| Claude Sonnet 5 | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_G03.md` |

| Claude Opus 4.8 | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_G03.md` |

| Claude Fable 5 | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_G03.md` |

| GPT 5 mini | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_G04.md` |

| GPT 5.3 Codex | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_G04.md` |

| GPT 6 Astra | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_6_astra_G04.md` |

| Gemini 3.7 Flash | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_G04.md` |

| Gemini 3.6 Flash | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_G04.md` |

| Claude Sonnet 5 | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_G04.md` |

| Claude Opus 4.8 | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_G04.md` |

| Claude Fable 5 | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_G04.md` |
