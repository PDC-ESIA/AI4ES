# BigCodeBench (complete) para o `cr_coder` — escolha e baseline

Issue: #422 · Código: `benchmarks/coding_review/bigcodebench/`

## Por que o BigCodeBench

O HumanEval, único benchmark do `cr_coder` até aqui, usa funções curtas e
autocontidas, quase sem dependências externas. Isso não representa o
`workflow_coding_review`, em que o agente compõe chamadas a bibliotecas de terceiros
a partir de instruções longas. O [BigCodeBench](https://huggingface.co/datasets/bigcode/bigcodebench)
([arXiv:2406.15877](https://arxiv.org/abs/2406.15877)) cobre essa lacuna: 1.140
tarefas sobre 139 bibliotecas.

Escolhemos o split **complete** (parte da docstring completa), por ser o mais próximo
do formato já usado no HumanEval. O split instruct fica para outra issue.

## Como foi medido

- **Tarefas:** 50 sorteadas do dataset (v0.1.4) com seed fixa 42 — escopo da primeira
  rodada, para validar o pipeline e obter um baseline inicial.
- **Modelo:** `github_copilot/gpt-4`, o mesmo nos dois benchmarks. 1 amostra por tarefa (pass@1).
- **Nota:** testes oficiais do dataset, sem reimplementar o grading.
- **Sandbox:** o código gerado roda só em container Docker (imagem com as bibliotecas
  das tarefas, sem rede, 4 GB de RAM, 2 CPUs). Antes da geração, as 50 soluções de
  referência do dataset passaram no mesmo sandbox (50/50), o que descarta ambiente
  quebrado como causa das falhas.
- **Agente:** o prompt do `cr_coder` não foi alterado; a rodada apenas mede.

## Baseline obtido

| Benchmark | Tarefas | pass@1 |
| --------- | ------- | ------ |
| HumanEval | 50 | **94,0%** (47/50) |
| BigCodeBench (complete) | 50 | **68,0%** (34/50) |
| Variação | | **−26,0 p.p.** (queda relativa de 27,7%) |

Falhas do BigCodeBench (16 de 50):

| Grupo | Qtde | Categorias |
| ----- | ---- | ---------- |
| Biblioteca (ausente / import / API) | 2 | 2 × `api_misuse` |
| Lógica | 14 | 11 × `logic` (asserção), 3 × `runtime_error` |
| Outras (sintaxe, timeout, sem solução, geração, sandbox) | 0 | — |

Execução: BigCodeBench com 195 interações de LLM e ~2,24 M tokens em ~14 min;
HumanEval com 194 interações e ~2,11 M tokens em ~9,5 min.

Resultados versionados em:

- `benchmarks/coding_review/bigcodebench/results/run_20261005_123852_github_copilot-gpt-4_n50/`
- `benchmarks/coding_review/humaneval/results/run_20261005_122558_github_copilot-gpt-4_n1_k1_lim50/`

## Leitura dos resultados

- Com bibliotecas reais, o `cr_coder` perde cerca de 26 p.p. de pass@1 neste modelo.
- A maior parte da queda não é biblioteca ausente: nenhuma falha foi `missing_dependency`
  ou `import_error`. Predominam falhas de lógica — o código roda, mas não cumpre o
  contrato da docstring (valores de retorno, tipos de exceção, rótulos de gráfico,
  estrutura do DataFrame). Usos incorretos de API aparecem, mas são poucos
  (ex.: `datetime.datetime.timedelta`, que não existe).
- Esta nota **não** propõe correção do prompt (fora de escopo da issue).

## Limitações (resumo; detalhes no README do benchmark)

- **Amostra pequena:** com n=50 o intervalo de confiança de 95% do pass@1 é de
  aproximadamente ±13 p.p. A queda é grande o bastante para ser real, mas os números
  exatos não devem ser tratados como definitivos.
- **Conjuntos diferentes:** as 50 tarefas do HumanEval e as 50 do BigCodeBench são
  problemas distintos; a comparação indica a ordem de grandeza, não uma diferença pareada.
- **`api_misuse` é heurístico:** a categoria vale se qualquer teste levantou erro de
  API, mesmo que outros tenham falhado por lógica; a contagem de "biblioteca" pode
  estar levemente superestimada.
- **Sem rede no sandbox:** tarefas que exigem rede real falhariam mesmo com solução
  correta. Nesta amostra isso não ocorreu (a tarefa 13, que usa FTP, passou porque o
  teste usa mocks).

## Como reproduzir

Requer Docker. Detalhes e flags no README do benchmark.

```bash
# HumanEval (no Windows, via WSL: o DirectSandbox não roda nativamente)
python -m benchmarks.coding_review.humaneval.run --model github_copilot/gpt-4 --limit 50

# BigCodeBench, com a comparação
python -m benchmarks.coding_review.bigcodebench.run --model github_copilot/gpt-4 --limit 50 \
  --verify-canonical --baseline benchmarks/coding_review/humaneval/results/<run_humaneval>
```

## Próximos passos (outras issues)

Escalar para mais tarefas (reduz o intervalo de confiança), rodar o split instruct e
comparar modelos.
