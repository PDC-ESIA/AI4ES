## Status: BLOQUEADO

## Issues

- severity: critical  
  file: solution.py  
  layer: corretude  
  description: O algoritmo itera de 1 até N (for i in range(1, N)), o que é inviável quando N pode ser até 2×10^9. Isso torna a solução impraticável (TLE / uso excessivo de CPU) nos limites do problema. A lógica simula passo-a-passo corretamente para N pequenos, mas falhará em tempo/recursos nas entradas válidas de grande escala. É necessário reescrever a iteração para percorrer apenas as posições que contêm pedras (sorted X) e usar os comprimentos dos "gaps" para multiplicar o número de pedras em trânsito pelo tamanho do salto (operations += excess * gap), mantendo as mesmas verificações de impossibilidade.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram incluídos testes automatizados (unit tests / casos de borda). Pelo menos adicionar testes cobrindo: (1) casos pequenos (os exemplos do enunciado), (2) casos com grandes gaps e pouca pedra (verifica retorno -1), e (3) casos extremos (M=N e M=1) ajudaria a evitar regressões.

## Resumo

A implementação contém uma lógica correta para simular o preenchimento das células e conta corretamente o número de operações quando executada passo-a-passo, e resolve os exemplos fornecidos. Entretanto, ela faz uma iteração por todas as posições 1..N, o que é proibitivo dado N ≤ 2×10^9 — essa limitação é bloqueante para aceitação. Recomendo reimplementar a varredura sobre as posições fornecidas (ordenadas), computando saltos (gaps) e acumulando operações por multiplicação (operations += excess * gap), com as mesmas checagens de impossibilidade aplicadas nos pontos intermediários; isso reduz a complexidade a O(M log M) (ou O(M) após ordenação), adequada para os limites do problema. Também é desejável adicionar testes automatizados cobrindo casos típicos e de borda.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "O algoritmo itera de 1 até N, o que é inviável para N até 2e9 — causará TLE/uso excessivo de recursos. Requer reescrever para iterar apenas sobre posições com pedras e usar gaps para multiplicar passos.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Arquivo de testes não foi criado; faltam testes automatizados para exemplos e bordas (ex.: exemplos do enunciado, grandes gaps, M=1, M=N).",
      "file": "solution.py",
      "layer": "completude"
    }
  ]
}
```