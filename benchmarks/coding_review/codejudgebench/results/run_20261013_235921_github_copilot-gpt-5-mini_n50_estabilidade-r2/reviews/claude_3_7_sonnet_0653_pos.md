## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A solução usa recursion DFS (operations_to_delete_node) sem garantir limite de recursão suficiente para N up to 3×10^5. O ambiente pré-carregado define sys.setrecursionlimit(50000), que é menor que o N máximo; com uma árvore em cadeia (depth ≈ N) o código levantará RecursionError e falhará em instâncias válidas de entrada.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram entregues arquivos de teste automatizados (unit tests / casos de borda). Falta cobertura de testes que verifiquem cenários críticos como cadeia longa (profundidade máxima), estrela, e casos pequenos — especialmente o caso que provoca RecursionError.

- severity: info  
  file: solution.py  
  layer: arquitetura  
  description: A função principal e a lógica estão concentradas no mesmo script (CLI), o que é aceitável para competição/CLI, porém para manutenção seria preferível separar a lógica (funções puras) e entrada/saída. Também há redundância de checagens triviais (por exemplo, n == 1 é irrelevante dado o enunciado que N>=2), sem impacto funcional.

## Resumo
A correção implementada resolve o erro lógico presente na versão anterior (tratamento especial apenas para o nó 1 em vez de em todos os nós), e a ideia algorítmica principal (somar custos das subárvores, mantendo uma subárvore para o fim apenas no nó 1) está correta e tem complexidade O(N). Contudo há um problema crítico: a solução usa recursão profunda e depende do limite de recursão do processo. O ambiente já ajustou recursionlimit para 50000, que é insuficiente para N máximo = 3×10^5; por isso o código irá falhar (RecursionError) em entradas pior caso (cadeia longa). Até que esse problema seja corrigido — substituindo recursão por versão iterativa (pilha) ou explicitamente ajustando recursionlimit para > N (p.ex. sys.setrecursionlimit(10**6)) — a entrega fica bloqueada. Além disso, falta suíte de testes automatizados cobrindo cenários críticos.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A solução usa recursion DFS sem garantir limite de recursão suficiente para N up to 3×10^5. O ambiente pré-carregado define sys.setrecursionlimit(50000), que é menor que o N máximo; com uma árvore em cadeia (depth ≈ N) o código levantará RecursionError e falhará em instâncias válidas de entrada.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues arquivos de teste automatizados (unit tests / casos de borda). Falta cobertura de testes que verifiquem cenários críticos como cadeia longa (profundidade máxima), estrela, e casos pequenos — especialmente o caso que provoca RecursionError.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "A função principal e a lógica estão concentradas no mesmo script (CLI); para manutenção seria preferível separar lógica e I/O. Há também checagens triviais (p.ex. n == 1) sem impacto funcional.",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```