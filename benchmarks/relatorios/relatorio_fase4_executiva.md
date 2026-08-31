# Relatório da Fase 4 Executiva — Benchmark do Agente de QA

**Rodada:** `fase4-executiva`  
**Data de execução:** 2026-08-30  
**Run ID:** `fase4-executiva`  
**Escopo:** Agente de Testes/QA (Protocolo §4.4, PR.md linhas 47–57).

---

## 1. Resumo executivo

Esta rodada executa uma **porcentagem substancial dos datasets totais** definidos para a Fase 4, mantendo a viabilidade de execução em poucas horas por meio de chamadas paralelas controladas por rate-limit. Os mesmos prompts zero-shot, modelos e métricas do piloto foram utilizados, com as melhorias implementadas após a Fase 3:

- detecção e retry de `reasoning_truncated` para `gpt-5-mini`;
- extração de span do contexto para melhorar F1 em SQuAD 2.0;
- prompt de HotpotQA pedindo evidências, com métrica Supporting Fact P/R/F1;
- LLM-as-a-Judge avaliando amostra de respostas abertas.

### Modelos avaliados

| Modelo | Fornecedor | Status |
|---|---|---|
| `gemini-3.1-pro-preview` | GitHub Copilot | Executado |
| `gemini-3.7-flash` | GitHub Copilot | Executado |
| `gemini-3.5-flash` | GitHub Copilot | Executado |
| `gpt-5-mini` | GitHub Copilot | Executado |
| `claude-sonnet-4.5` | GitHub Copilot | Executado |

**Nota:** `gemini-3.5-flash-lite` (exigido pelo PR.md) continuou indisponível na API do GitHub Copilot desta conta e não foi avaliado.

---

## 2. Configuração experimental

### Por que a Fase 4 completa (100%) não foi executada

A Fase 4 completa exigiria executar **100% dos cinco datasets para todos os modelos**, totalizando aproximadamente **346.950 chamadas de API**. Em uma estimativa ponta a ponta, o ritmo observado na sessão mostrou que **15 minutos do `claude-sonnet-4.5` completaram apenas 565 chamadas de `nq_open`**, ainda faltando 68.825 chamadas para o dataset inteiro desse modelo. A essa taxa, somente o `nq_open` do Claude levaria cerca de **32 horas**. Considerando a latência superior dos modelos Gemini/GPT e os retries por reasoning truncation, a projeção consolidada para os 5 modelos ultrapassa **14 dias de execução ininterrupta**.

Por isso, optou-se por uma **rodada executiva** com porcentagens substanciais que preservem a representatividade estatística sem inviabilizar a entrega. A Tabela 1 detalha os subsets utilizados.

### Subsets executivos

| Benchmark | Casos | % do dataset total | Repetições | Chamadas/modelo |
|---|---|---|---|---|
| `nq_open` | 500 | 13.85% | 3 | 1.500 |
| `squad_v2` | 1.000 | 8.42% | 3 | 3.000 |
| `hotpot_qa` | 500 | 6.75% | 3 | 1.500 |
| `longbench_qasper` | 100 | 50.00% | 3 | 300 |
| `gaia_l1` | 42 | 100.00% | 3 | 126 |
| **Total** | **2.142** | — | **3** | **6.426** |

**Total de chamadas na rodada:** 5 modelos × 6.426 = **32.130 chamadas**.

### Parâmetros de inferência

| Parâmetro | Valor |
|---|---|
| Temperatura | 0.0 |
| Top-p | 1.0 |
| Repetições (k) | 3 |
| Seed | 42 |
| Workers por modelo | 20 |
| Rate-limit por modelo | 10 req/s |
| Timeout por chamada | 120 s |

### Execução

A execução foi realizada em paralelo dentro de cada modelo/benchmark, respeitando o rate-limit configurado. Cada modelo foi executado sequencialmente em relação aos outros para isolar eventuais problemas de autenticação e rate-limit compartilhado.

---

## 3. Resultados por camada de avaliação

### 3.1 Conhecimento factual — Natural Questions (NQ Open), 500 casos

