## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A solução itera explicitamente por todos os índices de 1 até N-1 (for i in range(1, N)). Com N até 2·10^9 isso é inviável (tempo de execução e uso de CPU impossíveis na prática) — a solução vai TLE / não será executável nos limites do problema. O algoritmo deve iterar apenas sobre as posições que têm pedras (ou usar saltos calculados entre posições) em O(M log M) ou O(M).

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não há arquivos de teste no workspace. Nenhum caso de unidade/integração foi entregue para verificar a correção, performance ou regressões.

## Resumo
A implementação corrige a lógica funcional do passo-a-passo (a simulação por célula devolve -1 para o exemplo fornecido e a contagem de operações está consistente para N pequenos), e as verificações de impossibilidade e soma total de pedras estão corretas. Contudo, a iteração explícita por todos os N-1 índices a torna impraticável para os limites do problema (N até 2·10^9) — isso é um bloqueador crítico. Além disso, faltam testes automatizados para validar correções e casos limite.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A solução itera explicitamente por todos os índices de 1 até N-1 (for i in range(1, N)). Com N até 2·10^9 isso é inviável (tempo de execução e uso de CPU impossíveis na prática) — a solução vai TLE / não será executável nos limites do problema. O algoritmo deve iterar apenas sobre as posições que têm pedras (ou usar saltos calculados entre posições) em O(M log M) ou O(M).",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não há arquivos de teste no workspace. Nenhum caso de unidade/integração foi entregue para verificar a correção, performance ou regressões.",
      "file": "solution.py",
      "layer": "completude"
    }
  ]
}
```