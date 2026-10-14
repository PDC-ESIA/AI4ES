## Status: BLOQUEADO

## Issues
- critical — file: solution.py — layer: corretude  
  Descrição: Algoritmo atual ainda usa DP O(n*k) no caso geral; isso é intratável para limites n, k ~ 10^5 e fará Time Limit Exceeded em entradas grandes (por exemplo k ~ n/2 ou outros k grandes). Apesar de tratar os casos k == n-1 e k == 0, a solução geral permanece com complexidade quadrática/produção de iterações em massa e não satisfaz o requisito de desempenho. Recomenda-se substituir pelo resultado combinatório fechado answer = C(n-1, k) * m * (m-1)^(n-k-1) (com fatorial e inversos modulares pré-computados) para execução em tempo O(n) de pré-processamento e O(1) por consulta.

- warning — file: solution.py — layer: completude  
  Descrição: Não foram adicionados arquivos de teste ou casos de unidade (nenhum arquivo de testes no workspace). A entrega contém apenas a implementação — falta cobertura automática que comprove correção e desempenho nas bordas.

- warning — file: solution.py — layer: testes  
  Descrição: Não existem testes automatizados. Sem testes que cubram: (i) casos limites (n grande, k grande), (ii) casos triviais (n=1, m=1, k=0), não há verificação automática de regressões de performance/correção.

- info — file: solution.py — layer: arquitetura  
  Descrição: A lógica é concisa e a recursão/DP usada é correta do ponto de vista combinatório, porém a escolha arquitetural (DP iterativo sobre j até k para cada i) não é apropriada para os limites do problema. Recomenda-se adotar a fórmula combinatória (ver issue critical) — isso simplifica o código e reduz significativamente a complexidade.

## Resumo
A solução em solution.py está funcional e a recursão/recorrência implementada está correta do ponto de vista combinatório, e trata corretamente alguns casos especiais (k==n-1, k==0, m==1). Contudo a implementação geral permanece com complexidade O(n*k) e assim não cumpre os limites de desempenho para os maiores casos válidos; isso é um problema bloqueante (critical) porque viola os critérios de aceite que exigem soluções práticas para os limites do enunciado. Além disso, não há testes automatizados entregues. Para consertar definitivamente, implemente a solução combinatória fechada answer = C(n-1, k) * m * (m-1)^(n-k-1) usando pré-cálculo de fatoriais e inversos modulares (fatorial e inv_fatorial até n-1), o que dá tempo e memória adequados; adicione testes cobrindo casos limites e casos triviais.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "Algoritmo atual ainda usa DP O(n*k) no caso geral; isso é intratável para limites n, k ~ 10^5 e fará Time Limit Exceeded em entradas grandes (por exemplo k ~ n/2 ou outros k grandes). Apesar de tratar os casos k == n-1 e k == 0, a solução geral permanece com complexidade quadrática/produção de iterações em massa e não satisfaz o requisito de desempenho. Recomenda-se substituir pelo resultado combinatório fechado answer = C(n-1, k) * m * (m-1)^(n-k-1) (com fatorial e inversos modulares pré-computados) para execução em tempo O(n) de pré-processamento e O(1) por consulta.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram adicionados arquivos de teste ou casos de unidade (nenhum arquivo de testes no workspace). A entrega contém apenas a implementação — falta cobertura automática que comprove correção e desempenho nas bordas.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "warning",
      "description": "Não existem testes automatizados. Sem testes que cubram: (i) casos limites (n grande, k grande), (ii) casos triviais (n=1, m=1, k=0), não há verificação automática de regressões de performance/correção.",
      "file": "solution.py",
      "layer": "testes"
    },
    {
      "severity": "info",
      "description": "A lógica é concisa e a recursão/DP usada é correta do ponto de vista combinatório, porém a escolha arquitetural (DP iterativo sobre j até k para cada i) não é apropriada para os limites do problema. Recomenda-se adotar a fórmula combinatória (ver issue critical) — isso simplifica o código e reduz significativamente a complexidade.",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```