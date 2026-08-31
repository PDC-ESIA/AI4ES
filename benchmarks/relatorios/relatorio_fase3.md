# Relatório da Fase 3 — Benchmark do Agente de QA

**Rodada:** `fase3-piloto`  
**Data de execução:** 2026-08-30  
**Run ID:** `fase3-piloto-modelos-corretos`  
**Escopo:** Agente de Testes/QA (Protocolo §4.4, PR.md linhas 47–57).

---

## 1. Resumo executivo

Este relatório apresenta os resultados da **Fase 3 (Piloto e ajuste)** do benchmark de LLMs para o Agente de QA. A rodada foi executada com os modelos especificados no PR.md, usando um subconjunto reduzido (10–20% dos casos) para validar ponta a ponta o protocolo experimental antes da Fase 4.

**Nota importante sobre modelos:** o PR.md exigia seis modelos, incluindo `github_copilot/gemini-3.5-flash-lite`. Durante o preflight, este modelo retornou `The requested model is not supported` na API do GitHub Copilot desta conta, e várias variantes de slug também falharam. Por decisão do gerente de projeto, o modelo foi removido da rodada e o piloto foi executado com os cinco modelos acessíveis. O fato está documentado aqui e deve ser considerado na Fase 4.

### Modelos avaliados

| # | Modelo | Fornecedor | Status no piloto |
|---|---|---|---|
| 1 | `gemini-3.1-pro-preview` | GitHub Copilot | Executado |
| 2 | `gemini-3.7-flash` | GitHub Copilot | Executado |
| 3 | `gemini-3.5-flash` | GitHub Copilot | Executado |
| 4 | `gpt-5-mini` | GitHub Copilot | Executado |
| 5 | `claude-sonnet-4.5` | GitHub Copilot | Executado |
| — | `gemini-3.5-flash-lite` | GitHub Copilot | **Indisponível na conta** |

### Principais achados

- `gemini-3.1-pro-preview` e `gemini-3.7-flash` lideraram em **HotpotQA** (multi-hop), atingindo EM médio de 0.80 e F1 de 0.89.
- `gemini-3.7-flash` apresentou a melhor taxa de recusa correta em perguntas sem resposta (0.80) e o menor FPA (0.20).
- `gemini-3.1-pro-preview` foi o melhor em GAIA (0.60 EM), mostrando vantagem em tarefas de agente/ferramentas.
- `gpt-5-mini` apresentou problemas de conformidade de formato: 13 respostas vazias em `nq_open` e 25 em `gaia_l1`, apesar do ajuste de `max_tokens` para 512. Isso indica que o modelo de raciocínio pode consumir a cota de saída antes de emitir a resposta final.
- `claude-sonnet-4.5` foi o mais rápido em todos os benchmarks, mas teve desempenho intermediário em qualidade.

---

## 2. Configuração experimental

Os parâmetros foram fixados e idênticos para todos os modelos, conforme Protocolo §7/§8:

| Parâmetro | Valor |
|---|---|
| Temperatura | 0.0 |
| Top-p | 1.0 |
| Repetições por caso (k) | 3 |
| Seed de amostragem | 42 |
| Timeout por chamada | 120 s |
| Retries | 2 |

### Subsets avaliados

| Benchmark | Casos | % do dataset total | Propriedade avaliada |
|---|---|---|---|
| `nq_open` | 20 | ~0.55% de 3.610 | Conhecimento factual open-domain |
| `squad_v2` | 20 | ~0.17% de 11.873 | Reading comprehension + recusa |
| `hotpot_qa` | 20 | ~0.27% de 7.405 | Raciocínio multi-hop |
| `longbench_qasper` | 10 | 5% de 200 | Contexto longo (single-doc QA) |
| `gaia_l1` | 10 | ~24% de 42 | Comportamento de agente/ferramentas |

### Prompts

Zero-shot, padronizados em `prompts.yaml`. Sem few-shot, sem ajustes por modelo.

### Tratamento de vazios

