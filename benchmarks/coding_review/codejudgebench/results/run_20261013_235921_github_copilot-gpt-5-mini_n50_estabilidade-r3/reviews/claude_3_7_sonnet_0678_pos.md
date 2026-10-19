## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: arquitetura  
  description: Uso recursivo com programação dinâmica por vértice cria DP arrays em cada frame ativo. Em um pior caso permissível pelas restrições (cadeia de vértices com pesos estritamente decrescentes até N=5000 e W até 5000) a pilha recursiva pode ter O(N) frames ativos e cada frame aloca um dp de tamanho O(W), levando a uso de memória peak potencialmente enorme (ordem de dezenas/centenas de MBs ou mais) e provável MLE/segmentation fault na plataforma de avaliação. Esse risco torna a solução não robusta para os limites do problema e pode bloquear a execução/validação automática.

- severity: warning  
  file: solution.py  
  layer: corretude  
  description: Embora a formulação recursiva + memoização calcule corretamente F[v] (1 + max soma válida de F dos vizinhos com peso menor), a implementação ainda pode ser custosa em tempo no pior caso; a complexidade total de atualizações DP pode chegar a O(sum over edges of W_higher), que, embora geralmente aceitável para M ≤ 5000, é marginal. Recomenda-se processamento iterativo/topológico por peso (calcular F em ordem crescente de W) para evitar recursão profunda e reduzir overhead.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram entregues artefatos de teste (testes unitários / casos de borda) que comprovem a correção e desempenho sob casos extremos (cadeia decrescente de pesos, muitos vizinhos com W próximos do limite). A ausência de testes torna a validação automatizada incompleta.

- severity: info  
  file: solution.py  
  layer: testes  
  description: O código executa os cálculos e preenche memo para todos os vértices antes de somar A[i]*F[i], e trata corretamente casos triviais (ex.: W[i] = 1). Seriam úteis casos de teste que verifiquem comportamento em limites (N=5000, M=5000, W variando até 5000) para confirmar ausência de TLE/MLE.

## Resumo
A solução implementa corretamente a recursão memoizada que define F[v] = 1 + max_{S subset of neighbors, sum W < W_v} sum F[y], usando um DP de mochila por vértice e evita recomputações por memoização. Contudo, o desenho recursivo pode acumular muitos DP arrays simultaneamente em profundidade de recursão alta (cadeia de vértices de pesos estritamente decrescentes), o que cria um risco real de estouro de memória (e possivelmente TLE em casos extremos). Em razão desse risco de execução falhar em entradas limites permitidas pelas restrições, a entrega fica bloqueada até que a abordagem seja reestruturada para evitar o pico de uso de memória (por exemplo, computando F iterativamente em ordem crescente de W ou usando técnicas de reutilização/compartilhamento de DP).

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "Uso recursivo com programação dinâmica por vértice cria DP arrays em cada frame ativo. Em um pior caso permissível pelas restrições (cadeia de vértices com pesos estritamente decrescentes até N=5000 e W até 5000) a pilha recursiva pode ter O(N) frames ativos e cada frame aloca um dp de tamanho O(W), levando a uso de memória peak potencialmente enorme (ordem de dezenas/centenas de MBs ou mais) e provável MLE/segmentation fault na plataforma de avaliação. Esse risco torna a solução não robusta para os limites do problema e pode bloquear a execução/validação automática.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Embora a formulação recursiva + memoização calcule corretamente F[v] (1 + max soma válida de F dos vizinhos com peso menor), a implementação ainda pode ser custosa em tempo no pior caso; a complexidade total de atualizações DP pode chegar a O(sum over edges of W_higher), que, embora geralmente aceitável para M ≤ 5000, é marginal. Recomenda-se processamento iterativo/topológico por peso (calcular F em ordem crescente de W) para evitar recursão profunda e reduzir overhead.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues artefatos de teste (testes unitários / casos de borda) que comprovem a correção e desempenho sob casos extremos (cadeia decrescente de pesos, muitos vizinhos com W próximos do limite). A ausência de testes torna a validação automatizada incompleta.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "O código executa os cálculos e preenche memo para todos os vértices antes de somar A[i]*F[i], e trata corretamente casos triviais (ex.: W[i] = 1). Seriam úteis casos de teste que verifiquem comportamento em limites (N=5000, M=5000, W variando até 5000) para confirmar ausência de TLE/MLE.",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```