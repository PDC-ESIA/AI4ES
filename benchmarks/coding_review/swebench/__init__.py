"""Benchmark SWE-bench Verified sobre o loop coder → executor (issue #417).

Mede o `code_execute_loop` do `workflow_coding_review` (coder ↔ executor, com o
`implementation_validator` e a política de progresso dentro do executor) sobre
instâncias reais do SWE-bench Verified, e corrige o resultado com o harness
OFICIAL do SWE-bench — nunca com os testes que o próprio coder escreveu.

Três métricas (ver `metrics.py` e o README):
1. taxa de resolução (harness oficial);
2. rodadas do loop e motivo de encerramento;
3. concordância do validador (aprovou × resolveu de fato).

O benchmark mede, não corrige: nenhum módulo daqui altera o executor, o
validador ou a `loop_policy`.
"""
