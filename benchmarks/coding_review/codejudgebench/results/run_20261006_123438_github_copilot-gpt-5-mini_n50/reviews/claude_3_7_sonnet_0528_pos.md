## Status: BLOQUEADO

## Issues

- Severity: CRITICAL  
  File: solution.py — Camada: arquitetura / corretude  
  Descrição: Uso de uma tabela binomial 2D (binom) de tamanho (n+1) x (k+1) em Python. Com os limites do problema (n até 10^5 e k até 70) isso cria ~7e6 entradas em listas Python, cada uma referenciando um inteiro — memória necessária vai explodir (muito provavelmente levar a MemoryError ou troca massiva) em entradas grandes. Isso torna a solução não executável em casos reais mesmo que a lógica de contagem esteja correta para entradas pequenas. Recomendação: evitar a matriz 2D; use uma solução com memória O(n) ou O(1) extra, por exemplo:
  - pré-calcular factorials e inverse factorials (O(n) memória) e usar C(n, r) = fact[n] * invfact[r] * invfact[n-r] mod M para cada combinação necessária; somas sobre t=0..k-1 podem ser feitas em O(k) por elemento (total O(n*k) tempo, com k ≤ 70), ou
  - calcular combinações iterativamente por linha (C(m,0)=1 e C(m,t+1)=C(m,t)*(m-t)/(t+1) mod M) e somar até k-1, sem armazenar toda a tabela.  
  Motivo da criticidade: a falha impede execução prática para entradas máximas (bloqueia a pipeline).

- Severity: WARNING  
  File: solution.py — Camada: completude / testes  
  Descrição: Não foram fornecidos testes automatizados (unit tests) acompanhando a correção. A DoD do exercício pedia a correção em solution.py (entregue), mas a ausência de testes torna mais difícil reproduzir e garantir correção contra casos de borda e esforço regressivo. Recomenda-se adicionar testes unitários cobrindo: arrays pequenos e grandes, repetição de valores, k = 1, k = n, e casos limites (n=1, valores 0 e máximos).

- Severity: INFO  
  File: solution.py — Camada: corretude  
  Descrição: A lógica de contagem (somar C(available, t) para t = 0..min(k-1, available)) para contribuição como mínimo e análoga para máximo está correta e alinha-se ao enunciado — subsequências não-vazias e soma de min+max por subsequência. O uso de operações módulo sobre os coeficientes binomiais é coerente com o pedido de resposta módulo 1e9+7.

## Resumo

A implementação entregue resolve corretamente a fórmula de contagem (cada elemento contribui como mínimo e como máximo somando as combinações possíveis de elementos adicionais), e o uso de loops até k (com k ≤ 70) faz o tempo aceitável. Contudo, a escolha de construir uma tabela binomial 2D de tamanho (n+1) x (k+1) em Python cria um consumo de memória proibitivo para n na ordem de 10^5 — isso provavelmente causará falha de execução em entradas grandes. Por esse motivo a entrega está BLOQUEADA até que a construção da tabela binomial seja substituída por uma abordagem com uso de memória linear ou constante (ex.: factorials + inverse factorials, ou cálculo iterativo de C(m,t) por linha). Também recomenda-se incluir testes automatizados cobrindo casos normais e de borda.