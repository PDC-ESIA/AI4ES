## Status: BLOQUEADO

## Issues
- critical — solution.py — corretude
  - Descrição: A implementação pré-calcula a tabela completa de binomiais `binom` com dimensão (n+1) x (n+1), usando O(n^2) tempo e memória. Com n até 10^5 (conforme restrição), isso é intratável (OOM / tempo de execução exponencial). Essa falha torna a solução não executável para entradas dentro das restrições do problema e bloqueia a entrega. Recomendações: calcular combinações apenas até k (colunas até k) ou usar pré-cálculo factorial + inversos mod P para obter C(n, r) em O(1) com O(n) memória, ou usar somas de binomiais com prefixos/potências que respeitem O(n·k) tempo e O(k) memória.

- warning — solution.py — arquitetura
  - Descrição: A lógica de contagem das contribuições por elemento (somar C(right_count, t) para t=0..k-1 para mínimos e análogo para máximos) está conceitualmente correta, porém a escolha de implementação (tabela binomial completa) não respeita a restrição prática de k (k ≤ 70). A responsabilidade poderia ser melhor separada: pré-computar apenas os coeficientes necessários (até k) ou expor utilitários de combinação mod que usem factorials/inversos. Isso reduziria acoplamento e memória.

- warning — solution.py — completude
  - Descrição: Não há arquivos de teste/unitários entregues no workspace que validem a correção (happy path e edge cases). Sem testes automatizados não é possível comprovar que a solução corrigida atende CA-01/CA-02 de forma reprodutível.

- info — solution.py — testes
  - Descrição: Os cenários de teste necessários deveriam incluir pelo menos: (1) casos pequenos (ex.: exemplos do enunciado), (2) casos com n grande e k pequeno (para checar performance), e (3) limites (n=1e5 com k=70) para garantir escalabilidade. Esses testes não foram adicionados.

## Resumo
A correção aborda corretamente a fórmula combinatória para contar subsequências onde um elemento é mínimo ou máximo, mas a implementação pré-calcula uma tabela binomial completa de dimensão O(n^2), o que a torna impraticável para os limites do problema (n até 10^5). Isso é um defeito bloqueante (critical) porque a solução não será executável no ambiente alvo. Além disso, não foram entregues testes automatizados que validem a solução. Recomendo reimplementar a pré-computação das combinações limitando-se a k (ou usando factorials + inversos mod) e acrescentar um conjunto de testes (incluindo casos limites) antes de re-submeter.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A implementação pré-calcula a tabela completa de binomiais com dimensão O(n^2), o que causa OOM/timeout para n até 10^5 (restrição do problema). Tornará a solução não executável. Use pré-cálculo limitado a k ou factorials+inversos para C(n,r).",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Implementação correta em conceito, mas a escolha de pré-processamento (tabela binomial completa) é ineficiente. Deve-se limitar a colunas até k ou usar uma estratégia com complexidade e memória adequadas (O(n) ou O(n·k)).",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Nenhum arquivo de teste/unitário foi entregue no workspace para validar a correção (happy path e edge cases).",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "Faltam testes que cubram: exemplos do enunciado, casos com n grande e k pequeno, e limites (n=1e5, k=70) para validar escalabilidade.",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```