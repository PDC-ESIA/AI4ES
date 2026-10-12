# Benchmark BigCodeBench (complete) — Coder Agent

- **Gerado em:** 2026-10-05T15:52:58.301483+00:00
- **Modelo:** github_copilot/gpt-4
- **Dataset:** bigcode/bigcodebench v0.1.4 (split complete)
- **Tarefas:** 50 (seed 42)
- **Sandbox:** Docker `ai4se-bigcodebench-sandbox:v0.1.4` (rede: none)

## 1. Pass@1

- **pass@1:** 0.6800 (68.0%) — 34/50 tarefas aprovadas nos testes oficiais

## 2. Falhas por import/dependência × lógica

| Grupo | Reprovações | % das reprovações |
| ----- | ----------- | ----------------- |
| Biblioteca (ausente / import / API) | 2 | 12% |
| Lógica (asserção / erro de execução) | 14 | 88% |
| Outras (sintaxe / timeout / sem solução / geração) | 0 | 0% |

| Categoria | Reprovações |
| --------- | ----------- |
| `api_misuse` | 2 |
| `logic` | 11 |
| `runtime_error` | 3 |

## 3. Comparação com o HumanEval (mesmo modelo)

| Benchmark | Tarefas | pass@1 |
| --------- | ------- | ------ |
| HumanEval | 50 | 94.0% |
| BigCodeBench (complete) | 50 | 68.0% |

- **Variação:** -26.0 p.p. (queda relativa de 27.7%)

## Métricas de execução

- **Tempo total:** 837.98s
- **Interações com LLM:** 195
- **Tokens (entrada/saída/total):** 2187927/48037/2235964
- **Soluções canônicas validadas no sandbox:** 50/50

## Por tarefa

| Task | Bibliotecas | Resultado | Categoria |
| ---- | ----------- | --------- | --------- |
| BigCodeBench/13 | subprocess, ftplib, os | PASS | — |
| BigCodeBench/51 | matplotlib, sklearn | PASS | — |
| BigCodeBench/54 | regex, pandas, sklearn | FAIL | `runtime_error` |
| BigCodeBench/61 | datetime, numpy, matplotlib | PASS | — |
| BigCodeBench/65 | pandas, matplotlib | FAIL | `runtime_error` |
| BigCodeBench/88 | pandas, datetime, numpy | FAIL | `logic` |
| BigCodeBench/93 | pandas, numpy, matplotlib, sklearn | FAIL | `logic` |
| BigCodeBench/142 | numpy, matplotlib | PASS | — |
| BigCodeBench/161 | pandas, datetime, re | FAIL | `logic` |
| BigCodeBench/163 | pandas, numpy | PASS | — |
| BigCodeBench/178 | re, json | PASS | — |
| BigCodeBench/189 | re, requests, json | PASS | — |
| BigCodeBench/191 | random, scipy | FAIL | `logic` |
| BigCodeBench/198 | statistics, bisect, numpy, matplotlib | FAIL | `logic` |
| BigCodeBench/209 | operator, numpy, matplotlib | PASS | — |
| BigCodeBench/228 | pandas, numpy | PASS | — |
| BigCodeBench/255 | numpy, matplotlib | FAIL | `logic` |
| BigCodeBench/285 | mechanize, bs4 | PASS | — |
| BigCodeBench/318 | math, random, matplotlib | PASS | — |
| BigCodeBench/326 | glob, subprocess, os, sys | FAIL | `logic` |
| BigCodeBench/393 | numpy, matplotlib, scipy | PASS | — |
| BigCodeBench/407 | csv, openpyxl, os | PASS | — |
| BigCodeBench/440 | pandas, numpy, sklearn | FAIL | `runtime_error` |
| BigCodeBench/447 | numpy, matplotlib, sklearn | PASS | — |
| BigCodeBench/451 | sklearn, numpy, matplotlib, seaborn | PASS | — |
| BigCodeBench/457 | pandas, numpy | FAIL | `api_misuse` |
| BigCodeBench/466 | enum, json | PASS | — |
| BigCodeBench/476 | matplotlib, scipy | FAIL | `logic` |
| BigCodeBench/501 | pandas, xlwt, os | PASS | — |
| BigCodeBench/541 | importlib, pkgutil, os, sys | FAIL | `logic` |
| BigCodeBench/563 | glob, ctypes, shutil, os | PASS | — |
| BigCodeBench/569 | types, math, inspect | PASS | — |
| BigCodeBench/592 | csv, datetime, random, os | FAIL | `api_misuse` |
| BigCodeBench/600 | pandas, numpy | PASS | — |
| BigCodeBench/689 | numpy, scipy | PASS | — |
| BigCodeBench/696 | math, numpy, random | PASS | — |
| BigCodeBench/704 | pandas, itertools | PASS | — |
| BigCodeBench/735 | numpy, itertools | PASS | — |
| BigCodeBench/740 | collections, heapq | PASS | — |
| BigCodeBench/775 | collections, string, re | PASS | — |
| BigCodeBench/778 | operator, collections, itertools | PASS | — |
| BigCodeBench/859 | warnings, sklearn | PASS | — |
| BigCodeBench/864 | pandas, numpy | PASS | — |
| BigCodeBench/865 | pandas, numpy, scipy, sklearn | PASS | — |
| BigCodeBench/919 | pandas, matplotlib | PASS | — |
| BigCodeBench/940 | nltk, collections, re | PASS | — |
| BigCodeBench/1034 | pandas, numpy | PASS | — |
| BigCodeBench/1098 | collections, re | PASS | — |
| BigCodeBench/1116 | statistics, random | FAIL | `logic` |
| BigCodeBench/1130 | hashlib, pathlib, os, json | FAIL | `logic` |