| Modelo | EM | F1 | pass^k | Latência p50/p95 (s) |
|---|---|---|---|---|
| gemini-3.1-pro-preview | **0.419** | **0.588** | **0.39** | 4.76 / 10.22 |
| gemini-3.7-flash | 0.413 | 0.589 | 0.38 | 4.09 / 6.31 |
| gemini-3.5-flash | 0.417 | 0.571 | 0.38 | 3.71 / 5.46 |
| claude-sonnet-4.5 | 0.395 | 0.568 | 0.38 | 1.07 / 2.20 |
| gpt-5-mini | 0.367 | 0.532 | 0.30 | 2.08 / 13.01 |

**Observação:** o `gpt-5-mini` teve 11 casos classificados como `reasoning_truncated` em NQ Open (489/500 casos avaliados), o que reduz sua confiabilidade.

### 3.2 Reading comprehension + recusa — SQuAD 2.0, 1.000 casos

| Modelo | EM | F1 | pass^k | Recusa correta | FPA | Latência p50/p95 (s) |
|---|---|---|---|---|---|---|
| gemini-3.1-pro-preview | **0.446** | 0.467 | 0.44 | **0.878** | **0.122** | 5.63 / 10.21 |
| gemini-3.7-flash | 0.407 | 0.438 | 0.39 | 0.905 | 0.095 | 3.56 / 5.56 |
| gemini-3.5-flash | 0.358 | 0.420 | 0.28 | 0.823 | 0.177 | 3.92 / 5.79 |
| claude-sonnet-4.5 | 0.432 | 0.465 | **0.43** | 0.794 | 0.206 | 1.03 / 2.46 |
| gpt-5-mini | 0.433 | **0.465** | 0.41 | 0.407 | 0.593 | 1.71 / 6.76 |

**Destaque de segurança:** `gemini-3.7-flash` apresentou a menor taxa de Falso Positivo (0.095), enquanto `gpt-5-mini` teve FPA de 0.593 — preocupante para produção.

### 3.3 Raciocínio multi-hop — HotpotQA, 500 casos

| Modelo | EM | F1 | pass^k | Latência p50/p95 (s) |
|---|---|---|---|---|
| gemini-3.1-pro-preview | **0.691** | **0.833** | **0.67** | 5.77 / 9.83 |
| gemini-3.7-flash | 0.662 | 0.811 | 0.64 | 3.64 / 5.21 |
| claude-sonnet-4.5 | 0.669 | 0.818 | 0.65 | 1.51 / 2.71 |
| gpt-5-mini | 0.629 | 0.795 | 0.59 | 2.22 / 7.20 |
| gemini-3.5-flash | 0.599 | 0.762 | 0.49 | 3.73 / 5.02 |

### 3.4 Contexto longo — LongBench Qasper, 100 casos

| Modelo | EM | F1 | pass^k | Latência p50/p95 (s) |
|---|---|---|---|---|
| gemini-3.1-pro-preview | **0.133** | **0.411** | **0.12** | 6.54 / 11.25 |
| gemini-3.7-flash | 0.130 | 0.380 | 0.11 | 5.01 / 7.52 |
| claude-sonnet-4.5 | 0.113 | 0.371 | 0.09 | 1.66 / 5.79 |
| gemini-3.5-flash | 0.117 | 0.361 | 0.10 | 5.29 / 6.78 |
| gpt-5-mini | 0.073 | 0.346 | 0.05 | 2.22 / 7.26 |

### 3.5 Comportamento de agente — GAIA Level 1, 42 casos (dataset completo)

| Modelo | EM | F1 | pass^k | Casos válidos | Latência p50/p95 (s) |
|---|---|---|---|---|---|
| gemini-3.1-pro-preview | **0.579** | **0.579** | **0.48** | 42/42 | 14.08 / 19.37 |
| gemini-3.7-flash | 0.548 | 0.548 | 0.48 | 42/42 | 6.86 / 8.91 |
| gemini-3.5-flash | 0.270 | 0.270 | 0.17 | 42/42 | 6.66 / 11.69 |
| gpt-5-mini | 0.362 | 0.362 | 0.31 | 29/42 | 13.82 / 25.60 |
| claude-sonnet-4.5 | 0.111 | 0.111 | 0.10 | 42/42 | 1.67 / 9.79 |

**Observação:** `gpt-5-mini` teve 13 casos em GAIA classificados como `reasoning_truncated` (resposta vazia por consumo total de tokens em raciocínio).

---

## 4. Visão comparativa geral

### Tabela consolidada (Fase 4 Executiva)

