## Status: BLOQUEADO

## Issues

- critical — solution.py — camada=corretude  
  Descrição: Atualização não-atômica das variáveis de DP (even_ending / odd_ending). O código atual só atualiza a variável correspondente à paridade do elemento atual, deixando a outra com o valor do passo anterior. Isso causa que, na iteração seguinte, um dos "prev_*" represente um estado de dp de i-2 em vez de i-1, permitindo concatenar elementos não contíguos ou formar subarrays com paridades iguais em posições adjacentes. Exemplo simples que demonstra o bug: a = [1 (odd), 2 (even), 4 (even)]. A implementação atual pode produzir even_ending = 5 (1+2+4), que corresponde ao subarray [1,2,4] — inválido porque 2 e 4 têm mesma paridade adjacente. A correção é calcular new_even e new_odd a partir de prev_even e prev_odd e só então atribuir even_ending = new_even; odd_ending = new_odd (ou usar lógica de Kadane alternado que reinicia corretamente), garantindo que ambos os dp representem subarrays que terminam na posição corrente.

- warning — solution.py — camada=completude  
  Descrição: Não há arquivos de teste entregues junto com a implementação. Pelo fluxo de revisão, testes unitários cobrindo casos críticos (happy path e edge cases como sequência curta, todos negativos, sequências com dois elementos de mesma paridade consecutiva, etc.) deveriam ter sido incluídos para validar a correção. Sem testes, a detecção automática de regressões fica comprometida.

- info — solution.py — camada=arquitetura  
  Descrição: Código em estilo script único aceitável para problema de competição. Sugestão de melhoria arquitetural: separar a lógica de computação (função que recebe lista e devolve inteiro) da leitura/IO para facilitar testes unitários.

## Resumo

A solução apresenta um bug crítico na atualização das variáveis de programação dinâmica: as duas variáveis de estado não são atualizadas de forma atômica, permitindo que valores obsoletos sejam usados em iterações subsequentes e gerando subarrays inválidos (ou seja, combinando elementos que violam a restrição de paridade alternada). Esse defeito pode causar respostas incorretas e, por isso, bloqueia a aceitação. Recomenda-se refatorar para calcular new_even e new_odd a partir dos valores "prev" e só depois atribuir os estados, além de adicionar uma bateria de testes que cubra os casos limítrofes e exemplos que demonstram o bug.