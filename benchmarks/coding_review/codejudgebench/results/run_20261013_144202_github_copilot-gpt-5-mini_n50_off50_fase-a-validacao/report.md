# Benchmark CodeJudgeBench (CodeRepair) — Reviewer Agent

- **Gerado em:** 2026-10-13T18:14:31.969162+00:00
- **Status do run:** completo
- **Experimento:** `fase-a-validacao` · código `19b1e6f9`
- **Modelo do reviewer:** `github_copilot/gpt-5-mini`
- **Dataset:** `mattymchen/codejudgebench` · config `coderepair` · split `claude_3.7_sonnet` · revisão `dd766c8a8e8d`
- **Amostra:** 50 pares (posições 51–100) · seed 42 · máx. 1 par(es) por problema
- **Modo:** pontual (cada resposta revisada separadamente) · relato do coder: sim · retries: 1 · análise estática: ligada

## Métricas da issue #421

| Métrica | Valor | IC 95% | k/n |
| --- | --- | --- | --- |
| Acurácia do julgamento (empate = erro) | 70.0% | 56.2% – 80.9% | 35/50 |
| Viés posicional | n/a | — | — |
| Resposta inválida — status não reconhecido pelo manifesto (1ª tentativa) | 0.0% | 0.0% – 3.7% | 0/100 |
| Resposta inválida — status não reconhecido pelo manifesto (após retries) | 0.0% | 0.0% – 3.7% | 0/100 |

> Viés posicional: Não aplicável ao modo pontual: cada revisão vê uma única resposta, então não existe ordem A/B a inverter.
>
> Resposta inválida mede se o pipeline consegue ler o veredito (a linha `Status:` que o manifesto procura). O reviewer produz markdown, não JSON: não há aderência ao `ReviewOutput` a medir — o harness converte o markdown nesse schema depois.

## Decisão por resposta

| Métrica | Valor | IC 95% | k/n |
| --- | --- | --- | --- |
| Aprovou código que falha nos testes (neg aprovada) | 14.0% | 7.0% – 26.2% | 7/50 |
| Bloqueou código que passa nos testes (pos bloqueada) | 18.0% | 9.8% – 30.8% | 9/50 |

Camadas das issues críticas nos bloqueios indevidos: corretude=10, arquitetura=2

## Julgamento detalhado

| Métrica | Valor | IC 95% | k/n |
| --- | --- | --- | --- |
| Decisividade (vereditos diferentes) | 72.0% | 58.3% – 82.5% | 36/50 |
| Acurácia entre pares decididos | 97.2% | 85.8% – 99.5% | 35/36 |
| Acurácia com empate = ½ acerto | 84.0% | — | — |

| Desfecho | Pares |
| --- | --- |
| `correct` | 35 |
| `tie_approve` | 6 |
| `tie_block` | 8 |
| `wrong` | 1 |

## Por dificuldade

| Dificuldade | Acurácia | IC 95% | k/n |
| --- | --- | --- | --- |
| easy | 77.8% | 54.8% – 91.0% | 14/18 |
| hard | 53.8% | 29.1% – 76.8% | 7/13 |
| medium | 73.7% | 51.2% – 88.2% | 14/19 |

## Aderência e execução

- Respostas com retry: 0
- Falhas só de formato (status existe, mas fora do padrão do manifesto): 0
- Gate de cobertura aplicado: 0 (esperado 0 — senão o summary sintético está errado)
- Respostas com falha operacional: 0
- Respostas sem bloco de código no dataset: 0
- Revisões executadas: 100 · interações LLM: 200 · tokens (in/out): 749449/319736
- Tempo total de revisão: 1930.3s · tempo total do run: 1932.3s

## Por par

| Par | Dificuldade | pos | neg | Desfecho |
| --- | --- | --- | --- | --- |
| claude_3.7_sonnet/129 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/700 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/637 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/437 | hard | pass | fail | `correct` |
| claude_3.7_sonnet/605 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/277 | easy | pass | pass | `tie_approve` |
| claude_3.7_sonnet/662 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/454 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/531 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/837 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/694 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/711 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/402 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/299 | medium | fail | fail | `tie_block` |
| claude_3.7_sonnet/612 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/816 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/732 | hard | pass | pass | `tie_approve` |
| claude_3.7_sonnet/587 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/294 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/249 | easy | fail | fail | `tie_block` |
| claude_3.7_sonnet/385 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/401 | medium | fail | pass | `wrong` |
| claude_3.7_sonnet/247 | hard | pass | fail | `correct` |
| claude_3.7_sonnet/450 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/539 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/198 | medium | pass | pass | `tie_approve` |
| claude_3.7_sonnet/851 | hard | fail | fail | `tie_block` |
| claude_3.7_sonnet/360 | hard | pass | fail | `correct` |
| claude_3.7_sonnet/867 | hard | fail | fail | `tie_block` |
| claude_3.7_sonnet/506 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/547 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/554 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/625 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/329 | hard | pass | fail | `correct` |
| claude_3.7_sonnet/227 | hard | fail | fail | `tie_block` |
| claude_3.7_sonnet/515 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/105 | hard | pass | fail | `correct` |
| claude_3.7_sonnet/713 | hard | pass | fail | `correct` |
| claude_3.7_sonnet/467 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/792 | hard | pass | fail | `correct` |
| claude_3.7_sonnet/768 | hard | fail | fail | `tie_block` |
| claude_3.7_sonnet/229 | easy | fail | fail | `tie_block` |
| claude_3.7_sonnet/860 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/50 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/302 | medium | pass | fail | `correct` |
| claude_3.7_sonnet/423 | hard | pass | pass | `tie_approve` |
| claude_3.7_sonnet/41 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/148 | easy | fail | fail | `tie_block` |
| claude_3.7_sonnet/842 | easy | pass | fail | `correct` |
| claude_3.7_sonnet/193 | easy | pass | fail | `correct` |