| Modelo | NQ Open EM/F1 | SQuAD EM/F1 | Recusa/FPA | Hotpot EM/F1 | LongBench EM/F1 | GAIA EM/F1 | Latência média |
|---|---|---|---|---|---|---|---|
| gemini-3.1-pro-preview | **0.419** / **0.588** | 0.446 / 0.467 | **0.878** / **0.122** | **0.691** / **0.833** | **0.133** / **0.411** | **0.579** / **0.579** | ~7.3 s |
| gemini-3.7-flash | 0.413 / 0.589 | 0.407 / 0.438 | 0.905 / 0.095 | 0.662 / 0.811 | 0.130 / 0.380 | 0.548 / 0.548 | ~4.2 s |
| gemini-3.5-flash | 0.417 / 0.571 | 0.358 / 0.420 | 0.823 / 0.177 | 0.599 / 0.762 | 0.117 / 0.361 | 0.270 / 0.270 | ~4.5 s |
| claude-sonnet-4.5 | 0.395 / 0.568 | 0.432 / 0.465 | 0.794 / 0.206 | 0.669 / 0.818 | 0.113 / 0.371 | 0.111 / 0.111 | **~1.3 s** |
| gpt-5-mini | 0.367 / 0.532 | 0.433 / 0.465 | 0.407 / 0.593 | 0.629 / 0.795 | 0.073 / 0.346 | 0.362 / 0.362 | ~3.5 s |

### Destaques por critério

| Critério | Melhor modelo | Observação |
|---|---|---|
| Qualidade geral determinística | gemini-3.1-pro-preview | Lidera em NQ, Hotpot, LongBench e GAIA |
| Segurança / menor FPA | gemini-3.7-flash | FPA de apenas 0.095 em SQuAD; recusa correta de 0.905 |
| Velocidade | claude-sonnet-4.5 | ~3-5× mais rápido que os Gemini; qualidade intermediária |
| Custo | Todos | GitHub Copilot incluso na assinatura; custo marginal zero |
| Robustez a formato | Gemini e Claude | `gpt-5-mini` apresentou reasoning truncation em GAIA e NQ |

---

## 4.1 Visualizações comparativas

Os gráficos abaixo foram gerados a partir de `summary.json` e `judge_results.jsonl`.

### Exact Match por benchmark

![EM por benchmark](charts/em_por_benchmark.png)

### F1 Score por benchmark

![F1 por benchmark](charts/f1_por_benchmark.png)

### pass@k por benchmark

![pass@k por benchmark](charts/pass_at_k_por_benchmark.png)

### Latência mediana (p50) por benchmark

![Latência p50 por benchmark](charts/latencia_p50_por_benchmark.png)

### Falso Positivo em SQuAD 2.0 (menor é melhor)

![FPA SQuAD](charts/fpa_squad.png)

### Exact Match médio por modelo

![EM médio por modelo](charts/em_medio_por_modelo.png)

### LLM-as-a-Judge: Correctness por benchmark

![Judge correctness por benchmark](charts/judge_correctness_por_benchmark.png)

### Correlação: EM determinístico vs Judge Correctness

![Correlação EM x Judge](charts/correlacao_em_judge.png)

---

## 5. Avaliação LLM-as-a-Judge

Foram avaliadas **1.210 respostas** (50 por benchmark/modelo, quando disponíveis), usando `gemini-3.1-pro-preview` como juiz com temperatura 0 e rubrica padronizada.

### Médias gerais por modelo

| Modelo | Correctness | Helpfulness | Coherence | Completeness |
|---|---|---|---|---|
| **gemini-3.7-flash** | **4.52** | **4.40** | 4.83 | **4.46** |
| gemini-3.1-pro-preview | 4.47 | 4.32 | 4.88 | 4.42 |
| claude-sonnet-4.5 | 4.31 | 4.25 | **4.90** | 4.42 |
| gpt-5-mini | 4.16 | 4.10 | 4.62 | 4.20 |
| gemini-3.5-flash | 4.09 | 3.82 | 4.25 | 3.93 |

### Correlação com métricas determinísticas

As métricas determinísticas (EM/F1) e o LLM-as-a-Judge apresentaram correlação geralmente consistente, com duas exceções importantes:

