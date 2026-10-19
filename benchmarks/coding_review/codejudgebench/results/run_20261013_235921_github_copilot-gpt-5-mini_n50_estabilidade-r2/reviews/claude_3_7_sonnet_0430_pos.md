## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: Algoritmo incorreto — o código ordena rewardValues em ordem crescente e explora apenas selecionar itens nessa ordem. Isso restringe arbitrariamente a ordem de escolha e falha em casos onde é necessário pular elementos menores para escolher um maior primeiro (ex.: [1,6,4,3,2] → saída obtida 7, saída esperada 11). A lógica assume uma propriedade que não vale para o problema, portanto entrega resultados incorretos.

- severity: critical  
  file: solution.py  
  layer: arquitetura  
  description: Complexidade e uso de memória impraticáveis para limites do problema — o memo usa a tupla (idx, total) como chave, onde total pode crescer até a soma de todos os valores (até ~4e6). Com n até 2000 isso pode produzir um espaço de estados enorme e/ou estar fora dos limites de tempo/memória práticos; além disso a recursão em profundidade n=2000 é arriscada (embora sys.setrecursionlimit tenha sido ajustado). O método não escala para as restrições dadas.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram entregues arquivos de teste unitários nem casos de validação automatizados junto com a implementação. Tests ajudam a demonstrar correção (por exemplo, incluir o caso que falhava anteriormente e outros casos limites).

- severity: warning  
  file: solution.py  
  layer: testes  
  description: Sem testes — não há cobertura de cenários críticos (happy path + edge cases) fornecida. Recomenda-se adicionar testes que incluam o exemplo que falhava, casos com repetição de valores, casos em que escolher elementos maiores primeiro é vantajoso, e casos-limite (n=1, n grande, valores máximos).

## Resumo
A implementação presente em solution.py não resolve corretamente o problema: ela impõe uma ordem de seleção (ordenando ascendentemente) que não reflete a liberdade de escolha permitida pelo enunciado, levando a respostas erradas (ex.: o caso fornecido). Além disso, a estratégia de memoização por (idx, total) não é escalável para os limites do problema e pode causar uso excessivo de tempo/memória. Faltam testes automatizados que comprovem correção e cubram os casos observados. Devido à combinação de incorreção funcional e problemas de escalabilidade, a entrega está bloqueada até que o algoritmo seja substituído por uma abordagem correta e eficiente e testes sejam adicionados.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "Algoritmo incorreto — o código ordena rewardValues em ordem crescente e explora apenas selecionar itens nessa ordem. Isso restringe arbitrariamente a ordem de escolha e falha em casos onde é necessário pular elementos menores para escolher um maior primeiro (ex.: [1,6,4,3,2] → saída obtida 7, saída esperada 11). A lógica assume uma propriedade que não vale para o problema, portanto entrega resultados incorretos.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "critical",
      "description": "Complexidade e uso de memória impraticáveis para limites do problema — o memo usa a tupla (idx, total) como chave, onde total pode crescer até a soma de todos os valores (até ~4e6). Com n até 2000 isso pode produzir um espaço de estados enorme e/ou estar fora dos limites de tempo/memória práticos; além disso a recursão em profundidade n=2000 é arriscada (embora sys.setrecursionlimit tenha sido ajustado). O método não escala para as restrições dadas.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues arquivos de teste unitários nem casos de validação automatizados junto com a implementação. Tests ajudam a demonstrar correção (por exemplo, incluir o caso que falhava anteriormente e outros casos limites).",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "warning",
      "description": "Sem testes — não há cobertura de cenários críticos (happy path + edge cases) fornecida. Recomenda-se adicionar testes que incluam o exemplo que falhava, casos com repetição de valores, casos em que escolher elementos maiores primeiro é vantajoso, e casos-limite (n=1, n grande, valores máximos).",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```