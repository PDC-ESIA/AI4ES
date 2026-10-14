# Estabilidade entre execuções — CodeJudgeBench

- `run_20261013_210125_github_copilot-gpt-5-mini_n50_fase-c`
- `run_20261013_235921_github_copilot-gpt-5-mini_n50_estabilidade-r2`
- `run_20261013_235921_github_copilot-gpt-5-mini_n50_estabilidade-r3`

| Métrica | Por execução | Média ± desvio |
| --- | --- | --- |
| Acurácia do julgamento | 58% · 64% · 58% | 60.0% ± 3.5 p.p. |
| Aprovou código que falha nos testes | 14% · 12% · 10% | 12.0% ± 2.0 p.p. |
| Bloqueou código que passa nos testes | 28% · 26% · 38% | 30.7% ± 6.4 p.p. |

- Pares com o mesmo desfecho nas 3 execuções: 24/50
- Respostas com o mesmo veredito nas 3 execuções: 71/100
- Pares acertados sempre: 19 · errados sempre: 8 · instáveis: 23
- Voto da maioria: acurácia 29/50 (IC 95% 44.2–70.6%) · aprovou código que falha 3 · bloqueou código que passa 18