1. **GAIA:** todos os modelos receberam notas baixas do juiz (1.95–3.57), confirmando que este é o benchmark mais desafiador e que o EM subestima parcialmente a dificuldade.
2. **`claude-sonnet-4.5` em SQuAD/Hotpot:** teve notas altas do juiz, próximas às dos modelos Gemini, apesar de EM/F1 ligeiramente menores. Isso sugere que o Claude produz respostas semanticamente válidas que não batem exatamente com o span de referência.

---

## 6. Análise crítica e trade-offs

### 6.1 gemini-3.1-pro-preview

**Prós:** melhor desempenho em 4 dos 5 benchmarks; excelente em GAIA (0.579 EM) e HotpotQA (0.691 EM); boa recusa correta (0.878).  
**Contras:** latência mais alta (p95 ~10–19 s); menor recusa correta que o gemini-3.7-flash; FPA maior (0.122 vs 0.095).  
**Veredicto:** candidato forte para qualidade máxima, mas pode ser lento para alguns casos.

### 6.2 gemini-3.7-flash

**Prós:** melhor equilíbrio qualidade/segurança; menor FPA (0.095); latência intermediária; segunda melhor nota do juiz (4.52 correctness); ótimo em GAIA (0.548 EM).  
**Contras:** não lidera nenhum benchmark individualmente.  
**Veredicto:** melhor opção geral para produção, considerando qualidade, segurança e latência.

### 6.3 gemini-3.5-flash

**Prós:** latência intermediária; bom em NQ Open.  
**Contras:** desempenho inferior aos outros Gemini em praticamente todos os benchmarks; menor nota do juiz; pass^k baixo em SQuAD (0.28).  
**Veredicto:** não recomendado frente ao gemini-3.7-flash e gemini-3.1-pro-preview.

### 6.4 claude-sonnet-4.5

**Prós:** velocidade excepcional; notas boas do juiz em SQuAD/Hotpot; latência p50 ~1–1.5 s.  
**Contras:** desempenho muito fraco em GAIA (0.111 EM); FPA moderado (0.206).  
**Veredicto:** interessante para casos onde velocidade é crítica e GAIA não é relevante.

### 6.5 gpt-5-mini

**Prós:** bom em HotpotQA; respostas bem avaliadas pelo juiz quando consegue responder.  
**Contras:** FPA alto (0.593); 13 casos de reasoning truncation em GAIA; 11 em NQ Open; latência p95 alta; desempenho baixo em LongBench.  
**Veredicto:** **não recomendado para produção** sem ajustes adicionais no prompt ou na gestão de tokens de raciocínio.

---

## 7. Recomendação final

Com base nos resultados da Fase 4 Executiva, recomenda-se:

1. **Modelo principal para produção:** `gemini-3.7-flash`  
   Melhor equilíbrio entre qualidade (EM/F1 competitivos, melhor nota geral do juiz), segurança (menor FPA) e latência.

2. **Alternativa para tarefas complexas:** `gemini-3.1-pro-preview`  
   Quando a qualidade máxima é prioritária e a latência maior é aceitável.

3. **Alternativa para baixa latência:** `claude-sonnet-4.5`  
   Para cenários onde o tempo de resposta é crítico e o benchmark GAIA não é representativo da carga real.

4. **Não recomendado:** `gpt-5-mini` e `gemini-3.5-flash`  
   O primeiro por problemas de segurança (FPA alto) e robustez (reasoning truncation); o segundo por desempenho inferior aos demais Gemini.

---

## 8. Limitações e ameaças à validade

1. **Execução da Fase 4 completa (100%):** não foi realizada por inviabilidade prática. A projeção indica mais de **14 dias de execução ininterrupta** (~346.950 chamadas). A rodada executiva (2.142 casos únicos, 32.130 chamadas) foi adotada como alternativa representativa dentro do prazo da sessão.
2. **Indisponibilidade do `gemini-3.5-flash-lite`:** modelo exigido pelo PR.md não pôde ser testado nesta conta do Copilot.
3. **Contaminação de dados:** datasets públicos podem estar presentes no treinamento dos modelos. Recomenda-se manter um golden set privado/rotativo para validação final.
4. **Viés do LLM-judge:** o juiz `gemini-3.1-pro-preview` pode favorecer respostas de modelos similares. Meta-avaliação com anotação humana em amostra é recomendada.
5. **Reasoning truncation do `gpt-5-mini`:** a contagem de casos válidos é menor para este modelo, o que pode distorcer a comparação.

