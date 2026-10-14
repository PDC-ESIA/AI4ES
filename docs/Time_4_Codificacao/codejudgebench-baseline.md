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

## Evolução do reviewer

Mudanças medidas contra o baseline, uma de cada vez. Cada uma é ajustada nos 50
pares de **desenvolvimento** (posições 1–50) e confirmada uma única vez nos 50 de
**validação** (posições 51–100, `--offset 50`), problemas distintos e nunca vistos
durante o ajuste — para não decorar a amostra.

### Fase A — modelo dedicado ao reviewer

**Mudança:** variável `REVIEWER_LLM_MODEL`, com fallback para `ADK_LLM_MODEL`.
Antes, trocar o modelo do reviewer trocava o de todos os agentes.

**Validação** (posições 51–100):

| Métrica | gpt-4.1 | gpt-5-mini | McNemar p |
| --- | --- | --- | --- |
| Acurácia do julgamento | 12,0% (6/50) | **70,0%** (35/50) · IC 56,2–80,9% | < 0,001 |
| Aprovou código que falha nos testes | 88,0% (44/50) | 14,0% (7/50) | < 0,001 |
| Bloqueou código que passa nos testes | 0,0% (0/50) | 18,0% (9/50) | 0,004 |
| Acurácia quando decidiu | 100% (6/6) | 97,2% (35/36) | — |

O gpt-5-mini acertou 31 pares que o gpt-4.1 errou; o inverso ocorreu em 2. Os
números repetem o desenvolvimento (gpt-4.1: 12% nos dois conjuntos; gpt-5-mini:
58% → 70%): a vantagem do modelo não é efeito da amostra. O bloqueio indevido do
gpt-5-mini ficou menor na validação (32% → 18%), mas continua o alvo da Fase B.

Resultados: `results/run_20261013_144202_github_copilot-{gpt-4,gpt-5-mini}_n50_off50_fase-a-validacao/`
e a comparação em `results/comparacoes/fase-a-validacao_gpt-4_vs_gpt-5-mini.md`.
O metadata desses runs registra o commit `19b1e6f9`, feito segundos depois do
início; o código executado foi o de `c0cebe2c`, que difere só no README do
benchmark. O harness passou a capturar a versão no início do processo.

### Fase B — rigor com desempenho (investigada, não adotada)

**Hipótese:** o gpt-5-mini bloqueia respostas corretas por prever Time Limit
Exceeded; como o reviewer não executa código, suspeita de desempenho deveria
ser `warning`, não `critical`.

**Antes de mudar o prompt**, a hipótese foi testada sem LLM: as issues que o
reviewer já escreveu nas 200 revisões salvas foram reclassificadas por regra e o
veredito recalculado (`severity_simulation.py`). Sem regra nenhuma (V0), o
simulador concorda com o veredito real em 96/100 revisões nos dois conjuntos.

| Regra | Desenvolvimento: acertos · aprovou neg · bloqueou pos | Validação: idem |
| --- | --- | --- |
| V0 — sem mudança | 27 · 6 · 18 | 32 · 10 · 10 |
| V1 — crítica só de desempenho vira `warning` | **21** · 19 · 10 | **25** · 22 · 8 |
| V2 — idem, exceto se a falha original foi TLE | 28 · 9 · 14 | 31 · 12 · 10 |

**Resultado negativo.** A V1 piora o reviewer: libera respostas corretas, mas
triplica a aprovação de código que falha — muitas `neg` falham nos testes
justamente por tempo (15 das 18 `neg` bloqueadas só por desempenho no
desenvolvimento vinham de código original com TLE). A V2 fica neutra. Nenhuma
justifica um run pago.

**Por quê:** nos bloqueios indevidos que sobram, a análise do reviewer é
plausível — "laços aninhados, O(N²) com N até 3×10⁵" — e ainda assim a resposta
passa nos testes ocultos. A informação que decide se há TLE só existe
executando. Desempenho deve ser verificado pela execução (o executor do
pipeline, com limite de tempo nos testes), não por uma regra no prompt do
reviewer.

### Fase C — robustez estrutural (adotada)

**Mudanças** (sem alterar o critério de julgamento):

- **Ferramenta bloqueada vira diagnóstico.** Um `PermissionError` ao executar
  Ruff ou Bandit caía num `except` genérico e virava "nenhum achado"; agora o
  reviewer recebe `tool-unavailable` com o motivo.
- **Prompt sem remendos.** O `prompt.py` era escrito para "diff git" e adaptado
  em runtime por cinco `.replace()` de strings exatas, que falhavam em silêncio a
  qualquer edição. Agora o texto é o usado de fato — idêntico byte a byte ao que
  o reviewer recebia — e testes guardam o que as substituições garantiam.
