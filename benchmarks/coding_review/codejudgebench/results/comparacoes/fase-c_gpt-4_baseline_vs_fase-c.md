# Comparação pareada — CodeJudgeBench

- **A (referência):** `run_20261006_123438_github_copilot-gpt-4_n50` · modelo `github_copilot/gpt-4` · rótulo `—` · código `?`
- **B (candidato):** `run_20261013_210125_github_copilot-gpt-4_n50_fase-c` · modelo `github_copilot/gpt-4` · rótulo `fase-c` · código `cb7056d7`
- **Pares em comum:** 50

| Métrica | A | B | Δ | Só A · só B | McNemar p | Leitura |
| --- | --- | --- | --- | --- | --- | --- |
| Acurácia do julgamento | 12.0% (6/50) | 12.0% (6/50) | +0.0 p.p. | 1 · 1 | 1.000 | sem diferença |
| Aprovou código que falha nos testes | 88.0% (44/50) | 88.0% (44/50) | +0.0 p.p. | 1 · 1 | 1.000 | sem diferença |
| Bloqueou código que passa nos testes | 0.0% (0/50) | 0.0% (0/50) | +0.0 p.p. | 0 · 0 | 1.000 | sem diferença |

> "Só A · só B": pares em que só um dos runs marcou a métrica — o acerto na primeira linha,
> o erro nas outras duas. O McNemar usa apenas esses pares discordantes.

## Pares que mudaram de desfecho (2)

| Par | Dificuldade | A | B |
| --- | --- | --- | --- |
| claude_3.7_sonnet/572 | medium | `correct` | `tie_approve` |
| claude_3.7_sonnet/728 | easy | `tie_approve` | `correct` |
