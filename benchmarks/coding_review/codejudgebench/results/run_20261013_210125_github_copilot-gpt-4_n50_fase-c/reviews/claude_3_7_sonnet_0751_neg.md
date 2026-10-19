## Status: APROVADO

## Issues

Nenhuma issue encontrada.

## Resumo

A solução corrigida em `solution.py` substitui o algoritmo ineficiente O(N²) por uma abordagem eficiente O(N), utilizando mapas de contagem de prefixos para calcular os estados da programação dinâmica. Isso viabiliza a execução para N até 2 × 10⁵, eliminando o problema de timeout observado anteriormente. O código segue boas práticas de arquitetura, sem acoplamento indevido ou mistura de responsabilidades. Toda a lógica é tratada em função pura, não havendo falhas aparentes de segurança, edge cases, nem bugs lógicos observáveis. Embora não haja arquivos de teste explícitos, isso é aceitável pois se trata de um problema de programação competitiva, onde a função `solve()` lê a entrada do stdin, conforme esperado pelo enunciado.

```json
{
  "status": "APROVADO",
  "issues": []
}
```