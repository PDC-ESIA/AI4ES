## Status: BLOQUEADO

## Issues

- critical — solution.py — camada: corretude  
  Descrição: A implementação atual é correta funcionalmente mas usa um algoritmo O(n^2) (dois loops aninhados sobre o array). Com n até 10^5 isso leva a Time Limit Exceeded (falha observada). A entrega deve eliminar a falha observada (CA-02); portanto este problema de desempenho é bloqueante até que seja substituído por uma solução O(n) ou O(m) onde m = número de ocorrências do máximo.

- warning — solution.py — camada: completude  
  Descrição: Não há arquivos de teste entregues junto com a implementação. Não foram fornecidos testes unitários cobrindo o caso trivial, casos limites (por exemplo, quando o número de ocorrências do máximo < k) nem o caso de stress que evidencia o TLE. Entregar testes automatizados ajudaria a validar correção e desempenho (CA-01).

- info — solution.py — camada: arquitetura  
  Descrição: A função está isolada e cumpre a assinatura esperada; responsabilidade única está respeitada. Contudo a escolha de abordagem (varrer todos os subarrays explicitamente) não escala. Recomenda-se separar a lógica de contagem eficiente numa função helper para clareza e testar independentemente.

## Resumo

O arquivo solution.py implementa corretamente a contagem de subarrays que contêm ao menos k ocorrências do valor máximo do array, porém com complexidade quadrática que causa Time Limit Exceeded em entradas grandes. Isso viola os critérios de aceite (eliminar a falha observada) — por isso o status é BLOQUEADO. Recomendo substituir a abordagem por uma solução linear baseada nas posições do elemento máximo: coletar índices pos[] onde nums[i] == max_val; se len(pos) < k retornar 0; para cada i de 0 a len(pos)-k calcular left_options = pos[i] - (pos[i-1] if i>0 else -1) e right_options = ( (pos[i+k] if i+k < len(pos) else n) - pos[i+k-1] ) e somar left_options * right_options ao resultado. Essa solução é O(n) e resolverá o problema de TLE. Também entregue um conjunto de testes unitários cobrindo casos pequenos, casos limites e um caso grande para verificar desempenho.