Reexecuções por `api_error`/`timeout` são registradas em `total_registros_brutos`, mas apenas a última ocorrência de cada par `(case_id, repetition)` entra nas métricas. Respostas `empty` (texto vazio) são mantidas e afetam as métricas de qualidade.

---

## 3. Resultados por camada de avaliação

### 3.1 Conhecimento factual — Natural Questions (NQ Open)

| Modelo | EM | F1 | pass^k | Latência p50/p95 (s) | Respostas vazias |
|---|---|---|---|---|---|
| gemini-3.1-pro-preview | **0.267** | **0.475** | 0.25 | 5.89 / 11.57 | 0 |
| gemini-3.7-flash | 0.233 | 0.446 | 0.20 | 4.31 / 6.23 | 0 |
| gemini-3.5-flash | 0.250 | 0.396 | 0.25 | 4.00 / 6.04 | 0 |
| claude-sonnet-4.5 | 0.250 | 0.390 | 0.25 | 1.82 / 2.36 | 0 |
| gpt-5-mini | 0.200 | 0.316 | 0.20 | 2.81 / 6.05 | 13/60 |

Interpretação: todos os modelos tiveram desempenho modesto em NQ (EM ~0.20–0.27), o que é esperado para um dataset de perguntas reais do Google Search sem contexto fornecido. A variante `gemini-3.1-pro-preview` liderou em F1. O `gpt-5-mini` teve 13 respostas vazias (21.7% das chamadas), indicando que o prompt curto combinado com tokens de raciocínio prejudica a conformidade de formato.

### 3.2 Reading comprehension + recusa — SQuAD 2.0

| Modelo | EM | F1 | pass^k | Recusa correta | FPA | Latência p50/p95 (s) |
|---|---|---|---|---|---|---|
| gemini-3.7-flash | 0.450 | 0.487 | 0.45 | **0.80** | **0.20** | 3.49 / 5.94 |
| gemini-3.1-pro-preview | 0.450 | 0.487 | 0.45 | 0.77 | 0.23 | 6.76 / 9.91 |
| claude-sonnet-4.5 | 0.450 | 0.483 | 0.45 | 0.67 | 0.33 | 1.74 / 2.77 |
| gemini-3.5-flash | 0.417 | 0.460 | 0.35 | 0.63 | 0.37 | 3.79 / 5.64 |
| gpt-5-mini | 0.450 | 0.493 | 0.45 | 0.50 | 0.50 | 2.05 / 6.65 |

Interpretação: a capacidade de recusa correta é crítica para produção. `gemini-3.7-flash` teve o melhor equilíbrio (80% de recusa correta, apenas 20% de FPA). `gpt-5-mini` foi o pior nesse quesito, com 50% de FPA. Os modelos Gemini apresentaram F1 semelhante (~0.46–0.49), enquanto `claude-sonnet-4.5` foi mais rápido.

### 3.3 Raciocínio multi-hop — HotpotQA

| Modelo | EM | F1 | pass^k | Latência p50/p95 (s) |
|---|---|---|---|---|
| gemini-3.5-flash | **0.783** | **0.902** | 0.75 | 3.39 / 4.40 |
| gemini-3.1-pro-preview | 0.800 | 0.891 | 0.80 | 5.22 / 7.19 |
| gemini-3.7-flash | 0.800 | 0.891 | 0.80 | 3.48 / 4.94 |
| claude-sonnet-4.5 | 0.750 | 0.841 | 0.75 | 1.68 / 1.95 |
| gpt-5-mini | 0.750 | 0.841 | 0.75 | 1.85 / 4.71 |

Interpretação: os três modelos Gemini superaram 0.78 EM, indicando forte capacidade de síntese de múltiplos parágrafos. `gemini-3.5-flash` teve o maior F1 (0.902). A consistência (`pass^k`) foi alta para `gemini-3.1-pro-preview` e `gemini-3.7-flash` (0.80).

### 3.4 Contexto longo — LongBench Qasper

