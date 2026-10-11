# Comparação TACO × TACO + QA Agent em loop

Benchmark pareado e repetido usando entradas no schema nativo do TACO. Cada par
parte de um único snapshot de código, clonado para o pipeline atual e para o
loop com QA. Um oráculo oculto, que não é fornecido aos agentes, avalia os dois
resultados finais.

## Execução

```bash
compare-qa/.venv-locked/bin/python compare-qa/robust_benchmark.py \
  --model github_copilot/gemini-3.7-flash \
  --repetitions 3 \
  --max-iterations 3
```

Artefatos principais:

- `robust_results.json`: evidência estruturada dos 18 pares.
- `comparacao_pipeline_taco_qa_robusta.md`: tabela comparativa e conclusão.
- `hidden_oracle.json`: oráculo independente usado somente após cada ramo.
- `inputs/`: as seis entradas idênticas usadas nos dois cenários.
- `workspaces/robust_evidence/`: snapshots e evidências por par.
- `compare_pipelines.py`: primitivas de execução compartilhadas pelo benchmark
  robusto.

O ambiente virtual e os workspaces gerados são temporários e ignorados pelo
Git. HumanEval não faz parte da medição.
