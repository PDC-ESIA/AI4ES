## Status: BLOQUEADO

## Issues

### Corretude

- **Arquivo: solution.py / Camada: corretude**
  - **Descrição:** A implementação corrigida ainda está incorreta. O código tenta calcular a soma total dos subarrays usando uma frequência de restos (`mod_freq`) para prefix sums, porém a soma acumulada resulta em valores inconsistentes (inclui somas ponderadas por `v` para todos os restos possíveis em `[0, M)`, mas o subarray correto é sempre: `(prefix_sum[r] - prefix_sum[l-1]) % M`, para cada `1 <= l <= r <= N`).  
    A contagem de subarrays cuja soma módulo M é `v` está errada: ela soma *todas* as possibilidades de `v` de 0 a M-1, multiplicando pela frequência de antecedente que geraria esse resto, o que gera supercontagem e respostas completamente incorretas.  
    O correto seria: para cada posição r, contar **para cada l < r quantas vezes `prefix_sum[l-1] == (prefix_sum[r] - v) % M` ocorreu** para um único valor de v, mas o problema pede o valor real do subarray, não apenas a contagem.  
    Além disso, está faltando o controle de todas as somas de subarray de todos os tamanhos, e não apenas por diferença de frequências de restos.  
    **Conclusão:** O output do código será sempre inválido para a maior parte dos casos devido à lógica incorreta de cálculo das somas de subarrays. O algoritmo não reflete corretamente o enunciado.

### Completude

- **Arquivo: solution.py / Camada: completude**
  - **Descrição:** Não há nenhum arquivo de teste entregue junto. Como a task é de programação competitiva, não é obrigatório um arquivo à parte, mas a ausência de auto-teste dificulta a validação manual de edge cases e confirmações pós-correção.

## Resumo

A tentativa de otimizar o cálculo da soma dos subarrays módulo M ainda não está correta funcionalmente: o código não calcula para cada subarray a soma real módulo M, e sim tenta combinar contagens de prefixos com múltiplos restos, resultando em um valor errado. Com isso, o principal critério de aceite (CA-01: Produzir a saída correta para toda entrada válida) não é cumprido. Além disso, não há cobertura de testes explícita (comum em problemas competitivos, mas relevante para revisão). Portanto, a submissão está BLOQUEADA até que a lógica do cálculo seja devidamente ajustada para somar corretamente todos os subarrays conforme o enunciado.