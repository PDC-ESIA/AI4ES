## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: Lógica de transição do DP incorreta — ao estender uma subsequência anterior o código usa sempre dp[i] = nums[i] + prev_max quando prev_max != -inf. Se prev_max for negativo, estender é pior do que começar uma nova subsequência em i; a expressão correta é dp[i] = max(nums[i], nums[i] + prev_max) (ou tratar prev_max < 0 como não estender). Esse erro produz respostas incorretas (ex.: nums = [-5, -1] ou outros casos com prefixos negativos) e corresponde exatamente à falha funcional observada.

- severity: warning  
  file: (workspace)  
  layer: completude  
  description: Não foram entregues testes automatizados (nenhum arquivo de teste presente). O repositório contém apenas solution.py; adicionar testes unitários que cubram happy path e casos com números negativos e empates de diferença é recomendado.

- severity: warning  
  file: solution.py  
  layer: testes  
  description: Não há cases de verificação embutidos nem asserts no arquivo; sem testes não há garantia automatizada de correção depois do ajuste.

## Resumo
O arquivo solution.py implementa a ideia correta de usar a transformação a_i = nums[i] - i e um BIT (Fenwick) para obter o máximo dp entre índices com a_j <= a_i processando na ordem original — isso é arquiteturalmente adequado e tem complexidade O(n log n). Entretanto a regra de transição do DP é incorreta: o código não considera que começar uma nova subsequência em i pode ser melhor quando a melhor subsequência anterior tem soma negativa. Esse erro causa respostas erradas e bloqueia a aceitação. Também faltam testes automatizados para validar correções.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "Lógica de transição do DP incorreta — ao estender uma subsequência anterior o código usa sempre dp[i] = nums[i] + prev_max quando prev_max != -inf. Se prev_max for negativo, estender é pior do que começar uma nova subsequência em i; a expressão correta é dp[i] = max(nums[i], nums[i] + prev_max) (ou tratar prev_max < 0 como não estender). Esse erro produz respostas incorretas (ex.: nums = [-5, -1] ou outros casos com prefixos negativos) e corresponde exatamente à falha funcional observada.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues testes automatizados (nenhum arquivo de teste presente). O repositório contém apenas solution.py; adicionar testes unitários que cubram happy path e casos com números negativos e empates de diferença é recomendado.",
      "file": "(workspace)",
      "layer": "completude"
    },
    {
      "severity": "warning",
      "description": "Não há cases de verificação embutidos nem asserts no arquivo; sem testes não há garantia automatizada de correção depois do ajuste.",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```