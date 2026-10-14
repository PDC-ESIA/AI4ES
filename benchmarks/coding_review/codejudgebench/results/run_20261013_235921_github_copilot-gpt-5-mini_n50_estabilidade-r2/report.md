# Benchmark CodeJudgeBench (CodeRepair) — Reviewer Agent

- **Gerado em:** 2026-10-14T03:36:35.691163+00:00
- **Status do run:** completo
- **Experimento:** `estabilidade-r2` · código `485b9046`
- **Modelo do reviewer:** `github_copilot/gpt-5-mini`
- **Dataset:** `mattymchen/codejudgebench` · config `coderepair` · split `claude_3.7_sonnet` · revisão `dd766c8a8e8d`
- **Amostra:** 50 pares (posições 1–50) · seed 42 · máx. 1 par(es) por problema
- **Modo:** pontual (cada resposta revisada separadamente) · relato do coder: sim · retries: 1 · análise estática: ligada

## Métricas da issue #421

| Métrica | Valor | IC 95% | k/n |
| --- | --- | --- | --- |
| Acurácia do julgamento (empate = erro) | 64.0% | 50.1% – 75.9% | 32/50 |
| Viés posicional | n/a | — | — |
| Resposta inválida — status não reconhecido pelo manifesto (1ª tentativa) | 0.0% | 0.0% – 3.7% | 0/100 |
| Resposta inválida — status não reconhecido pelo manifesto (após retries) | 0.0% | 0.0% – 3.7% | 0/100 |

> Viés posicional: Não aplicável ao modo pontual: cada revisão vê uma única resposta, então não existe ordem A/B a inverter.
>
> Resposta inválida mede se o pipeline consegue ler o veredito (a linha `Status:` que o manifesto procura). O reviewer produz markdown, não JSON: não há aderência ao `ReviewOutput` a medir — o harness converte o markdown nesse schema depois.

## Decisão por resposta

| Métrica | Valor | IC 95% | k/n |
| --- | --- | --- | --- |
| Aprovou código que falha nos testes (neg aprovada) | 12.0% | 5.6% – 23.8% | 6/50 |
| Bloqueou código que passa nos testes (pos bloqueada) | 26.0% | 15.9% – 39.6% | 13/50 |

Camadas das issues críticas nos bloqueios indevidos: corretude=14, arquitetura=2

## Julgamento detalhado

| Métrica | Valor | IC 95% | k/n |
| --- | --- | --- | --- |
| Decisividade (vereditos diferentes) | 66.0% | 52.1% – 77.6% | 33/50 |
| Acurácia entre pares decididos | 97.0% | 84.7% – 99.5% | 32/33 |
| Acurácia com empate = ½ acerto | 81.0% | — | — |

| Desfecho | Pares |
| --- | --- |
| `correct` | 32 |
| `tie_approve` | 5 |
| `tie_block` | 12 |
| `wrong` | 1 |

## Por dificuldade

| Dificuldade | Acurácia | IC 95% | k/n |
| --- | --- | --- | --- |
| easy | 65.2% | 44.9% – 81.2% | 15/23 |
| hard | 45.5% | 21.3% – 72.0% | 5/11 |
| medium | 75.0% | 50.5% – 89.8% | 12/16 |

## Aderência e execução

- Saída estruturada válida (`ReviewOutput`): 100.0% (100/100) · status corrigido pela regra em código: 0
- Respostas com retry: 0
- Falhas só de formato (status existe, mas fora do padrão do manifesto): 0
- Gate de cobertura aplicado: 0 (esperado 0 — senão o summary sintético está errado)
- Respostas com falha operacional: 0
- Respostas sem bloco de código no dataset: 0
- Revisões executadas: 100 · interações LLM: 200 · tokens (in/out): 811738/310459
- Tempo total de revisão: 2216.1s · tempo total do run: 2218.3s

## Por par

| Par | Dificuldade | pos | neg | Desfecho |
| --- | --- | --- | --- | --- |
| claude_3.7_sonnet/262 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/110 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/760 | easy | fail | fail | `tie_block` |
| claude_3.7_sonnet/579 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/717 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/49 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/325 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/88 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/461 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/418 | hard | pass | fail | `correct` |
| claude_3.7_sonnet/678 | hard | pass | fail | `correct` |
| claude_3.7_sonnet/728 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/483 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/796 | medium | fail | fail | `tie_block` |
| claude_3.7_sonnet/430 | easy | fail | pass | `wrong` |
| claude_3.7_sonnet/544 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/241 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/150 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/600 | hard | pass | pass | `tie_approve` |
| claude_3.7_sonnet/689 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/221 | hard | fail | fail | `tie_block` |
| claude_3.7_sonnet/495 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/202 | easy | fail | fail | `tie_block` |
| claude_3.7_sonnet/36 | hard | fail | fail | `tie_block` |
| claude_3.7_sonnet/442 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/333 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/751 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/744 | hard | pass | fail | `correct` |
| claude_3.7_sonnet/398 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/670 | hard | fail | fail | `tie_block` |
| claude_3.7_sonnet/528 | medium | fail | fail | `tie_block` |
| claude_3.7_sonnet/304 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/391 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/439 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/152 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/653 | medium | fail | fail | `tie_block` |
| claude_3.7_sonnet/572 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/375 | hard | pass | fail | `correct` |
| claude_3.7_sonnet/822 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/320 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/577 | hard | pass | fail | `correct` |
| claude_3.7_sonnet/345 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/683 | easy | fail | fail | `tie_block` |
| claude_3.7_sonnet/593 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/354 | hard | fail | fail | `tie_block` |
| claude_3.7_sonnet/737 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/856 | easy | fail | fail | `tie_block` |
| claude_3.7_sonnet/28 | hard | fail | fail | `tie_block` |
| claude_3.7_sonnet/92 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/783 | easy | pass | fail | `correct` |
