

## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A lógica central está incorreta. O algoritmo mantém uma heap com os K menores valores de B dentre os elementos da prefixo até o índice i e usa essa soma para calcular A_i * sum_B. Isso não garante que o elemento i (cujo A_i é o máximo do subconjunto considerado) esteja incluído na soma de B — para que A_i seja realmente o máximo do subconjunto, a soma deve ser B_i mais os K-1 menores B entre os elementos com A <= A_i (ou seja, entre os primeiros i elementos excluindo i). A implementação atual mantém K menores entre os primeiros i+1 e pode excluir B_i; portanto os produtos avaliados não correspondem necessariamente a subconjuntos válidos e o resultado pode ser incorreto. Em outras palavras: a soma usada para A_i deve forçar a inclusão de B_i (heap de tamanho K-1 sobre prefixo anterior + B_i), mas o código usa heap de tamanho K sobre a prefixo inclusive i. Isso quebra a corretude (casos com K=1 e K>1 são afetados).  
  how_to_fix: usar uma heap (max-heap) de tamanho K-1 que mantenha os K-1 menores B dos elementos anteriores ao índice i; para cada i >= K-1 avaliar candidate = A_i * (B_i + sum_heap). Depois inserir B_i na heap (mantendo tamanho K-1). Especial-case K==1 (simplesmente minimizar A_i * B_i em O(N)).  

- severity: warning  
  file: (workspace)  
  layer: testes  
  description: Não há arquivos de teste automatizados entregues que cubram os cenários críticos (happy path e edge cases). Adicionar testes que verifiquem: K=1, K=N, casos com A repetidos, e casos extremos de valores/tamanhos.  

- severity: info  
  file: solution.py  
  layer: arquitetura  
  description: Há imports redundantes/duplicados na parte superior do arquivo (essa seção é marcada como pré-carregada pela plataforma). Embora não bloqueie a execução, os avisos do linter (redefinição de heapq, import em nível de módulo fora do topo) aparecem na análise estática; pode-se limpar imports duplicados para satisfazer linters.

## Resumo
O arquivo solution.py foi entregue, mas contém uma falha de corretude crítica: a soma de B usada ao avaliar um A_i não garante que o elemento i esteja incluído, portanto muitos candidatos avaliados não correspondem a subconjuntos válidos e o resultado pode ser incorreto. A complexidade (O(N log K)) é adequada, mas a lógica precisa ser ajustada para manter os K-1 menores B dos elementos anteriores e então somar B_i ao avaliar o caso em que A_i é o máximo. Além disso, não foram entregues testes automatizados. Por causa da falha funcional impactante, a entrega fica BLOQUEADA até a correção da lógica.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A lógica central está incorreta. O algoritmo mantém os K menores B na prefixo inclusive o elemento i e usa essa soma para calcular A_i * sum_B, mas para que A_i seja o máximo do subconjunto a soma deve incluir obrigatoriamente B_i (ou seja, deve ser B_i + os K-1 menores B entre os primeiros i elementos). O código atual pode excluir B_i da soma e, portanto, avalia produtos que não correspondem a subconjuntos válidos.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues testes automatizados. Adicionar testes para K=1, K=N, A repetidos e limites de entrada.",
      "file": "(workspace)",
      "layer": "testes"
    },
    {
      "severity": "info",
      "description": "Há imports redundantes/duplicados (seção pré-carregada e re-imports como heapq). Limpar imports melhora a qualidade e remove avisos de linter.",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```