# Benchmark HumanEval — Coder Agent

Executa o benchmark [HumanEval](https://github.com/openai/human-eval) usando o
**Coder Agent** do projeto (`adk/src/agents/workflow_coding_review/coder/`) como
gerador de código, e os **testes canônicos oficiais** do HumanEval como avaliador.

## Separação de responsabilidades

| Etapa | Responsável | Detalhe |
| ----- | ----------- | ------- |
| Geração | `cr_coder_agent` (real) | Implementa a função pedida em `solution.py`. |
| Avaliação | Teste canônico do HumanEval | Roda `check(entry_point)` isolado no `DirectSandbox`. |
| Métrica | `metrics.py` | Estimador não-enviesado `pass@k`. |

> A avaliação **nunca** usa os testes que o coder porventura escreve — apenas os
> testes oficiais do dataset. Isso garante uma pontuação justa.

## Pré-requisitos

- Ambiente Python do `adk/` já instalado (mesmas dependências do projeto).
- Credencial do LLM configurada no `adk/.env` (ex.: token do provider).
- Modelo informado explicitamente via `--model` (argumento **obrigatório**).
- Acesso à internet no primeiro uso (download dinâmico do dataset).

## Uso

A partir da raiz do repositório:

```bash
# Smoke test: 3 problemas, 1 amostra cada (pass@1)
python -m benchmarks.coding_review.humaneval.run --model github_copilot/gpt-4 --limit 3

# Problemas específicos
python -m benchmarks.coding_review.humaneval.run --model github_copilot/gpt-4 --task-ids HumanEval/0 HumanEval/2

# pass@k com múltiplas amostras
python -m benchmarks.coding_review.humaneval.run --model github_copilot/gpt-4 --limit 20 --samples 5 --k 1 5

# Retomar uma execução interrompida (pula problemas já concluídos)
python -m benchmarks.coding_review.humaneval.run \
  --model github_copilot/gpt-4 --samples 5 --k 1 5 \
  --resume-dir results/run_20260822_120000_github_copilot-gpt-4_n5_k1-5
```

> O parâmetro `--model` é **obrigatório**: a execução aborta com erro se ele não
> for informado.

### Principais flags

| Flag | Default | Descrição |
| ---- | ------- | --------- |
| `--model` | **obrigatório** | Modelo LLM a utilizar (ex.: `github_copilot/gpt-4`). |
| `--limit` | todos (164) | Máximo de problemas. |
| `--task-ids` | — | Filtra por `task_id` específicos. |
| `--samples` | 1 | Amostras por problema (n). |
| `--k` | 1 | Valores de k para pass@k. |
| `--timeout` | 30 | Teto (s) por avaliação no sandbox. |
| `--output-dir` | `results/` | Base dos relatórios. |
| `--resume-dir` | — | Retoma um run existente e completa os problemas restantes. |

## Saídas

Cada execução cria um diretório em `results/` com nome **descritivo**, formado
pelo timestamp e pelos parâmetros que caracterizam o run:

```
run_<timestamp>_<modelo>_n<samples>_k<k>[_lim<limit>]
```

Exemplos:

- `run_20260822_120000_github_copilot-gpt-4_n1_k1`
- `run_20260822_120000_github_copilot-gpt-4_n5_k1-5_lim20`

O id do modelo é sanitizado (barras e caracteres inseguros viram `-`) para ser
um nome de diretório válido. Cada diretório contém:

- `report.json` — relatório completo (métricas + por problema + por amostra).
- `report.md` — resumo legível.
- `metadata.json` — parâmetros da execução (`model`, `samples`, `k`, `timeout`).
- `progress.jsonl` — checkpoint incremental (um problema concluído por linha).
- `workspace/` — workspace do coder usado na execução (para inspeção).

### Retomada (Resume Guard)

Ao usar `--resume-dir`, o benchmark lê o `progress.jsonl` e **pula** os problemas
já concluídos, completando apenas os restantes. Antes de retomar, um _guard_
valida que os parâmetros atuais (`model`, `samples`, `k`, `timeout`) coincidem
com os originais persistidos no `metadata.json` — abortando com erro em caso de
divergência, para evitar misturar resultados de configurações diferentes. Runs
antigos sem `metadata.json` são validados retroativamente a partir do
`progress.jsonl`/`report.json` e migrados automaticamente.

## Sandbox

O padrão é o `DirectSandbox` (subprocess efêmero, env limpo, limites de recurso,
timeout de wall-clock) — rápido e adequado para muitos problemas. Como o código
avaliado é gerado por LLM, prefira rodar em um ambiente já isolado (container/CI)
quando usar `DirectSandbox`.

## Arquitetura dos módulos

- `bootstrap.py` — prepara `sys.path`, `.env`, provider LiteLLM e workspace.
- `dataset.py` — download dinâmico + parsing do `.jsonl.gz`.
- `contract.py` — problema → contrato de task + mensagem de entrada do coder.
- `coder_runner.py` — invoca o `cr_coder_agent` via `Runner` do ADK.
- `grading.py` — teste canônico executado no `DirectSandbox`.
- `metrics.py` — cálculo `pass@k`.
- `run.py` — orquestrador CLI.
