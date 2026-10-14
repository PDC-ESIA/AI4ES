## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A implementação atual é O(n^2) (dois laços aninhados sobre todos os subarrays). Com n até 1e5 isso levará a Time Limit Exceeded nos casos grandes (já observado na falha reportada). Embora a contagem por subarray esteja logicamente correta para entradas pequenas, a solução não é escalável e falhará nos testes de desempenho. Sugestão de correção: identificar as posições do elemento máximo global e somar, para cada janela de k ocorrências consecutivas, (pos[i] - prev_pos) * (next_pos - pos[i+k-1]) — isso torna a solução O(m) onde m é o número de ocorrências do máximo (ou O(n) no pior caso).

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram entregues testes automatizados (unit tests) cobrindo casos básicos e limites (pequeno, k maior que contagem total, k = 1, todos elementos iguais, entradas grandes). A ausência de testes torna difícil validar regressões e garante que o problema de TLE não seja detectado automaticamente.

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: Código implementado diretamente em dois laços aninhados sem abstração ou helper. Isso combina lógica e iteração de forma que prejudica legibilidade e impede facilmente trocar a estratégia por uma versão linear. Recomenda-se refatorar extraindo a lógica de coleta de posições do máximo e o cálculo de contribuições por janela em funções separadas.

## Resumo
O arquivo solution.py contém uma correção parcial: o código agora conta todas as extensões de um início i que satisfaçam count_max >= k (removendo o break), o que corrige um defeito lógico apontado pelo coder para casos pequenos. No entanto, a abordagem continua sendo uma busca por todos os subarrays (O(n^2)) e, portanto, não atende aos limites de entrada (n até 1e5) — isto causa Time Limit Exceeded nos casos grandes e viola os critérios de aceite. Além disso, não foram incluídos testes automatizados. A entrega precisa ser reescrita para usar a abordagem baseada nas posições do elemento máximo (complexidade linear relativa ao número de ocorrências) e incluir testes.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A implementação é O(n^2) (dois laços aninhados) e vai causar Time Limit Exceeded para entradas grandes; precisa ser substituída por um método que use as posições do máximo e conte janelas de k ocorrências em O(m) tempo.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues testes automatizados (unit tests) cobrindo casos básicos e limites; inclua testes para validar corretude e desempenho.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "warning",
      "description": "Arquitetura: uso de laços aninhados sem abstração torna difícil alterar a estratégia. Recomenda-se refatorar extraindo helpers (coletar posições do máximo, calcular contribuições por janela).",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```