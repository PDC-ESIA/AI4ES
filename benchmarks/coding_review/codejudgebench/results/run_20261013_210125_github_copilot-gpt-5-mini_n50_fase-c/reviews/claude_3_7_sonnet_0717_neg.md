## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A implementação atual é O(N * M) no pior caso: para cada pessoa (M) o código varre potencialmente toda a lista de N caixas (o loop interno reinicia sempre no início de boxes). Com N, M ≤ 2·10^5 isso leva a tempo/executável inviável (Time Limit Exceeded) e não atende o critério de aceitação CA-02. Recomenda-se usar uma abordagem O((N+M) log N) — por exemplo: ordenar requisitos em ordem decrescente, ordenar caixas em ordem decrescente e, ao iterar requisitos, ir inserindo em um min-heap as caixas elegíveis (cada caixa é inserida no heap no máximo uma vez) e extrair a menor válida; ou usar uma estrutura de multiset/árvore balanceada para remover o menor elemento >= requisito.

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: Estrutura e escolhas de dados são inadequadas para escala (scan repetido da lista boxes, uso de set para marcar usados sem evitar varreduras completas). Isso aumenta acoplamento entre iteração e estado e resulta em complexidade quadrática. Separe a lógica de seleção eficiente (estruturas apropriadas: heap/multiset/pointer único) da lógica de leitura e soma.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram entregues arquivos de teste automatizados (unit tests / casos de borda). Os critérios de aceite incluem desempenho em entradas grandes; faltar testes que provem correção e performance deve ser registrado.

- severity: info  
  file: solution.py  
  layer: testes  
  description: Nenhum caso de teste está presente no repositório. Recomenda-se adicionar testes unitários que cubram: entradas pequenas (ex.: amostras), casos impossíveis (impraticável), e grandes cenários estressantes para validar performance e memória.

## Resumo
O arquivo solution.py apresenta uma lógica funcional porém com complexidade quadrática que provoca Time Limit Exceeded para entradas de grande porte — isso falha diretamente o critério de aceitação sobre eliminar a falha observada. A correção deve reformular a seleção de caixas para uma abordagem O((N+M) log N) (ex.: sort + heap / multiset) de forma a empurrar cada caixa para uma estrutura auxiliar apenas uma vez. Além disso, faltam testes automatizados que comprovem tanto a correção quanto o desempenho nos limites do problema.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A implementação atual é O(N * M) no pior caso: para cada pessoa (M) o código varre potencialmente toda a lista de N caixas (o loop interno reinicia sempre no início de boxes). Com N, M ≤ 2·10^5 isso leva a tempo/executável inviável (Time Limit Exceeded) e não atende o critério de aceitação CA-02. Recomenda-se usar uma abordagem O((N+M) log N) — por exemplo: ordenar requisitos em ordem decrescente, ordenar caixas em ordem decrescente e, ao iterar requisitos, ir inserindo em um min-heap as caixas elegíveis (cada caixa é inserida no heap no máximo uma vez) e extrair a menor válida; ou usar uma estrutura de multiset/árvore balanceada para remover o menor elemento >= requisito.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Estrutura e escolhas de dados são inadequadas para escala (scan repetido da lista boxes, uso de set para marcar usados sem evitar varreduras completas). Isso aumenta acoplamento entre iteração e estado e resulta em complexidade quadrática. Separe a lógica de seleção eficiente (estruturas apropriadas: heap/multiset/pointer único) da lógica de leitura e soma.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues arquivos de teste automatizados (unit tests / casos de borda). Os critérios de aceite incluem desempenho em entradas grandes; faltar testes que provem correção e performance deve ser registrado.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "Nenhum caso de teste está presente no repositório. Recomenda-se adicionar testes unitários que cubram: entradas pequenas (ex.: amostras), casos impossíveis (impraticável), e grandes cenários estressantes para validar performance e memória.",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```