## Status: BLOQUEADO

## Issues

- Severity: critical
  - File: solution.py
  - Camada: corretude
  - Descrição: Decisões numéricas incorretas ao avaliar se um prefixo (ou tentativa de colocar '1' em um '?') mantém a possibilidade de obter um número ≤ N. O código compara int(prefix, 2) com N em vez de comparar o valor mínimo possível ao completar o restante dos bits (i.e., prefix + escolhido_bit + para j>i: usar S[j] se for '0'/'1' ou '0' se for '?'). Do modo atual:
    - As verificações usam apenas o valor do prefixo parcial (int(result, 2)), que ignora os bits fixos futuros e o efeito do deslocamento (<<) quando o prefixo for interpretado como parte de um número de comprimento maior.
    - O laço de retrocesso (backtracking) também verifica int(result, 2) > N, ou seja, não está comparando contra o menor valor possível obtido ao completar os bits restantes com os valores fixos/padrão — isso torna a lógica propensa a decisões erradas ou a retrocessos insuficientes.
  - Impacto / exemplo de problema conceitual: a decisão correta para aceitar um '1' em uma posição '?' deve ser: "se eu escolher '1' aqui e preencher todos os '?' restantes com '0' (e manter os bits fixos), o número resultante é ≤ N?" — o código não implementa essa verificação. Mesmo que a implementação atual consiga resolver alguns casos graças ao backtracking simples, essa verificação incompleta deixa o algoritmo fragilmente incorreto para entradas arbitrárias (aceitação/repúdio de '1' feita com base em comparações incorretas).
  - Correção sugerida: ao avaliar uma escolha para a posição i, construir explicitamente a string candidata mínima:
      candidate = prefix_so_far + chosen_bit + ''.join(S[j] if S[j] in '01' else '0' for j in range(i+1, L))
    e comparar int(candidate, 2) <= N. Usar a mesma abordagem para decidir se o prefixo fixo já torna impossível continuar (retornar -1) e ao conduzir o backtracking.

- Severity: warning
  - File: solution.py
  - Camada: completude
  - Descrição: Não há testes automáticos entregues. O repositório contém apenas solution.py. Dado que a correção visa eliminar um caso de falha observado, é recomendável incluir testes unitários (casos limite e exemplos públicos, inclusive o caso informado no enunciado) para validar regressões.
  - Impacto: sem testes é difícil garantir que a correção cubra todos os cenários e que a regressão original foi realmente solucionada.

- Severity: info
  - File: solution.py
  - Camada: arquitetura
  - Descrição: O código manipula a string `result` e faz slicing repetido para retroceder, o que é aceitável com o limite de 60 bits (complexidade pequena), mas poderia ficar mais claro e menos propenso a erros se `result` fosse um list de caracteres (mutável) e as posições armazenadas em pos_of_ones fossem inteiros que representam índices imutáveis desde o início (ou ainda, trabalhar com inteiros e operações bitwise para evitar conversões frequentes com int(str, 2)). Não é uma falha funcional, apenas uma sugestão de clareza/eficiência.
  - Sugestão: usar uma lista de chars e construir candidatas com compreensão que leva em conta bits fixos futuros.

- Severity: warning
  - File: solution.py
  - Camada: testes
  - Descrição: Falta cobertura clara de casos de borda: comprimento máximo (60), N muito grande (até 1e18), S composta apenas por '1' e nenhum '?', e cenários em que os bits fixos futuros forçam impossibilidade logo no começo. Incluir esses casos como testes automatizados é recomendado.

## Resumo

A solução entregue apresenta um erro conceitual na forma como decide se uma escolha (colocar '1' em um '?', ou aceitar um bit fixo) mantém a possibilidade de obter um número ≤ N: as comparações são feitas usando apenas o prefixo parcial (int(result, 2)) e não com o menor número possível ao completar o restante dos bits respeitando os bits fixos. Isso torna a decisão incorreta/fragilmente correta em geral. Além disso, não foram entregues testes automatizados para validar a correção (incluindo o caso de falha observada). Por essas razões, a entrega está BLOQUEADA até que as comparações sejam corrigidas para construir e comparar o candidato mínimo (prefix + escolhido_bit + preencher '?' remanescentes com '0', respeitando bits fixos) e até que casos de teste relevantes sejam adicionados.