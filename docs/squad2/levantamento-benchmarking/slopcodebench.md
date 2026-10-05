# SlopCodeBench — baseline do `cr_coder` (issue #420)

## Por que o SlopCodeBench

O `cr_coder` só era medido pelo HumanEval, que avalia correção em tarefas curtas e de
uma única passada. O [SlopCodeBench](https://scbench.ai)
([arXiv:2603.24755](https://arxiv.org/abs/2603.24755)) mede o que o HumanEval não vê:
cada problema é uma sequência de 3 a 8 checkpoints em que o agente **estende o próprio
código**, com testes ocultos que incluem a regressão dos checkpoints anteriores. Além da
correção, o benchmark define as próprias métricas de qualidade — **verbosidade**
(código redundante/duplicado) e **erosão** (complexidade concentrada em poucas funções)
— calibradas contra 473 repositórios humanos. É a linha de base de degradação de que
precisamos antes de mexer no prompt ou no loop.

## Baseline obtido

**Configuração:** `github_copilot/gpt-4`, só o `cr_coder` (como no HumanEval), 10
problemas sorteados com seed 42 (50 checkpoints), harness oficial no commit `31ceea3`,
catálogo no `38d627e`, `scb-check` 0.1.3. Run de 03 a 05/10/2026.

| Métrica | Resultado |
| ------- | --------- |
| **Correção** — strict / isolated / core | 0% / 0% / **4%** (2 de 50 checkpoints com todos os testes core) |
| **Correção** — quebrou o que funcionava | 2 de 27 checkpoints (39 de 687 testes que passavam antes) |
| **Diff** por checkpoint (média) | +154 / −21 linhas; `churn_ratio` 0,29 |
| **Slop** — verbosidade (média) | **0,37**, de 0,21 no início a 0,46 no fim |
| **Slop** — erosão (média) | **0,68**, de 0,56 no início a 0,74 no fim |
| Trajetórias com erosão / verbosidade subindo | 67% / 78% |
| Custo | ~12 M tokens de entrada, ~2,3 mil créditos do Copilot (uso total do ciclo), 2,7 h de coder |

Para contexto, o paper reporta verbosidade/erosão de **0,19 / 0,34** em código humano e
**0,44 / 0,68** na média dos agentes avaliados.

> **Timeout do LLM:** o run usou `AI4ES_LLM_TIMEOUT=600` (o padrão do projeto é 120 s).
> Com 120 s, o GPT-4 estoura o tempo ao reescrever arquivos grandes; os checkpoints
> afetados foram refeitos. As execuções ficam registradas em `execucoes` no `metadata.json`.

Resultado completo (por checkpoint e por fase):
[`report.md`](../../../benchmarks/coding_review/slopcodebench/results/run_20261003_150411_github_copilot-gpt-4_n10/report.md) ·
como rodar e limitações:
[`README.md`](../../../benchmarks/coding_review/slopcodebench/README.md)
