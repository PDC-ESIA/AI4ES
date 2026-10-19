## Status: BLOQUEADO

## Issues

- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A solução atual armazena as posições de todos os N componentes em um deque e indexa esse deque para responder queries do tipo 2. Isso gera dois problemas funcionais que bloqueiam a correção: (1) inicialização e manutenção de N tuples consome tempo e memória O(N) (N ≤ 10^6) — risco de MLE/TLE; (2) indexing de collections.deque é O(n) por acesso, então responder queries do tipo 2 pode custar O(N) no pior caso, levando a TLE para entradas grandes. A estratégia correta é evitar representar todos os N nós explicitamente: mantenha apenas o histórico das posições da cabeça (lista com a posição inicial e as posições após cada movimento) e um contador de movimentos m. Para uma query atual com m movimentos, parte p tem posição:
    - se p <= m+1: head_history[m - (p-1)]
    - caso contrário: (p - m, 0)
  Essa abordagem tem custo O(1) por operação e memória O(M) onde M = número de movimentos (≤ Q), resolvendo os problemas de performance e memória.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram entregues artefatos de teste (nenhum arquivo de testes no workspace). Não há testes automatizados que validem correções para os casos limites (grandes N e padrões de queries que expõem o problema de performance). Recomendo incluir testes que cubram: cargas com N ~ 10^6 inicialização/limites de memória, Q ~ 2·10^5 com misturas de tipos 1 e 2, e casos onde p varia desde 1 até N.

## Resumo

O código submetido funciona corretamente em instâncias pequenas, mas a escolha de armazenar todas as N posições em um deque e indexá-lo para responder queries provoca consumo excessivo de memória e tempo (deque indexing é O(n)), resultando em TLE/MLE nas entradas grandes descritas pelo enunciado. A correção é conceitual: mantenha somente o histórico das posições da cabeça (lista) e o contador de movimentos m; responda queries em O(1) por fórmula simples (usar head_history quando p ≤ m+1, caso contrário (p - m, 0)). Após essa mudança a solução terá complexidade O(Q) em tempo e O(M) em memória (M ≤ Q), conforme restrições do problema. Além disso, inclua testes automatizados que cubram os limites para evitar regressões.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A solução armazena todas as N posições num deque e indexa esse deque para responder queries. Isso causa inicialização O(N) em tempo/memória (risco de MLE) e consultas O(N) (deque indexing é linear), levando a TLE/MLE. Use em vez disso o histórico das posições da cabeça (lista) e um contador de movimentos m: para query com p, se p <= m+1 responder head_history[m-(p-1)] senão (p-m, 0).",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues testes automatizados no workspace. Acrescente testes que verifiquem casos limite (N ~ 10^6, Q ~ 2e5) e variadas combinações de queries 1/2 para garantir que a correção remove o TLE/MLE.",
      "file": "solution.py",
      "layer": "completude"
    }
  ]
}
```