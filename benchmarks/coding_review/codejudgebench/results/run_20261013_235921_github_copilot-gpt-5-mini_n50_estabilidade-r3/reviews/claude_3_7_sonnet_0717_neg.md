## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: Algoritmo com complexidade O(N * M) no pior caso. O código itera sobre toda a lista de boxes para cada pessoa (laço aninhado implícito), o que causa Time Limit Exceeded em entradas grandes (N, M até 2e5). Esta falha torna a solução inexequível no ambiente de avaliação e bloqueia a entrega.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram incluídos arquivos de teste (unit tests, casos de borda ou testes de performance) no workspace. Critério CA-02 (eliminar TLE observado) não pode ser comprovado por testes entregues; falta de testes deve ser registrada como ressalva.

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: Estratégia atual mantém a lista completa de boxes e usa um conjunto de índices usados, mas revarre a lista do início para cada pessoa. Isso revela acoplamento entre a escolha (pesquisa linear repetida) e o armazenamento dos boxes. Recomenda-se usar uma abordagem com ordenação + heap/pointer (ex.: processar pessoas por requisito decrescente e empilhar boxes elegíveis, retirando sempre o menor preço), o que reduz complexidade para O((N+M) log N).

## Resumo
O arquivo `solution.py` está funcional em entradas pequenas, mas contém uma falha de escalabilidade grave: a abordagem atual é O(N*M) e causará TLE em entradas grandes (como a indicada no relato). Isso é um problema crítico e bloqueia a aceitação. Além disso, não foram fornecidos testes para validar a correção e o desempenho da solução. Para aceitar a tarefa, a implementação deve ser reescrita usando uma estrutura eficiente (por exemplo, ordenar pessoas e caixas e usar um heap com ponteiro para obter complexidade O((N+M) log N)), e idealmente incluir casos de teste que comprovem a remoção do TLE.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "Algoritmo com complexidade O(N * M) no pior caso. O código itera sobre toda a lista de boxes para cada pessoa (laço aninhado implícito), o que causa Time Limit Exceeded em entradas grandes (N, M até 2e5). Esta falha torna a solução inexequível no ambiente de avaliação e bloqueia a entrega.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram incluídos arquivos de teste (unit tests, casos de borda ou testes de performance) no workspace. Critério CA-02 (eliminar TLE observado) não pode ser comprovado por testes entregues; falta de testes deve ser registrada como ressalva.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "warning",
      "description": "Estratégia atual mantém a lista completa de boxes e usa um conjunto de índices usados, mas revarre a lista do início para cada pessoa. Isso revela acoplamento entre a escolha (pesquisa linear repetida) e o armazenamento dos boxes. Recomenda-se usar uma abordagem com ordenação + heap/pointer (ex.: processar pessoas por requisito decrescente e empilhar boxes elegíveis, retirando sempre o menor preço), o que reduz complexidade para O((N+M) log N).",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```