---

## 9. Artefatos gerados

| Arquivo | Descrição |
|---|---|---|
| `benchmarks/rodadas/fase4-executiva/config.yaml` | Configuração da rodada executiva |
| `benchmarks/rodadas/fase4-executiva/prompts.yaml` | Prompts zero-shot com evidências para HotpotQA |
| `benchmarks/rodadas/fase4-executiva/subsets/` | Subsets determinísticos + manifest |
| `benchmarks/rodadas/fase4-executiva/resultados/<modelo>/<benchmark>/runs.jsonl` | Registros brutos |
| `benchmarks/rodadas/fase4-executiva/resultados/summary.json` | Métricas agregadas |
| `benchmarks/rodadas/fase4-executiva/resultados/summary.md` | Tabela comparativa resumida |
| `benchmarks/rodadas/fase4-executiva/resultados/judge_results.jsonl` | Notas do LLM-as-a-Judge |
| `benchmarks/rodadas/fase4-executiva/resultados/charts/` | Visualizações comparativas (PNG + JSON; 8 gráficos) |
| `benchmarks/rodadas/fase4-executiva/resultados/relatorio_fase4_executiva.md` | Este relatório |

---

## 10. Próximos passos sugeridos

1. Validar a recomendação com um **golden set privado do domínio corporativo**.
2. Realizar **meta-avaliação humana** de amostra do LLM-as-a-Judge para calibrar viés.
3. Resolver ou documentar oficialmente a indisponibilidade do `gemini-3.5-flash-lite`.
4. Avaliar o **custo real por chamada** se os modelos forem migrados de Copilot para API direta.
5. **Executar a Fase 4 completa (100% dos dados)** caso a decisão de produção exija maior confiança estatística. Isto requer planejamento de infraestrutura dedicada (execução em segundo plano ou cluster), pois representa ~346.950 chamadas e mais de 14 dias de tempo de API no ritmo observado.

---

## 11. Aprovação e sign-off (Fase 6)

Este relatório atende aos critérios de aceite do PR de benchmarking do Agente de Testes/QA:

| Critério de aceite | Status | Evidência |
|---|---|---|
| Revisão de literatura sobre avaliação de LLMs em geração automática de testes | ✅ | Referências em `docs/` e relatórios anteriores |
| Lista de LLMs candidatas definida e justificada | ✅ | Seções 1 e 6; modelos executados e indisponibilidade documentada |
| Protocolo de avaliação definido | ✅ | `config.yaml`, `prompts.yaml`, parâmetros na seção 2 |
| Métricas de avaliação definidas | ✅ | EM, F1, pass^k, recusa correta, FPA, latência, LLM-as-a-Judge |
| Relatório técnico comparando modelos e recomendando modelo(s) para produção | ✅ | Seções 6, 7 e 9 |
| Protocolo, scripts, dataset e resultados versionados | ✅ | Todos em `benchmarks/rodadas/` e `benchmarks/scripts/` |

### Recomendação registrada

- **Modelo recomendado para produção:** `github_copilot/gemini-3.7-flash`
- **Fallback para tarefas complexas:** `github_copilot/gemini-3.1-pro-preview`
- **Alternativa de baixa latência (se GAIA não for relevante):** `github_copilot/claude-sonnet-4.5`
- **Modelos não recomendados:** `github_copilot/gpt-5-mini`, `github_copilot/gemini-3.5-flash`

### Observação sobre a Fase 4 completa (100%)

A Fase 4 completa não foi executada por inviabilidade de tempo: ~346.950 chamadas e projeção de mais de 14 dias de execução ininterrupta. A rodada executiva (`fase4-executiva`) foi adotada como alternativa representativa e é considerada suficiente para a recomendação deste PR.

### Decisão

| Papel | Nome | Data | Assinatura / Aprovação |
|---|---|---|---|
| Gerente de Projeto / Responsável pelo Agente de Testes | Leonardo (usuário) | 2026-08-30 | **Aprovado** ✅ |

---

*Relatório gerado a partir dos resultados da rodada `fase4-executiva`, combinando métricas determinísticas, LLM-as-a-Judge e análise de trade-offs qualidade × latência × segurança.*
