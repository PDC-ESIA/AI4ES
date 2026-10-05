# Benchmark SlopCodeBench — Coder Agent

- **Gerado em:** 2026-10-05T00:28:06.483350+00:00
- **Modelo:** github_copilot/gpt-4
- **Seed:** 42
- **Problemas:** dynamic_config_service_api (4 cp), circuit_eval (8 cp), file_query_tool (5 cp), file_backup (4 cp), execution_server (6 cp), database_migration (5 cp), metric_transform_lang (5 cp), dag_execution (3 cp), log_query (5 cp), rejector (5 cp)
- **Checkpoints rodados / previstos:** 50/50
- **Tempo do coder (soma de todos os checkpoints):** 2.7 h
- **Duração desta execução:** 118s (o run pode ter sido retomado; ver `execucoes` no metadata.json)
- **Tokens (in/out):** 11991475/286311

## 1. Correção ao longo do horizonte

Solve rates sobre TODOS os checkpoints previstos (os não rodados contam como não resolvidos).

- **Strict** (`strict_pass_rate == 1`, inclui regressão): 0.00%
- **Isolated** (`isolated_pass_rate == 1`, sem regressão): 0.00%
- **Core** (`core_pass_rate == 1`): 4.00%
- **Problemas com solução parcial / completa:** 0 / 0
- **Quebrou o que funcionava:** 2 de 27 checkpoints quebraram testes que passavam no checkpoint anterior (39 de 687 testes; comparação teste a teste da avaliação oficial)
- **Taxa média nos testes de regressão:** 0.2205 (inclui testes que já falhavam antes)

## 2. Crescimento do diff

| Métrica | n | Média | Mediana |
| ------- | - | ----- | ------- |
| `lines_added` | 50 | 154.2000 | 124.0000 |
| `lines_removed` | 50 | 20.9000 | 0.0000 |
| `delta.loc` | 38 | 17.4849 | 11.3670 |
| `delta.churn_ratio` | 38 | 0.2885 | 0.1894 |

`delta.churn_ratio = (lines_added + lines_removed) / linhas do checkpoint anterior`, a partir do 2º checkpoint. O SlopCodeBench não mede "quanto do código final foi escrito e depois reescrito"; o churn aqui é o oficial, por checkpoint.

## 3. Slop (definição do SlopCodeBench)

| Métrica | n | Média | Mediana |
| ------- | - | ----- | ------- |
| `verbosity` | 42 | 0.3687 | 0.3383 |
| `erosion` | 42 | 0.6802 | 0.7450 |
| `cloned_pct` | 42 | 0.0371 | 0.0334 |
| `verbosity_flagged_pct` | 42 | 0.3687 | 0.3383 |
| `mass.high_cc_pct` | 50 | 0.5562 | 0.7079 |

- **Trajetórias com erosão subindo:** 66.67% (6/9); paper: 77.0%
- **Trajetórias com verbosidade subindo:** 77.78% (7/9); paper: 75.5%

Checkpoints cujo código não é Python válido (erro de sintaxe) ficam sem métricas estáticas (`—`) ou com valores só dos arquivos legíveis: é o comportamento da ferramenta oficial.

Referência do paper (Tabela 2), só para contexto:

| Referência | Verbosidade | Erosão |
| ---------- | ----------- | ------ |
| Painel humano (473 repositórios) | 0.19 | 0.34 |
| Checkpoints de agentes (15 modelos) | 0.44 | 0.68 |

## Por fase de progresso

| Fase | Checkpoints (rodados) | Strict % | Iso % | Core % | Churn médio | Verbosidade média | Erosão média |
| ---- | --------------------- | -------- | ----- | ------ | ----------- | ----------------- | ------------ |
| 20% | 7 (7) | 0.00% | 0.00% | 28.57% | — | 0.2067 | 0.5564 |
| 40% | 11 (11) | 0.00% | 0.00% | 0.00% | 0.3469 | 0.2984 | 0.5997 |
| 60% | 9 (9) | 0.00% | 0.00% | 0.00% | 0.2644 | 0.3704 | 0.7000 |
| 80% | 11 (11) | 0.00% | 0.00% | 0.00% | 0.3408 | 0.4004 | 0.7255 |
| 100% | 12 (12) | 0.00% | 0.00% | 0.00% | 0.2224 | 0.4634 | 0.7395 |

## Por checkpoint

