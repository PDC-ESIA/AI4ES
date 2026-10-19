## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A lógica para subsequências de paridade alternada é incorreta. O código assume alternating_parity_length = 2 * min(even_count, odd_count), usando apenas as contagens de pares/ímpares e ignorando a ordem dos elementos no array. Isso produz comprimentos impossíveis em muitos casos (ex.: todos os pares vêm antes de todos os ímpares) e falha nos requisitos funcionais — a solução retornará respostas erradas para entradas válidas.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram incluídos arquivos de teste (unit tests) cobrindo casos críticos (happy path, casos com blocos de pares/ímpares agrupados, alternâncias já presentes, pequenas entradas). A ausência de testes automatizados dificulta detectar regressões e verificar a correção da solução.

- severity: warning  
  file: solution.py  
  layer: corretude  
  description: A verificação final que transforma qualquer resposta menor que 2 em 0 (if max_length < 2: return 0) é desnecessária dado o limite do problema (nums.length >= 2) e pode ocultar comportamentos inesperados; melhor é garantir a lógica correta sem esse ajuste.

- severity: info  
  file: solution.py  
  layer: arquitetura  
  description: A solução segue um formato simples (classe Solution com método esperado), o que é adequado; contudo a heurística usada mistura raciocínio de contagem com suposições sobre ordenação — separar claramente o caso "todo mesmo parity" (simples contagem) do caso "alternância" (cálculo por varredura/guloso) tornaria o código mais robusto e legível.

## Resumo
A implementação atual tem complexidade temporal adequada (O(n)), e a estrutura (classe Solution / método esperado) está conforme o contrato. Entretanto, há um defeito lógico crítico: a determinação do comprimento máximo para subsequências com paridades alternadas usa somente as contagens de pares e ímpares, ignorando a ordem dos elementos no array, resultando em respostas incorretas. Além disso, não há testes entregues para validar correções. Devido à falha funcional que impede atingir os critérios de aceite, a entrega está BLOQUEADA até que o algoritmo de alternância seja corrigido (por exemplo, implementando uma varredura gulosa para os padrões (0,1) e (1,0) além das contagens para os casos de mesma paridade) e testes automatizados sejam adicionados.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A lógica para subsequências de paridade alternada é incorreta. O código assume alternating_parity_length = 2 * min(even_count, odd_count), usando apenas as contagens de pares/ímpares e ignorando a ordem dos elementos no array. Isso produz comprimentos impossíveis em muitos casos (ex.: todos os pares vêm antes de todos os ímpares) e falha nos requisitos funcionais — a solução retornará respostas erradas para entradas válidas.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram incluídos arquivos de teste (unit tests) cobrindo casos críticos (happy path, casos com blocos de pares/ímpares agrupados, alternâncias já presentes, pequenas entradas). A ausência de testes automatizados dificulta detectar regressões e verificar a correção da solução.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "warning",
      "description": "A verificação final que transforma qualquer resposta menor que 2 em 0 (if max_length < 2: return 0) é desnecessária dado o limite do problema (nums.length >= 2) e pode ocultar comportamentos inesperados; melhor é garantir a lógica correta sem esse ajuste.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "info",
      "description": "A solução segue um formato simples (classe Solution com método esperado), o que é adequado; contudo a heurística usada mistura raciocínio de contagem com suposições sobre ordenação — separar claramente o caso \"todo mesmo parity\" (simples contagem) do caso \"alternância\" (cálculo por varredura/guloso) tornaria o código mais robusto e legível.",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```