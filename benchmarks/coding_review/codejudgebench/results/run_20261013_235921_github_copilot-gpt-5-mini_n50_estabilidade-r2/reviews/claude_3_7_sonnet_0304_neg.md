## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: Memoization bug — o código faz `if mask in memo: return memo[memo]` em vez de `return memo[mask]`. Isso causará um TypeError/KeyError quando for atingida uma entrada em memo e impede a execução correta da função.

- severity: critical  
  file: solution.py  
  layer: arquitetura  
  description: Abordagem incorreta/insustentável — o algoritmo usa programação dinâmica por máscara de bits sobre as posições divergentes (estado com 2^n combinações). Com n potencialmente até 500 (conforme restrições), essa estratégia é exponencial e impraticável (estouro de tempo/memória). Mesmo que o bug de memo fosse corrigido, o método não escala e falhará em entradas de tamanho moderado.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não há arquivos de teste no workspace. Não foram entregues testes automatizados cobrindo exemplos (happy path) nem casos de borda (p. ex. strings idênticas, todas diferentes, n pequeno e n grande), o que impede verificação automatizada da correção.

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: Uso de recursão com DP por máscara (mesmo com sys.setrecursionlimit aumentado) é arriscado e, aliado ao ponto exponencial, causa problemas de performance e risco de estouro de pilha para entradas realistas. Uma solução linear/DP por índice ou estratégica de emparelhamento é necessária.

## Resumo
O arquivo solution.py foi entregue, mas contém um defeito bloqueante (erro na recuperação do memo: `memo[memo]`), que faz a função falhar em tempo de execução, e adota uma abordagem arquitetural inviável (DP por máscara exponencial) para as restrições do problema (n até 500). Além disso, não foram incluídos testes automatizados. Devido à combinação de erro de implementação que impede execução e à escolha de algoritmo que não escala, a entrega deve ser bloqueada até que o memoization bug seja corrigido e, preferencialmente, a abordagem seja reescrita para um algoritmo polinomial (por exemplo DP linear sobre índices ou estratégia gulosa/dinâmica conhecida para esse problema). Também recomendo adicionar testes que cubram os exemplos do enunciado e casos de borda.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "Memoization bug — o código faz `if mask in memo: return memo[memo]` em vez de `return memo[mask]`. Isso causará um TypeError/KeyError quando for atingida uma entrada em memo e impede a execução correta da função.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "critical",
      "description": "Abordagem incorreta/insustentável — o algoritmo usa programação dinâmica por máscara de bits sobre as posições divergentes (estado com 2^n combinações). Com n potencialmente até 500 (conforme restrições), essa estratégia é exponencial e impraticável (estouro de tempo/memória). Mesmo que o bug de memo fosse corrigido, o método não escala e falhará em entradas de tamanho moderado.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não há arquivos de teste no workspace. Não foram entregues testes automatizados cobrindo exemplos (happy path) nem casos de borda (p. ex. strings idênticas, todas diferentes, n pequeno e n grande), o que impede verificação automatizada da correção.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "warning",
      "description": "Uso de recursão com DP por máscara (mesmo com sys.setrecursionlimit aumentado) é arriscado e, aliado ao ponto exponencial, causa problemas de performance e risco de estouro de pilha para entradas realistas. Uma solução linear/DP por índice ou estratégica de emparelhamento é necessária.",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```