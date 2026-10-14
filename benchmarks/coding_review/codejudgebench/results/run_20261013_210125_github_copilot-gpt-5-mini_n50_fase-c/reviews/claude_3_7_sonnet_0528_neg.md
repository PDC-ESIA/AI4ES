## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: arquitetura  
  description: A solução aloca e preenche uma tabela binomial de tamanho (n+1) x (n+1) (triangular), o que causa custo O(n^2) em tempo e memória. Com as restrições do problema (n até 10^5) isso é inviável na prática — resultará em estouro de memória ou timeout. A abordagem torna o programa não executável para entradas grandes e, portanto, bloqueia a entrega.

- severity: warning  
  file: solution.py  
  layer: testes  
  description: Não foram incluídos arquivos de teste/unitários no workspace. Não há casos automatizados que comprovem a correção sobre os limites e casos de borda (p.ex. n grande, k = 1, k >= n, elementos iguais). Recomenda-se adicionar testes que cobrem happy path e limites.

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: A implementação calcula toda a tabela binomial quando apenas valores com j <= k-1 são necessários. Como k <= min(70, n), a memória e o tempo podem ser drasticamente reduzidos limitando a tabela às primeiras (k) colunas ou usando pré-cálculo com factorial/inversos modular ou potência de 2/combinações acumuladas. Isso é uma oportunidade clara de otimização.

## Resumo
O código implementa a lógica correta para contar contribuições de cada elemento como mínimo e máximo em subsequências (a formulação combinatória está conceptualmente correta para instâncias pequenas), mas a implementação atual constrói uma tabela binomial completa O(n^2) que torna a solução impraticável para os limites do problema (n até 10^5). Por esse motivo há um problema crítico de arquitetura/escala que bloqueia a entrega. Além disso, não há testes automatizados no workspace; recomenda-se adicionar testes e otimizar o cálculo combinatorial (ex.: usar pré-cálculo factorial + inverso modular, pré-computar apenas até k colunas, ou utilizar somas acumuladas de binomiais) para resolver a questão de desempenho e permitir aprovação.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A solução aloca e preenche uma tabela binomial de tamanho (n+1) x (n+1), causando custo O(n^2) em tempo e memória. Com n até 10^5 isso é inviável (estouro de memória/timeout), tornando o programa não executável para entradas grandes.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não foram incluídos arquivos de teste/unitários no workspace. Não há casos automatizados que comprovem a correção sobre os limites e casos de borda (p.ex. n grande, k = 1, k >= n, elementos iguais).",
      "file": "solution.py",
      "layer": "testes"
    },
    {
      "severity": "warning",
      "description": "A implementação calcula toda a tabela binomial quando apenas valores com j <= k-1 são necessários. Como k <= min(70, n), a memória e o tempo podem ser reduzidos limitando a tabela às primeiras k colunas ou usando factorials/inversos modulares.",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```