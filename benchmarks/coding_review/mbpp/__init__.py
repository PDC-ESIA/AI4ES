"""Benchmark MBPP sobre o Coder Agent (workflow_coding_review/coder).

Este pacote orquestra a execução do benchmark MBPP (Mostly Basic Python
Problems, versão *sanitized*) usando o Coder Agent real do projeto como
gerador de código, e os testes oficiais (`test_list`/`test_imports` do
dataset) como avaliador (grading), executados no `DirectSandbox` do projeto.

Separação de responsabilidades:
- Geração: o `cr_coder_agent` implementa a função pedida (código do modelo).
- Avaliação: os `assert`s oficiais do MBPP rodam contra o código gerado,
  isolados no `DirectSandbox` — nunca os testes auto-autorados pelo coder.

Mesmas decisões de isolamento e versionamento do benchmark HumanEval (ver
`benchmarks/coding_review/humaneval/`): dataset baixado dinamicamente (não
versionado em git), workspace do coder limpo a cada amostra, grading em
sandbox efêmero e runs identificados/checkpointados por `metadata.json` +
`progress.jsonl`.
"""
