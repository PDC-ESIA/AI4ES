# Benchmark CodeJudgeBench (CodeRepair) — Reviewer Agent

- **Gerado em:** 2026-10-06T15:42:45.619782+00:00
- **Status do run:** completo
- **Modelo do reviewer:** `github_copilot/gpt-4`
- **Dataset:** `mattymchen/codejudgebench` · config `coderepair` · split `claude_3.7_sonnet` · revisão `dd766c8a8e8d`
- **Amostra:** 50 pares · seed 42 · máx. 1 par(es) por problema
- **Modo:** pontual (cada resposta revisada separadamente) · relato do coder: sim · retries: 1 · análise estática: ligada

## Métricas da issue #421

| Métrica | Valor | IC 95% | k/n |
| --- | --- | --- | --- |
| Acurácia do julgamento (empate = erro) | 12.0% | 5.6% – 23.8% | 6/50 |
| Viés posicional | n/a | — | — |
| Resposta inválida (1ª tentativa) | 0.0% | 0.0% – 3.7% | 0/100 |
| Resposta inválida (após retries) | 0.0% | 0.0% – 3.7% | 0/100 |

> Viés posicional: Não aplicável ao modo pontual: cada revisão vê uma única resposta, então não existe ordem A/B a inverter.

## Decisão por resposta

| Métrica | Valor | IC 95% | k/n |
| --- | --- | --- | --- |
| Aprovou código que falha nos testes (neg aprovada) | 88.0% | 76.2% – 94.4% | 44/50 |
| Bloqueou código que passa nos testes (pos bloqueada) | 0.0% | 0.0% – 7.1% | 0/50 |

Camadas das issues críticas nos bloqueios indevidos: nenhuma

## Julgamento detalhado

| Métrica | Valor | IC 95% | k/n |
| --- | --- | --- | --- |
| Decisividade (vereditos diferentes) | 12.0% | 5.6% – 23.8% | 6/50 |
| Acurácia entre pares decididos | 100.0% | 61.0% – 100.0% | 6/6 |
| Acurácia com empate = ½ acerto | 56.0% | — | — |

| Desfecho | Pares |
| --- | --- |
| `correct` | 6 |
| `tie_approve` | 44 |

## Por dificuldade

| Dificuldade | Acurácia | IC 95% | k/n |
| --- | --- | --- | --- |
| easy | 21.7% | 9.7% – 41.9% | 5/23 |
| hard | 0.0% | 0.0% – 25.9% | 0/11 |
| medium | 6.2% | 1.1% – 28.3% | 1/16 |

## Aderência e execução

- Respostas com retry: 0
- Falhas só de formato (status existe, mas fora do padrão do manifesto): 0
- Gate de cobertura aplicado: 0 (esperado 0 — senão o summary sintético está errado)
- Respostas com falha operacional: 0
- Respostas sem bloco de código no dataset: 0
- Revisões executadas: 100 · interações LLM: 200 · tokens (in/out): 756426/24305
- Tempo total de revisão: 459.9s · tempo total do run: 465.4s

## Por par

| Par | Dificuldade | pos | neg | Desfecho |
| --- | --- | --- | --- | --- |
| claude_3.7_sonnet/262 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/110 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/760 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/579 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/717 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/49 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/325 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/88 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/461 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/418 | hard | pass | pass | `tie_approve` |
| claude_3.7_sonnet/678 | hard | pass | pass | `tie_approve` |
| claude_3.7_sonnet/728 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/483 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/796 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/430 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/544 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/241 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/150 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/600 | hard | pass | pass | `tie_approve` |
| claude_3.7_sonnet/689 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/221 | hard | pass | pass | `tie_approve` |
| claude_3.7_sonnet/495 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/202 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/36 | hard | pass | pass | `tie_approve` |
| claude_3.7_sonnet/442 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/333 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/751 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/744 | hard | pass | pass | `tie_approve` |
| claude_3.7_sonnet/398 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/670 | hard | pass | pass | `tie_approve` |
| claude_3.7_sonnet/528 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/304 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/391 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/439 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/152 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/653 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/572 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/375 | hard | pass | pass | `tie_approve` |
| claude_3.7_sonnet/822 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/320 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/577 | hard | pass | pass | `tie_approve` |
| claude_3.7_sonnet/345 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/683 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/593 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/354 | hard | pass | pass | `tie_approve` |
| claude_3.7_sonnet/737 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/856 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/28 | hard | pass | pass | `tie_approve` |
| claude_3.7_sonnet/92 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/783 | easy | pass | pass | `tie_approve` |
