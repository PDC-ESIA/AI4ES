## Status: BLOQUEADO

## Issues

- Severity: critical  
  File: solution.py — Camada: arquitetura / corretude  
  Descrição: A solução aloca duas matrizes 2D em Python com tamanho H×W (grid e dp). No pior caso H = W = 3000 isso cria 9.000.000 células por matriz. Em Python cada inteiro tem overhead grande, portanto duas matrizes desse tamanho muito provavelmente excedem os limites de memória da plataforma (estimativa: centenas de MB por matriz, total >> limites típicos), resultando em erro em entradas válidas — ou falha de execução / MLE. Isto torna a solução não aceitável para "toda entrada válida" (critério CA-01). Recomendações de correção:
  - Evitar alocar a matriz dp completa. Use apenas duas linhas (prev, curr) de comprimento W e atualize por linhas — complexidade de tempo continua O(H·W) mas a memória cai para O(W).
  - Para marcar furos, em vez de uma matriz 2D também prefira um set de tuplas {(a,b)} ou uma estrutura por linha (por exemplo, um dict/list de sets por linha), ou use uma lista de bytearray por linha (mais compacta) para checagem constante de buraco.
  - Alternativa de implementação eficiente e simples: iterar i de 0..H-1 e manter prev = [0]*W, curr = [0]*W; para cada j: se (i,j) não é furos: curr[j] = 1 + min(prev[j], curr[j-1] if j>0 else 0, prev[j-1] if j>0 else 0); conte curr[j]; ao fim da linha faça prev, curr = curr, prev e zere curr. Isso elimina o problema de memória.

- Severity: warning  
  File: solution.py — Camada: completude  
  Descrição: Não foram adicionados testes automatizados (unit/integration). Embora não obrigatório pela task, a ausência de testes torna mais difícil verificar regressões (ex.: casos com muitos furos, furos em bordas, casos N grande mas < H·W). Recomendo incluir pelo menos: (i) casos mínimos (H=W=1, N=0/1), (ii) casos de exemplo do enunciado, (iii) casos limite como H=W=3000 com N=0 e um caso com N grande espalhado para validar memória/comportamento.

- Severity: info  
  File: solution.py — Camada: corretude  
  Descrição: A otimização para o caso N == 0 resolve o Time Limit Exceeded observado naquele caso (usa soma direta dos quadrados ou loop curto até min(H,W)). O DP usado para casos com furos está logicamente correto (soma de dp[i][j] conta todos os quadrados sem furos), e os índices são ajustados corretamente para zero-based.

## Resumo

A correção aborda o TLE no caso N=0 com uma fórmula/loop eficiente e emprega o algoritmo DP correto para contar todas as subquadas sem furos quando há furos. Entretanto, a implementação atual aloca duas matrizes H×W em Python (grid e dp), o que provavelmente causará estouro de memória para entradas grandes (por exemplo H=W=3000). Isso bloqueia a aceitação automática, pois impede que a solução funcione para "toda entrada válida" (critério CA-01). Para liberar o bloqueio é necessário reimplementar a parte com furos usando uma estratégia de memória reduzida (p.ex. DP por linhas com apenas duas arrays de tamanho W e uma estrutura de marcação de furos mais compacta). Após essa mudança a solução deve ser capaz de passar nos limites de tempo e memória.