## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A implementação atual está incorreta e tem complexidade algorítmica inaceitável para os limites do problema. A função incrementa result apenas quando count_max >= k para o par (i, j) corrente, contabilizando somente o subarray que termina em j, em vez de contabilizar também todos os subarrays com o mesmo início i e fim >= j (ou usar uma formula combinatória). Além disso o algoritmo é quadrático (duplo for), o que causa Time Limit Exceeded para n ~ 10^5. Isso faz com que os critérios de aceite CA-01 e CA-02 não sejam atendidos: resultados errados para muitos casos e falha observada de TLE não foi eliminada.

- severity: warning  
  file: (workspace)  
  layer: completude  
  description: Não há arquivos de teste/unitários no workspace cobrindo a função. Tests automatizados (happy path e edge cases: k > count, k = 1, ocorrências consecutivas, início/fim do vetor) não foram fornecidos, o que dificulta verificações de regressão.

## Resumo
A solução entregue em solution.py não está correta nem eficiente. O algoritmo atual falha em contar todos os subarrays válidos (contabiliza apenas o subarray que termina exatamente em j) e permanece O(n^2), levando a Time Limit Exceeded em entradas grandes. Recomendo reescrever countSubarrays usando os índices das ocorrências do elemento máximo: colecione as posições pos[] onde nums[pos]==max_element; para cada i tal que existe pos[i+k-1], acumule (pos[i] - prev_pos) * (next_pos - pos[i+k-1]) onde prev_pos = pos[i-1] ou -1, next_pos = pos[i+k] ou n. Isso produz resultado correto em O(m) onde m = número de ocorrências do máximo (≤ n) e resolve tanto a corretude quanto a performance. Além disso, adicione testes automatizados cobrindo casos limites.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A implementação atual está incorreta e tem complexidade algorítmica inaceitável para os limites do problema. A função incrementa result apenas quando count_max >= k para o par (i, j) corrente, contabilizando somente o subarray que termina em j, em vez de contabilizar também todos os subarrays com o mesmo início i e fim >= j (ou usar uma formula combinatória). Além disso o algoritmo é quadrático (duplo for), o que causa Time Limit Exceeded para n ~ 10^5. Isso faz com que os critérios de aceite CA-01 e CA-02 não sejam atendidos: resultados errados para muitos casos e falha observada de TLE não foi eliminada.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não há arquivos de teste/unitários no workspace cobrindo a função. Tests automatizados (happy path e edge cases: k > count, k = 1, ocorrências consecutivas, início/fim do vetor) não foram fornecidos, o que dificulta verificações de regressão.",
      "file": "(workspace)",
      "layer": "completude"
    }
  ]
}
```