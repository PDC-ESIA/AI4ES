# Benchmark SWE-bench Verified — loop coder → executor

- **Gerado em:** 2026-10-05T19:32:25.518699+00:00
- **Modelo:** `github_copilot/gemini-3.7-flash`
- **Instâncias:** 26 (seed 42, limit 30)
- **Dataset:** `SWE-bench/SWE-bench_Verified` @ `78f471bf655a`
- **Harness oficial:** swebench 5.0.2
- **Teto do loop (`max_iterations`):** 20
- **Commit do repositório:** `0af110aed7c8` (árvore com alterações locais)
- **Correção oficial:** código de saída `0`

> Linha de base com amostra pequena: leia sempre o intervalo de confiança junto da taxa. Limitações na seção final e no README.

## Métrica 1 — Taxa de resolução (harness oficial)

- **Resolvidas:** 19/26 (73.1%) — IC 95%: [53.9%, 86.3%]

| Status no SWE-bench | Instâncias |
| ------------------- | ---------- |
| resolved | 19 |
| unresolved | 7 |

## Métrica 2 — Rodadas do loop e motivo de parada

- **Rodadas por instância:** média 1.65, mediana 1.0, mín. 1, máx. 4

| Rodadas | Instâncias |
| ------- | ---------- |
| 1 | 15 |
| 2 | 6 |
| 3 | 4 |
| 4 | 1 |

| Motivo de parada | Instâncias | Detalhe (`motivo_terminacao`) |
| ---------------- | ---------- | ----------------------------- |
| aprovacao_do_validador | 24 | aprovado: 24 |
| politica_de_progresso | 2 | bloqueado_erro_repetido: 1, bloqueado_sem_alteracao_arquivos: 1 |

## Métrica 3 — Concordância do validador

Instâncias com gabarito conhecido: 26 (fora da matriz: 0, das quais 0 excluídas pelo `--gold-sanity`).

| | Resolvida (SWE-bench) | Não resolvida |
| --- | --- | --- |
| **Validador aprovou** | 19 | 5 (falso positivo) |
| **Validador não aprovou** | 0 (falso negativo) | 2 |

- **Falsos positivos entre as aprovações:** 5/24 (20.8%) — IC 95%: [9.2%, 40.5%]
- **Precisão do validador:** 19/24 (79.2%) — IC 95%: [59.5%, 90.8%]
- **Recall do validador:** 19/19 (100.0%) — IC 95%: [83.2%, 100.0%]
- **Instâncias com falso positivo:** django__django-11400, django__django-11734, django__django-14034, matplotlib__matplotlib-20859, pylint-dev__pylint-7080
- **Aceitas com ressalvas pelo sistema** (validador reprovou, política aceitou): 0, das quais 0 resolvidas

O validador aprova pelo status técnico da suíte que o PRÓPRIO coder declarou. Os qualificadores mostram o que sustentava cada aprovação:

| Qualificador | Aprovações | Entre os falsos positivos |
| ------------ | ---------- | ------------------------- |
| suite_vazia_ou_pulada | 0 | 0 |
| patch_vazio | 0 | 0 |
| testes_nao_identificados | 13 | 3 |

## Ambiente do executor com a solução oficial (`--executor-sanity`)

Com o patch e os testes oficiais aplicados, o harness do executor deu sucesso em **26/30** instâncias — é o teto de aprovações corretas que o validador consegue dar neste ambiente.

| Resultado | Instâncias |
| --------- | ---------- |
| sucesso | 26 |
| testes_falharam | 4 |

## Por repositório

| Repositório | Instâncias | Resolvidas | Aprovadas pelo validador |
| ----------- | ---------- | ---------- | ------------------------ |
| django/django | 13 | 8 | 11 |
| astropy/astropy | 4 | 4 | 4 |
| scikit-learn/scikit-learn | 4 | 4 | 4 |
| matplotlib/matplotlib | 1 | 0 | 1 |
| pydata/xarray | 1 | 1 | 1 |
| pylint-dev/pylint | 1 | 0 | 1 |
| pytest-dev/pytest | 1 | 1 | 1 |
| sympy/sympy | 1 | 1 | 1 |

## Operacional

- **Estouros de contexto do modelo:** 0
- **Erros operacionais:** 0
- **Timeouts de instância:** 0
- **Ambiente restaurado pela guarda:** 0
- **Coder usou virtualenv no `run.json`:** 0
- **Duração total do loop:** 21262.16s, das quais 15784.98s em espera do controle de ritmo e 0.0s em pausa por rate limit do provedor
- **Interações com LLM:** 674
- **Tokens (entrada/saída/total):** 53224352/103403/53327755
  - `cr_coder_agent`: 468 interações, 38809462/71685 tokens
  - `cr_executor_agent`: 124 interações, 13890548/17865 tokens
  - `implementation_validator`: 82 interações, 524342/13853 tokens

## Por instância

| Instância | Rodadas | Parada | Validador | SWE-bench | Arquivos no patch |
| --------- | ------- | ------ | --------- | --------- | ----------------- |
| astropy__astropy-14508 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| astropy__astropy-14539 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| astropy__astropy-14995 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| astropy__astropy-7166 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| django__django-11292 | 2 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| django__django-11400 | 3 | aprovacao_do_validador (aprovado) | aprovado | unresolved | 3 |
| django__django-11532 | 2 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| django__django-11734 | 2 | aprovacao_do_validador (aprovado) | aprovado | unresolved | 1 |
| django__django-12125 | 4 | politica_de_progresso (bloqueado_sem_alteracao_arquivos) | reprovado | unresolved | 2 |
| django__django-13158 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| django__django-13401 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| django__django-13417 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 2 |
| django__django-13551 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| django__django-13741 | 3 | aprovacao_do_validador (aprovado) | aprovado | resolved | 2 |
| django__django-14034 | 1 | aprovacao_do_validador (aprovado) | aprovado | unresolved | 1 |
| django__django-16032 | 3 | politica_de_progresso (bloqueado_erro_repetido) | reprovado | unresolved | 2 |
| django__django-16100 | 2 | aprovacao_do_validador (aprovado) | aprovado | resolved | 2 |
| matplotlib__matplotlib-20859 | 1 | aprovacao_do_validador (aprovado) | aprovado | unresolved | 2 |
| pydata__xarray-3677 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| pylint-dev__pylint-7080 | 3 | aprovacao_do_validador (aprovado) | aprovado | unresolved | 1 |
| pytest-dev__pytest-7571 | 2 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| scikit-learn__scikit-learn-13142 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| scikit-learn__scikit-learn-14141 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| scikit-learn__scikit-learn-25973 | 2 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| scikit-learn__scikit-learn-26323 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| sympy__sympy-16766 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |

## Como ler estes números

- **Amostra pequena:** com 30 instâncias, cada uma vale 3,3 pontos percentuais; compare runs pelo intervalo de confiança, não pela taxa pontual.
- **Métrica 1 mede o loop inteiro:** depende mais do coder (sem ferramenta de busca, lendo arquivos inteiros) do que do executor.
- **Métrica 3 mede o sinal de parada:** um falso positivo significa que a suíte do coder passou e o bug continuou — testes fracos ou ausentes, ou um validador permissivo. Os qualificadores ajudam a separar os casos.
- **O gabarito também erra:** os testes oficiais só cobrem o que o PR original testou. Revise à mão as discordâncias da métrica 3.

