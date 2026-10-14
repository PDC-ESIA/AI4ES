# Comparação robusta: pipeline TACO atual vs. TACO + QA Agent em loop

**Execução:** 11 de outubro de 2026

**Modelo:** `github_copilot/gemini-3.7-flash`

**Resultado bruto:** `compare-qa/robust_results.json`

**Benchmark reproduzível:** `compare-qa/robust_benchmark.py`

## Conclusão executiva

Neste experimento, **não há evidência de que o loop TACO + QA melhore a qualidade funcional**, e há evidência operacional clara de aumento de custo e latência. O pipeline TACO atual obteve resultado melhor no oráculo independente, com menos tokens e menor latência.

O loop QA:

- reduziu a taxa agregada de testes ocultos aprovados de **93,02% para 90,70%**;
- reduziu a média de cobertura de **93,08% para 91,44%**;
- não melhorou nenhum dos 18 pares no oráculo oculto, empatou 16 e piorou 2;
- aumentou o consumo total de tokens em **71,35%**;
- aumentou a latência acumulada em **69,45%**;
- precisou em média de **1,56 iteração**, contra uma única passagem do pipeline atual.

As duas regressões ocorreram na mesma tarefa, em repetições diferentes. O QA criou casos com uma semântica que não existia no requisito, induziu o Coder a alterar uma solução correta e terminou com todos os testes gerados pelo próprio QA passando, enquanto o oráculo independente detectou a regressão.

**Decisão recomendada:** manter o TACO atual como padrão. O QA Agent pode ser explorado como gerador de evidência ou como gate consultivo, mas **não deve corrigir automaticamente código de produção sem rastreabilidade dos testes ao requisito, suíte de regressão independente e rollback obrigatório**.

## Tabela comparativa principal

| Métrica | TACO atual | TACO + QA em loop | Diferença do loop |
|---|---:|---:|---:|
| Testes públicos aprovados | 57/60 (95,00%) | 57/60 (95,00%) | 0,00 p.p. |
| Testes ocultos independentes aprovados | **120/129 (93,02%)** | 117/129 (90,70%) | **-2,33 p.p.** |
| Execuções com 100% do oráculo oculto | **17/18 (94,44%)** | 15/18 (83,33%) | **-11,11 p.p.** |
| Cobertura de linhas, média | **93,08%** | 91,44% | **-1,64 p.p.** |
| Convergência declarada | 17/18 (94,44%) | 17/18 (94,44%) | 0,00 p.p. |
| Iterações, média | **1,00** | 1,56 | +0,56 (+55,56%) |
| Tokens por execução, média | **124.191** | 212.805 | +88.614 (+71,35%) |
| Tokens totais | **2.235.432** | 3.830.482 | +1.595.050 (+71,35%) |
| Latência por execução, média | **48,47 s** | 82,13 s | +33,66 s (+69,45%) |
| Latência acumulada dos cenários | **872,39 s** | 1.478,26 s | +605,87 s (+69,45%) |
| Chamadas ao modelo | **209** | 357 | +148 (+70,81%) |
| Testes finais gerados pelo QA | não se aplica | 308/308 aprovados | métrica interna, não usada como verdade |

Os totais de tokens e latência representam o custo contrafactual de executar cada pipeline separadamente: a geração inicial compartilhada no desenho pareado é contabilizada integralmente nos dois lados.

## Resultado por entrada

Cada entrada foi executada três vezes. As taxas ocultas abaixo agregam as três repetições; tokens, cobertura, iterações e latência são médias.

| Entrada | Testes ocultos: atual → loop | Cobertura: atual → loop | Iterações no loop | Tokens: atual → loop | Latência: atual → loop |
|---|---:|---:|---:|---:|---:|
| Soma de dois inteiros | 12/12 → 12/12 | 96,67% → 96,67% | 1,00 | 107.935 → 109.249 | 43,3 s → 53,9 s |
| Validador de colchetes com ruído | **24/24 → 21/24** | **100,00% → 89,00%** | 2,00 | 131.925 → 283.330 | 49,5 s → 103,3 s |
| União de intervalos | 18/18 → 18/18 | 90,58% → 90,58% | 1,00 | 121.335 → 122.955 | 44,7 s → 56,8 s |
| Janela mínima | 18/27 → 18/27 | 76,79% → 77,93% | 2,33 | 141.489 → 409.799 | 47,3 s → 116,1 s |
| RLE Unicode | 24/24 → 24/24 | 98,55% → 98,55% | 1,00 | 126.709 → 128.682 | 48,4 s → 65,0 s |
| Moedas limitadas | 24/24 → 24/24 | 95,87% → 95,91% | 2,00 | 115.751 → 222.811 | 57,6 s → 97,6 s |

