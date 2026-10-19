"""Benchmark CodeJudgeBench (split CodeRepair) sobre o Reviewer Agent.

Mede a qualidade do julgamento do `cr_reviewer` (workflow_coding_review/reviewer)
usando pares de tentativas de correção do CodeJudgeBench: para cada problema,
uma resposta que passa nos testes ocultos (`pos_response`) e uma que falha
(`neg_response`). O rótulo já vem do dataset — nenhum código é executado aqui.

Separação de responsabilidades:
- Julgamento: o `cr_reviewer` real avalia cada resposta e emite o veredito.
- Avaliação: o veredito é comparado ao rótulo pos/neg do dataset.
"""
