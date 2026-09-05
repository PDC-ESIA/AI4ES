# 📊 Relatório de Avaliação Comparativa de LLMs — Agente de Design (AI4ES)

> **Foco:** Avaliação Experimental da Família Gemini (Série 3.x) via GitHub Copilot como Núcleo Cognitivo do Pipeline de Design
> **Data da Análise:** 2026-09-05
> **Protocolo de Referência:** `03. Protocolo de Avaliação Comparativa de Modelos de Linguagem (Agente de Design)`
> **Avaliador Juiz (Cross-Family):** `github_copilot/claude-opus-5` (Mitigação de Self-Enhancement Bias — Seção 6.1)

---

## 1. Sumário Executivo & Ranking Consolidado

O presente estudo executou a avaliação experimental comparativa dos modelos candidatos submetidos ao pipeline completo do Agente de Design (Análise Arquitetural, Diagramação Mermaid, Modularização de Componentes e Síntese de Relatório Canônico) sobre 13 cenário(s) do dataset mockado de requisitos (P01 - Pequeno, P02 - Pequeno, P03 - Pequeno, P04 - Pequeno, P05 - Pequeno, M01 - Médio, M02 - Médio, M03 - Médio, M04 - Médio, G01 - Grande, G02 - Grande, G03 - Grande, G04 - Grande).

### 🏆 Ranking Geral (Média das Rodadas Experimentais)

| Posição | Modelo | Pontuação Média (Máx 30) | Aderência / Qualidade (%) | Desvio Padrão | Latência Média | Validade Mermaid | Rastreabilidade |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 🥇 | **Claude Fable 5** | **27.92/30** | **93.1%** | ±0.49 | 81.46s | 13/13 | 13/13 |
| 🥈 | **Gemini 3.7 Flash** | **26.85/30** | **89.5%** | ±1.28 | 49.82s | 13/13 | 13/13 |
| 🥉 | **Claude Opus 4.8** | **26.77/30** | **89.2%** | ±0.44 | 78.06s | 13/13 | 13/13 |
| 4º | **Claude Sonnet 5** | **26.54/30** | **88.5%** | ±0.78 | 61.24s | 13/13 | 13/13 |
| 5º | **GPT 5 mini** | **25.38/30** | **84.6%** | ±1.26 | 63.44s | 13/13 | 13/13 |
| 6º | **GPT 5.3 Codex** | **25.38/30** | **84.6%** | ±1.04 | 36.7s | 12/13 | 13/13 |
| 7º | **Gemini 3.6 Flash** | **25.23/30** | **84.1%** | ±1.3 | 36.61s | 12/13 | 13/13 |

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
| **Claude Fable 5** | 5/5 | 4/5 | 5/5 | 5/5 | 4.1/5 | 4.8/5 | **27.92/30 (93.1%)** |
| **Gemini 3.7 Flash** | 5/5 | 3.9/5 | 5/5 | 4.5/5 | 3.8/5 | 4.6/5 | **26.85/30 (89.5%)** |
| **Claude Opus 4.8** | 5/5 | 3.9/5 | 5/5 | 4.9/5 | 3.9/5 | 4/5 | **26.77/30 (89.2%)** |
| **Claude Sonnet 5** | 5/5 | 4/5 | 5/5 | 4.8/5 | 3.8/5 | 4/5 | **26.54/30 (88.5%)** |
| **GPT 5 mini** | 5/5 | 3.2/5 | 4.9/5 | 4.8/5 | 3.5/5 | 4/5 | **25.38/30 (84.6%)** |
| **GPT 5.3 Codex** | 5/5 | 3.2/5 | 5/5 | 4.5/5 | 3.7/5 | 4/5 | **25.38/30 (84.6%)** |
| **Gemini 3.6 Flash** | 5/5 | 3.5/5 | 5/5 | 4.1/5 | 3.7/5 | 4/5 | **25.23/30 (84.1%)** |

---

## 3. Detalhamento dos Resultados por Cenário de Teste

