# Benchmark do loop coder → executor: escolha do SWE-bench Verified

Issue: #417 · Implementação: [`benchmarks/coding_review/swebench/`](../../../benchmarks/coding_review/swebench/README.md)

## Por que um benchmark para o executor

O `cr_coder` já tinha benchmarks (HumanEval, MBPP), mas o `cr_executor`, o
`implementation_validator` e a política de parada do loop
(`executor/loop_policy.py`) não tinham medição nenhuma. O executor não gera
código: ele **julga** o que o coder produziu e decide quando o loop para. Por
isso métricas de geração como o pass@k não servem para ele. O que interessa é
quanto o sinal de "aprovado" dele corresponde à realidade e como o loop gasta
as suas rodadas.

## O que foi levantado

Referências internas: os benchmarks de outras squads, que separam os resultados
por dataset e nunca fundem métricas de fontes diferentes (Agente de QA, Fases 3
e 4); o harness LLM-as-a-Judge do Agente de Requisitos
(`time1/benchmarking`); e o protocolo de avaliação comparativa de LLMs.

Candidatos externos avaliados para as funcionalidades do executor:

| Candidato | Cobriria | Situação |
| --------- | -------- | -------- |
| **SWE-bench Verified** | Juiz + harness + loop completo, com bugs reais e gabarito executável | **Escolhido** para a linha de base |
| CodeJudgeBench (split CodeRepair) | Julgamento de correção, sem execução | Fora do escopo da #417 |
| SlopCodeBench, AgentBoard (progress rate) | Dinâmica de iterações e platô | Fora do escopo da #417 |
| CUDABeaver, VRR-Stop | Sinais de estagnação e critério de parada | Fora do escopo da #417 |

Pela issue #417, os demais só entram em issue separada, **depois** da linha de
base.

## Por que o SWE-bench Verified

- São issues reais de projetos Python populares, revisadas por humanos, com
  gabarito executável (`FAIL_TO_PASS` e `PASS_TO_PASS`) e harness oficial
  (nada de reimplementar a correção).
- Rodando o loop do workflow sobre cada issue, um único dataset mede as três
  coisas pedidas: resolução, rodadas e motivo de parada, e concordância do
  validador.
- A arquitetura bate com a nossa: evidência determinística (testes) separada do
  veredito, como o harness (sensor) e o validador (juiz) do executor.
- Os testes do gabarito foram escritos por desenvolvedores humanos, então
  servem de evidência **independente** do coder.

Limitações assumidas (detalhes no README do benchmark): amostra de 30
instâncias, gabarito imperfeito (os testes oficiais só cobrem o que o PR
testou), dataset só com projetos Python, possível contaminação dos modelos e
aprovação do validador baseada na suíte que o próprio coder declara.

## Linha de base

> **A preencher após o primeiro run completo** (critério de aceite da #417):
> `python -m benchmarks.coding_review.swebench.run --model <m> --limit 30`

| Campo | Valor |
| ----- | ----- |
| Data do run | — |
| Modelo | — |
| Instâncias / seed / revisão do dataset | 30 / 42 / `78f471bf655a3137b2e8a75af1501690ec009ec3` |
| Instâncias excluídas pelo `--gold-sanity` | Nenhuma: 30/30 resolvidas com o patch oficial (2026-09-29) |
| Harness do executor com a solução oficial (`--executor-sanity`) | 26/30 com sucesso (2026-09-29). As 4 restantes (`matplotlib__matplotlib-25479`, `mwaskom__seaborn-3069`, `pydata__xarray-4687`, `pylint-dev__pylint-7080`) têm testes que falham também na avaliação oficial, fora das listas `FAIL_TO_PASS`/`PASS_TO_PASS`: o SWE-bench os ignora, mas o executor julga pelo código de saída do comando inteiro e reprova |
| **Métrica 1** — resolvidas (IC 95%) | — |
| **Métrica 1** — resolvidas sem as exclusões do gold (IC 95%) | — |
| **Métrica 2** — rodadas: média / mediana | — |
| **Métrica 2** — paradas: aprovação / política / `max_iterations` / outro | — |
| **Métrica 3** — falsos positivos / aprovações (IC 95%) | — |
| Diretório do run | `benchmarks/coding_review/swebench/results/run_20260929_122944_github_copilot-gpt-4_n30/` (sorteio e sanidades prontos; loop pendente de cota de LLM) |
