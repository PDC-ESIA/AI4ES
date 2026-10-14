## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A implementação atual tem complexidade O(n^2) no pior caso (para cada candidato faz copy/remove/sum sobre a lista). Com n até 1e5 isso causa Time Limit Exceeded — a solução falha nos critérios de aceite (CA-01, CA-02). Use um contador (collections.Counter ou dict de frequências) e itere sobre os valores únicos para reduzir a complexidade para O(k) onde k é o número de valores distintos (≤ 2001), ou O(n) total.

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: Projeto ineficiente: lógica core mistura verificação algébrica com operações pesadas de I/O de lista (copy, remove, sum) repetidas. A responsabilidade de validação pode ser concentrada numa verificação por contagem de ocorrências sem recriar/somar a lista a cada teste.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não há arquivos de teste/unitários entregues. Não foram providos testes que cubram o caminho feliz e casos de borda (por exemplo valores repetidos, sum_element == outlier, lista grande que demonstraria performance).

- severity: info  
  file: solution.py  
  layer: corretude  
  description: A verificação final `if sum(temp) == sum_element:` é logicamente redundante dado que sum_element foi derivado de (total_sum - outlier) // 2 — se sum_element existe com índice distinto do outlier a condição é algebraicamente satisfeita. Essa operação adicional custa O(n) e pode ser removida se a verificação de contagens for feita corretamente.

## Resumo
O arquivo solution.py implementa a lógica correta do ponto de vista algébrico (calcula sum_element = (total - outlier) / 2 e tenta validar presença do sum_element), mas a estratégia de validação faz cópias da lista e soma os elementos repetidamente, levando a complexidade quadrática e Time Limit Exceeded em entradas grandes. Isso viola os critérios de aceite que exigem que a correção elimine a falha observada. Recomenda-se reimplementar usando um Counter/dicionário de frequências e iterando sobre valores únicos para verificar disponibilidade dos elementos com contagens adequadas; isso reduz drasticamente o custo e resolve o TLE. Além disso, faltam testes automatizados para validar correção e performance.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A implementação atual tem complexidade O(n^2) no pior caso (para cada candidato faz copy/remove/sum sobre a lista). Com n até 1e5 isso causa Time Limit Exceeded — a solução falha nos critérios de aceite (CA-01, CA-02). Use um contador (collections.Counter ou dict de frequências) e itere sobre os valores únicos para reduzir a complexidade para O(k) onde k é o número de valores distintos (≤ 2001), ou O(n) total.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Projeto ineficiente: lógica core mistura verificação algébrica com operações pesadas de I/O de lista (copy, remove, sum) repetidas. A responsabilidade de validação pode ser concentrada numa verificação por contagem de ocorrências sem recriar/somar a lista a cada teste.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não há arquivos de teste/unitários entregues. Não foram providos testes que cubram o caminho feliz e casos de borda (por exemplo valores repetidos, sum_element == outlier, lista grande que demonstraria performance).",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "A verificação final `if sum(temp) == sum_element:` é logicamente redundante dado que sum_element foi derivado de (total_sum - outlier) // 2 — se sum_element existe com índice distinto do outlier a condição é algebraicamente satisfeita. Essa operação adicional custa O(n) e pode ser removida se a verificação de contagens for feita corretamente.",
      "file": "solution.py",
      "layer": "corretude"
    }
  ]
}
```