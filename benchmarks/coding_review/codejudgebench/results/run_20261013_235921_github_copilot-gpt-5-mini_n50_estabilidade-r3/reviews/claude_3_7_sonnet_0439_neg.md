## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A lógica para calcular o comprimento máximo de uma subsequência de paridade alternada está incorreta. O código assume que, quando existem even_count e odd_count, é sempre possível construir uma subsequência alternada de comprimento 2 * min(even_count, odd_count), ignorando a ordem original dos elementos. Essa suposição é falsa: a ordem dos elementos pode impedir o entrelaçamento completo de pares. Exemplo simples: nums = [2, 4, 1, 3] (paridades e, e, o, o). even_count = odd_count = 2 → código retorna 4, mas o maior subsequência válida alternada possível respeitando a ordem é 2. A implementação atual pode produzir resultados incorretos para muitos casos e, portanto, não atende ao critério CA-01 (saídas corretas para todas entradas).

- severity: warning  
  file: solution.py  
  layer: testes  
  description: Não há arquivos de teste no workspace cobrindo casos críticos (happy path e edge cases). Pelo enunciado/DoD, não foram entregues testes automatizados que validem cenários como entradas que forçam alternância limitada pela ordem, arrays já todos de mesma paridade, e casos mínimos (tamanho 2). Recomenda-se adicionar testes unitários cobrindo esses casos para evitar regressões.

## Resumo
A solução substituiu o DP O(n^2) por uma abordagem O(1) baseada em contagens, o que resolve o problema de TLE, porém introduziu uma suposição incorreta: que todos os pares de paridades podem ser intercalados independentemente da ordem. Isso gera resultados incorretos em muitos casos e portanto bloqueia a aceitação. A correção exigida é trocar a fórmula 2 * min(even_count, odd_count) por uma computação que respeite a ordem — por exemplo, duas varreduras greedy para computar o máximo possível de alternâncias (uma supondo início por paridade par, outra por paridade ímpar), além de comparar com o maior conjunto de mesma paridade. Após essa correção e adição de testes que cubram os casos citados, o código poderá ser reavaliado.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A lógica para alternância usa 2 * min(even_count, odd_count) assumindo que todos os evens/odds podem ser intercalados independente da ordem. Isso é incorreto (ex.: [2,4,1,3] faz o código retornar 4 enquanto o máximo válido é 2).",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não há testes automatizados fornecidos cobrindo cenários críticos (alternância limitada pela ordem, todos mesmos pares, casos mínimos).",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```