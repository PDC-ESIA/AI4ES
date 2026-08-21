"""Benchmark HumanEval sobre o Coder Agent (workflow_coding_review/coder).

Este pacote orquestra a execução do benchmark HumanEval usando o Coder Agent
real do projeto como gerador de código, e os testes canônicos oficiais do
HumanEval como avaliador (grading), executados no `DirectSandbox` do projeto.

Separação de responsabilidades:
- Geração: o `cr_coder_agent` implementa a função pedida (código do modelo).
- Avaliação: os testes canônicos do HumanEval rodam contra o código gerado,
  isolados no `DirectSandbox` — nunca os testes auto-autorados pelo coder.
"""
