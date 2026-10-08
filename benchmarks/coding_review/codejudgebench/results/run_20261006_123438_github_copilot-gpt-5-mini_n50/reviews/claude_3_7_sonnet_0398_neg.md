## Status: BLOQUEADO

## Issues

- Severity: critical  
  File: solution.py / Camada: corretude  
  Descrição: A lógica principal não garante que o elemento do índice mediano ficará igual a k. O algoritmo tenta ajustar apenas a contagem de elementos < k, e quando precisa diminuir elementos maiores que k os transforma em valores < k (k-1) em vez de garantir que exista pelo menos um elemento igual a k na posição mediana. Isso produz resultados incorretos em muitos casos. Exemplo de contra-exemplo simples:
  - Entrada: nums = [10, 10, 10], k = 1  
  - Saída do código atual: 10  
  - Saída correta: 18  
  Explicação: para que o mediano (índice mid = 1) seja 1, é necessário que pelo menos dois elementos sejam <= 1 e pelo menos dois sejam >= 1; o custo mínimo é reduzir dois 10s para 1 (9+9=18). O código atual tenta apenas transformar um elemento em < k, resultando em valor incorreto. Conclusão: existe uma falha lógica que leva a respostas erradas — bloqueante.

- Severity: warning  
  File: solution.py / Camada: completude  
  Descrição: Não foram fornecidos testes unitários no workspace. Não há arquivos de teste cobrindo happy path e edge cases (ex.: arrays todos maiores que k, todos menores, mix com muitos equals, tamanhos pares/ímpares). Recomenda-se incluir um conjunto mínimo de testes automatizados para validar correções.

- Severity: info  
  File: solution.py / Camada: arquitetura  
  Descrição: Implementação atual cria listas separadas less/equal/greater e faz ordenações parciais para escolher elementos a ajustar. Embora funcional em alguns casos, a intenção e a construção estão confusas e tornam difícil garantir corretude; uma abordagem mais simples e comprovada é:
    - ordenar nums,
    - usar mid = n // 2,
    - somar deficits para índices i in [mid, n-1] onde nums[i] < k (k - nums[i]),
    - somar excessos para índices i in [0, mid] onde nums[i] > k (nums[i] - k).
  Essa abordagem é mais direta, menos sujeita a erros conceituais e fácil de testar.

## Resumo
A solução entregue contém uma falha conceitual importante: ajustar apenas a contagem de elementos estritamente menores que k e, em alguns casos, transformar elementos maiores que k em valores < k (k-1) não assegura que o elemento do índice mediano será k. Isso produz resultados incorretos (ex.: [10,10,10], k=1). Como há uma issue critical de corretude, a task fica BLOQUEADA até que o algoritmo seja corrigido — recomendo substituir a lógica por uma abordagem direta baseada em array ordenado e iteração sobre os dois lados do índice mediano (incluindo o índice mediano nas verificações), e adicionar testes cobrindo casos pares/ímpares e extremos.