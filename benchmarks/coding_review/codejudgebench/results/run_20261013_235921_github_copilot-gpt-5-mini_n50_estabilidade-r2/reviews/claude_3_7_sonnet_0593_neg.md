## Status: BLOQUEADO

## Issues
- Severity: critical  
  File: solution.py  
  Layer: corretude  
  Description: A implementação atual faz, a cada evento, um loop for person in range(1, N+1) e testa membership em out_of_row para achar o primeiro presente. Isso gera complexidade O(N * M) no pior caso e causa Time Limit Exceeded para os limites do problema (N, M até 2e5). Como consequência, o programa não entrega resposta em tempo para entradas grandes e falha nos critérios automáticos (CA-01, CA-02). É necessário substituir a varredura linear por uma estrutura que retorne o primeiro elemento presente em O(log N) ou amortizado O(1) por operação (ex.: conjunto ordenado / balanced BST, Fenwick + busca binária para predecessor/sucessor, ou outra técnica de conjunto ordenado); atualmente o código é inviável para os limites do enunciado.

- Severity: warning  
  File: solution.py  
  Layer: arquitetura  
  Description: O design mistura uma heap para retornos (correto) com uma varredura linear para localizar o front_person, evidenciando falta de coesão entre estruturas de dados. Recomenda-se manter uma única representação eficiente do estado da fila (por exemplo, um conjunto ordenado de índices presentes, implementado via Fenwick Tree + busca binária, ou uma árvore balanceada) em vez de combinação heap + varredura completa.

- Severity: warning  
  File: solution.py  
  Layer: completude  
  Description: Não há arquivos de teste no workspace associados à solução (nenhum unit test / caso de integração). Ausência de testes automatizados dificulta validação e regressão. Adicionar testes que incluam os samples do enunciado e casos limites (todos fora/um só presente/retornos simultâneos) é recomendado.

- Severity: info  
  File: solution.py  
  Layer: arquitetura  
  Description: O arquivo contém imports redundantes/duplicados (muitos imports no topo do arquivo devido ao ambiente pré-carregado e novo import de heapq). Há também avisos estáticos (ruff) sobre import fora do topo e redefinição; isso não impede execução, mas reduz clareza e deve ser limpo.

## Resumo
O código funciona corretamente em instâncias pequenas, mas sua estratégia para localizar a pessoa à frente da fila é ineficiente (varredura linear por evento) e resulta em Time Limit Exceeded para entradas nos limites do enunciado. Isso viola os critérios automáticos (saída correta para toda entrada válida e eliminação da falha observada). A entrega está bloqueada até que a busca do front_person seja substituída por uma estrutura com complexidade por operação adequada (por exemplo, Fenwick Tree + busca binária para localizar o próximo índice presente, ou outra implementação de conjunto ordenado). Também é recomendável adicionar testes automatizados e limpar imports redundantes.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A implementação usa, a cada evento, um loop for de 1..N para achar o primeiro presente, resultando em O(N*M) e causando Time Limit Exceeded para N,M até 2e5. Substituir por estrutura que obtenha o primeiro presente em O(log N) ou melhor.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Design misto: heap para retornos + varredura linear para front_person. Recomenda-se manter representação única e eficiente (conjunto ordenado / Fenwick + busca binária / árvore balanceada).",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não há arquivos de teste fornecidos no workspace. Adicionar testes (samples e casos limites) para validação automática.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "Imports redundantes/duplicados e avisos estáticos (ruff) sobre import fora do topo e redefinição de heapq. Limpar imports para melhor legibilidade.",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```