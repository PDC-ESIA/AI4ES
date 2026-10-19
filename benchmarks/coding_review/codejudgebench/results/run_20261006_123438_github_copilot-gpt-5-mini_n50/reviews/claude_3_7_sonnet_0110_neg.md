## Status: BLOQUEADO

## Issues

- Critical — corretude — solution.py
  - Descrição: A implementação correta em termos lógicos, mas tem complexidade O(n * k) no caso geral (duas loops aninhadas onde o segundo vai até k), o que não atende às restrições (n, k ≤ 1e5). Isso pode causar Time Limit Exceeded para muitos casos grandes (por exemplo n=1e5, k≈5e4) — a solução só evita a TLE no caso específico k == n-1 graças a um caso especial, mas não elimina a possibilidade de TLE em entradas gerais. A aceitação requer correção que funcione dentro dos limites do problema (CA-01 e CA-02). Recomendação: usar a fórmula combinatória fechada
    ans = C(n-1, k) * m * (m-1)^(n-k-1) (mod 1e9+7)
    e calcular C(n-1,k) com fatoriais précomputados e inversos modulares (O(n) pré-computação + O(1) por consulta), resultando em tempo O(n) e memória O(n) — suficiente para n ≤ 1e5.

- Warning — completude — solution.py
  - Descrição: Não há testes/unit tests entregues no workspace. O bundle de entrega não contém casos de teste automatizados que verifiquem correctness e performance (happy path, edge cases e limites máximos). Recomenda-se incluir testes que cubram: pequenos exemplos (fornecidos no enunciado), casos de borda (n=1, m=1, k=0; k=n-1), e casos grandes para detectar regressões de complexidade (ex.: n=100000, m varying, k large).

- Info — arquitetura — solution.py
  - Descrição: Estrutura simples e legível (método único com SRP claro). No entanto, a escolha de abordagem DP iterativa (estado por número de pares iguais) é subótima quando existe solução combinatória direta. Seria melhor encapsular a lógica combinatória em funções utilitárias (pré-computar factorials, inversos modulares) para separação de responsabilidades e testabilidade.

## Resumo

A solução implementa corretamente a transição DP e trata alguns casos especiais (k == n-1, m == 1, k == 0), mas permanece com complexidade O(n * k) no caso geral e, portanto, pode sofrer Time Limit Exceeded para entradas de grande escala — isto viola os critérios de aceite que exigem eliminação da falha observada e correta execução para todos os limites do problema. Recomendo substituir a DP por uma fórmula combinatória fechada (ans = C(n-1, k) * m * (m-1)^(n-k-1) mod 1e9+7) calculando C(n-1,k) via factorials e inversos modulares para garantir desempenho determinístico O(n). Além disso, incluir um conjunto de testes automáticos que cubra casos de exemplo, borda e limites máximos.