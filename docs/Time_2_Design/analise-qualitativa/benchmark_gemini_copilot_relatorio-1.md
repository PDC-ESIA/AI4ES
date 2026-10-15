# 📊 Relatório de Avaliação Comparativa de LLMs — Agente de Design (AI4ES)

> **Foco:** Avaliação Experimental da Família Gemini (Série 3.x) via GitHub Copilot como Núcleo Cognitivo do Pipeline de Design
> **Data da Análise:** 2026-09-02
> **Protocolo de Referência:** `03. Protocolo de Avaliação Comparativa de Modelos de Linguagem (Agente de Design)`
> **Avaliador Juiz (Cross-Family):** `github_copilot/claude-opus-5` (Mitigação de Self-Enhancement Bias — Seção 6.1)

---

## 1. Sumário Executivo & Ranking Consolidado

O presente estudo executou a avaliação experimental comparativa dos modelos da família Gemini (Série 3.x, via GitHub Copilot) submetidos ao pipeline completo do Agente de Design (Análise Arquitetural, Diagramação Mermaid, Modularização de Componentes e Síntese de Relatório Canônico) sobre 3 cenários com níveis crescentes de complexidade (P02 - Pequeno, M01 - Médio, G01 - Grande).

### 🏆 Ranking Geral (Média das Rodadas Experimentais)

| Posição | Modelo | Pontuação Média (Máx 30) | Aderência / Qualidade (%) | Desvio Padrão | Latência Média | Validade Mermaid | Rastreabilidade |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 🥇 | **GPT 5.3 Codex** | **22/30** | **73.3%** | ±0.71 | 37.34s | 5/5 | 5/5 |
| 🥈 | **Claude Sonnet 5** | **21.2/30** | **70.7%** | ±1.92 | 50.99s | 5/5 | 5/5 |
| 🥉 | **Claude Opus 4.8** | **21/30** | **70.0%** | ±1.58 | 65.56s | 5/5 | 5/5 |
| 4º | **Gemini 3.7 Flash** | **19.4/30** | **64.7%** | ±2.07 | 50.37s | 5/5 | 5/5 |
| 5º | **Gemini 3.6 Flash** | **18.2/30** | **60.7%** | ±1.64 | 37.56s | 5/5 | 5/5 |
| 6º | **GPT 5 mini** | **12.6/30** | **42.0%** | ±9.04 | 51.07s | 2/5 | 2/5 |

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
| **GPT 5.3 Codex** | 5/5 | 4/5 | 4.8/5 | 1.2/5 | 3.2/5 | 3.8/5 | **22/30 (73.3%)** |
| **Claude Sonnet 5** | 4.4/5 | 3.6/5 | 5/5 | 1.4/5 | 3/5 | 3.8/5 | **21.2/30 (70.7%)** |
| **Claude Opus 4.8** | 4.4/5 | 3.6/5 | 5/5 | 1.2/5 | 3/5 | 3.8/5 | **21/30 (70.0%)** |
| **Gemini 3.7 Flash** | 4.6/5 | 2.6/5 | 4.8/5 | 1/5 | 2.8/5 | 3.6/5 | **19.4/30 (64.7%)** |
| **Gemini 3.6 Flash** | 4/5 | 2.4/5 | 4.6/5 | 1/5 | 3/5 | 3.2/5 | **18.2/30 (60.7%)** |
| **GPT 5 mini** | 2.6/5 | 2/5 | 2.6/5 | 1.2/5 | 2/5 | 2.2/5 | **12.6/30 (42.0%)** |

---

## 3. Detalhamento dos Resultados por Cenário de Teste

