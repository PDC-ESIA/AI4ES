"""Coleta de testes do benchmark: só o código, nunca os dados de um run.

O harness oficial grava `test_output.txt` nos logs de `results/`, e o pytest
coleta `test*.txt` como doctest por padrão — rodar a suíte depois de um run
quebraria a coleta.
"""

collect_ignore_glob = ["results/*", "datasets/*", ".venv-swebench/*"]
