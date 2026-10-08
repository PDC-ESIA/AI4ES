## Status: BLOQUEADO

## Issues

- Severidade: critical  
  Arquivo: solution.py — Camada: corretude  
  Descrição: A implementação atual computa o comprimento máximo de uma subsequência com paridade alternada apenas como 2 * min(even_count, odd_count), ignorando a ordem dos elementos no vetor original. Isso gera respostas incorretas (falha em CA-01 / CA-02). Exemplo simples que demonstra o erro: nums = [1,1,1,2,2,2] (odd_count = 3, even_count = 3). O código atual retorna alternating_parity_length = 6, mas, respeitando a ordem original, o maior subsequência alternada tem comprimento 2 (por exemplo [1,2]). A suposição de que se pode sempre intercalar todos os valores baseando-se apenas nas contagens é falsa. Recomenda-se substituir essa aproximação por um algoritmo O(n) que respeite a ordem (ver sugestão de correção abaixo).

- Severidade: warning  
  Arquivo: solution.py — Camada: completude  
  Descrição: Não foram entregues testes automatizados (unit tests) cobrindo cenários críticos (happy path, casos com agrupamentos por paridade extremos, alternâncias já ordenadas e alternâncias agrupadas). A ausência de testes dificulta a detecção de regressões e validação automática da correção (critério CA-01 é automatizável).

- Severidade: info  
  Arquivo: solution.py — Camada: arquitetura  
  Descrição: A solução tem boa complexidade temporal (atual O(n) por contagem), mas contém uma suposição algorítmica incorreta. A separação de responsabilidades está simples e adequada (uma única função que resolve o problema), porém seria melhor encapsular a lógica de “maior subsequência alternada respeitando a ordem” em uma função pequena para legibilidade e testes.

## Resumo

O arquivo solution.py foi entregue e compila/executa, mas contém um defeito lógico crítico: a determinação do comprimento máximo de uma subsequência com soma adjacente de paridade ímpar foi reduzida a 2 * min(even_count, odd_count), o que ignora a ordem dos elementos e produz resultados incorretos em muitos casos. Essa falha viola os critérios de aceite (CA-01 e CA-02) e bloqueia a entrega. Além disso, não há testes automatizados para validar cenários-chave. Recomenda-se implementar um algoritmo linear que calcule a maior subsequência alternada respeitando a ordem — por exemplo, varrendo nums e mantendo dois contadores dp_even e dp_odd: para cada num, se paridade p == 0 faça dp_even = max(dp_even, dp_odd + 1) else dp_odd = max(dp_odd, dp_even + 1); ao final alternating_length = max(dp_even, dp_odd). Então retornar max(max(even_count, odd_count), alternating_length) (e, se desejado, forçar 0 quando o resultado < 2 conforme a interpretação do enunciado). Após essa correção, adicionar testes unitários cobrindo casos como blocos agrupados por paridade e alternâncias perfeitas.