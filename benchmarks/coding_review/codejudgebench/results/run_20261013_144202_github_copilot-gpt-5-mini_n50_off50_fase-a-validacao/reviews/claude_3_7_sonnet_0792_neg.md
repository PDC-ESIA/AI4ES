## Status: BLOQUEADO

## Issues

- CRITICAL — corretude — solution.py  
  Descrição: A contagem das posições da progressão aritmética está incorreta. O código atual conta todas as posições que coincidem com o passo (pos += interval) ao longo do intervalo [0, n-1] mesmo que haja uma lacuna (uma posição esperada que não tenha o mesmo height). Isso permite agregar índices que NÃO formam termos consecutivos de uma progressão aritmética (por exemplo, contar 3,4,6,7 ao usar interval=1), produzindo respostas maiores do que o permitido. Esse erro corresponde exatamente à falha observada no enunciado (saída 4 em vez de 3 para o primeiro exemplo).  
  Impacto: retorna conjuntos inválidos (não-aritméticos) e portanto resultados incorretos para muitas entradas. Bloqueia aceitação.  
  Sugestão de correção: ao iterar pos = start + k*interval, interromper a contagem (break) tão logo encontre uma posição pos que NÃO pertença ao conjunto de índices com aquela altura; só os termos consecutivos (a partir do início escolhido) devem ser contabilizados.

- WARNING — performance / corretude potencial — solution.py  
  Descrição: Mesmo corrigindo o bug acima, a abordagem atual testa todos os pares (i, j) de índices de um mesmo height e percorre a progressão para frente, o que no pior caso (todos os N índices têm a mesma altura) tem custo próximo de O(N^2 log N) em número de passos (estima-se ~N^2 * H_N ≈ N^2 log N), próximo de ~7e7 iterações para N=3000. Em Python puro isso corre risco de Time Limit Exceeded em limites estritos.  
  Impacto: risco de TLE em entradas piores; aceita a correção lógica, mas pode falhar por tempo em plataformas com limites apertados.  
  Sugestão de melhoria: usar uma abordagem O(N^2) determinística, por exemplo:
    - Para cada lista de índices (por altura), resolver o problema do "Longest Arithmetic Subsequence" sobre índices usando um dicionário por posição (dp[j][d] = dp[i].get(d,1) + 1), mantendo apenas diferenças inteiras; isso leva a O(m^2) por grupo e ao total O(N^2) no pior caso, sendo tipicamente aceitável para N=3000 em Python com implementações otimizadas; ou
    - Alternativamente, ao tentar intervalos d, interromper cedo sempre que a previsão máxima remanescente não puder superar o máximo atual (pruning) — mas a solução DP é preferível e mais robusta.

- INFO — completude (testes ausentes) — solution.py  
  Descrição: Não foram entregues arquivos de teste unitários ou casos de borda automatizados no workspace. A ausência de testes automatizados dificulta regressões futuras e validação de performance/limites.  
  Impacto: aumenta o risco de regressão e torna difícil reproduzir localmente falhas de TLE ou de corretude em entradas extremas.  
  Sugestão: adicionar um conjunto de testes incluindo:
    - os exemplos do enunciado;
    - casos pequenos com repetições e lacunas (para verificar o bug descrito);
    - o pior caso: todos os H_i iguais (N=3000) para validação de tempo;
    - casos variados com poucas ocorrências por altura.

## Resumo

O arquivo solution.py está incompleto do ponto de vista de corretude: a lógica que conta quantos edifícios podem ser escolhidos com mesma altura e em intervalos iguais está errada — ela não interrompe a sequência quando encontra a primeira posição faltante, levando a contagens que não correspondem a termos consecutivos de uma progressão aritmética (o que causa o WA citado). Além disso, a abordagem atual tem risco de TLE no pior caso (por exemplo, todos os edifícios com a mesma altura) e não há testes automatizados no workspace. Por essas razões, a entrega deve ser considerada BLOQUEADA até que (1) o bug de contagem seja corrigido (parar ao encontrar a primeira posição faltante) e (2) a implementação seja revisada para garantir complexidade aceitável (preferível solução O(N^2) tipo DP para Longest Arithmetic Subsequence) e acompanhada por testes que cubram os casos críticos.