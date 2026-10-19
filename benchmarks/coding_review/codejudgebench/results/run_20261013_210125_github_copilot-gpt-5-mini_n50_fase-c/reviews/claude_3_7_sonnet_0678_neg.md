## Status: BLOQUEADO

## Issues

- critical | file: solution.py | layer: corretude
  - Descrição: O algoritmo de iteração para fixpoint usa um limite fixo muito baixo (`for _ in range(100):`). A convergência do vetor F não é garantida em 100 iterações: as dependências são direcionadas de vértices com peso menor para maior, e no pior caso a “cadeia” de propagação pode ter comprimento O(N), logo pode ser necessário muito mais que 100 iterações (N ≤ 5000). Se o laço terminar por esgotamento do contador sem atingir estabilidade, o resultado impresso será incorreto. Isto viola o critério CA-01 (saída correta para toda entrada válida).

- warning | file: solution.py | layer: arquitetura
  - Descrição: Complexidade de tempo e estratégia de iteração — a implementação atual faz uma DP tipo knapsack por vértice e ainda tenta convergir por iterações sucessivas. Isso cria risco de TLE para instâncias grandes (W_i até 5000, N e M até 5000). A abordagem determinística e mais eficiente é ordenar os vértices por W ascendente e computar F[i] em uma única passagem (já que dependências só vão de pesos menores para maiores), evitando iterações repetidas.

- warning | file: solution.py | layer: completude
  - Descrição: Não há arquivos de teste (unit/integration tests) entregues junto com a implementação. Ausência de testes automatizados impede verificação local de correção e regressão (issue de completude, CA-02).

- info | file: solution.py | layer: arquitetura
  - Descrição: O arquivo contém muitos imports no topo vindos do “ambiente pré-carregado”, o que gerou um aviso de linter (ruff/E402: module level import not at top of file). Isso não impede execução, mas polui o cabeçalho e pode mascarar imports necessários/indesejados.

## Resumo

A solução codifica corretamente a ideia central (usar um knapsack por vértice considerando apenas vizinhos com W_j < W_i e somar A_i * F_i), e trata casos simples/limítrofes (p.ex. W[i] == 1). No entanto a estratégia de convergência baseada em um número fixo de iterações (100) é insegura: pode não convergir para instâncias com cadeias longas de dependência, produzindo respostas erradas — isto é um defeito bloqueante para aceitação automática. Além disso há risco de TLE pela combinação de DP por vértice e iterações repetidas; recomenda-se calcular F em uma única passagem ordenada por W para garantir correção e desempenho. Finalmente, não foram fornecidos testes automatizados.

Recomendações práticas de correção:
- Calcular F de forma determinística: ordenar vértices por W ascendente e, para cada vértice, executar a knapsack usando os F já computados (uma única passagem, sem iterações globais).
- Remover o limite arbitrário de iterações; se mantiver iteração, usar condição de parada baseada em estabilidade sem limite artificial, ou provar um limite seguro.
- Adicionar um conjunto de testes que cubra: grafos em cadeia longo (cadeia de W estritamente crescente), casos com W_i = 1, grafos densos/esparsos e limites superiores (N, M, W máximos).

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "O algoritmo usa um limite fixo de iterações (`for _ in range(100):`) para atingir o ponto fixo. A convergência não é garantida em 100 iterações e, em casos com cadeias longas de dependência, isso produzirá resultado incorreto.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Risco de TLE: a implementação executa um knapsack por vértice e ainda repete isso em iterações sucessivas. A complexidade combinada pode exceder os limites; é preferível ordenar vértices por W e computar F em uma única passagem.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não foram fornecidos testes automatizados (unit/integration) junto com a implementação — impossibilita verificação local e regressões.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "Muitos imports no topo (pré-carregados) geraram aviso de linter (module level import not at top of file). Não bloqueante, mas polui o cabeçalho.",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```