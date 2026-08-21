# Benchmark de LLMs — Agente de QA

Infraestrutura do estudo de benchmarking definido em `benchmark/PR.md`,
seguindo o `benchmark/Protocolo de Avaliação Comparativa de Modelos de
Linguagem - Benchmarking - v1.2.md` (seção 4.4 — Agente de Testes/QA).

## Layout (orientado a rodadas)

Cada rodada de benchmark é autocontida em `benchmarks/rodadas/<nome>/`:
config, prompts, subsets e resultados vivem juntos — impossível confundir
de qual experimento são os dados. O código em `scripts/` é compartilhado.

```
benchmarks/
├── rodadas/
│   └── fase3-piloto/              # exemplo: piloto da Fase 3
│       ├── config.yaml            # modelos, temp, k, timeouts, tamanhos dos subsets
│       ├── prompts.yaml           # prompts padronizados zero-shot
│       ├── subsets/               # JSONLs amostrados + manifest (seed, SHA-256)
│       └── resultados/
│           ├── <modelo>/<benchmark>/runs.jsonl   # registro bruto por chamada
│           └── summary.{json,md}                 # métricas agregadas
├── scripts/                       # harness reutilizável entre rodadas
└── .venv/                         # ambiente (gitignored)
```

Datasets brutos ficam em `benchmark/datasets/` (**gitignored**, compartilhados
entre rodadas); os subsets versionados por rodada são a entrada real dos
experimentos.

## Como criar uma nova rodada

```bash
mkdir -p benchmarks/rodadas/<nome>
cp benchmarks/rodadas/fase3-piloto/config.yaml  benchmarks/rodadas/<nome>/
cp benchmarks/rodadas/fase3-piloto/prompts.yaml benchmarks/rodadas/<nome>/
# edite config.yaml: run_id, models, repetitions, subsets...
```

## Reprodução

```bash
# 1. Ambiente (Python 3.14 + litellm + pyarrow)
/opt/homebrew/opt/python@3.14/bin/python3.14 -m venv benchmarks/.venv
benchmarks/.venv/bin/pip install litellm pyarrow pyyaml python-dotenv requests tenacity

# 2. Credenciais — benchmark/.env (gitignored):
#    HF_TOKEN=...            (GAIA, gated no Hugging Face)
#    GOOGLE_API_KEY=...      (baseline Gemini)
#    Copilot: device-flow automático via preflight (~/.config/litellm/github_copilot)

# 3. Download e normalização dos datasets (uma vez; compartilhado entre rodadas)
benchmarks/.venv/bin/python benchmarks/scripts/download_datasets.py

# 4. Amostragem determinística dos subsets da rodada
benchmarks/.venv/bin/python benchmarks/scripts/sample_subsets.py --rodada fase3-piloto

# 5. Preflight de credenciais (dispara device-flow do Copilot se preciso)
benchmarks/.venv/bin/python benchmarks/scripts/preflight_models.py --rodada fase3-piloto

# 6. Dry-run (contagem de chamadas + estimativa de custo) e execução
benchmarks/.venv/bin/python benchmarks/scripts/run_benchmark.py --rodada fase3-piloto --dry-run
benchmarks/.venv/bin/python benchmarks/scripts/run_benchmark.py --rodada fase3-piloto

# 7. Métricas agregadas da rodada
benchmarks/.venv/bin/python benchmarks/scripts/aggregate.py --rodada fase3-piloto
```

## Modelos do piloto (rodada fase3-piloto)

| Modelo | Papel | Acesso |
|---|---|---|
| `gemini/gemini-2.5-flash` | baseline oficial do PR (usado no fluxo TACO/QA) | GOOGLE_API_KEY |
| `github_copilot/gpt-5.4` | alternativa comercial GPT | OAuth Copilot (device-flow) |
| `github_copilot/gemini-3.5-flash` | geração Gemini atual via Copilot | OAuth Copilot |

`gpt-5.4` confirmado no preflight como o GPT de geração atual acessível via
`/chat/completions` na conta (`gpt-5.4-mini`/`gpt-5.5` só aceitam Responses API;
`gpt-4.1`, `gpt-4o`, `gpt-4o-mini` também funcionam). O Copilot **não** expõe
o gemini-2.5-flash — apenas geração 3.x.

## Notas metodológicas

- **Isolamento**: chamadas LiteLLM diretas, sem passar pelo agente ADK.
- **Copilot**: headers de IDE + `X-Initiator: user` replicados de
  `adk/shared/llm.py` para evitar a cota reduzida de "utility models".
- **Rate-limit**: retries internos do LiteLLM zerados; em `RateLimitError` o
  runner espera o tempo sugerido pela API antes de tentar novamente.
- **Retomada**: registros `ok/empty` existentes são pulados; falhas de API são
  reexecutadas e contabilizadas separadamente das falhas de qualidade.
- **Custo**: `litellm.completion_cost()` quando o provider expõe preço
  (Gemini); Copilot é incluso na assinatura → custo marginal zero.
- **Modelos thinking**: exigem `model_max_tokens` maior (raciocínio + resposta);
  com limite baixo a resposta final vem vazia.
