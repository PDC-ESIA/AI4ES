## Status: BLOQUEADO

## Issues

- CRITICAL — solution.py / corretude  
  Descrição: A implementação atual é quadraticamente lenta e continuará a falhar por Time Limit Exceeded em entradas grandes (n até 1e5). Para cada candidato outlier o código faz temp = nums.copy(), temp.remove(...), e sum(temp) — cada operação é O(n), fazendo o algoritmo O(n^2). Isto torna a solução inaceitável para os limites do problema e viola o critério CA-02 (eliminar a falha observada).  

- WARNING — solution.py / completude  
  Descrição: Não foram entregues arquivos de teste unitários. O repositório contém apenas solution.py; não há testes que verifiquem casos básicos, casos de borda nem o caso grande que causa TLE. Registre: "Arquivo de testes não foi criado".

- WARNING — solution.py / corretude (robustez)  
  Descrição: A função usa max(potential_outliers) sem verificar se a lista ficou vazia; embora o enunciado garanta ao menos um outlier potencial, essa chamada pode lançar ValueError em entradas fora do contrato. Recomenda-se tratar explicitamente ou documentar a pré-condição.

- INFO — solution.py / arquitetura  
  Descrição: A solução mistura operações de alto custo em laço principal (cópia de lista, remoções por valor, somas completas). Arquiteturalmente, a implementação não usa uma estrutura de contagem/lookup que seria a escolha correta aqui (ex.: collections.Counter ou um dicionário de frequências). A separação de preocupações e a legibilidade podem ser melhoradas adotando uma verificação baseada em frequências e somas pré-computadas.

## Resumo
A solução atual está conceitualmente correta (a lógica de que sum_element = (total - outlier)/2 e a verificação da existência do elemento é a abordagem correta), mas a implementação é ineficiente: copiar a lista, remover elementos e recalcular somas dentro de um laço sobre todos os elementos resulta em O(n^2) e provocará Time Limit Exceeded nas entradas grandes — por isso a entrega fica BLOQUEADA até corrigir o desempenho. Recomenda-se reimplementar usando um map/Counter de frequências e verificações em O(1) por valor (por exemplo, iterar sobre valores únicos ou sobre keys de Counter, verificar paridade de total-outlier e disponibilidade de ocorrências do sum_element ajustando para o caso outlier == sum_element). Além disso, adicione testes automatizados cobrindo happy path e casos de borda (duplicatas, negativos, maiores tamanhos) e trate a situação em que nenhum outlier é encontrado para tornar o código mais robusto.