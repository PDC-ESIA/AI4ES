## Status: BLOQUEADO

## Issues

- Severity: CRITICAL  
  File: solution.py — Camada: corretude  
  Descrição: A estratégia atual de deduplicação usa um conjunto `seen` que armazena cada permutação gerada como string. No pior caso (por exemplo N = 10 e todas as letras distintas, K > 2), a solução itera por 10! = 3.628.800 permutações e irá tentar guardar até esse número de strings no conjunto, o que causa consumo de memória muito elevado (provável MLE / crash) e também risco de TLE. Isto torna a solução não confiável para entradas limites permitidas pelo enunciado e bloqueia a execução correta do programa em cenários reais. Recomenda-se gerar permutações únicas por construção (backtracking usando um Counter/dicionário de contagens) e aplicar verificação/pruning enquanto constrói a string, para evitar armazenamento/iteração exponencial desnecessária.

- Severity: WARNING  
  File: solution.py — Camada: arquitetura  
  Descrição: A solução faz uma otimização especial apenas para k == 2 e todos os caracteres distintos, mas não lida eficientemente com o caso geral de todos caracteres distintos e k > 2 (onde também haveria 10! permutações válidas). A técnica de deduplicação por `seen` é funcional, porém ineficiente em memória. Arquiteturalmente, para N ≤ 10 a solução ideal é gerar permutações únicas diretamente a partir das contagens de caracteres e cortar ramos assim que um palíndromo de tamanho K é formado (backtracking + pruning). Isso evita armazenamento massivo e reduz tempo de execução.

- Severity: WARNING  
  File: solution.py — Camada: completude  
  Descrição: Não há arquivos de teste entregues com a implementação (nenhum teste unitário / de integração). Falta validar automaticamente cenários chave: (a) N = 10 com todos caracteres distintos e K > 2; (b) casos com repetições que exigem deduplicação; (c) limites K = 1, K = N. Adicionar um conjunto de testes que cubra esses cenários tornaria a correção verificável e evitaria regressões.

- Severity: INFO  
  File: solution.py — Camada: corretude  
  Descrição: Comportamentos corretos observados: o caso K = 1 é tratado corretamente (retorna 0) e há uma micro-otimização para K = 2 quando todos os caracteres são distintos (retorna n!). A verificação de substring-palíndromo está correta logicamente.

## Resumo

O arquivo solution.py apresenta uma correção funcional para o caso que causava TLE original (K=2 com todos caracteres distintos), mas usa uma abordagem de deduplicação que armazena todas as permutações vistas em memória. Isso cria um risco crítico de falha (OOM/TLE) em entradas limites permitidas (por exemplo N=10, todas letras distintas e K>2), portanto a entrega está bloqueada. Recomendo substituir a geração/filtragem atual por uma enumeração de permutações únicas por backtracking sobre as contagens de caracteres com verificação incremental e pruning (cortar ramos assim que o palíndromo de tamanho K aparece). Além disso, incluir um conjunto de testes que cubra os casos limites e cenários com/sem repetições para garantir robustez.