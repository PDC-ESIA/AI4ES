# Comparação dos pipelines TACO e QA

Este commit contém somente a documentação da análise. O MVP, os runners
atualizados e os artefatos da nova medição estão preservados separadamente
para avaliação em outra branch; não são ativados nem publicados neste commit.

## Conclusão

O loop com QA teve diferença de **0 testes ocultos aprovados** em relação ao TACO atual, nos 18 pares executados.
A validação determinística mantém o código original e não acrescenta chamadas ao modelo. Ela entrega uma decisão estruturada sobre os exemplos fornecidos; esse desenho não pode melhorar a correção funcional do gabarito. Seu custo adicional é medido separadamente.
O TACO atual já verifica esses exemplos. Portanto, eventual vantagem do gate deve ser demonstrada na integração, no isolamento e no tratamento explícito de bloqueios; não pode ser deduzida apenas de testes públicos repetidos.

## Tabela comparativa principal

| Métrica | TACO atual | TACO + QA em loop | TACO + QA determinístico |
| --- | --- | --- | --- |
| Testes públicos aprovados | 60/60 (100.00%) | 60/60 (100.00%) | 60/60 (100.00%) |
| Testes ocultos aprovados | 129/129 (100.00%) | 129/129 (100.00%) | 129/129 (100.00%) |
| Execuções com todo o oráculo oculto aprovado | 18/18 | 18/18 | 18/18 |
| Cobertura média | 94.57% | 94.57% | 94.57% |
| Convergência declarada | 18/18 | 18/18 | 18/18 |
| Iterações médias | 1.0 | 1.0 | 1.0 |
| Tokens totais | 2212386 | 2246455 | 2212386 |
| Tokens médios | 122910.3 | 124803.1 | 122910.3 |
| Chamadas ao modelo | 206 | 224 | 206 |
| Latência média | 62.493 s | 84.258 s | 64.057 s |
| Latência acumulada | 1124.870 s | 1516.653 s | 1153.026 s |

O loop acrescentou 1.54% de tokens e 34.83% de latência. O gate determinístico acrescentou 2.50% de latência, com o mesmo consumo de tokens do baseline.
O baseline atingiu 100% nesta amostra. Não havia defeitos detectados pelo oráculo para demonstrar redução de erros: isso limita o experimento e não prova ausência de benefício em outras tarefas. Não há vantagem funcional clara observada que justifique habilitar correção automática por padrão.

Custo próprio do gate: média de 1.564 segundos por pedido, sem tokens adicionais.
Os três cenários contabilizam integralmente a geração inicial compartilhada. A latência inclui a avaliação independente. A cobertura e a aprovação oculta do terceiro cenário reutilizam o baseline, com igualdade do código verificada por hash; não são uma nova execução do oráculo.

## Resultado por entrada

| Exercício | Ocultos: atual / loop / determinístico | Cobertura: atual / loop | Iterações do loop |
| --- | --- | --- | --- |
| Soma de dois inteiros | 12/12 / 12/12 / 12/12 | 90.61% / 90.61% | 1.00 |
| Validador de colchetes com ruído | 24/24 / 24/24 / 24/24 | 100.00% / 100.00% | 1.00 |
| Mesclar intervalos inteiros adjacentes | 18/18 / 18/18 / 18/18 | 91.11% / 91.11% | 1.00 |
| Menor janela com soma mínima | 27/27 / 27/27 / 27/27 | 89.74% / 89.74% | 1.00 |
| Codificação RLE Unicode | 24/24 / 24/24 / 24/24 | 100.00% / 100.00% | 1.00 |
| Troco mínimo com moedas limitadas | 24/24 / 24/24 / 24/24 | 95.97% / 95.97% | 1.00 |

## Incerteza estatística

As repetições da mesma tarefa são agrupadas. O bootstrap usa médias por tarefa, 10.000 reamostragens e semente 42.

| Métrica do loop menos baseline | Média | IC bootstrap 95% |
| --- | --- | --- |
| hidden_pass_rate_pp | 0.0 | [0.0, 0.0] |
| coverage_pp | 0.0 | [0.0, 0.0] |
| tokens | 1892.722 | [1546.333, 2258.0] |
| latency_s | 21.766 | [17.206, 27.81] |

## Casos críticos e decisões

```json
{
  "baseline_accepted_with_hidden_failures": 0,
  "deterministic_accepted_with_hidden_failures": 0,
  "deterministic_blocked": 0,
  "deterministic_rejected": 0
}
```

Aprovar exemplos públicos e falhar em testes ocultos não representa descumprimento do contrato do gate: seu escopo é explicitamente provided_examples. Não se deve apresentar essa decisão como garantia para todas as entradas.

## Desenho experimental

Os seis exercícios e o oráculo independente são os mesmos do benchmark original. Cada par usa uma geração inicial compartilhada e até três iterações corretivas no loop. Os testes ocultos são executados apenas na avaliação, sem entrar no feedback dos agentes.
A semântica do validator original é carregada da revisão f4efc646, trocando sua execução por Docker. O cenário determinístico chama o contrato TACO-QA de fato e mantém a solução. Todo código avaliado executa no sandbox, sem fallback para o host.

## Testes próprios da integração

A seleção automatizada da integração e do benchmark possui 100 testes aprovados. Ela cobre contrato, matching, normalização, decisões por solução, handoff, API ADK, configuração do sandbox e agregação estatística. Esses testes são diferentes dos casos algorítmicos usados para medir a qualidade dos gabaritos.
A homologação real de console teve **8 testes aprovados, nenhum ignorado**. Ela verifica solução correta, saída incorreta, erro de runtime, timeout, limite de saída, consulta de identidade, confirmação explícita de UID 1000 e tentativa de interferir na saída do harness. Evidência preservada com o MVP: console_homologacao.xml. Esses casos demonstram o comportamento do executor, não aumento de qualidade do gabarito.

## Limitações

- Seis tarefas e um modelo não representam todos os usos de QA.
- O oráculo precisa de revisão independente do domínio.
- Os resultados originais e a nova rodada não formam pares entre si; não atribua diferenças entre rodadas apenas às nossas mudanças.
- O gate reutiliza as mesmas respostas esperadas públicas do baseline; não mede ganho de testes novos.
- A ordem dos cenários não é randomizada; carga do provedor afeta latência.
- O benchmark não mede correção pedagógica, comportamento concorrente ou qualidade do feedback ao aluno.

## Recomendação de evolução

Decidir sobre correção automática a partir do oráculo independente, com rastreabilidade dos testes ao requisito e rollback. Avaliar o gate como validação explícita e isolada, sem prometer melhoria funcional. Adicionar bugs semeados e exercícios reais revisados para avaliar a detecção de defeitos.

## Reprodutibilidade e evidências

- Resultados: `three_scenarios_results.json`.
- Modelo: `github_copilot/gemini-3.7-flash`.
- Python: `3.14.4`.
- SHA-256 do benchmark: `1ad546142778724fd20e748a64890f97ead8f9a94b8e0057d4a04ca63edc30e9`.
- SHA-256 das entradas: `00fe4d9d2da4149024f5cffa53079239958c93d73d6474a74cd85700d87d4589`.
- Snapshots e testes gerados: `workspaces/robust_evidence/`, preservados também em `evidencias_tres_cenarios.zip` (preservado com o MVP, fora deste commit).
- O relatório original permanece em `comparacao_pipeline_taco_qa_robusta.md`.