- **Saída estruturada e decisão em código.** O reviewer encerra a análise com um
  bloco JSON no formato do `ReviewOutput`. Em Python, o JSON é validado e o status
  é decidido pela regra que vivia só no prompt (qualquer `critical` bloqueia; o
  gate de cobertura continua tendo precedência). O resultado vai para
  `verificacao_revisao.json`, que o manifesto lê antes do markdown; sem JSON
  válido, nada muda em relação ao comportamento anterior.

**Não-regressão** (desenvolvimento, mesmos 50 pares do baseline):

| Métrica | gpt-4.1: baseline → fase C | gpt-5-mini: baseline → fase C |
| --- | --- | --- |
| Acurácia do julgamento | 12,0% → 12,0% (p = 1,000) | 58,0% → 58,0% (p = 1,000) |
| Aprovou código que falha nos testes | 88,0% → 88,0% | 12,0% → 14,0% (p = 1,000) |
| Bloqueou código que passa nos testes | 0,0% → 0,0% | 32,0% → 28,0% (p = 0,727) |
| Saída estruturada válida (`ReviewOutput`) | — → **100% (100/100)** | — → **100% (100/100)** |
| Status corrigido pela regra em código | — → 0 | — → 0 |
| Pares que mudaram de desfecho | 2 | 18 (8 para melhor, 8 para pior) |

Nenhuma métrica mudou de forma significativa, e a aderência ao `ReviewOutput` —
que antes não tinha como ser medida — ficou em 100% nos dois modelos.

**Variação entre execuções.** A mudança no prompt foi pequena (um bloco JSON no
fim), e ainda assim 18 dos 50 pares do gpt-5-mini mudaram de desfecho, com saldo
zero; no gpt-4.1, só 2. A maior parte dessas trocas é a variação natural do modelo
entre execuções: com o gpt-5-mini, uma diferença de poucos pares entre dois runs
isolados pode ser só ruído.

No run do gpt-4.1, dois pares tiveram `Connection error` com a API do Copilot e
foram refeitos com `--resume-dir`, sem repetir os demais.

Resultados: `results/run_20261013_210125_github_copilot-{gpt-4,gpt-5-mini}_n50_fase-c/`
e as comparações em `results/comparacoes/fase-c_*`.

### Estabilidade entre execuções

A configuração final (gpt-5-mini com o reviewer da fase C) rodou 3 vezes nos
mesmos 50 pares de desenvolvimento (`stability.py`):

| Métrica | Por execução | Média ± desvio |
| --- | --- | --- |
| Acurácia do julgamento | 58% · 64% · 58% | **60,0% ± 3,5 p.p.** |
| Aprovou código que falha nos testes | 14% · 12% · 10% | 12,0% ± 2,0 p.p. |
| Bloqueou código que passa nos testes | 28% · 26% · 38% | 30,7% ± 6,4 p.p. |

**O número agregado é estável; o veredito individual, não.** A acurácia varia
cerca de ±3,5 p.p. entre execuções — um run de 50 pares estima bem o
desempenho. Mas só 24 dos 50 pares tiveram o mesmo desfecho nas 3 execuções, e
29 das 100 respostas receberam vereditos diferentes entre elas: 19 pares foram
acertados sempre, 8 errados sempre e 23 oscilaram.

**Votar não resolve.** Com o veredito mais frequente das 3 revisões, a acurácia
fica igual (29/50); o voto só troca aprovação de código que falha (3) por
bloqueio de código que passa (18), ao triplo do custo.

**Implicação para o pipeline:** o mesmo código revisado duas vezes pode receber
vereditos diferentes em cerca de 3 a cada 10 respostas. Para pôr o reviewer
dentro do loop coder↔executor, essa instabilidade precisa ser considerada: um
juiz que muda de ideia pode fazer o loop oscilar entre bloquear e aprovar.

Resultados: os runs `fase-c`, `estabilidade-r2` e `estabilidade-r3` do gpt-5-mini
e `results/comparacoes/estabilidade_gpt-5-mini_3-execucoes.md`.

## Próximos passos (outras issues)

- Decidir o modelo oficial do reviewer: os dados mostram que o gpt-4.1 não serve
  para essa função.
- Reduzir o rigor com desempenho: suspeita de TLE sem execução como `warning`, não
  `critical`; medir nos mesmos 50 pares.
- Melhorias estruturais do reviewer: saída validada pelo `ReviewOutput`, regra de
  decisão em código e prompt sem remendos via `.replace()`.
- Avaliar o reviewer dentro do loop coder↔executor.
- Re-rodar este benchmark, com os mesmos pares e a mesma seed, após cada mudança.
