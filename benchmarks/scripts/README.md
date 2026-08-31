# Benchmark de LLMs — Agente de QA

Infraestrutura do estudo de benchmarking para o Agente de Testes/QA, executada
em rodadas autocontidas. Cada rodada vive em
`benchmarks/rodadas/<nome-da-rodada>/` e contém: configuração, prompts,
subsets e resultados. O código em `benchmarks/scripts/` é reutilizado entre
as rodadas.

## Layout (orientado a rodadas)

```
benchmarks/
├── rodadas/
│   ├── fase3-piloto/                 # piloto pequeno (Fase 3)
│   │   ├── config.yaml
│   │   ├── prompts.yaml
│   │   ├── subsets/                  # JSONLs amostrados + manifest
│   │   └── resultados/
│   │       ├── <modelo>/<benchmark>/runs.jsonl
│   │       └── summary.{json,md}
│   └── fase4-executiva/              # rodada executiva (Fase 4 representativa)
│       ├── config.yaml
│       ├── prompts.yaml
│       ├── subsets/
│       └── resultados/
│           ├── <modelo>/<benchmark>/runs.jsonl
│           ├── summary.{json,md}
│           ├── judge_results.jsonl
│           ├── charts/               # PNG + JSON para visualização
│           └── relatorio_fase4_executiva.md
├── scripts/                          # harness reutilizável
│   ├── download_datasets.py
│   ├── sample_subsets.py
│   ├── preflight_models.py
│   ├── run_benchmark.py
│   ├── aggregate.py
│   ├── metrics.py
│   └── llm_judge.py
└── .venv/                            # ambiente (gitignored)
```

Datasets brutos ficam em `benchmark/datasets/` (**gitignored**, compartilhados
entre rodadas); os subsets versionados por rodada são a entrada real dos
experimentos.

## Modelos avaliados nas rodadas atuais

| Modelo | Papel |
|---|---|
| `github_copilot/gemini-3.1-pro-preview` | Melhor qualidade bruta em GAIA/Hotpot |
| `github_copilot/gemini-3.7-flash` | **Recomendado para produção** — melhor equilíbrio qualidade/segurança/latência |
| `github_copilot/gemini-3.5-flash` | Alternativa rápida, porém inferior ao 3.7-flash |
| `github_copilot/gpt-5-mini` | Não recomendado (FPA alto, reasoning truncation) |
| `github_copilot/claude-sonnet-4.5` | Alternativa de baixa latência, fraco em GAIA |

**Nota:** o `github_copilot/gemini-3.5-flash-lite` constava da lista inicial do
PR, mas retornou `The requested model is not supported` na API do GitHub
Copilot desta conta em todos os slugs testados. Foi documentado como
indisponível e removido das rodadas.

## Preparação do ambiente

```bash
# 1. Python 3.14 + dependências
/opt/homebrew/opt/python@3.14/bin/python3.14 -m venv benchmarks/.venv
benchmarks/.venv/bin/pip install litellm pyarrow pyyaml python-dotenv requests tenacity matplotlib

# 2. Credenciais — benchmark/.env (gitignored):
#    HF_TOKEN=...            (GAIA, gated no Hugging Face)
#    GOOGLE_API_KEY=...      (fallback para Gemini via LiteLLM)
#    Copilot: device-flow automático via preflight (~/.config/litellm/github_copilot)
```

## Reprodução de uma rodada

```bash
# 1. Download e normalização dos datasets (uma vez; compartilhado entre rodadas)
benchmarks/.venv/bin/python benchmarks/scripts/download_datasets.py

# 2. Amostragem determinística dos subsets da rodada
benchmarks/.venv/bin/python benchmarks/scripts/sample_subsets.py --rodada fase4-executiva

# 3. Preflight de credenciais (dispara device-flow do Copilot se necessário)
benchmarks/.venv/bin/python benchmarks/scripts/preflight_models.py --rodada fase4-executiva

# 4. Dry-run (contagem de chamadas + estimativa de tempo) e execução
benchmarks/.venv/bin/python benchmarks/scripts/run_benchmark.py --rodada fase4-executiva --dry-run
benchmarks/.venv/bin/python benchmarks/scripts/run_benchmark.py --rodada fase4-executiva

# 5. Agregação de métricas
benchmarks/.venv/bin/python benchmarks/scripts/aggregate.py --rodada fase4-executiva

# 6. (Opcional) LLM-as-a-Judge em amostra
benchmarks/.venv/bin/python benchmarks/scripts/llm_judge.py \
    --rodada fase4-executiva \
    --judge github_copilot/gemini-3.1-pro-preview \
    --samples 50
```

## Reprodução dos gráficos

```bash
# Os gráficos são gerados pelo script charts.py (a ser criado) ou via notebook.
# Os dados prontos estão em:
# benchmarks/rodadas/fase4-executiva/resultados/charts/
```

## Notas metodológicas

- **Isolamento**: chamadas LiteLLM diretas, sem passar pelo agente ADK.
- **Copilot**: headers de IDE + `X-Initiator: user` replicados de
  `adk/shared/llm.py` para evitar a cota reduzida de "utility models".
- **Rate-limit**: controle próprio via `TokenBucketRateLimiter`; retries
  controlados por tipo de erro.
- **Retomada**: registros `ok` existentes são pulados; falhas de infraestrutura
  (`api_error`, `timeout`, `rate_limited`, `reasoning_truncated`) são
  contabilizadas separadamente das falhas de qualidade do modelo.
- **Custo**: GitHub Copilot é incluso na assinatura → custo marginal zero para
  os modelos via Copilot Chat; modelos via Google API têm contabilização do
  próprio provider.
- **Modelos thinking**: `gpt-5-mini` consome tokens de raciocínio. Quando o
  limite total é atingido antes da resposta final, o registro é marcado como
  `reasoning_truncated`. O runner ajusta `max_tokens` em retries, mas nem
  sempre é suficiente para tarefas difíceis como GAIA.

## Sobre a Fase 4 completa (100% dos datasets)

A Fase 4 completa exigiria executar 100% dos cinco datasets para todos os
modelos — aproximadamente **346.950 chamadas de API**. Na prática,
15 minutos do modelo mais rápido (`claude-sonnet-4.5`) completaram apenas
565 chamadas de `nq_open`, restando 68.825 para finalizar apenas aquele
benchmark/modelo. A projeção ultrapassa **14 dias de execução ininterrupta**.

Por isso, foi adotada uma **rodada executiva** (`fase4-executiva`) com
subsets substanciais e representativos, totalizando 2.142 casos únicos e
32.130 chamadas.
