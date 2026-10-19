## Status: BLOQUEADO

## Issues

- [critical] (file: solution.py, layer: corretude)
  Descrição: A solução constrói explicitamente uma matriz de custo N x N e tenta aplicar um algoritmo de atribuição (Hungarian). Para N até 10^5 isso é intratável em memória e tempo (O(N^2) memória e pelo menos O(N^3) tempo na abordagem usada). Isso causa Time Limit Exceeded / Out of Memory e torna a solução inviável para os limites do problema.

- [critical] (file: solution.py, layer: corretude)
  Descrição: A implementação do algoritmo de Kuhn–Munkres/Hungarian está incorreta e inconsistente. Exemplos de problemas observados no código:
    - Uso de índices de matched que podem valer -1 sem checagem (ex.: u[match[j]] onde match[j] pode ser -1), levando a atualizações inválidas em u/v ou comportamento enganoso via indexação negativa.
    - Lógica de crescimento/relaxamento do caminho aumentante está incompleta e a ordem dos laços/condições não segue uma versão correta do algoritmo (variáveis j0, j1, prev, dist manipuladas de forma incorreta).
    - A construção final de assignment depende de match que provavelmente não foi preenchido corretamente.
  Consequência: além do problema de performance, o algoritmo pode produzir resultados incorretos ou falhar em tempo de execução.

- [warning] (file: solution.py, layer: arquitetura)
  Descrição: Design excessivamente complexo para o problema: o enunciado admite uma solução linear/greedy simples (calcular soma total de pesos e subtrair a soma dos maiores pesos por caixa) — construir um problema de atribuição geral e implementar Hungarian é desnecessário e propenso a erros. Escolha arquitetural inadequada para restrições e estrutura do problema.

- [warning] (file: solution.py, layer: completude)
  Descrição: Não há arquivos de teste entregues no workspace. Não existem testes unitários ou casos que comprovem correção e desempenho (happy path e casos limite). Falta cobertura automatizada que verifique a correção e que previna regressões.

## Resumo

A entrega contém um único arquivo solution.py, mas a implementação é inviável para os limites do problema e está incorreta. Construir uma matriz de custo N x N e rodar Hungarian levará a Time Limit Exceeded / Out of Memory para N grande; além disso a implementação do algoritmo de atribuição apresenta erros lógicos e uso inseguro de índices que causam resultados errados ou exceções. Arquitetonicamente o problema foi modelado de forma muito mais geral do que o necessário — a solução ótima e eficiente é O(N): para cada caixa escolher o item de maior peso para permanecer, e somar os pesos dos itens que precisam ser movidos (solução: total_weights - sum(max_weight_per_box)). Em razão das falhas críticas de corretude e performance o veredito é BLOQUEADO. Recomendo reimplementar usando a abordagem linear descrita acima e adicionar testes que cubram casos simples, casos com caixas vazias/cheias e limites superiores.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A solução constrói uma matriz de custo N x N e roda Hungarian. Para N até 10^5 isso é intratável (memória e tempo), levando a TLE/OOM.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "critical",
      "description": "Implementação do Kuhn–Munkres/Hungarian incorreta: uso de índices match que podem ser -1 sem checagem, lógica de augmenting path e atualizações de potenciais (u/v) inconsistentes, resultando em atribuições incorretas ou exceções.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Design excessivamente complexo: o problema pode ser resolvido em O(N) (somar todos os pesos e subtrair a soma dos maiores pesos por caixa). A escolha de modelar como assignment aumenta risco e erros.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não há arquivos de teste entregues. Falta suite de testes para verificar correção (casos simples, limites) e desempenho.",
      "file": "solution.py",
      "layer": "completude"
    }
  ]
}
```