O loop alterou o código em 5 das 18 execuções: nenhuma alteração melhorou a aprovação no oráculo oculto, 3 empataram e 2 pioraram. Em 12 execuções o loop encerrou na primeira tentativa, em 2 precisou de duas tentativas e em 4 chegou à terceira; uma dessas quatro atingiu o limite sem convergir.

## Incerteza estatística

Como as três repetições da mesma tarefa não são independentes entre si, o intervalo abaixo usa bootstrap por bloco de tarefa: primeiro calcula o efeito médio dentro de cada uma das seis tarefas e depois reamostra tarefas inteiras. São 10.000 reamostragens, com semente 42.

| Efeito médio pareado do loop | Estimativa | IC bootstrap 95% por tarefa |
|---|---:|---:|
| Taxa de aprovação oculta | -2,08 p.p. | [-6,25; 0,00] p.p. |
| Cobertura | -1,64 p.p. | [-5,49; +0,57] p.p. |
| Tokens | +88.614 | [+19.150; +177.452] |
| Latência | +33,66 s | [+17,02; +52,06] s |

O teste exato de sinais sobre execuções totalmente aprovadas tem `p = 0,5`: houve duas discordâncias favoráveis ao TACO atual e nenhuma favorável ao loop. Isso **não é evidência estatística suficiente para afirmar dano universal**, pois os dois eventos vieram da mesma tarefa; porém também não existe qualquer sinal positivo de qualidade que justifique o overhead observado. Os aumentos de tokens e latência permaneceram positivos mesmo no bootstrap agrupado por tarefa.

## Caso crítico: falso positivo do QA

O requisito do validador de colchetes dizia para analisar todos os caracteres, considerar apenas `()`, `[]` e `{}`, e ignorar quaisquer outros caracteres. Em duas repetições, o QA gerou testes que tratavam conteúdo entre aspas ou em comentários como uma região especial onde delimitadores também deveriam ser ignorados. Essa regra não estava no contrato.

O Coder seguiu o feedback e acrescentou lógica de strings e comentários. O resultado:

- repetição 1: 8/8 → 7/8 no oráculo oculto;
- repetição 3: 8/8 → 6/8 no oráculo oculto;
- o QA terminou as duas execuções com sua própria suíte em 100%;
- a cobertura do oráculo caiu de 100% para aproximadamente 83%, em parte porque a mudança acrescentou ramos desnecessários.

Esse é um exemplo de **auto-confirmação**: o agente cria uma expectativa incorreta, modifica o código para satisfazê-la e depois usa a própria expectativa para declarar convergência. Por isso os 308 testes finais aprovados do QA são evidência de consistência interna, não de correção funcional.

## Desenho experimental

### Entradas e repetição

- 6 tarefas Python no contrato nativo do TACO: soma, pilha/colchetes com ruído, união de intervalos, janela mínima, RLE Unicode e moedas limitadas;
- 3 repetições por tarefa, totalizando 18 pares;
- 43 verificações ocultas por repetição, ou 129 resultados de oráculo por cenário;
- máximo de 3 iterações no loop QA;
- `temperature = 0`, embora a infraestrutura e o provedor ainda possam introduzir variação.

### Pareamento

Para cada tarefa e repetição, o TACO gerou o código inicial uma única vez. O snapshot exato desse código foi clonado para os dois ramos:

1. **TACO atual:** matching, validação pública e composição do resultado, sem QA corretivo;
2. **TACO + QA:** mesmo snapshot, geração e execução real de testes pelo QA e feedback ao Coder até convergir ou atingir três iterações.

Assim, uma diferença dentro de um par é atribuível ao ramo QA, e não a duas gerações iniciais aleatórias diferentes.

### Oráculo e cobertura

Os testes ocultos não foram mostrados aos agentes. Eles foram executados somente ao final de cada ramo e constituem a medida principal de qualidade. A cobertura comparável foi medida sobre o código de produção com a mesma suíte completa — exemplos públicos mais oráculo oculto — nos dois cenários. A cobertura produzida pela suíte do próprio QA foi registrada apenas como diagnóstico.

### Modelo

Foi utilizado `github_copilot/gemini-3.7-flash`, disponível na configuração GitHub Copilot da máquina. A escolha segue o benchmark executivo já existente no repositório, que o recomenda como melhor equilíbrio de qualidade, segurança e latência e registra a menor taxa de falso positivo entre os modelos ali avaliados. Como o acesso ocorre via Copilot e não expõe preço marginal por token, o custo é reportado em tokens e chamadas, não em moeda.