### 📦 Cenário P01 — Cardápio Digital para Restaurante (P01) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Gemini 3.7 Flash** | 22 | 73.3% | 49.29s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 20 | 66.7% | 37.19s | 6/7 (85.7%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5 mini** | 23 | 76.7% | 46.87s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | graphql |
| **GPT 5.3 Codex** | 21 | 70.0% | 50.43s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 22 | 73.3% | 47.46s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 22 | 73.3% | 58.09s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário P03 — Controle de Estoque para Loja Física (P03) (Escopo Pequeno)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Gemini 3.7 Flash** | 21 | 70.0% | 44.79s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 20 | 66.7% | 37.72s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5 mini** | 22 | 73.3% | 34.54s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5.3 Codex** | 23 | 76.7% | 30.2s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 23 | 76.7% | 49.67s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 23 | 76.7% | 67.96s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário M02 — Gestão para Clínica Odontológica (M02) (Escopo Médio)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Gemini 3.7 Flash** | 19 | 63.3% | 51.89s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 17 | 56.7% | 36.38s | 5/7 (71.4%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5 mini** | 6 | 20.0% | 87.64s | 0/7 (0.0%) | ❌ Inválido | ⚠️ Ausente | 0 |
| **GPT 5.3 Codex** | 22 | 73.3% | 33.36s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 18 | 60.0% | 53.46s | 6/7 (85.7%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 19 | 63.3% | 68.65s | 5/7 (71.4%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário M03 — Marketplace de Produtos Artesanais (M03) (Escopo Médio)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Gemini 3.7 Flash** | 17 | 56.7% | 51.56s | 6/7 (85.7%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 17 | 56.7% | 35.19s | 6/7 (85.7%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5 mini** | 6 | 20.0% | 48.86s | 0/7 (0.0%) | ❌ Inválido | ⚠️ Ausente | 0 |
| **GPT 5.3 Codex** | 22 | 73.3% | 33.81s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 22 | 73.3% | 52.33s | 6/7 (85.7%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 20 | 66.7% | 66.62s | 6/7 (85.7%) | ✅ Válido | ✅ Presente | 0 |


### 📦 Cenário G02 — Plataforma de Telemedicina (G02) (Escopo Grande)

| Modelo | Pontuação (30) | % | Latência (s) | Aderência Template | Mermaid Válido | Rastreabilidade | Violações Neutralidade |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Gemini 3.7 Flash** | 18 | 60.0% | 54.3s | 6/7 (85.7%) | ✅ Válido | ✅ Presente | 0 |
| **Gemini 3.6 Flash** | 17 | 56.7% | 41.33s | 4/7 (57.1%) | ✅ Válido | ✅ Presente | 0 |
| **GPT 5 mini** | 6 | 20.0% | 37.42s | 0/7 (0.0%) | ❌ Inválido | ⚠️ Ausente | 0 |
| **GPT 5.3 Codex** | 22 | 73.3% | 38.92s | 7/7 (100.0%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Sonnet 5** | 21 | 70.0% | 52.01s | 6/7 (85.7%) | ✅ Válido | ✅ Presente | 0 |
| **Claude Opus 4.8** | 21 | 70.0% | 66.47s | 6/7 (85.7%) | ✅ Válido | ✅ Presente | 0 |


---

## 4. Análise Crítica dos Modelos Testados

### 🔍 GPT 5.3 Codex

- **Desempenho Geral:** 22/30 pontos (73.3% de conformidade).
- **Latência Média:** 37.34 segundos por pipeline completo.
- **Pontos Fortes:**
  - Matriz de rastreabilidade HU × RF × RNF clara e consistente
  - Diagrama de sequência abrangente cobrindo o ciclo completo admin→publicação→cliente
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência total de análise de lacunas e recomendações; documento truncado na decisão 7
  - Sobre-engenharia (separação leitura/escrita e serviço de publicação) sem justificativa e sem tratamento de cenários de exceção/consistência


### 🔍 Claude Sonnet 5

- **Desempenho Geral:** 21.2/30 pontos (70.7% de conformidade).
- **Latência Média:** 50.99 segundos por pipeline completo.
- **Pontos Fortes:**
  - Matriz de rastreabilidade HU→RF→RNF e tabela de decisões justificadas
  - Separação clara entre canal público anônimo e administrativo autenticado, coerente com RF08/RNF03
  - Diagrama de sequência com cenário alternativo de validação
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência total de gap analysis, riscos e recomendações acionáveis
  - Sem discussão de trade-offs (monolito modular vs. serviços, cache/CDN para RNF02 e RNF04)
  - Relatório truncado e presença de critérios inferidos não presentes nos requisitos
  - Nenhum modelo de dados/entidades apesar das regras de associação item-categoria e ordenação


### 🔍 Claude Opus 4.8

- **Desempenho Geral:** 21/30 pontos (70.0% de conformidade).
- **Latência Média:** 65.56 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita HU→RF/RNF e decisões com requisito de origem
  - Diagramas Mermaid corretos e coerentes, incluindo fluxo alternativo de validação
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência total de gap analysis e recomendações
  - Relatório truncado e trade-offs/aspectos de RNF02/RNF04 (cache, deploy, monitoramento) pouco explorados


### 🔍 Gemini 3.7 Flash

- **Desempenho Geral:** 19.4/30 pontos (64.7% de conformidade).
- **Latência Média:** 50.37 segundos por pipeline completo.
- **Pontos Fortes:**
  - Matriz de rastreabilidade HU → RF/RNF completa e coerente
  - Separação clara entre acesso público anônimo e área administrativa autenticada, com modelo de domínio que distingue disponibilidade de exclusão lógica
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência total de análise de gaps, riscos e recomendações acionáveis
  - Nenhum tratamento de fluxos de exceção/validação e ausência de decisões para RNF02 (desempenho) e RNF04 (disponibilidade), além do relatório estar truncado


### 🔍 Gemini 3.6 Flash

- **Desempenho Geral:** 18.2/30 pontos (60.7% de conformidade).
- **Latência Média:** 37.56 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade explícita HU → RF → RNF → critérios de aceite em tabela completa
  - Separação clara entre caminho público (leitura/cache) e administrativo (escrita/autenticação), com invalidação de cache modelada
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência total de gap analysis, riscos e recomendações acionáveis
  - Diagrama de sequência público truncado e sintaxe de quebra de linha potencialmente inválida; falta de modelo de dados e de discussão de trade-offs (cache vs. atualização imediata)


### 🔍 GPT 5 mini

- **Desempenho Geral:** 12.6/30 pontos (42.0% de conformidade).
- **Latência Média:** 51.07 segundos por pipeline completo.
- **Pontos Fortes:**
  - Rastreabilidade clara entre decisões arquiteturais e HUs/RFs/RNFs
  - Separação leitura/escrita com cache justificada por desempenho e independência de escala
- **Oportunidades de Melhoria / Lacunas:**
  - Ausência de análise de lacunas e trade-offs aprofundados; recomendações pouco acionáveis
  - Erro de sintaxe potencial no diagrama de componentes Mermaid e ausência de fluxos de exceção


---

## 5. Respostas Formais às Questões de Pesquisa (QPs do Protocolo)

### **QP1. Quais famílias/modelos apresentam maior aptidão para raciocínio arquitetural, diagramação e modularização?**
> **Resposta:** Na família Gemini (Série 3.x), o modelo **GPT 5.3 Codex** demonstrou a maior solidez analítica e aderência metodológica, alcançando **73.3%** de aproveitamento geral. O modelo se destacou especialmente na geração de diagramas Mermaid sintaticamente corretos com `autonumber` e participantes explicitados, além de rigor na rastreabilidade entre componentes e critérios de aceite das HUs.

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
| Gemini 3.7 Flash | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_P01.md` |
| Gemini 3.6 Flash | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_P01.md` |
| GPT 5 mini | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_P01.md` |
| GPT 5.3 Codex | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_P01.md` |
| Claude Sonnet 5 | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_P01.md` |
| Claude Opus 4.8 | P01 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_P01.md` |
| Gemini 3.7 Flash | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_P03.md` |
| Gemini 3.6 Flash | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_P03.md` |
| GPT 5 mini | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_P03.md` |
| GPT 5.3 Codex | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_P03.md` |
| Claude Sonnet 5 | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_P03.md` |
| Claude Opus 4.8 | P03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_P03.md` |
| Gemini 3.7 Flash | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_M02.md` |
| Gemini 3.6 Flash | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_M02.md` |
| GPT 5 mini | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_M02.md` |
| GPT 5.3 Codex | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_M02.md` |
| Claude Sonnet 5 | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_M02.md` |
| Claude Opus 4.8 | M02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_M02.md` |
| Gemini 3.7 Flash | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_M03.md` |
| Gemini 3.6 Flash | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_M03.md` |
| GPT 5 mini | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_M03.md` |
| GPT 5.3 Codex | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_M03.md` |
| Claude Sonnet 5 | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_M03.md` |
| Claude Opus 4.8 | M03 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_M03.md` |
| Gemini 3.7 Flash | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_7_flash_G02.md` |
| Gemini 3.6 Flash | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gemini_3_6_flash_G02.md` |
| GPT 5 mini | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_mini_G02.md` |
| GPT 5.3 Codex | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_gpt_5_3_codex_G02.md` |
| Claude Sonnet 5 | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_sonnet_5_G02.md` |
| Claude Opus 4.8 | G02 | ✅ OK | `docs/Time_2_Design/analise-qualitativa/outputs/relatorio_claude_opus_4_8_G02.md` |
