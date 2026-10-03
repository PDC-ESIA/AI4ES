# Benchmark SlopCodeBench — Coder Agent

Mede a **degradação** do **Coder Agent** (`adk/src/agents/workflow_coding_review/coder/`)
em tarefas iterativas longas, usando o [SlopCodeBench](https://scbench.ai)
([arXiv:2603.24755](https://arxiv.org/abs/2603.24755)). Cada problema é uma
sequência de 3 a 8 checkpoints: a cada um, o coder recebe uma spec nova e
**estende o próprio código** do checkpoint anterior.

Este benchmark **mede**; não corrige nada no coder.

## Separação de responsabilidades

| Etapa | Responsável | Detalhe |
| ----- | ----------- | ------- |
| Geração | `cr_coder_agent` (real) | Implementa a spec do checkpoint sobre o workspace que ele mesmo deixou. |
| Avaliação | Harness oficial do SlopCodeBench | Suíte oculta do checkpoint (core, functionality, error e **regressão** dos anteriores), em Docker. |
| Métricas | Harness oficial + `metrics.py` | Valores por checkpoint vêm do `checkpoint_results.jsonl` oficial; `metrics.py` só agrega. |

> O coder nunca vê `tests/` nem `solutions/` do catálogo: as tools dele só leem o
> workspace do run, que fica fora do catálogo.

## Pré-requisitos

- Ambiente Python do `adk/` já instalado (mesmas dependências do projeto).
- Docker em execução (o avaliador oficial roda os testes em container).
- `uv`/`uvx` no `PATH` (o harness chama `uvx scb-check` para verbosidade/erosão).
- Credencial do LLM configurada no `adk/.env` e modelo informado via `--model`.
- Acesso à internet no primeiro uso (download dinâmico, abaixo).

### Download dinâmico (primeira execução)

Como o dataset do HumanEval, tudo o que vem do SlopCodeBench é baixado sozinho
para `datasets/`, que não é versionado, sempre nos mesmos commits:

| O quê | Repositório | Commit |
| ----- | ----------- | ------ |
| Catálogo de problemas | [`gabeorlanski/scb-problems`](https://github.com/gabeorlanski/scb-problems) | `38d627e` |
| Harness oficial (avaliador) | [`SprocketLab/slop-code-bench`](https://github.com/SprocketLab/slop-code-bench) | `31ceea3` |

O harness não é instalado no venv do `adk`: ele exige Python 3.12 e rebaixaria
dependências do projeto (`litellm`, OpenTelemetry). Na primeira execução, o `run.py`
cria um venv próprio para ele com `uv sync --frozen --python 3.12`, a partir do
`uv.lock` dos próprios autores (alguns minutos; o `uv` baixa um Python 3.12 se
preciso). O benchmark chama esse venv por subprocesso (ver `grading.py`); o
`adk/pyproject.toml`, o `adk/uv.lock` e o `adk/.venv` não mudam.

Para usar checkouts próprios no lugar dos downloads: `SCBENCH_PROBLEMS_PATH`
(ou `--problems-path`) para o catálogo e `SCBENCH_HARNESS_PATH` para o harness (com o
venv já criado por `uv sync --frozen --python 3.12 --project <pasta>`).

## Uso

A partir da raiz do repositório:

```bash
# Baseline da issue: 10 problemas sorteados com a seed padrão (42)
python -m benchmarks.coding_review.slopcodebench.run --model github_copilot/gpt-4 --limit 10

# Smoke test: 1 problema específico
python -m benchmarks.coding_review.slopcodebench.run --model github_copilot/gpt-4 --problems dag_execution

# Retomar uma execução interrompida (pula checkpoints já concluídos)
python -m benchmarks.coding_review.slopcodebench.run --model github_copilot/gpt-4 --limit 10 \
  --resume-dir benchmarks/coding_review/slopcodebench/results/run_20260928_120000_github_copilot-gpt-4_n10
```

### Principais flags

| Flag | Default | Descrição |
| ---- | ------- | --------- |
| `--model` | **obrigatório** | Modelo LLM do coder (ex.: `github_copilot/gpt-4`). |
| `--limit` | todos (36) | Nº de problemas sorteados do catálogo. |
| `--seed` | 42 | Seed do sorteio — a mesma seed devolve o mesmo subset. |
| `--problems` | — | Roda exatamente estes problemas. |
| `--problems-path` | `$SCBENCH_PROBLEMS_PATH` | Checkout local do catálogo; sem ele, baixa o commit fixado para `datasets/`. |
| `--checkpoint-timeout` | 7200 | Limite de relógio (s) do coder por checkpoint, como no paper. |
| `--output-dir` | `results/` | Base dos relatórios. |
| `--resume-dir` | — | Retoma um run existente (Resume Guard valida modelo, seed, problemas e timeout). |

## Protocolo

- **Um problema por vez, checkpoints em ordem.** O workspace do coder só é limpo
  no 1º checkpoint; nos seguintes ele parte do próprio código.
- **Sessão nova a cada checkpoint.** O coder não vê a conversa do checkpoint
  anterior, só a spec nova e o workspace (protocolo do paper, seção 2.2).
- **Prompt oficial.** O enunciado é o template `just-solve` do SlopCodeBench,
  renderizado pela função do próprio harness, dentro do contrato de entrada que
  o coder espera (stack Python e arquivo de entrada; o tipo de produto — CLI ou
  serviço HTTP — é o que a especificação do checkpoint descreve).
- **Continuidade entre checkpoints.** A partir do 2º checkpoint, o estado da
  sessão é semeado como o `TaskIterator` do workflow faz entre tasks
  (`NOVA_TASK:` + fotografia dos arquivos herdados pelo `workspace_guard`). Nada
  no prompt, no guard ou no loop é alterado.
- **Pass policy oficial `any`.** É a política padrão do harness e, no código
  dele, nunca reprova por resultado de teste: todos os checkpoints rodam, mesmo
  com 0 testes passando. A trajetória de um problema só para se o coder falhar
  (erro na geração), como o runner oficial faz com erro do agente; os
  checkpoints restantes contam como não resolvidos.

## Métricas

### 1. Correção ao longo do horizonte

| Métrica | Definição (oficial) |
| ------- | ------------------- |
| `strict_pass_rate` (strict) | Testes passando / total, **incluindo** a regressão (todos os testes dos checkpoints anteriores). |
| `isolated_pass_rate` (isolated) | Mesma conta **sem** a regressão. |

> Os nomes são os que o harness fixado (`31ceea3`) grava no `checkpoint_results.jsonl`.
> O `docs/metrics-reference.md` do próprio harness ainda os chama de `pass_rate` e
> `checkpoint_pass_rate`: a documentação está desatualizada em relação ao código.
| `core_pass_rate` | Só os testes core do checkpoint. |
| Regressão | `regression_passed / regression_total`: o agente quebrou o que já funcionava? |

Um checkpoint é "resolvido" quando a taxa é 1.0. Os solve rates usam como
denominador **todos** os checkpoints previstos (como a Tabela 1 do paper).

### 2. Crescimento do diff

`lines_added`, `lines_removed`, `delta.loc` (% de variação do LOC) e
`delta.churn_ratio = (lines_added + lines_removed) / linhas do checkpoint anterior`,
a partir do 2º checkpoint.

### 3. Slop (definição do SlopCodeBench)

- **Verbosidade** = linhas marcadas por regras AST-grep ∪ linhas clonadas, dividido pelo LOC.
- **Erosão** = fração da massa de complexidade (CC × √SLOC) que está em funções com CC > 10.

Ambas vêm do `scb-check` chamado pelo harness. Checkpoints sem workspace avaliado
são excluídos, não imputados. O relatório inclui a fração de trajetórias em que
cada métrica sobe do 1º ao último checkpoint (no paper: 77% erosão, 75,5% verbosidade).

As fases de progresso usam `compute_progress_bins` do harness (5 faixas, 20%…100%).

## Saídas

```
results/run_<timestamp>_<modelo>_n<N>/
  report.json                # relatório completo
  report.md                  # resumo com as três métricas
  metadata.json              # parâmetros + proveniência (commits, hash do prompt do coder)
  progress.jsonl             # checkpoint incremental (retomada)
  checkpoint_results.jsonl   # linhas oficiais do harness, uma por checkpoint
  workspace/                 # workspace do coder + snapshots/avaliações — NÃO versionado
```

`workspace/` fica fora do git (`.gitignore`): contém o código gerado e cópias das
specs, e os arquivos do SlopCodeBench trazem um canary pedindo que não entrem em
corpora públicos.

## Limitações

- **Amostra pequena.** 10 problemas, um modelo e uma execução dão variância alta:
  o resultado é linha de base, não estimativa precisa.
- **Só o coder.** Como no benchmark HumanEval, roda o `cr_coder_agent` isolado, sem o
  executor Docker do loop nem o reviewer. A "iteração" medida é o checkpoint.
- **Churn do código final.** O SlopCodeBench não mede "quanto do código final foi
  escrito e depois reescrito"; o churn reportado é o oficial, por checkpoint.
- **Custo.** O workflow não expõe preço por modelo: o custo em USD fica 0 e os
  tokens são registrados integralmente.
- **Comparabilidade com o paper.** O paper roda agentes nos harnesses nativos
  (Claude Code, Codex CLI); aqui o coder roda no ADK. Comparar com o paper é só
  indicativo.

## Arquitetura dos módulos

- `bootstrap.py` — prepara `sys.path`, `.env`, provider LiteLLM e workspace.
- `dataset.py` — baixa o catálogo (commit fixado), lista os problemas e sorteia o subset (`--limit`, `--seed`).
- `contract.py` — checkpoint → contrato de task + mensagem de entrada do coder.
- `coder_runner.py` — invoca o `cr_coder_agent` via `Runner` do ADK sobre o workspace do problema.
- `grading.py` — baixa/instala o harness (commit fixado) e é a camada fina sobre o avaliador oficial, executada no venv do harness por subprocesso.
- `metrics.py` — agrega as três métricas a partir das saídas oficiais.
- `run.py` — orquestrador CLI.
