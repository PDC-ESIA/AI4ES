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

Limitações assumidas (detalhes no README do benchmark e em [pontos de atenção](swebench-relatorio.md#5-pontos-de-atenção)): amostra de 30
instâncias, gabarito imperfeito (os testes oficiais só cobrem o que o PR
testou), dataset só com projetos Python, possível contaminação dos modelos e
aprovação do validador baseada na suíte que o próprio coder declara.

## Linha de base

Resultados completos, custo e ressalvas em
[swebench-relatorio.md](swebench-relatorio.md#4-resultados-da-linha-de-base). Como o benchmark
funciona e como foi implementado: seções
[2](swebench-relatorio.md#2-como-o-benchmark-funciona) e
[3](swebench-relatorio.md#3-implementação). Como ler os números:
[pontos de atenção](swebench-relatorio.md#5-pontos-de-atenção).

> **Cobre 26 das 30 instâncias sorteadas** (as outras 4 não foram refeitas após
> uma correção do benchmark, por falta de créditos do LLM). Execução única, um
> modelo. A taxa de resolução tende a estar inflada.

| Campo | Valor |
| ----- | ----- |
| Data do run | 01/10/2026 a 05/10/2026 |
| Modelo | `github_copilot/gemini-3.7-flash` |
| Instâncias / seed / revisão do dataset | 30 sorteadas (26 com resultado válido) / 42 / `78f471bf655a3137b2e8a75af1501690ec009ec3` |
| Instâncias excluídas pelo `--gold-sanity` | Nenhuma: 30/30 resolvidas com o patch oficial (2026-09-29) |
| Harness do executor com a solução oficial (`--executor-sanity`) | 26/30 com sucesso (2026-09-29). As 4 restantes (`matplotlib__matplotlib-25479`, `mwaskom__seaborn-3069`, `pydata__xarray-4687`, `pylint-dev__pylint-7080`) têm testes que falham também na avaliação oficial, fora das listas `FAIL_TO_PASS`/`PASS_TO_PASS`: o SWE-bench os ignora, mas o executor julga pelo código de saída do comando inteiro e reprova |
| **Métrica 1** — resolvidas (IC 95%) | 20/26 (76,9%), IC 57,9% a 89,0%. No primeiro passe, antes da correção do teto: 20/30 (66,7%), IC 48,8% a 80,8% (não comparável) |
| **Métrica 1** — resolvidas sem as exclusões do gold (IC 95%) | Igual à linha acima: o gold não excluiu nenhuma instância |
| **Métrica 2** — rodadas: média / mediana | 1,65 / 1 (mín. 1, máx. 4) |
| **Métrica 2** — paradas: aprovação / política / `max_iterations` / outro | 24 / 2 / 0 / 0 |
| **Métrica 3** — falsos positivos / aprovações (IC 95%) | 5/24 (20,8%), IC 9,2% a 40,5%. Precisão 19/24, recall 19/20 (um falso negativo, `django-12125`) |
| Diretório do run | `benchmarks/coding_review/swebench/results/run_20261001_122939_github_copilot-gemini-3.7-flash_n30/` (o primeiro passe fica em `v1_timeout_contava_o_ritmo/`) |
