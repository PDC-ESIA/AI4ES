# Benchmark SWE-bench Verified — loop coder → executor

- **Gerado em:** 2026-10-02T03:54:07.416069+00:00
- **Modelo:** `github_copilot/gemini-3.7-flash`
- **Instâncias:** 30 (seed 42, limit 30)
- **Dataset:** `SWE-bench/SWE-bench_Verified` @ `78f471bf655a`
- **Harness oficial:** swebench 5.0.2
- **Teto do loop (`max_iterations`):** 20
- **Commit do repositório:** `0af110aed7c8` (árvore com alterações locais)
- **Correção oficial:** código de saída `0`

> Linha de base com amostra pequena: leia sempre o intervalo de confiança junto da taxa. Limitações na seção final e no README.

## Métrica 1 — Taxa de resolução (harness oficial)

- **Resolvidas:** 20/30 (66.7%) — IC 95%: [48.8%, 80.8%]

| Status no SWE-bench | Instâncias |
| ------------------- | ---------- |
| empty_patch | 1 |
| resolved | 20 |
| unresolved | 9 |

## Métrica 2 — Rodadas do loop e motivo de parada

- **Rodadas por instância:** média 1.7, mediana 1.0, mín. 1, máx. 4

| Rodadas | Instâncias |
| ------- | ---------- |
| 1 | 16 |
| 2 | 8 |
| 3 | 5 |
| 4 | 1 |

| Motivo de parada | Instâncias | Detalhe (`motivo_terminacao`) |
| ---------------- | ---------- | ----------------------------- |
| aprovacao_do_validador | 24 | aprovado: 24 |
| outro | 6 | timeout_da_instancia: 6 |

> 2 instância(s) com rodadas ≠ tamanho do histórico de notas (rodada sem veredito gravado): matplotlib__matplotlib-25479, pytest-dev__pytest-10356

## Métrica 3 — Concordância do validador

Instâncias com gabarito conhecido: 30 (fora da matriz: 0, das quais 0 excluídas pelo `--gold-sanity`).

| | Resolvida (SWE-bench) | Não resolvida |
| --- | --- | --- |
| **Validador aprovou** | 19 | 5 (falso positivo) |
| **Validador não aprovou** | 1 (falso negativo) | 5 |

- **Falsos positivos entre as aprovações:** 5/24 (20.8%) — IC 95%: [9.2%, 40.5%]
- **Precisão do validador:** 19/24 (79.2%) — IC 95%: [59.5%, 90.8%]
- **Recall do validador:** 19/20 (95.0%) — IC 95%: [76.4%, 99.1%]
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
| matplotlib/matplotlib | 2 | 0 | 1 |
| pydata/xarray | 2 | 1 | 1 |
| pytest-dev/pytest | 2 | 1 | 1 |
| mwaskom/seaborn | 1 | 1 | 0 |
| pylint-dev/pylint | 1 | 0 | 1 |
| sympy/sympy | 1 | 1 | 1 |

## Operacional

- **Estouros de contexto do modelo:** 0
- **Erros operacionais:** 0
- **Timeouts de instância:** 6 (django__django-12125, django__django-16032, matplotlib__matplotlib-25479, mwaskom__seaborn-3069, pydata__xarray-4687, pytest-dev__pytest-10356)
- **Ambiente restaurado pela guarda:** 0
- **Coder usou virtualenv no `run.json`:** 0
- **Duração total do loop:** 36861.41s, das quais 29776.96s em espera do controle de ritmo e 0.0s em pausa por rate limit do provedor
- **Interações com LLM:** 859
- **Tokens (entrada/saída/total):** 92352796/139490/92492286
  - `cr_coder_agent`: 617 interações, 71618239/91945 tokens
  - `cr_executor_agent`: 146 interações, 20064109/31353 tokens
  - `implementation_validator`: 96 interações, 670448/16192 tokens

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
| django__django-12125 | 2 | outro (timeout_da_instancia) | reprovado | unresolved | 3 |
| django__django-13158 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| django__django-13401 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| django__django-13417 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 2 |
| django__django-13551 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| django__django-13741 | 3 | aprovacao_do_validador (aprovado) | aprovado | resolved | 2 |
| django__django-14034 | 1 | aprovacao_do_validador (aprovado) | aprovado | unresolved | 1 |
| django__django-16032 | 3 | outro (timeout_da_instancia) | reprovado | empty_patch | vazio |
| django__django-16100 | 2 | aprovacao_do_validador (aprovado) | aprovado | resolved | 2 |
| matplotlib__matplotlib-20859 | 1 | aprovacao_do_validador (aprovado) | aprovado | unresolved | 2 |
| matplotlib__matplotlib-25479 | 4 | outro (timeout_da_instancia) | reprovado | unresolved | 1 |
| mwaskom__seaborn-3069 | 2 | outro (timeout_da_instancia) | reprovado | resolved | 1 |
| pydata__xarray-3677 | 1 | aprovacao_do_validador (aprovado) | aprovado | resolved | 1 |
| pydata__xarray-4687 | 1 | outro (timeout_da_instancia) | reprovado | unresolved | 4 |
| pylint-dev__pylint-7080 | 3 | aprovacao_do_validador (aprovado) | aprovado | unresolved | 1 |
| pytest-dev__pytest-10356 | 3 | outro (timeout_da_instancia) | reprovado | unresolved | 2 |
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

