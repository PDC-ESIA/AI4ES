

## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: Implementação tem complexidade O(n^2) no pior caso: para cada right e cada ajuste de left o código recalcula a soma das distâncias ao mediano com um loop, levando a até ~O(n^2) operações para n=10^5. Isso causará TLE nas entradas máximas descritas nas restrições e fará a solução falhar nos testes automáticos (não atende CA-01).

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: A estratégia de janela recalcula median/operations do zero a cada expansão/redução da janela em loops aninhados. Falta separação de responsabilidades para cálculo incremental (ex.: prefix sums ou soma cumulativa) que permitiria solução O(n). A função é correta para entradas pequenas, mas a arquitetura não escala.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram entregues testes automatizados (unit tests). Não há arquivos em workspace que verifiquem happy path e casos limites (n grande, k grande, todos iguais, todos distintos). Adicionar testes para CA-01 e para o caso que falhava anteriormente (ex.: [[1,2,4,6], 3]).

- severity: info  
  file: solution.py  
  layer: corretude  
  description: A verificação de viabilidade da janela usa a soma das distâncias ao mediano, que é o custo mínimo para tornar todos os elementos da janela iguais. Essa lógica é válida para checar se uma janela específica pode ser igualada com ≤ k operações, mas o custo mínimo calculado exige recomputação explícita na implementação atual, causando o problema de performance acima.

## Resumo
O arquivo solution.py implementa uma verificação correta da viabilidade de uma janela (usa soma das distâncias ao mediano), e a função produz resultados corretos em entradas pequenas, incluindo o caso relatado. Entretanto a implementação recalcula custos em loops aninhados, resultando em complexidade O(n^2) e risco concreto de TLE para os limites do problema (n até 10^5). Isso impede que a solução passe os testes automáticos de aceitação (CA-01). Além disso, não foram incluídos testes automatizados. Recomendo reescrever a janela com cálculo incremental usando prefix sums (custo para tornar a janela igual ao valor de nums[right]: cost = nums[right]*window_size - sum(window)) para obter solução O(n), e adicionar testes que cubram casos limites e o exemplo que falhava.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "Implementação tem complexidade O(n^2) no pior caso: para cada right e cada ajuste de left o código recalcula a soma das distâncias ao mediano com um loop, levando a até ~O(n^2) operações para n=10^5. Isso causará TLE nas entradas máximas descritas nas restrições e fará a solução falhar nos testes automáticos (não atende CA-01).",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "A estratégia de janela recalcula median/operations do zero a cada expansão/redução da janela em loops aninhados. Falta separação de responsabilidades para cálculo incremental (ex.: prefix sums ou soma cumulativa) que permitiria solução O(n). A função é correta para entradas pequenas, mas a arquitetura não escala.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues testes automatizados (unit tests). Não há arquivos em workspace que verifiquem happy path e casos limites (n grande, k grande, todos iguais, todos distintos). Adicionar testes para CA-01 e para o caso que falhava anteriormente (ex.: [[1,2,4,6], 3]).",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "A verificação de viabilidade da janela usa a soma das distâncias ao mediano, que é o custo mínimo para tornar todos os elementos da janela iguais. Essa lógica é válida para checar se uma janela específica pode ser igualada com ≤ k operações, mas o custo mínimo calculado exige recomputação explícita na implementação atual, causando o problema de performance acima.",
      "file": "solution.py",
      "layer": "corretude"
    }
  ]
}
```