## Por que este benchmark é mais adequado que HumanEval

HumanEval mede principalmente a geração de uma função a partir de um enunciado e seus testes de referência. Isso é útil para capacidade de codificação, mas não exercita de forma fiel:

- o formato real de entrada do TACO;
- o matching e o validator do pipeline atual;
- a geração de testes pelo QA Agent;
- o ciclo de feedback QA → Coder;
- regressões causadas por um teste gerado com semântica incorreta.

Este experimento usa os agentes e interfaces reais do repositório e um oráculo externo ao loop. Portanto, responde melhor à pergunta de arquitetura proposta. Ainda assim, ele representa tarefas algorítmicas Python e não todo o espectro de mudanças em repositórios reais.

## Limitações

- São seis tarefas e três repetições, suficientes para revelar comportamento e custo, mas não para generalizar a qualquer domínio.
- O resultado avalia um único modelo e a configuração atual dos prompts/agentes.
- O oráculo oculto foi construído para este benchmark e não passou por revisão externa de especialistas.
- A ordem dos ramos não foi randomizada; a latência pode conter variação de carga do provedor. O número muito maior de chamadas no loop, porém, explica diretamente parte substancial do overhead.
- O ambiente não pôde reproduzir literalmente o `uv.lock`: o projeto exige Python `>=3.14`, enquanto `litellm 1.85.0` do lock declara Python `<3.14`. A execução manteve `google-adk 1.33.0` e utilizou `litellm 1.105.0`, compatível com Python 3.14.7. Essa exceção está registrada no JSON bruto.
- Uma avaliação para decisão de produção deve adicionar tarefas reais do repositório, bugs semeados e um golden set privado/rotativo.

## Recomendação de evolução

Antes de habilitar correção automática pelo QA:

1. exigir que cada teste gerado cite o trecho exato do requisito que o justifica;
2. rejeitar testes que acrescentem semântica não especificada;
3. reexecutar uma suíte golden imutável após toda correção;
4. aceitar a alteração apenas se não houver regressão e houver ganho verificável;
5. restaurar automaticamente o snapshot anterior quando o gate falhar;
6. repetir o experimento com tarefas reais do repositório, ao menos cinco repetições e ordem de execução randomizada.

Com a implementação atual, o uso mais seguro do QA é **consultivo e com gate independente**, não um loop autônomo de correção.

## Reprodutibilidade e evidências

- Git HEAD: `f4efc6461ab6a4ae5d0a84093cd9a8223f04949b`
- Python: `3.14.7`
- `google-adk`: `1.33.0`
- `litellm`: `1.105.0`
- `pytest`: `9.0.3`
- SHA-256 do benchmark: `672b61621ecd2e45767b50a9bb8df928d52238ba28f2a201ca68033bcee799b7`
- SHA-256 das entradas e do oráculo: `27a14e401d8aeb7a2b8b46f0705788fb829427315f40cf7b17028c81caa8c8ed`
- SHA-256 dos agentes envolvidos: `4cc7a0290331cfac7dffa084e5f25eee00d4c27cb0eaa9a1e9f9614fb480cab2`
- Tempo de parede do experimento: 27 min 51,7 s
- Evidências por par: `compare-qa/workspaces/robust_evidence/`

## Complemento: integração determinística e testes próprios

A comparação com o contrato TACO-QA e o executor isolado está em
[Comparação dos três cenários](comparacao_pipeline_taco_qa_tres_cenarios.md).
O complemento segue a mesma estrutura deste relatório e inclui tabela dos
três cenários, resultados por entrada, bootstrap por tarefa, metodologia,
limitações, conclusão e testes de integração diferentes dos exercícios.

A nova amostra apresentou 129/129 aprovações ocultas em cada cenário. O loop
acrescentou 1,54% de tokens e 34,83% de latência. O gate determinístico
preservou o código e os tokens, com 1,56 segundo adicional por pedido em média.
Também passaram 96 testes automatizados e oito casos reais do console Docker.

Esses resultados pertencem a outro experimento e não substituem os números
acima. Diferenças entre as rodadas não podem ser atribuídas isoladamente ao QA.
Os intervalos estatísticos do complemento são calculados por tarefa; este
relatório original permanece como evidência da entrega do colega.

O complemento é documental. A implementação e as evidências da nova comparação
ficam preservadas separadamente para possível publicação em outra branch.