| Modelo | EM | F1 | pass^k | Latência p50/p95 (s) | Respostas vazias |
|---|---|---|---|---|---|
| gemini-3.1-pro-preview | **0.300** | **0.524** | 0.30 | 6.45 / 14.47 | 0 |
| gemini-3.7-flash | 0.300 | 0.505 | 0.30 | 4.51 / 7.79 | 0 |
| gemini-3.5-flash | 0.300 | 0.503 | 0.30 | 5.33 / 6.97 | 0 |
| claude-sonnet-4.5 | 0.167 | 0.449 | 0.10 | 1.90 / 8.19 | 0 |
| gpt-5-mini | 0.067 | 0.346 | 0.00 | 2.26 / 4.82 | 1/30 |

Interpretação: os modelos Gemini tiveram desempenho praticamente idêntico, liderando EM (0.30) e F1 (~0.50). `claude-sonnet-4.5` e `gpt-5-mini` ficaram atrás, especialmente em consistência. O `gpt-5-mini` também teve uma resposta vazia.

### 3.5 Comportamento de agente — GAIA Level 1

| Modelo | EM | F1 | pass^k | Latência p50/p95 (s) | Respostas vazias |
|---|---|---|---|---|---|
| gemini-3.1-pro-preview | **0.600** | **0.600** | 0.50 | 9.42 / 19.10 | 0 |
| gemini-3.7-flash | 0.467 | 0.467 | 0.40 | 5.22 / 7.88 | 0 |
| gemini-3.5-flash | 0.167 | 0.167 | 0.00 | 4.31 / 7.04 | 0 |
| claude-sonnet-4.5 | 0.100 | 0.100 | 0.10 | 3.08 / 5.00 | 0 |
| gpt-5-mini | 0.100 | 0.100 | 0.00 | 3.69 / 5.02 | 25/30 |

Interpretação: `gemini-3.1-pro-preview` foi dominante em GAIA, com 0.60 EM e 0.50 de consistência. `gemini-3.7-flash` ficou em segundo. `gpt-5-mini` praticamente falhou em responder, com 25 de 30 respostas vazias. Isso sugere que a configuração de `max_tokens=512` ainda é insuficiente para o modelo de raciocínio emitir a resposta final em tarefas de agente, ou que o prompt precisa de ajuste na Fase 4.

---

## 4. Visão comparativa geral

### Tabela consolidada

| Modelo | NQ Open EM/F1 | SQuAD EM/F1 | Recusa/FPA | Hotpot EM/F1 | LongBench EM/F1 | GAIA EM/F1 | Latência média geral (s) |
|---|---|---|---|---|---|---|---|
| gemini-3.1-pro-preview | 0.27 / 0.48 | 0.45 / 0.49 | 0.77 / 0.23 | 0.80 / 0.89 | 0.30 / 0.52 | **0.60 / 0.60** | ~6.3 |
| gemini-3.7-flash | 0.23 / 0.45 | 0.45 / 0.49 | **0.80 / 0.20** | 0.80 / 0.89 | 0.30 / 0.51 | 0.47 / 0.47 | ~4.2 |
| gemini-3.5-flash | 0.25 / 0.40 | 0.42 / 0.46 | 0.63 / 0.37 | **0.78 / 0.90** | 0.30 / 0.50 | 0.17 / 0.17 | ~4.0 |
| claude-sonnet-4.5 | 0.25 / 0.39 | 0.45 / 0.48 | 0.67 / 0.33 | 0.75 / 0.84 | 0.17 / 0.45 | 0.10 / 0.10 | **~2.0** |
| gpt-5-mini | 0.20 / 0.32 | 0.45 / 0.49 | 0.50 / 0.50 | 0.75 / 0.84 | 0.07 / 0.35 | 0.10 / 0.10 | ~2.9 |

### Destaques por critério

| Critério | Melhor modelo | Observação |
|---|---|---|
| Qualidade geral (média ponderada) | gemini-3.1-pro-preview | Lidera em NQ, LongBench e GAIA; empata em HotpotQA |
| Recusa correta / segurança | gemini-3.7-flash | Menor taxa de FPA (0.20) e maior recusa correta (0.80) |
| Velocidade | claude-sonnet-4.5 | ~2x mais rápido que os Gemini; trade-off de qualidade |
| Custo | Todos | GitHub Copilot é incluso na assinatura; custo marginal zero |
| Robustez a formato | Gemini e Claude | `gpt-5-mini` apresentou muitas respostas vazias |

