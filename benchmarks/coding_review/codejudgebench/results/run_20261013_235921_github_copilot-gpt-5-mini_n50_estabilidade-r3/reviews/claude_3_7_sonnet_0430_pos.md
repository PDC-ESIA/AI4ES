## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A solução usa recursão com memoização indexada por (idx, total). Como total pode crescer até a soma dos elementos (até 4e6 no pior caso), o espaço de estados e o tempo tornam-se impraticáveis (O(n * sum(rewardValues)) estados). Isso very likely causará MLE/TLE em entradas perto dos limites e, portanto, falha automatizada no critério CA-01 (não atende a todas as entradas válidas).

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não há arquivos de teste/unitários no workspace que verifiquem a correção; falta suíte de testes para validar a solução (incl. casos pequenos e limites).

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: Projeto com responsabilidade única ok, porém a escolha da estrutura de memoização (chave incluindo o "total") gera acoplamento entre dimensões que explode o espaço de estados. Recomenda-se uma abordagem baseada em bitset/inteiro para representar somas possíveis ao iterar valores ordenados, o que reduz memória e tempo na prática.

- severity: warning  
  file: solution.py  
  layer: testes  
  description: Mesmo sem arquivos de teste, a solução atual não evidencia testes para casos extremos (n=2000, valores=2000) nem para casos que mostram a diferença entre a solução gulosa e a ótima. Tests determinísticos cobrindo happy path e limites ausentes.

## Resumo
O código em solution.py está logicamente correto (explora todas as combinações) e resolve o caso relatado no enunciado, mas a implementação atual não escala para os limites do problema: a memoização por (idx, total) pode criar um número de estados proibitivo e levar a estouro de memória ou tempo de execução em entradas grandes. Como o critério de aceite CA-01 exige corretude para todas as entradas válidas, esta limitação é bloqueante. Recomendo substituir a abordagem por uma DP eficiente: ordenar os valores e usar um bitset representado por um inteiro (bit i = soma i alcançável); para cada valor v, permitir transição apenas de somas s < v fazendo dp |= ((dp & ((1<<v)-1)) << v). Essa versão corre eficientemente nas restrições dadas e produz 11 para o exemplo falho. Também solicito inclusão de testes unitários que cubram casos pequenos, casos que diferenciam estratégias gulosas e limites máximos.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A solução usa recursão com memoização indexada por (idx, total). Como total pode crescer até a soma dos elementos (até 4e6 no pior caso), o espaço de estados e o tempo tornam-se impraticáveis (O(n * sum(rewardValues)) estados). Isso very likely causará MLE/TLE em entradas perto dos limites e, portanto, falha automatizada no critério CA-01 (não atende a todas as entradas válidas).",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não há arquivos de teste/unitários no workspace que verifiquem a correção; falta suíte de testes para validar a solução (incl. casos pequenos e limites).",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "warning",
      "description": "Projeto com responsabilidade única ok, porém a escolha da estrutura de memoização (chave incluindo o \"total\") gera acoplamento entre dimensões que explode o espaço de estados. Recomenda-se uma abordagem baseada em bitset/inteiro para representar somas possíveis ao iterar valores ordenados, o que reduz memória e tempo na prática.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Mesmo sem arquivos de teste, a solução atual não evidencia testes para casos extremos (n=2000, valores=2000) nem para casos que mostram a diferença entre a solução gulosa e a ótima. Tests determinísticos cobrindo happy path e limites ausentes.",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```