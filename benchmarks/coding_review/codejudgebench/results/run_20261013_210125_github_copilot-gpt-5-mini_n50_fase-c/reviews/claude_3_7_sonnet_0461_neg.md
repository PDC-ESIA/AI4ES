## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: Lógica de transição incorreta quando nums[i] > nums[i-1]. O código usa upper_bound = min(max(0, j - diff), nums[i-1]) — isto converte um valor negativo de (j - diff) em 0, permitindo transições que deveriam ser inválidas. A condição correta exige que o limite superior para valores anteriores seja ub = j - max(0, diff); se ub < 0 então não há estados anteriores válidos (dp[i][j] deve ser 0). A implementação atual conta configurações extras, causando overcount (ex.: para [2,3,2] produz 7 em vez de 4).

- severity: warning  
  file: workspace (solution.py)  
  layer: completude  
  description: Não foram incluídos arquivos de teste automatizados que verifiquem o comportamento (happy path e casos limite como arrays crescentes, decrescentes e casos com aumento de nums). Sem testes, a correção não pode ser validada automaticamente no pipeline.

- severity: info  
  file: solution.py  
  layer: arquitetura  
  description: O DP é alocado em 2D com largura max(nums)+1; isso é aceitável para as restrições (n <= 2000, nums[i] <= 50). Poderia ser otimizado para duas linhas (rolling array) para reduzir uso de memória, mas não é necessário para correção funcional.

## Resumo
O código fornecido implementa uma solução DP plausível e já trata prefix sums para transições eficientes, mas contém um erro lógico específico na computação do intervalo de valores anteriores quando nums aumenta. Esse erro transforma limites negativos em 0, introduzindo transições inválidas e resultando em contagens incorretas (falha comprovada pelo exemplo do enunciado). Além disso faltam testes automatizados para validar a solução. Devido ao erro de corretude que afeta os requisitos funcionais, a entrega fica bloqueada até a correção da transição.

Sugestão de correção (conceito): ao computar a transição para dp[i][j] faça
- need = max(0, nums[i] - nums[i-1])
- ub = j - need
- se ub < 0: dp[i][j] = 0
- senão ub = min(ub, nums[i-1]); dp[i][j] = prefix_sum[ub + 1] % MOD

Adicionar testes que cubram:
- exemplos do enunciado ([2,3,2] -> 4, [5,5,5,5] -> 126)
- casos com nums estritamente crescentes/decrescentes
- limites (n=1, nums[i]=1 e nums[i]=50)

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "Lógica de transição incorreta quando nums[i] > nums[i-1]. O código usa upper_bound = min(max(0, j - diff), nums[i-1]) — isto converte um valor negativo de (j - diff) em 0, permitindo transições que deveriam ser inválidas. A condição correta exige que o limite superior para valores anteriores seja ub = j - max(0, diff); se ub < 0 então não há estados anteriores válidos (dp[i][j] deve ser 0). A implementação atual conta configurações extras, causando overcount (ex.: para [2,3,2] produz 7 em vez de 4).",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram incluídos arquivos de teste automatizados que verifiquem o comportamento (happy path e casos limite como arrays crescentes, decrescentes e casos com aumento de nums). Sem testes, a correção não pode ser validada automaticamente no pipeline.",
      "file": "workspace (solution.py)",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "O DP é alocado em 2D com largura max(nums)+1; isso é aceitável para as restrições (n <= 2000, nums[i] <= 50). Poderia ser otimizado para duas linhas (rolling array) para reduzir uso de memória, mas não é necessário para correção funcional.",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```