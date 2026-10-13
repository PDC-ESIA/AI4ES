## Status: BLOQUEADO

## Issues

### [critical] solution.py / corretude
- **DP State incorrectly models assignment constraints:**  
  O algoritmo tenta resolver via programação dinâmica usando uma matriz bidimensional `dp[used_op1][used_op2]` para armazenar o menor somatório, considerando quantas operações de cada tipo já foram usadas. No entanto, a construção dos estados DP e transições NÃO garantem que:
    - Cada operação (op1/op2) seja aplicada ao máximo a UM índice (limite: "not more than once per index").
    - Não há dupla contagem — a DP permite aplicar, por exemplo, 2x `op1` no mesmo índice (pois a definição dos estados e das operações no array `operations` não assegura exclusão mútua).
    - O modelo de DP está apropriado para problemas do tipo "escolher k dos n itens", mas aqui cada índice só pode receber ambas ou nenhuma, e cada operação total (op1, op2) tem limite global, mas também só pode ocorrer uma vez por índice.
    - O algoritmo está mais próximo de um problema de "Multiple-choice Knapsack", mas trata os estados por total usado, permitindo sobreposição e múltiplos picks por índice.

  **Concretamente:**  
  Na prática, o laço que varre todas as combinações (index, op1/op2 aplicadas, valor resultante) considera multiplas escolhas para o mesmo índice, corrompendo a contagem ("Aplicar Op1+Op2 e vários outros casos"), pois não há registro de para quais índices as operações já foram aplicadas num determinado estado DP.

- **Otimização incorreta e não polinomial:**  
  Como cada iteração de operação não “marca” o índice como usado, há situações em que, ao combinar operações, o índice pode ser escolhido múltiplas vezes – explorando decisões inconsistentes. Isso leva a somatórios inválidos e, em geral, o algoritmo não é correto para o problema proposto.

- **Não elimina a falha observada** (CA-02):  
  Ao rodar no exemplo `[2,4,3], 3, 2, 1`, o método retorna respostas incorretas (ao fazer manualmente ou por amostragem do raciocínio DP proposto).

### [info] solution.py / arquitetura
- Há código redundante (calcula todas as combinações possíveis para cada índice sem guiar/limitar transições de estado). O modelo DP deveria ser, para um conjunto de índices, marcar se para cada índice foram aplicadas ou não quais operações, e não por quantia global usada.

### [info] solution.py / completude
- Não existem testes no workspace. Apesar de não obrigatório para o contexto LeetCode/classe solution, seria boa prática incluir cenários minimalistas.

### [info] solution.py / corretude
- A linha `# Best value after both operations\n after_both = min(op1_then_op2, op2_then_op1)` está correta no cálculo, mas o uso subsequente não mitiga problema principal do DP.

### [warning] ruff/F841
- Há variáveis declaradas e não usadas em outras versões do código (não é blocking, mas sugere revisão superficial/confusão na lógica).

## Resumo

O código tenta resolver o problema usando programação dinâmica, mas falha em modelar corretamente a restrição de que cada operação pode ser aplicada no máximo uma vez por índice: diferentes estados DP permitem sobreposição de operações para o mesmo índice, violando a definição do problema e podendo causar respostas erradas — o que, de fato, ocorre no caso de teste do enunciado. O erro de lógica bloqueia o uso do código, pois não atende ao critério de corretude nem elimina a falha apresentada. Não há testes unitários, e a arquitetura DP é inadequada para a restrição do problema. Recomenda-se reescrever o núcleo da solução, modelando explicitamente as decisões “por índice” e garantindo que a combinação de operações respeite os limites individuais e globais.