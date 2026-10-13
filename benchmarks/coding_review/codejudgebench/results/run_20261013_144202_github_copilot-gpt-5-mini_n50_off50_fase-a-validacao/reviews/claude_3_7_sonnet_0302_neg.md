## Status: BLOQUEADO

## Issues

- Critical — corretude — solution.py  
  Descrição: A implementação principal está incorreta e produz resultados errados (ex.: o caso informado nums=[1,32,1,2], target=12 retorna 0 em vez de 2). Problemas específicos:
  - A lógica que "quebra" um número maior não trata corretamente a quebra por múltiplos níveis: o código apenas decrementa uma vez freq[j] e adiciona 2 a freq[j-1], e faz operations += 1. Quando o bloco disponível está a j níveis acima de i, o número de operações a somar deveria ser j - i e a propagação de contagens para as posições entre j e i deve ser feita até atingir i. O código atual não cumpre isso.
  - O código tenta reavaliar a mesma posição i fazendo `i -= 1` dentro do for, mas mutar a variável de iteração não impede o for de avançar; portanto a intenção de reprocessar o mesmo bit falha e deixa shortage/contagem em estado inconsistente.
  - A variável `shortage` e sua atualização (`shortage = shortage * 2`) não estão sendo usadas de maneira consistente com a estratégia correta (carregar excesso/necessidade entre bits), levando a decisões incorretas sobre quando e quantas quebras fazer.
  Impacto: impede a corretude do algoritmo em vários casos — bloqueante para aceitação.

- Warning — completude — solution.py  
  Descrição: Não há arquivos de teste (unit tests) no workspace. Os exemplos do enunciado e casos limite (happy path e edge cases) não foram entregues como testes automatizados, o que impede verificação automatizada da correção. (Acceptance CA-01/CA-02 são automatizáveis; falta artefato de teste.)

- Warning — arquitetura — solution.py  
  Descrição: tentativa de alterar o índice de iteração (`i -= 1`) dentro do for sugere confusão sobre controle de fluxo; isso reduz a legibilidade e é um antipadrão porque não afeta o fluxo do for em Python. Também há acoplamento de várias responsabilidades (gerenciar shortage/carry e fazer quebras/propagação) dentro do mesmo laço sem funções auxiliares, o que torna o código frágil e difícil de testar/estender.

- Info — corretude — solution.py  
  Descrição: O mapeamento de valores em freq pressupõe que todo num sempre aparece como uma potência de dois até 2^30 — conforme as restrições isso é válido, porém o código poderia ser mais robusto ao validar/achar o bit (hoje, se um valor inválido fosse passado, o while chegaria a 31 e acessaria fora do range).

## Resumo
O arquivo solution.py foi entregue, mas contém erros funcionais que fazem o algoritmo retornar respostas incorretas (o caso de falha informado não foi corrigido). A principal causa é o tratamento incorreto da operação de "quebrar" um valor em potências menores: o código só quebra um nível por vez, incrementa as operações por 1 mesmo quando o bloco está a vários níveis acima, e tenta (sem efeito) reprocessar o mesmo bit mutando a variável de iteração. Além disso não há testes automatizados. Esses problemas afetam diretamente a corretude do programa, portanto a entrega está BLOQUEADA até que o algoritmo seja corrigido e coberto por testes.

Sugestão curta de correção: implementar a estratégia padrão — para cada bit i, usar o excesso disponível como carry; se houver necessidade e freq[i] insuficiente, localizar o menor j>i com freq[j]>0, então fazer operations += (j - i), decrementar freq[j] e propagar a quebra down até i (por exemplo, para k from j-1 down to i: freq[k] += 1 << (j - 1 - k) ou iterativamente quebrar uma unidade e criar dois na posição imediatamente inferior várias vezes), depois reavaliar a posição i. Adicionar testes com os exemplos do enunciado e casos limítrofes.