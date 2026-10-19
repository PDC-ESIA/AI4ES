## Status: BLOQUEADO

## Issues

- critical — corretude — solution.py  
  Descrição: Lógica incorreta ao calcular o comprimento máximo de uma subsequência com paridade alternada. No laço principal o código faz:
  - ao ver um número par: dp_even_new = max(1, dp_odd + 1) e depois dp_even = dp_even_new (sem considerar o valor anterior de dp_even);
  - simetricamente para ímpar.
  Isso pode sobrescrever um dp_even maior por um valor menor (por exemplo quando já existe uma subsequência terminando em par mais longa que dp_odd+1), reduzindo o estado ótimo e produzindo resultados errados. Em outras palavras, a transição deve preservar o melhor comprimento já conhecido terminando com aquela paridade (dp[p] = max(dp[p], dp[1-p] + 1, 1)), mas o código atual perde dp[p] anterior. Essa falha leva a respostas incorretas para muitas entradas (falha em CA-01 e CA-02).

- warning — completude — workspace  
  Descrição: Não foram entregues arquivos de teste/unitários no workspace. Não há testes automatizados que verifiquem os cenários happy path e edge cases (ex.: longas entradas, sequências monotônicas, alternâncias par/ímpar). Adicionar testes ajudaria a detectar regressões como a atual.

- info — arquitetura — solution.py  
  Descrição: Estrutura simples (uma classe Solution com um método) adequada ao requisito. Pequena observação: o código força que respostas de comprimento < 2 sejam zeradas (same_parity_length < 2 → 0; alternating_length < 2 → 0). Confirme se esse comportamento condiz com a especificação (a descrição do problema usa comparações entre pares adjacentes, então faz sentido exigir pelo menos 2 elementos, mas vale confirmar explicitamente).

## Resumo

A solução proposta tem complexidade e intenções corretas (quer considerar dois cenários: todos elementos de mesma paridade e subsequência com paridade alternada) e opera em O(n), o que é adequado para entradas grandes. Entretanto a implementação da dinâmica para subsequências alternadas sobrescreve o estado ótimo ao atualizar dp_even/dp_odd, o que produz respostas incorretas em muitos casos. Por isso a tarefa NÃO pode ser aprovada até que o bug seja corrigido. Recomendo ajustar a atualização para preservar o melhor valor anterior (por exemplo: ao ver um elemento de paridade p fazer dp_p = max(dp_p, dp_{1-p} + 1, 1)) e adicionar um conjunto de testes (casos pequenos e um caso grande para performance) para validar a correção.