### 📦 Cenário P01 — Cardápio Digital para Restaurante (P01) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 27 | 90.0% | 77.27s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 25 | 83.3% | 29.19s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 27 | 90.0% | 36.9s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 25 | 83.3% | 31.54s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 45.11s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 65.95s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 55.55s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário P02 — Agendador de Consultas para Clínica Pequena (P02) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 27 | 90.0% | 37.14s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 27 | 90.0% | 35.03s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 28 | 93.3% | 40.66s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 27 | 90.0% | 33.62s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 46.04s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 76.25s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 74.17s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário P03 — Controle de Estoque para Loja Física (P03) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 26 | 86.7% | 32.38s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 24 | 80.0% | 38.72s | 7/7 (100.0%) | ❌ Inválido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 28 | 93.3% | 36.92s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 22 | 73.3% | 32.13s | 7/7 (100.0%) | ❌ Inválido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 46.63s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 70.06s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 77.83s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário P04 — Biblioteca Pessoal de Livros (P04) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 27 | 90.0% | 63.06s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | graphql |
| **GPT 5.3 Codex** | 25 | 83.3% | 31.33s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 28 | 93.3% | 36.86s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 25 | 83.3% | 27.46s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 26 | 86.7% | 46.26s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 26 | 86.7% | 67.48s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 27 | 90.0% | 58.34s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário P05 — Reservas para Quadras Esportivas (P05) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 26 | 86.7% | 35.57s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 27 | 90.0% | 27.79s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 28 | 93.3% | 42.84s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 31.06s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 54.94s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 65.47s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 29 | 96.7% | 79.85s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário M01 — Plataforma de Cursos Online (M01) (Escopo Médio)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 25 | 83.3% | 50.62s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | graphql |
| **GPT 5.3 Codex** | 25 | 83.3% | 32.62s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 26 | 86.7% | 41.81s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 36.41s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 63.67s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 73.68s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 27 | 90.0% | 64.04s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário M02 — Gestão para Clínica Odontológica (M02) (Escopo Médio)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 25 | 83.3% | 54.63s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 27 | 90.0% | 35.99s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 26 | 86.7% | 66.65s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 32.73s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 64.17s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 84.62s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 83.15s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário M03 — Marketplace de Produtos Artesanais (M03) (Escopo Médio)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 25 | 83.3% | 30.15s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 25 | 83.3% | 42.15s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 28 | 93.3% | 66.78s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | graphql |
| **Gemini 3.6 Flash** | 24 | 80.0% | 33.92s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 69.99s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 26 | 86.7% | 71.15s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 67.36s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário M04 — Sistema de Gestão de Condomínio (M04) (Escopo Médio)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 26 | 86.7% | 50.1s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 25 | 83.3% | 37.67s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 28 | 93.3% | 68.76s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 42.3s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 75.19s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 79.44s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 82.07s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G01 — Sistema Bancário Digital (G01) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 23 | 76.7% | 51.09s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 24 | 80.0% | 35.23s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 25 | 83.3% | 41.22s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 25 | 83.3% | 39.08s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 26 | 86.7% | 75.79s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 26 | 86.7% | 92.0s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 103.58s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G02 — Plataforma de Telemedicina (G02) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 25 | 83.3% | 139.48s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 25 | 83.3% | 42.06s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 25 | 83.3% | 37.59s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 53.06s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 27 | 90.0% | 76.13s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 71.1s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 99.8s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G03 — ERP para Indústria Manufatureira (G03) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 24 | 80.0% | 136.63s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 26 | 86.7% | 49.76s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 25 | 83.3% | 52.44s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 24 | 80.0% | 39.71s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 25 | 83.3% | 64.08s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 92.28s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 108.25s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G04 — Plataforma de Logística e Rastreamento de Cargas (G04) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT 5 mini** | 24 | 80.0% | 66.64s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 25 | 83.3% | 39.54s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.7 Flash** | 27 | 90.0% | 78.27s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 26 | 86.7% | 42.85s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 25 | 83.3% | 68.06s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 27 | 90.0% | 105.24s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Fable 5** | 28 | 93.3% | 104.94s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


---

## 4. Análise Crítica dos Modelos Testados

### 🔍 Claude Fable 5

- **Desempenho Geral:** 27.92/30 pontos (93.1% de conformidade).
- **Latência Média:** 81.46 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa HU→RF→componente→decisão, com tabela de cobertura e status honesto (RNF04 parcial)
  - Identificação madura de lacunas de alto impacto (multi-tenancy, integridade referencial, rate limiting, auditoria) com ações concretas
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de diagramas para HU02 (ordenação de categorias) e HU05 (exclusão com confirmação); 2.2 mistura dois fluxos
  - Não discute trade-offs de persistência compartilhada entre serviços nem estratégia concreta de acessibilidade/compatibilidade além da menção a padrões


