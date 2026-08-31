# Ajustes realizados após a Fase 3 — preparação para a Fase 4

**Rodada:** `fase3-piloto`  
**Data:** 2026-08-30  
**Objetivo:** corrigir os problemas identificados na execução piloto e deixar a infraestrutura pronta para a Fase 4 (execução completa).

---

## 1. Resumo dos problemas identificados na Fase 3

| # | Problema | Impacto | Ação tomada |
|---|---|---|---|
| 1 | `gpt-5-mini` consumia todo `max_tokens` em raciocínio interno e não emitia resposta final | 42 respostas vazias (13 em NQ, 25 em GAIA, 3 em SQuAD, 1 em LongBench) |‪ Implementado retry automático com max_tokens escalonado e status `reasoning_truncated` no runner |
| 2 | `gemini-3.5-flash-lite` indisponível no GitHub Copilot | Modelo do PR.md não pôde ser avaliado | Documentado oficialmente; mantidos 5 modelos executáveis |
| 3 | F1 modesto em SQuAD 2.0 (~0.46–0.49) | Span extraído pode conter artigos/pontuação extras | Adicionada normalização e extração de span do contexto para F1 |
| 4 | Falta de métrica Supporting Fact em HotpotQA | Não era possível diagnosticar se o modelo usava as evidências corretas | Novo prompt pede evidências + métrica P/R/F1 implementada |
| 5 | Ausência de LLM-as-a-Judge | EM/F1 podem subestimar respostas válidas | Criado `llm_judge.py` com rubrica de 5 dimensões |
| 6 | Configuração da Fase 4 inexistente | Sem plano para 100% dos dados | Criada `benchmarks/rodadas/fase4-completa/config.yaml` e prompts |

---

## 2. Ajuste 1 — Respostas vazias do `gpt-5-mini`

### 2.1 Causa raiz

O `github_copilot/gpt-5-mini` é um modelo de raciocínio. Sua `completion_tokens_details` mostra:

```
reasoning_tokens=512
text_tokens=0
finish_reason=length
```

Ou seja, todo o limite de saída é gasto em cadeia de raciocínio interna; nenhum token de texto é emitido. Aumentar `max_tokens` para 2048 não resolveu — o modelo simplesmente gastou 2048 tokens em raciocínio.

### 2.2 Solução implementada

Em `benchmarks/scripts/run_benchmark.py`:

- Adicionada função `reasoning_consumed_all_output()` que detecta quando todas as completion tokens são de raciocínio e o `finish_reason` é `length`.
- Modificada `call_model()` para, ao detectar essa condição, reexecutar automaticamente com `max_tokens` maior: 1.5× e depois 2× do valor original.
- Se mesmo assim não houver texto, o status registrado passa a ser `reasoning_truncated` em vez de `empty`.
- O runner trata `reasoning_truncated` como resultado final (não reexecuta novamente).
- O agregador `aggregate.py` exclui `reasoning_truncated` das métricas de qualidade, da mesma forma que `api_error`/`timeout`, mas contabiliza separadamente.

### 2.3 Configuração afetada

```yaml
# config.yaml (Fase 3 e Fase 4)
num_retries: 2
max_reasoning_retries: 2

model_max_tokens:
  github_copilot/gpt-5-mini: 512
```

Com 2 retries, o `gpt-5-mini` tentará com 512, 768 e 1024 tokens. Se ainda assim não emitir texto, será classificado como `reasoning_truncated`.

### 2.4 Recomendação para a Fase 4

- Monitorar a taxa de `reasoning_truncated` por benchmark. Se for alta, considerar remover o `gpt-5-mini` da Fase 4 ou adaptar o prompt para tarefas de agente.
- Não há parâmetro conhecido na API do Copilot para desabilitar o raciocínio. A mitigação é puramente instrumental.

---

## 3. Ajuste 2 — `gemini-3.5-flash-lite` indisponível

### 3.1 Diagnóstico

Durante o preflight, a API do GitHub Copilot respondeu:

```
litellm.BadRequestError: Github_copilotException - The requested model is not supported.
```

