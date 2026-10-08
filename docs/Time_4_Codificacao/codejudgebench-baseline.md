# CodeJudgeBench (CodeRepair) para o `cr_reviewer` — escolha e baseline

Issue: #421 · Código: `benchmarks/coding_review/codejudgebench/`

## Por que o CodeJudgeBench

O `cr_reviewer` decide se o código entregue pelo `cr_coder` está aceitável, e até
aqui não havia nenhuma medição da qualidade desse julgamento. O
[CodeJudgeBench](https://huggingface.co/datasets/mattymchen/codejudgebench)
([arXiv:2507.10535](https://arxiv.org/abs/2507.10535)) traz, no split **CodeRepair**,
pares de tentativas de correção para o mesmo código com bug: uma passa nos testes
ocultos (`pos`) e outra falha (`neg`). O rótulo vem da execução feita pelos autores,
então o gabarito é objetivo e nenhum código é executado no nosso lado.

É erro de programação, não validação de negócio — coerente com o próprio prompt do
reviewer: *"Você NÃO faz validação de requisitos. Você faz verificação."*

## Como foi medido

- **Pares:** 50 de 50 problemas distintos (máx. 1 par por problema), sorteados com
  seed 42 do split `claude_3.7_sonnet` (dataset rev `dd766c8a8e8d`): 23 easy,
  16 medium, 11 hard. O split de respostas geradas por Claude evita auto-preferência
  dos modelos avaliados.
- **Modo pontual:** o reviewer avalia um workspace e devolve APROVADO/BLOQUEADO; não
  tem campo de preferência entre duas respostas. Cada resposta é revisada sozinha, e a
  escolha é derivada dos dois vereditos (aprovou `pos` e bloqueou `neg` = acerto).
- **Agente intacto:** prompt, schema, análise estática (Ruff + Bandit) e gate de
  cobertura não foram alterados. O veredito é lido pela mesma função que o manifesto
  usa em produção (`manifest._validation_verdict`).
- **O que o harness fornece:** o código da resposta em `coder/src/solution.py`, a task
  no formato do context_engineer (enunciado, código com defeito, falha observada), e
  um `task_iteration_summary` mínimo para o gate de cobertura — que, sem ele, força
  BLOQUEADO em 100% das revisões. O summary não alega que testes passaram.
- **Ambiente de execução:** o `solution.py` traz o cabeçalho de imports que o
  LiveCodeBench (origem do dataset) insere antes de executar qualquer solução. Uma
  primeira rodada sem ele foi **descartada**: respostas LeetCode corretas usam `List`
  sem importar e eram bloqueadas como `NameError` (19 dos 32 bloqueios indevidos do
  gpt-5-mini, 6 dos 9 do gpt-4.1).
- **Modelos:** `github_copilot/gpt-4` (configurado no `.env` do projeto; servido pela
  API como `gpt-4.1-2025-04-14`) e `github_copilot/gpt-5-mini`. Uma execução por par.

## Baseline obtido

| Métrica | gpt-4.1 | gpt-5-mini |
| --- | --- | --- |
| Acurácia do julgamento (empate = erro) | **12,0%** (6/50) · IC 5,6–23,8% | **58,0%** (29/50) · IC 44,2–70,6% |
| Aprovou código que falha nos testes | 88,0% (44/50) · IC 76,2–94,4% | 12,0% (6/50) · IC 5,6–23,8% |
| Bloqueou código que passa nos testes | 0,0% (0/50) · IC 0,0–7,1% | 32,0% (16/50) · IC 20,8–45,8% |
| Vereditos diferentes para `pos` e `neg` | 12,0% (6/50) | 60,0% (30/50) |
| Acurácia quando decidiu | 100% (6/6) | 96,7% (29/30) |
| Viés posicional | n/a (modo pontual) | n/a (modo pontual) |
| Resposta inválida (sem status reconhecível) | 0,0% (0/100) | 0,0% (0/100) |
| Acurácia por dificuldade (easy · medium · hard) | 21,7% · 6,2% · 0,0% | 60,9% · 62,5% · 45,5% |

ICs de Wilson a 95%. Desfechos dos pares — gpt-4.1: 6 acertos, 44 empates aprovando
as duas respostas. gpt-5-mini: 29 acertos, 15 empates bloqueando as duas, 5 empates
aprovando as duas, 1 erro.

**Comparação pareada:** o gpt-5-mini acertou 26 pares que o gpt-4.1 errou; o inverso
ocorreu em 3. McNemar exato: p < 0,001.

Execução: gpt-4.1 com 200 interações de LLM, ~756 mil tokens de entrada, ~8 min e 0
créditos (modelo incluído no plano Copilot Business); gpt-5-mini com 200 interações,
~774 mil tokens de entrada, ~295 mil de saída, ~60 min e ~170 créditos.

Resultados versionados em:

- `benchmarks/coding_review/codejudgebench/results/run_20261006_123438_github_copilot-gpt-4_n50/`
- `benchmarks/coding_review/codejudgebench/results/run_20261006_123438_github_copilot-gpt-5-mini_n50/`

## Leitura dos resultados

- **Com o modelo configurado hoje, o reviewer funciona como carimbo de aprovação.** O
  gpt-4.1 lê o código (chama a tool de leitura em toda revisão), mas aprova 88% das
  correções que falham nos testes. Quando decide, acerta; o problema é não encontrar
  o defeito.
- **Trocar o modelo é a alavanca de maior impacto medida.** Sem mudar prompt nem
  código, o gpt-5-mini sobe a acurácia de 12% para 58% e derruba a aprovação de
  código quebrado de 88% para 12%.
- **O custo da troca é rigor demais com desempenho.** O gpt-5-mini bloqueia 32% das
  respostas corretas; em 14 dos 16 casos a issue crítica é uma previsão de Time Limit
  Exceeded que não se confirma nos testes. As issues críticas desses bloqueios caem em
  corretude (13) e arquitetura (5).
- **O formato de saída não foi gargalo:** zero respostas inválidas em 200 revisões.
  O ruído SDLC esperado (bloquear por falta de testes ou README) não apareceu.

## Desvios em relação à issue

- **Viés posicional:** a issue pede cada par nas duas ordens (A/B e B/A). No modo
  pontual não existe ordem a inverter, e um modo pareado exigiria mudar o schema do
  reviewer, fora do escopo. A métrica sai como n/a com a justificativa no relatório.
- **`schemas.py`:** o reviewer produz markdown e não usa o `ReviewOutput`. O harness
  converte o markdown em `ReviewOutput`; "resposta inválida" é a revisão sem status
  que o manifesto reconheça. O retry fica no harness, não no agente.
- **Local da nota:** `docs/squad2/levantamento-benchmarking` é um arquivo
  placeholder, não uma pasta. A nota segue o padrão do #422, em `docs/Time_4_Codificacao/`.
- **Premissa do contexto:** na develop atual o reviewer roda uma vez, depois do loop
  coder↔executor, e seu veredito define o status da fase no manifesto — não a parada
  do loop.

## Limitações (resumo; detalhes no README do benchmark)

- Programação competitiva cabe num arquivo, sem testes nem README: mede corretude,
  não as camadas de completude e arquitetura do reviewer.
- Uma execução por par; o protocolo sugere 10 a 20 para medir estabilidade.
- Com o cabeçalho de imports, o Ruff não distingue nome indefinido de nome vindo do
  ambiente — igual ao ambiente real dos testes.
- A leitura das issues (severidade, camada) é heurística sobre markdown livre; o
  veredito não é.

## Como reproduzir

```bash
# a partir da raiz do repositório, com o adk/.venv
python -m benchmarks.coding_review.codejudgebench.run --model github_copilot/gpt-4 --limit 50
python -m benchmarks.coding_review.codejudgebench.run --model github_copilot/gpt-5-mini --limit 50

# reler as revisões salvas com o parser atual, sem chamar o LLM
python -m benchmarks.coding_review.codejudgebench.regrade benchmarks/coding_review/codejudgebench/results/run_<ts>_<modelo>_n50
```

## Próximos passos (outras issues)

- Decidir o modelo oficial do reviewer: os dados mostram que o gpt-4.1 não serve
  para essa função.
- Reduzir o rigor com desempenho: suspeita de TLE sem execução como `warning`, não
  `critical`; medir nos mesmos 50 pares.
- Melhorias estruturais do reviewer: saída validada pelo `ReviewOutput`, regra de
  decisão em código e prompt sem remendos via `.replace()`.
- Avaliar o reviewer dentro do loop coder↔executor.
- Re-rodar este benchmark, com os mesmos pares e a mesma seed, após cada mudança.
