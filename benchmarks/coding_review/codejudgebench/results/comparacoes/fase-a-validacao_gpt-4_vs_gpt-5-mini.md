# Comparação pareada — CodeJudgeBench

- **A (referência):** `run_20261013_144202_github_copilot-gpt-4_n50_off50_fase-a-validacao` · modelo `github_copilot/gpt-4` · rótulo `fase-a-validacao` · código `19b1e6f9`
- **B (candidato):** `run_20261013_144202_github_copilot-gpt-5-mini_n50_off50_fase-a-validacao` · modelo `github_copilot/gpt-5-mini` · rótulo `fase-a-validacao` · código `19b1e6f9`
- **Pares em comum:** 50

| Métrica | A | B | Δ | Só A · só B | McNemar p | Leitura |
| --- | --- | --- | --- | --- | --- | --- |
| Acurácia do julgamento | 12.0% (6/50) | 70.0% (35/50) | +58.0 p.p. | 2 · 31 | < 0.001 | melhorou (significativo) |
| Aprovou código que falha nos testes | 88.0% (44/50) | 14.0% (7/50) | -74.0 p.p. | 37 · 0 | < 0.001 | melhorou (significativo) |
| Bloqueou código que passa nos testes | 0.0% (0/50) | 18.0% (9/50) | +18.0 p.p. | 0 · 9 | 0.004 | piorou (significativo) |

> "Só A · só B": pares em que só um dos runs marcou a métrica — o acerto na primeira linha,
> o erro nas outras duas. O McNemar usa apenas esses pares discordantes.

## Pares que mudaram de desfecho (40)

| Par | Dificuldade | A | B |
| --- | --- | --- | --- |
| claude_3.7_sonnet/105 | hard | `tie_approve` | `correct` |
| claude_3.7_sonnet/129 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/148 | easy | `tie_approve` | `tie_block` |
| claude_3.7_sonnet/193 | easy | `tie_approve` | `correct` |
| claude_3.7_sonnet/227 | hard | `tie_approve` | `tie_block` |
| claude_3.7_sonnet/229 | easy | `tie_approve` | `tie_block` |
| claude_3.7_sonnet/247 | hard | `tie_approve` | `correct` |
| claude_3.7_sonnet/249 | easy | `tie_approve` | `tie_block` |
| claude_3.7_sonnet/294 | easy | `tie_approve` | `correct` |
| claude_3.7_sonnet/299 | medium | `correct` | `tie_block` |
| claude_3.7_sonnet/302 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/329 | hard | `tie_approve` | `correct` |
| claude_3.7_sonnet/360 | hard | `tie_approve` | `correct` |
| claude_3.7_sonnet/401 | medium | `tie_approve` | `wrong` |
| claude_3.7_sonnet/402 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/437 | hard | `tie_approve` | `correct` |
| claude_3.7_sonnet/467 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/50 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/506 | easy | `tie_approve` | `correct` |
| claude_3.7_sonnet/531 | easy | `tie_approve` | `correct` |
| claude_3.7_sonnet/539 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/547 | easy | `tie_approve` | `correct` |
| claude_3.7_sonnet/554 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/587 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/605 | easy | `tie_approve` | `correct` |
| claude_3.7_sonnet/612 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/625 | easy | `tie_approve` | `correct` |
| claude_3.7_sonnet/637 | easy | `tie_approve` | `correct` |
| claude_3.7_sonnet/662 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/694 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/711 | easy | `tie_approve` | `correct` |
| claude_3.7_sonnet/713 | hard | `tie_approve` | `correct` |
| claude_3.7_sonnet/768 | hard | `correct` | `tie_block` |
| claude_3.7_sonnet/792 | hard | `tie_approve` | `correct` |
| claude_3.7_sonnet/816 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/837 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/842 | easy | `tie_approve` | `correct` |
| claude_3.7_sonnet/851 | hard | `tie_approve` | `tie_block` |
| claude_3.7_sonnet/860 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/867 | hard | `tie_approve` | `tie_block` |
