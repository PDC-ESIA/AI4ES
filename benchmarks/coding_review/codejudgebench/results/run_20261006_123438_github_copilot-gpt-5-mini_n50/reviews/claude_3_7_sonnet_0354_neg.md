## Status: BLOQUEADO

## Issues

1. Severity: critical  
   File: solution.py — Camada: corretude / performance  
   Descrição: A solução ainda é assintoticamente lenta para os limites do problema. O algoritmo tenta todas as substituições possíveis (len(s) * 25) e, para cada substituição, realiza uma simulação dos cortes (mesmo com memoização). Na pior hipótese isso chega a um comportamento próximo a O(n^2 * 26) em tempo e a um uso de memória muito grande (memo cresce com estados por par (i, mod_idx, new_char)). Para n = 10^4 (limite do enunciado) isso é impraticável e levará a Time Limit Exceeded / consumo excessivo de memória, exatamente o problema que a correção deveria eliminar. Evidência: o código faz "for i in range(len(s)): for char in 'abcdefghijklmnopqrstuvwxyz': calculate_partitions(0, i, char)" — número de tentativas é O(n*26) e cada cálculo percorre partes de s; memoização não amortiza entre diferentes mod_idx/new_char, portanto o custo por modificação não é reduzido de forma suficiente.  

   Impacto: bloqueia a aceitação automática (falha do critério CA-02).  

   Sugestão de correção: reimplementar com abordagem linear ou quase-linear. Exemplos de estratégia viáveis:
   - Pré-computar, em O(n), para cada posição i qual é o índice j = boundary[i] onde termina o maior prefixo que começa em i (do tipo two-pointer com contadores de caracteres; o ponteiro direito só anda para frente). Em seguida calcular dp[i] = 1 + dp[boundary[i]] por iterações decrescentes para obter as partições sem modificação em O(n).
   - Para avaliar o efeito de trocar um único caractere em p por um caractere c, evite recomputar tudo: a troca só afeta j = boundary[l] para j tal que o intervalo [l, j-1] contenha p. Procure limitar a recomputação às j/l cujo intervalo contém p (essa quantidade pode ainda ser O(n) no pior caso, mas em muitas instâncias é muito menor). Combine isso com técnicas de dividir-e-conquistar / atualização local de j e reuso do dp já pré-computado fora da região afetada.
   - Alternativa mais direta: para cada posição de início i, mantenha a janela maximal (usando two-pointer) e guarde boundary[i]; então, para cada p, ao testar uma mudança apenas simular os j's a partir do primeiro i cujo intervalo engloba p, e usar dp já calculado para saltar para o resto (em geral isso limita trabalho). O ponto chave é evitar tentar explicitamente todas as n * 26 simulações completas.
   - Pensar em soluções que limitam letras candidatas para mudança (por exemplo, testar somente letras que aparecem em torno de p ou que são de fato capazes de aumentar o número de cortes) pode reduzir a constante, mas não substitui a necessidade de uma estratégia assintoticamente mais eficiente.

2. Severity: warning  
   File: solution.py — Camada: completude  
   Descrição: Não foram entregues artefatos de teste (nenhum arquivo de testes unitários). O DoD implicito inclui corrigir a solução e garantir que o TLE observado na versão anterior foi resolvido — sem testes automatizados fica difícil validar regressões locais e medir cobertura do caso limite que causou TLE.  
   Sugestão: adicionar um conjunto de testes que inclua:
   - Casos pequenos (validação básica).
   - Casos extremos (n próximo a 10^4) com padrões que forçam muitos cortes (p.ex. alternância que provoque muitos cortes para k=1) e casos que provocaram TLE na submissão anterior.
   - Random tests com seed fixa para reproduzibilidade.

3. Severity: info / arquitetura  
   File: solution.py — Camada: arquitetura  
   Descrição: O uso de memoização com a chave (i, mod_idx, new_char) cria pouco reaproveitamento entre diferentes tentativas de modificação (mod_idx/new_char distintos). A responsabilidade do método calculate_partitions mistura a lógica de computar limites de prefixo (sliding-window) com o controle de modificação, o que torna difícil aplicar otimizações globais. Também há iteração ingênua sobre todas as 26 letras para cada posição, sem heurística de poda.  
   Sugestão: desacoplar o cálculo das boundaries (boundary[i]) e o DP de partições do mecanismo que testa uma modificação; isso permite reuso e atualizações locais mais fáceis. Documentar claramente invariantes (por exemplo: boundary[i] = menor j tal que s[i..j-1] tem <= k letras e s[i..j] tem > k letras) e garantir implementação two-pointer para boundary em O(n).

4. Severity: info / testes  
   File: solution.py — Camada: testes  
   Descrição: Além de não existir um arquivo de testes, a função não tem comentários explicativos nem exemplos embutidos (doctests) que facilitem validação rápida.  
   Sugestão: incluir alguns doctests ou um pequeno bloco "if __name__ == '__main__':" com casos representativos para facilitar checagem manual local.

## Resumo

A implementação atual simula corretamente a sequência de partições e trata corretamente a possibilidade de alterar um caractere, mas não resolve o problema de desempenho que motivou a correção: testar todas as substituições e recalcular (mesmo com memoização) leva a custo alto e uso de memória potencialmente impraticável para n = 10^4. Por isso a entrega deve ser considerada bloqueada até que a estratégia seja reescrita para um algoritmo linear ou quase-linear (por exemplo: two-pointer para calcular boundary[i] em O(n) + dp, combinado com uma forma de avaliar uma única alteração com custo sublinear ou com recomputação local limitada). Também recomendo adicionar testes automatizados que incluam os casos extremos que causaram TLE na versão anterior.