### 🔍 Gemini 3.7 Flash

- **Desempenho Geral:** 26.85/30 pontos (89.5% de conformidade).
- **Latência Média:** 49.82 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita e completa de RF/RNF/HU até componentes e mecanismos
  - Decisões arquiteturais bem contextualizadas e proporcionais ao escopo do sistema
- **Oportunidades de Melhoria / Lacunas:**
  - Nomenclatura 'ItensAtivos' na consulta conflita com o requisito de exibir itens indisponíveis
  - Ausência de fluxos de exceção/validação nos diagramas de sequência e tratamento raso do RNF04 (disponibilidade)


### 🔍 Claude Opus 4.8

- **Desempenho Geral:** 26.77/30 pontos (89.2% de conformidade).
- **Latência Média:** 78.06 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa HU→RF/RNF→componente com matriz de cobertura e status parciais honestos
  - Gap analysis profundo, priorizado e com responsáveis por decisão claramente indicados
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de diagramas de sequência para HU02, HU03 e HU05 (incluindo o passo de confirmação de exclusão)
  - Direção de dependência questionável no diagrama de componentes (entidades → repositório) e tratamento superficial de RNF02/RNF04


### 🔍 Claude Sonnet 5

- **Desempenho Geral:** 26.54/30 pontos (88.5% de conformidade).
- **Latência Média:** 61.24 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita HU→RF→componentes e tabela de cobertura com status parcial honesto
  - Gap analysis detalhada e acionável, com responsáveis sugeridos
- **Oportunidades de Melhoria / Lacunas:**
  - Não trata estratégias concretas para RNF02/RNF04 (cache, CDN, redundância), delegando integralmente à infraestrutura
  - Falta cobertura de fluxos de exclusão com confirmação, login e modelo de dados; acoplamento AUTH↔serviços não justificado


### 🔍 GPT 5 mini

- **Desempenho Geral:** 25.38/30 pontos (84.6% de conformidade).
- **Latência Média:** 63.44 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa RF/RNF/HU → componentes em tabelas claras
  - Gap analysis e bloqueios altamente detalhados e acionáveis
  - Neutralidade tecnológica mantida com decisões justificadas por RNFs
- **Oportunidades de Melhoria / Lacunas:**
  - Possível sobre-engenharia (CQRS/read model) para domínio simples, sem análise de alternativa mais leve
  - Poucos diagramas: ausência de modelo de dados e de fluxos de exclusão/indisponibilidade
  - Validações de negócio (campos obrigatórios, preço) tratadas superficialmente na camada de domínio


### 🔍 GPT 5.3 Codex

- **Desempenho Geral:** 25.38/30 pontos (84.6% de conformidade).
- **Latência Média:** 36.7 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita entre HU, RF/RNF e componentes
  - Gap analysis e pendências específicas e acionáveis, com severidade
  - Modelagem correta da indisponibilidade como estado e ordenação de categorias
- **Oportunidades de Melhoria / Lacunas:**
  - Inconsistência entre diagrama de componentes e de sequência (acesso direto ao repositório)
  - Cobertura de diagramas limitada: sem fluxos de exceção nem modelo de domínio
  - Orquestrador genérico como possível ponto de acoplamento central; poucos trade-offs técnicos discutidos


### 🔍 Gemini 3.6 Flash

- **Desempenho Geral:** 25.23/30 pontos (84.1% de conformidade).
- **Latência Média:** 36.61 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade completa HU/RF/RNF com tabela de cobertura por componente
  - Gap analysis acionável com recomendações concretas (ordem_exibicao, bloqueio de exclusão, multi-tenancy)
- **Oportunidades de Melhoria / Lacunas:**
  - Critérios de aceite comportamentais (confirmação de exclusão, validações obrigatórias, atualização imediata) pouco refletidos na arquitetura
  - RNF04 e otimização de leitura tratados de forma superficial, sem cache/CDN/redundância explícitos
  - Ausência de diagramas para fluxos de cadastro/exclusão e leve inconsistência de atribuição do RF05


---

## 5. Respostas Formais às Questões de Pesquisa (QPs do Protocolo)