---

## 5. Problemas identificados e ajustes para a Fase 4

### 5.1 Problema: respostas vazias no `gpt-5-mini`

- Ocorrências: 13/60 em NQ Open; 25/30 em GAIA; 1/30 em LongBench; 3/60 em SQuAD.
- Causa provável: o modelo usa tokens de raciocínio internos que consomem a cota de `max_tokens` antes de gerar a resposta final.
- Ajuste proposto para Fase 4: aumentar `max_tokens` para 2048 ou 4096 para `gpt-5-mini`, ou adicionar instrução explícita no prompt para responder imediatamente sem raciocínio visível.

### 5.2 Problema: `gemini-3.5-flash-lite` indisponível

- A API do Copilot desta conta não expõe este modelo.
- Ajuste proposto: na Fase 4, tentar novamente ou substituir oficialmente por outro modelo Gemini acessível.

### 5.3 Problema: SQuAD F1 modesto

- Todos os modelos ficaram com F1 ~0.46–0.49, o que indica que o prompt zero-shot de extração de span pode não ser ideal.
- Ajuste proposto: avaliar na Fase 4 se a extração da primeira linha da resposta penaliza spans que incluem artigos/pontuação; considerar normalização adicional.

### 5.4 Melhoria: latência do `gemini-3.1-pro-preview`

- Modelo mais lento (média ~6.3 s, p95 até 19 s em GAIA), embora tenha melhor qualidade.
- Ajuste proposto: monitorar se a latência é aceitável para o agente de QA em produção; se não, considerar `gemini-3.7-flash` como alternativa de melhor custo-benefício.

---

## 6. Recomendações preliminares para produção

Com base apenas nos resultados do piloto (não definitivos):

1. **Candidato principal:** `gemini-3.1-pro-preview` — melhor qualidade geral, especialmente em GAIA e NQ Open.
2. **Alternativa segura:** `gemini-3.7-flash` — melhor recusa correta, velocidade intermediária e qualidade próxima à do pro.
3. **Opção rápida:** `claude-sonnet-4.5` — se a latência for crítica e a queda de qualidade for aceitável.
4. **Não recomendado sem ajustes:** `gpt-5-mini` — problemas sérios de conformidade de formato que precisam ser resolvidos antes de qualquer uso.

---

## 7. Artefatos gerados

| Arquivo | Descrição |
|---|---|
| `benchmarks/rodadas/fase3-piloto/config.yaml` | Configuração atualizada da rodada |
| `benchmarks/rodadas/fase3-piloto/prompts.yaml` | Prompts zero-shot padronizados |
| `benchmarks/rodadas/fase3-piloto/subsets/` | Subsets determinísticos (seed 42) + manifest |
| `benchmarks/rodadas/fase3-piloto/resultados/<modelo>/<benchmark>/runs.jsonl` | Registros brutos de cada chamada |
| `benchmarks/rodadas/fase3-piloto/resultados/summary.json` | Métricas agregadas completas |
| `benchmarks/rodadas/fase3-piloto/resultados/summary.md` | Tabela comparativa resumida |
| `benchmarks/rodadas/fase3-piloto/resultados/relatorio_fase3.md` | Este relatório |
| `benchmarks/rodadas/fase3-piloto/resultados-errata-modelos-incorretos/` | Backup dos resultados antigos |

---

## 8. Próximos passos

1. Resolver o problema de respostas vazias no `gpt-5-mini` antes da Fase 4.
2. Confirmar ou substituir oficialmente o `gemini-3.5-flash-lite` indisponível.
3. Executar a Fase 4 com 100% dos casos definidos e o número de repetições estabelecido.
4. Adicionar métrica de Supporting Fact Precision/Recall para HotpotQA (requer prompt de evidências).
5. Incluir avaliação LLM-as-a-Judge para respostas abertas que EM/F1 subestimam.

---

*Relatório gerado automaticamente a partir dos resultados da rodada `fase3-piloto`.*