Testamos também as variantes:
- `github_copilot/gemini-3.5-flash-lite-preview`
- `github_copilot/gemini-flash-lite-3.5`
- `github_copilot/gemini-3.5-flash-latest`
- `github_copilot/gemini-3.5-flash-001`
- `github_copilot/gemini-3.0-flash-lite`
- `github_copilot/gemini-3.0-flash`

Todas retornaram a mesma mensagem. Portanto, não é um erro de slug.

### 3.2 Decisão oficial

- O modelo `gemini-3.5-flash-lite` não será executado nesta conta do Copilot.
- A lista oficial de modelos para a Fase 4 fica:
  1. `github_copilot/gemini-3.1-pro-preview`
  2. `github_copilot/gemini-3.7-flash`
  3. `github_copilot/gemini-3.5-flash`
  4. `github_copilot/gpt-5-mini`
  5. `github_copilot/claude-sonnet-4.5`
- Essa limitação deve ser explicitada no relatório técnico final da Fase 4.

---

## 4. Ajuste 3 — Métricas de SQuAD 2.0

### 4.1 Problema

O F1 modesto pode ser parcialmente explicado por respostas como:
- Predição: `"the American biographical period comedy-drama film"`
- Gold: `"American biographical period comedy-drama film"`

A normalização token-level já remove artigos, mas quando o modelo inclui palavras extras, o F1 cai.

### 4.2 Solução implementada

Em `benchmarks/scripts/metrics.py`:

- Adicionada `extract_span_from_context()`: dada a predição e o contexto, busca no contexto a substring de tokens consecutivos que melhor se sobrepõe à predição.
- O EM continua sendo calculado sobre a predição original (não podemos inventar a resposta).
- O F1 passa a ser calculado sobre o span alinhado (`pred_for_f1`), melhorando a avaliação sem deturpar a corretude absoluta.

### 4.3 Limitação

Se o modelo responde com uma reformulação completamente diferente do texto do contexto, o span alinhado pode não ser representativo. Para esses casos, a Fase 4 usará LLM-as-a-Judge como segunda camada.

---

## 5. Ajuste 4 — Supporting Facts em HotpotQA

### 5.1 Problema

O prompt antigo pedia apenas a resposta curta. Não era possível saber se o modelo usou os parágrafos corretos para chegar à resposta.

### 5.2 Solução implementada

1. **Prompt atualizado** (`prompts.yaml`):
   ```
   First, write the short answer on one line, prefixed with "Answer:".
   Then, on the next line, list the paragraph titles you used as evidence,
   prefixed with "Supporting facts:" and separated by " | ".
   ```

2. **Parser** em `metrics.py` — `extract_supporting_facts()` extrai os títulos listados.

3. **Métricas** — `supporting_fact_metrics()` calcula precision, recall e F1 sobre os títulos dos parágrafos gold.

### 5.3 Resultado esperado

Nas próximas rodadas, será possível reportar, por modelo:
- `supporting_fact_precision`
- `supporting_fact_recall`
- `supporting_fact_f1`

---

## 6. Ajuste 5 — LLM-as-a-Judge

### 6.1 Motivação

EM e F1 penalizam reformulações válidas. Para a Fase 4, é necessária uma camada semântica de avaliação.

### 6.2 Solução implementada

Criado `benchmarks/scripts/llm_judge.py`:

- Juiz configurável (padrão: `github_copilot/gemini-3.1-pro-preview`).
- Avalia cinco dimensões: Correctness, Helpfulness, Coherence, Completeness, Abstention.
- Notas de 1 a 5 para cada dimensão.
- Saída em JSON estrito.
- Pode amostrar N respostas por benchmark.
- Respeita as boas práticas do protocolo: juiz forte, distinto do modelo avaliado, temperatura 0, rubrica explícita.

### 6.3 Uso planejado na Fase 4

```bash
benchmarks/.venv/bin/python benchmarks/scripts/llm_judge.py \
    --rodada fase4-completa \
    --judge github_copilot/gemini-3.1-pro-preview \
    --samples 200 \
    --output benchmarks/rodadas/fase4-completa/resultados/judge_results.jsonl
```

---

## 7. Ajuste 6 — Preparação da Fase 4

### 7.1 Nova rodada criada

