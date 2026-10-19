## Status: BLOQUEADO

## Issues
- critical — solution.py — corretude  
  Descrição: O código usa collections.deque e faz indexing direto (head_history[p-1]). Em Python, o acesso por índice em deque é O(k) (linear na distância do índice), portanto cada consulta do tipo 2 pode custar tempo linear no deslocamento pedido. Com N e Q nos limites do problema isso pode resultar em Time Limit Exceeded. Este é um problema funcional que mantém a solução inaceitavelmente lenta para entradas grandes.

- warning — solution.py — arquitetura  
  Descrição: Há um uso misto de operações de cabeça (appendleft/pop) e acessos indexados aleatórios na mesma estrutura (deque). Isso indica uma escolha de estrutura inadequada para os padrões de acesso (precisa-se de push/pop amortizado O(1) e também de indexing O(1)). Uma estrutura mais adequada é uma lista (mantendo o histórico com append e usando indexação negativa) — assim as consultas ficam O(1).

- warning — solution.py — completude  
  Descrição: Não foram entregues testes automatizados cobrindo casos críticos (happy path + casos limites, incluindo cenários com p muito grande e muitos queries). A ausência de testes dificulta garantir que a correção realmente elimina o TLE em todos os casos.

## Resumo
A solução corrige a atualização quadrática anterior e move para um histórico do cabeçalho, o que é a direção correta. Entretanto ela usa collections.deque e faz indexação por posição (head_history[p-1]), que em deque é operação linear — isto provavelmente reproduz o Time Limit Exceeded observado. Recomendo trocar a deque por uma lista (append ao final) e acessar posições com indexação negativa (head_history[-p]) ou ajustar a organização do histórico para garantir indexing O(1). Também recomendo adicionar testes que incluam casos com muitos movimentos e consultas aleatórias para validar desempenho.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "O código usa collections.deque e faz indexing direto (head_history[p-1]). O acesso por índice em deque é O(k), então consultas do tipo 2 podem custar tempo linear e causar TLE em entradas grandes.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Estrutura inadequada para o padrão de acesso: mistura appendleft/pop com acessos indexados aleatórios. Use lista com append e indexação negativa para O(1) em consultas.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues testes automatizados cobrindo casos críticos (performance e limites).",
      "file": "solution.py",
      "layer": "completude"
    }
  ]
}
```