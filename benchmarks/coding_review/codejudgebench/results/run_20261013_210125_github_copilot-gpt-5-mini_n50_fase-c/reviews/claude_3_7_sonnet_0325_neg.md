## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A lógica de transição do DP está incorreta: o código sempre estende a melhor subsequência anterior (prev_max) sem considerar que iniciar uma nova subsequência pode ser melhor quando prev_max é negativo. Concretamente, a implementação faz dp[i] = nums[i] + prev_max (quando prev_max != -inf), mas o correto é dp[i] = nums[i] + max(0, prev_max). Como resultado a solução produz respostas erradas em casos com somas parciais negativas (ex.: nums = [-2, -1] devolve -2 em vez de -1).

- severity: warning  
  file: (workspace)  
  layer: completude  
  description: Não foram entregues arquivos de teste/unitários junto com a implementação. Recomenda-se adicionar testes que cubram os exemplos do enunciado e casos com somas negativas, duplicatas de diff e comprimentos extremos.

## Resumo
A implementação segue a ideia correta (transformar a condição em diffs = nums[i] - i, usar compressão de coordenadas e um BIT para obter o máximo prefixo), e processa os elementos na ordem original — a parte estrutural está correta. No entanto há um erro de corretude na fórmula do DP: ela não toma o máximo entre começar uma nova subsequência e estender uma subsequência anterior (não trata prev_max negativo). Esse defeito causa resultados incorretos (casos de Wrong Answer) e, portanto, a entrega está bloqueada até corrigir essa transição. Além disso, faltam testes automatizados para validar essa e outras situações limites.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A lógica de transição do DP está incorreta: o código sempre estende a melhor subsequência anterior (prev_max) sem considerar que iniciar uma nova subsequência pode ser melhor quando prev_max é negativo. Concretamente, a implementação faz dp[i] = nums[i] + prev_max (quando prev_max != -inf), mas o correto é dp[i] = nums[i] + max(0, prev_max). Como resultado a solução produz respostas erradas em casos com somas parciais negativas (ex.: nums = [-2, -1] devolve -2 em vez de -1).",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues arquivos de teste/unitários junto com a implementação. Recomenda-se adicionar testes que cubram os exemplos do enunciado e casos com somas negativas, duplicatas de diff e comprimentos extremos.",
      "file": "(workspace)",
      "layer": "completude"
    }
  ]
}
```