```
benchmarks/rodadas/fase4-completa/
├── config.yaml       # 100% dos datasets
└── prompts.yaml      # mesmo prompts ajustados
```

### 7.2 Configuração Fase 4

- `subsets` com valor `null` indica uso do dataset completo.
- `max_tokens` maior para `gaia_l1` (512).
- `max_reasoning_retries: 2` para lidar com o `gpt-5-mini`.
- 5 modelos executáveis (ver Ajuste 2).

### 7.3 Adaptação do `sample_subsets.py`

Modificado para aceitar `n=None` ou `n="all"` e copiar todo o dataset normalizado para o subset da rodada, preservando rastreabilidade via `manifest.json`.

### 7.4 Comando para gerar subsets da Fase 4

```bash
benchmarks/.venv/bin/python benchmarks/scripts/sample_subsets.py --rodada fase4-completa
```

### 7.5 Comando para executar a Fase 4

```bash
# Preflight
benchmarks/.venv/bin/python benchmarks/scripts/preflight_models.py --rodada fase4-completa

# Execução completa
benchmarks/.venv/bin/python benchmarks/scripts/run_benchmark.py --rodada fase4-completa

# Agregação
benchmarks/.venv/bin/python benchmarks/scripts/aggregate.py --rodada fase4-completa

# LLM-as-a-Judge (amostral)
benchmarks/.venv/bin/python benchmarks/scripts/llm_judge.py --rodada fase4-completa
```

---

## 8. Checklist de readiness para a Fase 4

| Item | Status |
|---|---|
| Runner com retry de reasoning truncation | ✅ |
| Agregador reconhece `reasoning_truncated` | ✅ |
| Normalização de span para SQuAD | ✅ |
| Métrica Supporting Fact para HotpotQA | ✅ |
| Prompt de HotpotQA pedindo evidências | ✅ |
| Script LLM-as-a-Judge | ✅ |
| Configuração Fase 4 (100% dataset) | ✅ |
| Tratamento de `gemini-3.5-flash-lite` | ✅ documentado |
| Amostragem de subsets para dataset completo | ✅ |
| Código compilado sem erros | ✅ |

---

## 9. Recomendações para execução da Fase 4

1. **Escalonar execução por modelo:** a Fase 4 terá ~16.000 chamadas (5 modelos × ~1.070 casos × 3 repetições). Executar um modelo por vez, como foi feito na Fase 3.
2. **Monitorar `reasoning_truncated`:** se a taxa do `gpt-5-mini` continuar alta, considerar remover esse modelo ou reduzir os benchmarks aplicados.
3. **Executar LLM-as-a-Judge em amostra:** não é necessário avaliar todas as ~16.000 respostas. Uma amostra estratificada de 200–500 respostas por benchmark é suficiente.
4. **Manter backup incremental:** os `runs.jsonl` são retomáveis. Recomenda-se fazer backup a cada modelo concluído.
5. **Meta-avaliação do juiz:** comparar ~50 notas do LLM-judge com avaliação humana para calibrar viés.

---

## 10. Arquivos alterados/criados

| Arquivo | Alteração |
|---|---|
| `benchmarks/scripts/run_benchmark.py` | Retry por reasoning truncation; status `reasoning_truncated` |
| `benchmarks/scripts/aggregate.py` | Ignora `reasoning_truncated` nas métricas |
| `benchmarks/scripts/metrics.py` | Span extraction para SQuAD; Supporting Facts para HotpotQA |
| `benchmarks/scripts/sample_subsets.py` | Suporte a dataset completo (`n=None`) |
| `benchmarks/scripts/llm_judge.py` | **Novo** — avaliação LLM-as-a-Judge |
| `benchmarks/rodadas/fase3-piloto/prompts.yaml` | HotpotQA agora pede evidências |
| `benchmarks/rodadas/fase4-completa/config.yaml` | **Novo** — configuração da Fase 4 |
| `benchmarks/rodadas/fase4-completa/prompts.yaml` | **Novo** — prompts da Fase 4 |
| `benchmarks/rodadas/fase3-piloto/resultados/ajustes_pre_fase4.md` | **Este relatório** |

---

*Documento gerado após análise dos resultados da Fase 3 e implementação dos ajustes de infraestrutura.*
