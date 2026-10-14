## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A implementação ainda faz uma varredura linear (for person in range(1, N + 1)) para encontrar a pessoa da frente em cada evento, resultando em complexidade O(N * M) no pior caso. Com N, M até 2e5 isso causará Time Limit Exceeded; a correção não eliminou a falha observada (CA-02).

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: Estrutura de dados inadequada para a operação mais crítica. Em vez de escanear linearmente, deve-se manter um heap/min-heap de pessoas atualmente disponíveis (inicializado com 1..N), pop para obter a frente e push quando a pessoa retorna, limpando do heap elementos marcados como "out" (lazy deletion). A mistura atual de set + varredura não é escalável.

- severity: warning  
  file: solution.py  
  layer: testes  
  description: Não há arquivos de teste no workspace nem casos de regressão (por exemplo, os samples do enunciado). Ausência de testes automatizados dificulta a validação contra TLE/regressões.

- severity: info  
  file: solution.py  
  layer: completude  
  description: Apenas solution.py foi entregue (conforme contrato). Não há documentação adicional nem comentários explicando a escolha de estrutura de dados ou complexidade esperada.

## Resumo
O arquivo solution.py está funcional para entradas pequenas, mas não resolveu o problema de performance que causou Time Limit Exceeded: a seleção da pessoa da frente ainda é feita por varredura linear em cada evento, levando a O(N*M). Para aceitar, implemente a seleção em O(log N) usando um min-heap de pessoas disponíveis (1..N) com push ao retorno e lazy-removal dos ids que estiverem temporariamente fora; após essa alteração e adicionando testes com os samples do enunciado, a solução provavelmente passará nos critérios automatizados. Até lá, a task está bloqueada por falha de corretude/performance.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A implementação ainda faz uma varredura linear (for person in range(1, N + 1)) para encontrar a pessoa da frente em cada evento, resultando em complexidade O(N * M) no pior caso. Com N, M até 2e5 isso causará Time Limit Exceeded; a correção não eliminou a falha observada (CA-02).",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Estrutura de dados inadequada para a operação mais crítica. Em vez de escanear linearmente, deve-se manter um heap/min-heap de pessoas atualmente disponíveis (inicializado com 1..N), pop para obter a frente e push quando a pessoa retorna, limpando do heap elementos marcados como \"out\" (lazy deletion). A mistura atual de set + varredura não é escalável.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não há arquivos de teste no workspace nem casos de regressão (por exemplo, os samples do enunciado). Ausência de testes automatizados dificulta a validação contra TLE/regressões.",
      "file": "solution.py",
      "layer": "testes"
    },
    {
      "severity": "info",
      "description": "Apenas solution.py foi entregue (conforme contrato). Não há documentação adicional nem comentários explicando a escolha de estrutura de dados ou complexidade esperada.",
      "file": "solution.py",
      "layer": "completude"
    }
  ]
}
```