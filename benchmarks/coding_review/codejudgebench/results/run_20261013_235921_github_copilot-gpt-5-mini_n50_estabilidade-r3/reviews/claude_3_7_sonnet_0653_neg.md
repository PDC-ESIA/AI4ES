## Status: BLOQUEADO

## Issues

- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A algorithm está incorreta — produz respostas erradas (não atende CA-01 / CA-02). A solução ainda falha no exemplo fornecido no enunciado. Para a Entrada de exemplo 1 (a mesma do relato), a função retorna 4 (ou retornava 2 antes da alteração), enquanto a saída esperada é 5. O DP/recorrência atual (usar sum(children) - max(children) + 1 com caso especial para um único filho) não reflete corretamente o processo de remoção de folhas em geral e produz resultados incorretos para várias topologias de árvore.

- severity: critical  
  file: solution.py  
  layer: corretude  
  description: Risco de estouro de pilha (RecursionError) em casos limites. O ambiente pré-carregado define sys.setrecursionlimit(50000), mas N pode chegar a 3×10^5; a DFS recursiva usada aqui pode ultrapassar esse limite em árvores do tipo caminho e causar exceção em entradas válidas grandes. Isso torna a solução não executável para os limites máximos do problema.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não há testes automatizados (unit tests / casos de borda) no workspace. O enunciado e as falhas observadas mostram exemplos — esses e outros casos críticos (pequenas árvores, caminhos longos, estrela, etc.) deveriam ser incluídos como testes para validar a correção da implementação.

- severity: info  
  file: solution.py  
  layer: arquitetura  
  description: O código depende de imports e configuração de recursão que vêm do "ambiente pré-carregado" (conforme indicado no enunciado). Isso deve estar documentado (está no enunciado), mas torna a função menos explícita quanto à necessidade de ajuste do recursionlimit. Como boa prática, implementar versão iterativa ou ajustar recursionlimit explicitamente com margem segura para N máximo.

## Resumo

A entrega não está correta: a função principal contém uma formulação de DP que não corresponde ao processo real de remoção ótima de folhas e já falha no exemplo do enunciado — logo não atende os critérios de aceite automáticos. Além disso, a implementação usa DFS recursiva que pode causar RecursionError para N grande (limite do problema); isto impede que a solução seja considerada confiável/produzível em produção. Recomendo bloquear a entrega até (1) rever a abordagem algorítmica e fornecer uma prova/argumento do DP correto (ou uma simulação/gulosa correta) e (2) tornar a travessia segura para N ≤ 3e5 (usar iteração/stack ou garantir recursionlimit > N). Adicionalmente, inclua testes que cubram os exemplos do enunciado e casos limites (linha, estrela, root já folha, etc.).

Sugestões de próxima etapa (rápidas):
- Reavaliar a definição do estado DP. Uma formulação robusta típica é: enraizar em 1 e para cada nó computar o custo mínimo para "remover" esse nó assumindo que não podemos tocar seu pai, e então no nó 1 escolher qual subárvore manter. Se a derivação DP for confusa, implementar uma busca por força controlada/greedy simulando remoções por camadas (BFS/priority) que processe folhas em ordem apropriada até que o vértice 1 seja removido — isso pode ser feito em O(N) com deque/contagem de graus.  
- Substituir DFS recursivo por versão iterativa (stack) para evitar RecursionError, ou aumentar recursionlimit além de 3e5+10 (menos desejável).

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A algorithm está incorreta — produz respostas erradas (não atende CA-01 / CA-02). A solução ainda falha no exemplo fornecido no enunciado. Para a Entrada de exemplo 1 a função retorna um valor diferente do esperado. O DP/recorrência atual (usar sum(children) - max(children) + 1 com caso especial para um único filho) não reflete corretamente o processo de remoção de folhas em geral e produz resultados incorretos para várias topologias de árvore.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "critical",
      "description": "Risco de estouro de pilha (RecursionError) em casos limites. O ambiente define recursionlimit=50000 mas N pode ser até 3e5; a DFS recursiva usada pode ultrapassar esse limite e falhar em entradas grandes.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não há testes automatizados (unit tests / casos de borda) no workspace. Casos do enunciado e casos extremos (linha, estrela, root já folha, N=2, etc.) deveriam ser adicionados.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "Dependência do ambiente pré-carregado (imports e recursionlimit) está correta segundo o enunciado, mas o código deveria ser explícito quanto à necessidade de uma travessia iterativa ou um ajuste seguro do recursionlimit para N máximo.",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```