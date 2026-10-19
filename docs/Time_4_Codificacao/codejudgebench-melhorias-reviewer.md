# Melhorias do `cr_reviewer` medidas pelo CodeJudgeBench

Issue: #421 · Benchmark: `benchmarks/coding_review/codejudgebench/` · Baseline e
método: [`codejudgebench-baseline.md`](codejudgebench-baseline.md)

O benchmark da #421 mede o reviewer como está; esta nota registra as mudanças
**no reviewer** feitas a partir dele, cada uma medida contra o baseline nos mesmos
pares. Ficam numa branch própria porque alteram código de produção
(`reviewer/agent.py`, `reviewer/prompt.py`, `reviewer/structured_output.py`,
`manifest.py`, `shared/review/capability.py`).

Cada mudança é ajustada nos 50 pares de **desenvolvimento** (posições 1–50) e,
quando cabe, confirmada uma única vez nos 50 de **validação** (posições 51–100,
`--offset 50`), problemas nunca vistos durante o ajuste.

Os runs desta nota registram, no `metadata.json`, commits da branch em que foram
executados originalmente (`feature/421-benchmark-codejudgebench`, mantida no
remoto): `cb7056d7` (fase C) e `485b9046` (estabilidade). O código do reviewer e
do harness nesses commits é o mesmo desta branch.

## Fase A — modelo dedicado ao reviewer

**Mudança:** variável `REVIEWER_LLM_MODEL`, com fallback para `ADK_LLM_MODEL`.
Antes, o reviewer lia a mesma variável de todos os agentes, e trocar o modelo do
reviewer trocava também o do coder.

**Evidência:** a comparação de modelos no baseline — no desenvolvimento
(gpt-4.1 12% × gpt-5-mini 58%) e na validação (12% × 70%, McNemar p < 0,001) —
mostra que o modelo é a alavanca de maior impacto. Com o gpt-4.1, hoje no
`.env.example`, o reviewer aprova 88% das correções que falham nos testes.
Recomendação: `REVIEWER_LLM_MODEL=github_copilot/gpt-5-mini`.

## Fase B — rigor com desempenho (investigada, não adotada)

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

## Fase C — robustez estrutural (adotada)

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

## Estabilidade entre execuções

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

## Próximos passos

- **Reviewer dentro do loop coder↔executor** (próxima branch da #421): mudança
  mais profunda, medida pelo efeito no pipeline — o CodeJudgeBench mede o
  julgamento isolado, não o loop. A instabilidade medida acima (cerca de 3 em cada
  10 vereditos mudam entre execuções) precisa entrar no desenho.
- Desempenho deve ser verificado pela execução (o executor, com limite de tempo
  nos testes), não por regra no prompt do reviewer — ver fase B.
