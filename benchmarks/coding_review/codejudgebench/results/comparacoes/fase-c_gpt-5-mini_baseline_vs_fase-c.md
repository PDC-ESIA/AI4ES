# Comparação pareada — CodeJudgeBench

- **A (referência):** `run_20261006_123438_github_copilot-gpt-5-mini_n50` · modelo `github_copilot/gpt-5-mini` · rótulo `—` · código `?`
- **B (candidato):** `run_20261013_210125_github_copilot-gpt-5-mini_n50_fase-c` · modelo `github_copilot/gpt-5-mini` · rótulo `fase-c` · código `cb7056d7`
- **Pares em comum:** 50

| Métrica | A | B | Δ | Só A · só B | McNemar p | Leitura |
| --- | --- | --- | --- | --- | --- | --- |
| Acurácia do julgamento | 58.0% (29/50) | 58.0% (29/50) | +0.0 p.p. | 8 · 8 | 1.000 | sem diferença |
| Aprovou código que falha nos testes | 12.0% (6/50) | 14.0% (7/50) | +2.0 p.p. | 5 · 6 | 1.000 | piorou (não significativo) |
| Bloqueou código que passa nos testes | 32.0% (16/50) | 28.0% (14/50) | -4.0 p.p. | 5 · 3 | 0.727 | melhorou (não significativo) |

> "Só A · só B": pares em que só um dos runs marcou a métrica — o acerto na primeira linha,
> o erro nas outras duas. O McNemar usa apenas esses pares discordantes.

## Pares que mudaram de desfecho (18)

| Par | Dificuldade | A | B |
| --- | --- | --- | --- |
| claude_3.7_sonnet/110 | easy | `correct` | `tie_approve` |
| claude_3.7_sonnet/221 | hard | `tie_block` | `correct` |
| claude_3.7_sonnet/262 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/304 | medium | `correct` | `tie_block` |
| claude_3.7_sonnet/325 | medium | `tie_approve` | `correct` |
| claude_3.7_sonnet/333 | easy | `correct` | `tie_approve` |
| claude_3.7_sonnet/354 | hard | `correct` | `tie_block` |
| claude_3.7_sonnet/430 | easy | `tie_block` | `correct` |
| claude_3.7_sonnet/439 | easy | `tie_block` | `tie_approve` |
| claude_3.7_sonnet/579 | easy | `wrong` | `tie_block` |
| claude_3.7_sonnet/593 | easy | `correct` | `tie_approve` |
| claude_3.7_sonnet/600 | hard | `correct` | `tie_approve` |
| claude_3.7_sonnet/670 | hard | `tie_block` | `correct` |
| claude_3.7_sonnet/678 | hard | `tie_approve` | `correct` |
| claude_3.7_sonnet/717 | easy | `tie_approve` | `correct` |
| claude_3.7_sonnet/737 | medium | `tie_block` | `correct` |
| claude_3.7_sonnet/88 | medium | `correct` | `tie_block` |
| claude_3.7_sonnet/92 | easy | `correct` | `tie_approve` |
