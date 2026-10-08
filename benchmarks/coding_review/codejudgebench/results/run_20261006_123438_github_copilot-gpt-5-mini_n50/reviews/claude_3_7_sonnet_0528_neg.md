## Status: BLOQUEADO

## Issues

- CRITICAL — solution.py — camada: arquitetura/corretude  
  Descrição: O código pré-compila uma tabela binomial completa de tamanho (n+1) x (n+1). Com n até 10^5 (conforme enunciado), isso exige memória/time impossíveis (O(n^2) células), causando estouro de memória ou execução impraticável. Essa falha impede a execução em inputs grandes e bloqueia a entrega.

- WARNING — solution.py — camada: completude  
  Descrição: Não há arquivos de teste entregues no workspace. Não foram incluídos testes unitários cobrindo o exemplo fornecido nem casos de borda (pequenos e grandes n, k limites). Isso impede verificação automatizada local do comportamento e regressões.

- INFO — solution.py — camada: arquitetura  
  Descrição: A lógica de contagem dos subsequentes (soma de C(m, t) para t = 0..min(k-1, m)) está correta e corresponde ao raciocínio esperado. No entanto a implementação da pré-computação dos binomiais é ineficiente; recomenda-se calcular apenas o que é necessário (ex.: usar fatoriais + inversos modulares ou calcular Pascal apenas até k) para reduzir complexidade espacial para O(n) ou O(n*k).

- INFO — solution.py — camada: testes  
  Descrição: Não existem asserts sobre propriedades importantes (por exemplo, comparar saída com exemplos do enunciado) nem testes de desempenho que capturem o comportamento em n grande. Recomenda-se adicionar testes unitários que incluam: exemplos do enunciado, casos com valores repetidos, k = 1, k >= n, e um caso de stress com n grande e k pequeno para verificar tempo/memória.

## Resumo

A solução implementa a lógica correta para contar quantas subsequências têm cada elemento como mínimo ou máximo (a soma de combinações é feita com os índices corretos), e para entradas pequenas produz o resultado esperado. Contudo a implementação pré-computa uma tabela binomial inteira em O(n^2) espaço, o que é impraticável dado n ≤ 10^5 e tornará a solução inutilizável em entradas reais (memory/time blowup). Por isso a entrega está BLOQUEADA até que a pré-computação seja reescrita de forma eficiente (ex.: usar fatorial/inv-fatorial modular, ou construir apenas colunas/linhas necessárias até k) e sejam adicionados testes automatizados cobrindo os casos do enunciado e bordas de desempenho.