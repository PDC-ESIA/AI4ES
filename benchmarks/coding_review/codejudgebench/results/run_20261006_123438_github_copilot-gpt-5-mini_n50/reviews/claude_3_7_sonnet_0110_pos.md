## Status: APROVADO

## Issues

- [warning] (completude) Arquivos de teste não foram fornecidos — não há testes automatizados no workspace cobrindo os casos (happy path e edge cases). Recomenda-se adicionar um conjunto de testes unitários (ex.: pytest) com exemplos fornecidos e casos limites (n=1, m=1, k=0, k=n-1, valores grandes).
  - Arquivo: (nenhum)
  - Camada: completude

- [info] (arquitetura) Pequena redundância/otimização possível: o caso especial k == n-1 é desnecessário porque a fórmula geral também o cobre. Não afeta corretude, mas pode simplificar o código.
  - Arquivo: solution.py
  - Camada: arquitetura

- [info] (arquitetura) Cálculo da combinação usa inverso modular em cada iteração com pow(..., MOD-2, MOD). Isso é eficiente o suficiente para n ≤ 1e5, mas poderia ser micro-otimizado com pré-cálculo de fatoriais/inversos se desejado.
  - Arquivo: solution.py
  - Camada: arquitetura

## Resumo

A solução apresentada em solution.py está correta e eficiente para os limites do problema: implementa a fórmula combinatória correta C(n-1, k) * m * (m-1)^(n-k-1) com tratamento de casos especiais e cálculos sob módulo primo, evitando o DP que causava TLE. Não foram encontrados bugs de lógica nem problemas de segurança; casos de borda relevantes (n=1, m=1, k=0 ou k=n-1) são tratados corretamente. O único ponto prático a melhorar é a ausência de testes automatizados no repositório; isso deve ser preenchido antes de integrar em um pipeline que dependa de testes.