### **QP1. Quais famílias/modelos apresentam maior aptidão para raciocínio arquitetural, diagramação e modularização?**
> **Resposta:** Entre os modelos avaliados, **Claude Fable 5** demonstrou a maior solidez analítica e aderência metodológica, alcançando **93.1%** de aproveitamento geral. O modelo se destacou especialmente na geração de diagramas Mermaid sintaticamente corretos com `autonumber` e participantes explicitados, além de rigor na rastreabilidade entre componentes e critérios de aceite das HUs.

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

| Gemini 3.7 Flash | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_P01.md` |

| Gemini 3.6 Flash | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_P01.md` |

| Claude Sonnet 5 | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_P01.md` |

| Claude Opus 4.8 | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_P01.md` |

| Claude Fable 5 | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_P01.md` |

| GPT 5 mini | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_P02.md` |

| GPT 5.3 Codex | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_P02.md` |

| Gemini 3.7 Flash | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_P02.md` |

| Gemini 3.6 Flash | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_P02.md` |

| Claude Sonnet 5 | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_P02.md` |

| Claude Opus 4.8 | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_P02.md` |

| Claude Fable 5 | P02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_P02.md` |

| GPT 5 mini | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_P03.md` |

| GPT 5.3 Codex | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_P03.md` |

| Gemini 3.7 Flash | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_P03.md` |

| Gemini 3.6 Flash | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_P03.md` |

| Claude Sonnet 5 | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_P03.md` |

| Claude Opus 4.8 | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_P03.md` |

| Claude Fable 5 | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_P03.md` |

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

| GPT 5 mini | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_M01.md` |

| GPT 5.3 Codex | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_M01.md` |

| Gemini 3.7 Flash | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_M01.md` |

| Gemini 3.6 Flash | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_M01.md` |

| Claude Sonnet 5 | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_M01.md` |

| Claude Opus 4.8 | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_M01.md` |

| Claude Fable 5 | M01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_M01.md` |

| GPT 5 mini | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_M02.md` |

| GPT 5.3 Codex | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_M02.md` |

| Gemini 3.7 Flash | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_M02.md` |

| Gemini 3.6 Flash | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_M02.md` |

| Claude Sonnet 5 | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_M02.md` |

| Claude Opus 4.8 | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_M02.md` |

| Claude Fable 5 | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_M02.md` |

| GPT 5 mini | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_M03.md` |

| GPT 5.3 Codex | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_M03.md` |

| Gemini 3.7 Flash | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_M03.md` |

| Gemini 3.6 Flash | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_M03.md` |

| Claude Sonnet 5 | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_M03.md` |

| Claude Opus 4.8 | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_M03.md` |

| Claude Fable 5 | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_M03.md` |

| GPT 5 mini | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_M04.md` |

| GPT 5.3 Codex | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_M04.md` |

| Gemini 3.7 Flash | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_M04.md` |

| Gemini 3.6 Flash | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_M04.md` |

| Claude Sonnet 5 | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_M04.md` |

| Claude Opus 4.8 | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_M04.md` |

| Claude Fable 5 | M04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_M04.md` |

| GPT 5 mini | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_G01.md` |

| GPT 5.3 Codex | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_G01.md` |

| Gemini 3.7 Flash | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_G01.md` |

| Gemini 3.6 Flash | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_G01.md` |

| Claude Sonnet 5 | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_G01.md` |

| Claude Opus 4.8 | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_G01.md` |

| Claude Fable 5 | G01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_G01.md` |

| GPT 5 mini | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_G02.md` |

| GPT 5.3 Codex | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_G02.md` |

| Gemini 3.7 Flash | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_G02.md` |

| Gemini 3.6 Flash | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_G02.md` |

| Claude Sonnet 5 | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_G02.md` |

| Claude Opus 4.8 | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_G02.md` |

| Claude Fable 5 | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_G02.md` |

| GPT 5 mini | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_G03.md` |

| GPT 5.3 Codex | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_G03.md` |

| Gemini 3.7 Flash | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_G03.md` |

| Gemini 3.6 Flash | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_G03.md` |

| Claude Sonnet 5 | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_G03.md` |

| Claude Opus 4.8 | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_G03.md` |

| Claude Fable 5 | G03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_G03.md` |

| GPT 5 mini | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_G04.md` |

| GPT 5.3 Codex | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_G04.md` |

| Gemini 3.7 Flash | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_G04.md` |

| Gemini 3.6 Flash | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_G04.md` |

| Claude Sonnet 5 | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_G04.md` |

| Claude Opus 4.8 | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_G04.md` |

| Claude Fable 5 | G04 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_fable_5_G04.md` |
