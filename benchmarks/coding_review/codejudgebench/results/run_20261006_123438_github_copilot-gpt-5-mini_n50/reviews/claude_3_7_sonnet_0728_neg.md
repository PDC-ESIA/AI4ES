## Status: BLOQUEADO

## Issues

Critical
- solution.py / arquitetura
  - O código constrói uma matriz de custos NxN (cost_matrix = [[...]*N]*N). Para N até 1e5 isso é impossível (memória e tempo O(N^2)). Isso torna a solução inviável no domínio dado e bloqueará a execução (MemoryError / TLE). A estratégia algorítmica é inadequada para as restrições do problema.
- solution.py / corretude
  - A implementação do algoritmo de Kuhn–Munkres (função kuhn_munkres) está incorreta e inconsistente: usa índices e arrays (match, visited, u, v, dist, prev) de forma incoerente, faz acessos a u[match[j]] sem garantir match[j] != -1, e o laço principal (j0, visited) não segue a versão correta do algoritmo. É muito provável que gere exceções, produz um casamento inválido (valores -1) ou resultados incorretos.
- solution.py / corretude
  - Mesmo se o matching fosse obtido, a construção/uso do assignment é frágil: assignment pode conter -1 para linhas não atribuídas e a soma final assume que qualquer item cujo assignment != original_box custa W[item]. Com assignment incompleto ou inválido, o cálculo do custo final será incorreto.

Warning
- solution.py / completude
  - Não foram incluídos testes unitários ou casos de teste no repositório para validar soluções, nem há nenhuma verificação automática (scripts). Isso impede detectar regressões ou confirmar correção de bordas localmente.
- solution.py / arquitetura
  - O uso de um algoritmo de emparelhamento geral aqui é desnecessário para a estrutura de custo particular do problema (custos são 0 para a caixa original e W_i para qualquer outra caixa). Isso aumenta complexidade e risco de bugs; existe uma solução linear/greedy muito mais simples e eficiente.

Info
- solution.py / corretude
  - A função kuhn_munkres modifica in-place cost_matrix e não preserva os custos originais para efeito de verificação. Além disso, vários trechos do algoritmo parecem ser adaptações incompletas de pseudocódigo e não foram comentados nem testados.

## Resumo

A implementação fornecida não é aceitável para o problema nas condições dadas. Há uma falha de arquitetura crítica: a criação de uma matriz N×N e o uso de um algoritmo de atribuição geral tornam a solução impraticável para N até 1e5 (memória/time blow-up). Além disso, a implementação do Kuhn–Munkres está incorreta e vai provavelmente provocar erros de execução ou um resultado errado; o cálculo final do custo também assume um matching válido e completo, o que não é garantido. Recomendo rejeitar esta entrega até que a solução seja reescrita usando a abordagem correta e eficiente: agrupar itens por caixa, somar todos os pesos e subtrair, para cada caixa não vazia, o maior peso presente nessa caixa (resultado = sum(W) - sum(max_weight_per_non_empty_box)). Essa solução é O(N) em tempo e O(N) em memória e resolve os critérios de aceite. Além disso, incluir testes cobrindo casos simples, casos com caixas vazias e grandes N.