| Problema | Checkpoint | Estado | Strict | Iso | Core | Quebrou | +linhas | −linhas | Churn | Verbosidade | Erosão |
| -------- | ---------- | ------ | ------ | --- | ---- | ------- | ------- | ------- | ----- | ----------- | ------ |
| dynamic_config_service_api | checkpoint_1 | ran | 0.0000 | 0.0000 | 0.0000 | — | 502 | 0 | — | 0.3024 | 0.0000 |
| dynamic_config_service_api | checkpoint_2 | ran | 0.1290 | 0.2609 | 0.5000 | 0/0 | 297 | 3 | 0.5976 | 0.3250 | 0.2638 |
| dynamic_config_service_api | checkpoint_3 | ran | 0.2237 | 0.2237 | 0.4167 | — | 306 | 0 | 0.3844 | 0.2978 | 0.2414 |
| dynamic_config_service_api | checkpoint_4 | ran | 0.5185 | 0.5185 | 0.6667 | — | 243 | 0 | 0.2205 | 0.2769 | 0.2787 |
| circuit_eval | checkpoint_1 | ran | 0.0278 | 0.0278 | 0.1111 | — | 354 | 0 | — | 0.2104 | 0.5185 |
| circuit_eval | checkpoint_2 | ran | 0.0101 | 0.0000 | 0.0000 | 0/1 | 0 | 0 | 0.0000 | — | — |
| circuit_eval | checkpoint_3 | ran | 0.0049 | 0.0000 | 0.0000 | 0/1 | 0 | 0 | 0.0000 | — | — |
| circuit_eval | checkpoint_4 | ran | 0.0023 | 0.0000 | 0.0000 | 0/1 | 293 | 0 | — | 0.3024 | 0.7550 |
| circuit_eval | checkpoint_5 | ran | 0.0022 | 0.0000 | 0.0000 | 0/1 | 0 | 0 | 0.0000 | 0.3024 | 0.7550 |
| circuit_eval | checkpoint_6 | ran | 0.0020 | 0.0000 | 0.0000 | 0/1 | 0 | 0 | 0.0000 | 0.3024 | 0.7550 |
| circuit_eval | checkpoint_7 | ran | 0.0019 | 0.0000 | 0.0000 | 0/1 | 0 | 0 | 0.0000 | 0.3024 | 0.7550 |
| circuit_eval | checkpoint_8 | ran | 0.0018 | 0.0000 | 0.0000 | 0/1 | 0 | 0 | 0.0000 | 0.3024 | 0.7550 |
| file_query_tool | checkpoint_1 | ran | 0.0000 | 0.0000 | 0.0000 | — | 304 | 0 | — | 0.1808 | 0.9108 |
| file_query_tool | checkpoint_2 | ran | 0.0000 | 0.0000 | 0.0000 | 0/0 | 119 | 16 | 0.4441 | 0.1859 | 0.8752 |
| file_query_tool | checkpoint_3 | ran | 0.0000 | 0.0000 | 0.0000 | 0/0 | 39 | 3 | 0.1032 | 0.1860 | 0.8314 |
| file_query_tool | checkpoint_4 | ran | 0.0000 | 0.0000 | 0.0000 | 0/0 | 220 | 5 | 0.5079 | 0.1879 | 0.9155 |
| file_query_tool | checkpoint_5 | ran | 0.0000 | 0.0000 | 0.0000 | 0/0 | 311 | 373 | 1.0395 | 0.3797 | 0.7992 |
| file_backup | checkpoint_1 | ran | 0.1562 | 0.1562 | 0.0000 | — | 189 | 0 | — | 0.1280 | 0.7705 |
| file_backup | checkpoint_2 | ran | 0.1200 | 0.0556 | 0.0000 | 0/5 | 175 | 13 | 0.9947 | 0.4268 | 0.8649 |
| file_backup | checkpoint_3 | ran | 0.1176 | 0.1111 | 0.0000 | 0/6 | 87 | 21 | 0.3077 | 0.4358 | 0.9099 |
| file_backup | checkpoint_4 | ran | 0.1011 | 0.0476 | 0.0000 | 0/8 | 135 | 52 | 0.4484 | 0.7187 | 0.9480 |
| execution_server | checkpoint_1 | ran | 0.6889 | 0.6889 | 1.0000 | — | 267 | 0 | — | 0.1239 | 0.0000 |
| execution_server | checkpoint_2 | ran | 0.6379 | 0.4615 | 0.8333 | 0/31 | 40 | 2 | 0.1573 | 0.1456 | 0.4883 |
| execution_server | checkpoint_3 | ran | 0.0000 | 0.0000 | 0.0000 | 37/37 | 126 | 2 | 0.4197 | 0.3895 | 0.7349 |
| execution_server | checkpoint_4 | ran | 0.0000 | 0.0000 | 0.0000 | 0/0 | 218 | 71 | 0.6737 | 0.4950 | 0.8269 |
| execution_server | checkpoint_5 | ran | 0.0000 | 0.0000 | 0.0000 | 0/0 | 103 | 23 | 0.2188 | 0.5009 | 0.8141 |
| execution_server | checkpoint_6 | ran | 0.0000 | 0.0000 | 0.0000 | 0/0 | 306 | 20 | 0.4970 | 0.5890 | 0.8708 |
| database_migration | checkpoint_1 | ran | 0.9744 | 0.9744 | 1.0000 | — | 442 | 0 | — | 0.3930 | 0.6207 |
| database_migration | checkpoint_2 | ran | 0.8387 | 0.6087 | 0.3333 | 0/38 | 257 | 3 | 0.5882 | 0.3804 | 0.5916 |
| database_migration | checkpoint_3 | ran | 0.7241 | 0.4800 | 0.0000 | 0/51 | 0 | 0 | 0.0000 | 0.3804 | 0.5916 |
| database_migration | checkpoint_4 | ran | 0.5983 | 0.2333 | 0.0000 | 0/63 | 330 | 88 | 0.6006 | 0.4696 | 0.6459 |
| database_migration | checkpoint_5 | ran | 0.5766 | 0.4500 | 0.0000 | 0/70 | 228 | 2 | 0.2452 | 0.5136 | 0.7081 |
| metric_transform_lang | checkpoint_1 | ran | 0.3696 | 0.3696 | 0.0000 | — | 0 | 0 | — | — | — |
| metric_transform_lang | checkpoint_2 | ran | 0.2959 | 0.2308 | 0.0000 | 0/17 | 502 | 205 | — | 0.7690 | 0.8707 |
| metric_transform_lang | checkpoint_3 | ran | 0.2378 | 0.1515 | 0.0000 | 0/29 | 0 | 0 | 0.0000 | 0.7690 | 0.8707 |
| metric_transform_lang | checkpoint_4 | ran | 0.1150 | 0.0645 | 0.0000 | 0/22 | 59 | 49 | 0.1600 | 0.7309 | 0.8282 |
| metric_transform_lang | checkpoint_5 | ran | 0.0676 | 0.1923 | 0.0000 | 0/0 | 0 | 0 | 0.0000 | 0.7309 | 0.8282 |
| dag_execution | checkpoint_1 | ran | 0.0000 | 0.0000 | 0.0000 | — | 240 | 0 | — | 0.2921 | 0.5136 |
| dag_execution | checkpoint_2 | ran | 0.0000 | 0.0000 | 0.0000 | 0/0 | 122 | 0 | 0.5083 | 0.4309 | 0.6683 |
| dag_execution | checkpoint_3 | ran | 0.0000 | 0.0000 | 0.0000 | 0/0 | 0 | 0 | 0.0000 | 0.4309 | 0.6683 |
| log_query | checkpoint_1 | ran | 0.3284 | 0.3284 | 0.0000 | — | 0 | 0 | — | — | — |
| log_query | checkpoint_2 | ran | 0.2464 | 0.0959 | 0.0000 | 0/44 | 0 | 0 | 0.0000 | — | — |
| log_query | checkpoint_3 | ran | 0.2176 | 0.1091 | 0.0000 | 0/51 | 0 | 0 | 0.0000 | — | — |
| log_query | checkpoint_4 | ran | 0.2107 | 0.1622 | 0.0000 | 0/57 | 0 | 0 | 0.0000 | — | — |
| log_query | checkpoint_5 | ran | 0.2113 | 0.2162 | 0.0000 | 0/63 | 0 | 0 | 0.0000 | — | — |
| rejector | checkpoint_1 | ran | 0.8095 | 0.8095 | 0.7333 | — | 306 | 0 | — | 0.1255 | 0.7319 |
| rejector | checkpoint_2 | ran | 0.6765 | 0.4615 | 0.5000 | 2/17 | 288 | 91 | 1.2386 | 0.1839 | 0.6879 |
| rejector | checkpoint_3 | ran | 0.4800 | 0.0625 | 0.0769 | 0/23 | 0 | 0 | 0.0000 | 0.1839 | 0.6879 |
| rejector | checkpoint_4 | ran | 0.3582 | 0.0000 | 0.0000 | 0/24 | 302 | 3 | 0.6064 | 0.3516 | 0.7093 |
| rejector | checkpoint_5 | ran | 0.3038 | 0.0000 | 0.0000 | 0/24 | 0 | 0 | 0.0000 | 0.3516 | 0.7093 |
