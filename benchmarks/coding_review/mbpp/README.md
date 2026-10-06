# Benchmark MBPP — Coder Agent

Executa o benchmark [MBPP](https://github.com/google-research/google-research/tree/master/mbpp)
(*Mostly Basic Python Problems*, versão **sanitized**, ~427 problemas) usando o
**Coder Agent** do projeto (`adk/src/agents/workflow_coding_review/coder/`) como
gerador de código, e os **testes oficiais** do dataset (`test_imports` +
`test_list`) como avaliador.

Mesmas decisões de isolamento e versionamento do benchmark
[HumanEval](../humaneval/README.md) irmão deste pacote — replicadas aqui
propositalmente para manter os dois benchmarks comparáveis.

## Separação de responsabilidades

| Etapa | Responsável | Detalhe |
| ----- | ----------- | ------- |
| Geração | `cr_coder_agent` (real) | Implementa a função pedida em `solution.py`. |
| Avaliação | `assert`s oficiais do MBPP | Roda `test_imports` + `test_list` isolados no `DirectSandbox`. |
| Métrica | `metrics.py` | Estimador não-enviesado `pass@k` (idêntico ao HumanEval). |

> A avaliação **nunca** usa os testes que o coder porventura escreve — apenas os
> `assert`s oficiais do dataset. Isso garante uma pontuação justa.

## Diferenças em relação ao HumanEval

O MBPP *sanitized* não tem o mesmo formato do HumanEval, então três decisões
de design foram necessárias (sem alterar a filosofia de isolamento/avaliação):

1. **Sem `entry_point` explícito.** O dataset não declara o nome da função-alvo
   (o HumanEval declara). Ele é **derivado** a partir da solução de referência
   (`code`): localizamos as funções de nível de módulo via AST e escolhemos a
   que é de fato referenciada em `test_list` (cross-check, necessário porque
   vários `assert`s embrulham a chamada-alvo, ex.:
   `assert set(func(x)) == set(y)`). Essa estratégia foi validada contra os
   427 problemas do dataset (0 ambiguidades não resolvidas). Ver
   `dataset._derive_entry_point`. A solução de referência **não** é usada para
   avaliar — apenas para nomear o alvo.
2. **Sem `check(candidate)` indireto.** O enunciado do HumanEval usa uma função
   de verificação que recebe o candidato por parâmetro; o MBPP usa `assert`s
   que chamam a função pelo nome direto. O programa de grading (ver
   `grading.py`) carrega o arquivo-solução pelo caminho (`importlib`), expõe
   a função com o nome original (sem alias) e injeta `test_imports` +
   `test_list` tal como vêm do dataset.
3. **Exemplo de assinatura no prompt do coder.** Como o enunciado do MBPP é só
   linguagem natural (sem assinatura de função), seguimos o protocolo original
   do benchmark (Austin et al., 2021): o coder recebe o **primeiro** item de
   `test_list` como exemplo de uso, o suficiente para fixar nome/assinatura
   sem revelar a suíte completa. A avaliação roda contra **todos** os itens de
   `test_list`, incluindo esse primeiro caso.

## Pré-requisitos

- Ambiente Python do `adk/` já instalado (mesmas dependências do projeto).
- Credencial do LLM configurada no `adk/.env` (ex.: token do provider).
- Modelo informado explicitamente via `--model` (argumento **obrigatório**).
- Acesso à internet no primeiro uso (download dinâmico do dataset).

## Uso

A partir da raiz do repositório:

```bash
# Smoke test: 3 problemas, 1 amostra cada (pass@1)
python -m benchmarks.coding_review.mbpp.run --model github_copilot/gpt-4 --limit 3

# Problemas específicos
python -m benchmarks.coding_review.mbpp.run --model github_copilot/gpt-4 --task-ids Mbpp/2 Mbpp_3

# pass@k com múltiplas amostras
python -m benchmarks.coding_review.mbpp.run --model github_copilot/gpt-4 --limit 20 --samples 5 --k 1 5

# Retomar uma execução interrompida (pula problemas já concluídos)
python -m benchmarks.coding_review.mbpp.run \
  --model github_copilot/gpt-4 --samples 5 --k 1 5 \
  --resume-dir benchmarks/coding_review/mbpp/results/run_20260822_120000_github_copilot-gpt-4_n5_k1-5
```

> O parâmetro `--model` é **obrigatório**: a execução aborta com erro se ele não
> for informado.

### Principais flags

| Flag | Default | Descrição |
| ---- | ------- | --------- |
| `--model` | **obrigatório** | Modelo LLM a utilizar (ex.: `github_copilot/gpt-4`). |
| `--limit` | todos (~427) | Máximo de problemas. |
| `--task-ids` | — | Filtra por `task_id` específicos (`Mbpp/2`, `Mbpp_2` ou `2`). |
| `--samples` | 1 | Amostras por problema (n). |
| `--k` | 1 | Valores de k para pass@k. |
| `--timeout` | 30 | Teto (s) por avaliação no sandbox. |
| `--output-dir` | `benchmarks/coding_review/mbpp/results/` | Base dos relatórios. |
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

O padrão é o `DirectSandbox` (subprocess efêmero, env limpo, limites de
recurso, timeout de wall-clock) — rápido e adequado para muitos problemas. Como
o código avaliado é gerado por LLM, prefira rodar em um ambiente já isolado
(container/CI) quando usar `DirectSandbox`.

## Arquitetura dos módulos

- `bootstrap.py` — prepara `sys.path`, `.env`, provider LiteLLM e workspace.
- `dataset.py` — download dinâmico + parsing do `sanitized-mbpp.json`,
  incluindo a derivação do `entry_point`.
- `contract.py` — problema → contrato de task + mensagem de entrada do coder.
- `coder_runner.py` — invoca o `cr_coder_agent` via `Runner` do ADK.
- `grading.py` — testes oficiais (`test_imports` + `test_list`) executados no
  `DirectSandbox`.
- `metrics.py` — cálculo `pass@k`.
- `run.py` — orquestrador CLI.
