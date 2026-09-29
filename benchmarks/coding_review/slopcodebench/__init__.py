"""Benchmark SlopCodeBench sobre o Coder Agent (workflow_coding_review/coder).

Este pacote mede a degradação do Coder Agent em tarefas iterativas longas
usando o SlopCodeBench (https://scbench.ai, arXiv:2603.24755): o
`cr_coder_agent` estende o próprio código checkpoint a checkpoint, e o
avaliador oficial do benchmark julga cada checkpoint.

Separação de responsabilidades:
- Geração: o `cr_coder_agent` implementa a spec de cada checkpoint sobre o
  workspace deixado pelo checkpoint anterior.
- Avaliação: o protocolo oficial do SlopCodeBench (testes ocultos, incluindo
  regressão) e a métrica de slop do próprio benchmark — nada reimplementado.
"""
