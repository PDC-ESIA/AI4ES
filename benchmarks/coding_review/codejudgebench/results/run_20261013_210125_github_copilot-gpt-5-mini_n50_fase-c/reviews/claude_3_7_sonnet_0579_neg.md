## Status: BLOQUEADO

## Issues

- severity: critical  
  file: solution.py  
  layer: arquitetura  
  description: A implementação aloca matrizes 2D completas `grid` e `prefix_sum` de tamanho (H+1) × (W+1). Para H = W = 3000 isso corresponde a ~9e6 entradas. Em Python uma lista de listas com inteiros desse tamanho consome memória muito maior que a estimativa de 9e6×(tamanho do int) — provavelmente vários centenas de MB até vários GB devido ao overhead de listas e objetos int, o que tende a causar MemoryError ou uso de memória além do limite de execução em ambientes de judge. Este problema torna a solução não executável para entradas máximas e bloqueia a entrega.

- severity: warning  
  file: solution.py  
  layer: corretude  
  description: A correção tratou eficientemente o caso N == 0 com fórmula matemática (bom), mas deixou o algoritmo geral inalterado: para N > 0 ele executa um laço triplo implícito (para cada top-left percorre tamanhos n crescentes) e ainda constrói prefix sums em toda a grade. Em instâncias intermediárias (por exemplo, poucos furos ou furos colocados de forma que muitos cantos superiores permitam grandes n) o tempo pode permanecer alto e possivelmente causar Time Limit Exceeded em alguns casos. A complexidade no pior caso continua demasiada para Python puro com H,W=3000.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram adicionados testes automatizados (unit tests / casos limites) nem scripts de verificação. Falta cobertura demonstrável dos cenários críticos além dos exemplos (happy path, N=0, N grande, casos com furos distribuídos).

- severity: info  
  file: solution.py  
  layer: arquitetura  
  description: O tratamento especial para N == 0 é uma correção apropriada e resolve o TLE observado para o caso sem furos. Entretanto, a solução geral precisa ser reestruturada para não depender de matrizes 2D completas: alternativas mais seguras em memória/tempo incluem trabalhar por linha com estruturas compactas, usar mapas/dicionários de furos por linha/coluna e técnicas de varredura/binary search ou algoritmos baseados em “largest square ending at” (DP) adaptados para furos esparsos.

## Resumo

A entrega resolve corretamente e eficientemente o caso observado que causava Time Limit Exceeded (N == 0) usando a fórmula matemática para somar quadrados; porém, a solução geral ainda aloca e percorre matrizes 2D completas (grid e prefix_sum) e itera intensamente sobre tamanhos de quadrados para cada topo — isso implica risco alto de uso excessivo de memória e tempo para H,W no limite (3000), o que torna a solução não confiável em ambientes de avaliação. Dado que há pelo menos uma issue crítica relacionada à arquitetura/memória, a task fica BLOQUEADA até que a implementação seja reescrita para evitar alocação de estruturas O(H·W) em Python e reduzir a complexidade do caso geral.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A implementação aloca matrizes 2D completas `grid` e `prefix_sum` de tamanho (H+1) × (W+1). Para H = W = 3000 isso corresponde a ~9e6 entradas, o que em Python consome memória suficiente para causar MemoryError ou violar limites de execução em judges.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "A correção trata o caso N == 0 com fórmula matemática (correto), mas o algoritmo geral continua com laços aninhados que podem causar TLE em instâncias com furos; a complexidade no pior caso permanece alta para Python com H,W=3000.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não há testes automatizados entregues cobrindo casos críticos (N=0, N grande, furos distribuídos).",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "O tratamento especial para N == 0 é adequado e resolve o TLE observado para esse caso. Recomenda-se reestruturar a solução geral para evitar estruturas O(H·W) (usar mapas por linha/coluna, DP adaptado, busca binária ou varredura por furos).",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```