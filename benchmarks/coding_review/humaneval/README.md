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
- Credencial do LLM configurada no `adk/.env` (ex.: `ADK_LLM_MODEL=github_copilot/gpt-4`).
- Acesso à internet no primeiro uso (download dinâmico do dataset).

## Uso

A partir da raiz do repositório:

```bash
# Smoke test: 3 problemas, 1 amostra cada (pass@1)
python -m benchmarks.coding_review.humaneval.run --limit 3

# Problemas específicos
python -m benchmarks.coding_review.humaneval.run --task-ids HumanEval/0 HumanEval/2

# pass@k com múltiplas amostras
python -m benchmarks.coding_review.humaneval.run --limit 20 --samples 5 --k 1 5

# Sobrescrever o modelo
python -m benchmarks.coding_review.humaneval.run --limit 5 --model github_copilot/gpt-4
```

### Principais flags

| Flag | Default | Descrição |
| ---- | ------- | --------- |
| `--limit` | todos (164) | Máximo de problemas. |
| `--task-ids` | — | Filtra por `task_id` específicos. |
| `--samples` | 1 | Amostras por problema (n). |
| `--k` | 1 | Valores de k para pass@k. |
| `--timeout` | 30 | Teto (s) por avaliação no sandbox. |
| `--model` | do `.env` | Sobrescreve `ADK_LLM_MODEL`. |
| `--output-dir` | `results/` | Base dos relatórios. |

## Saídas

Cada execução cria `results/run_<timestamp>/` com:

- `report.json` — relatório completo (métricas + por problema + por amostra).
- `report.md` — resumo legível.
- `workspace/` — workspace do coder usado na execução (para inspeção).

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
