## Status: BLOQUEADO

## Issues

- Severidade: critical  
  Arquivo: solution.py — Camada: corretude / performance  
  Descrição: A implementação é O(n^2): para cada prefixo (loop externo sobre i) o código recomputa a posição e as contagens percorrendo novamente os j primeiros caracteres (loop interno). Para |s| até 10^5 isso é impraticável e causa Time Limit Exceeded (o problema já relatado). Isso viola o requisito CA-02 (eliminar a falha observada). Resultado: entrada grande TLE — bloqueante.

- Severidade: warning  
  Arquivo: solution.py — Camada: arquitetura  
  Descrição: O código implementa quatro "estratégias" e recontagens por prefixo, com duplicação de lógica e complexidade desnecessária. Existe uma formulação muito mais simples e direta para o problema por prefixo (ver sugestão abaixo). A implementação atual torna o código mais longo e difícil de manter.

- Severidade: info  
  Arquivo: solution.py — Camada: completude  
  Descrição: Apenas o arquivo solution.py foi entregue — não foram incluídos testes automatizados (unit tests) que verifiquem casos pequenos, limites e os exemplos do enunciado. Para pipelines automatizados isso dificulta validação regressiva. Recomenda-se entregar um conjunto de testes (ex.: pytest) cobrindo happy path e limites.

## Resumo

A solução atual produz corretas ideias localmente (calcula posição por prefixo e tenta aplicar até k alterações), mas permanece com complexidade quadrática por recomputar contagens do zero para cada prefixo, portanto continuará a falhar por Time Limit Exceeded em entradas grandes (n ≈ 1e5). Isso é um problema crítico que bloqueia a aceitação. A correção requerida é transformar o algoritmo em linear: manter posição (x,y) incrementalmente enquanto avança pelos prefixos e, para cada prefixo de comprimento i, computar em O(1) a melhor distância possível após até k alterações usando a observação simples abaixo.

Sugestão de correção (algoritmo O(n), explicação e esboço):
- Ao avançar por s index a index mantenha x,y atual (soma incremental).
- Para cada prefixo de tamanho i:
  - d0 = |x| + |y|
  - mudanças_disponiveis = min(k, i)  # não se pode mudar mais do que i passos
  - máxima distância possível naquele prefixo = min(i, d0 + 2 * mudanças_disponiveis)
    - justificativa: cada alteração pode aumentar a distância L1 em até 2, e a distância L1 está limitada por i (máximo alcançável com i passos).
- Mantenha o máximo global sobre todos os prefixos. Complexidade O(n) e memória O(1).

Exemplo de implementação correta e eficiente (esboço):
- iterar i de 0..n-1:
  - atualizar x,y de acordo com s[i]
  - d0 = abs(x) + abs(y)
  - candidate = min(i+1, d0 + 2*min(k, i+1))
  - max_distance = max(max_distance, candidate)
- também considerar i = 0 (origem) se desejar (distance 0).

Aplicando essa mudança elimina-se o TLE e atende aos critérios automáticos.

Observação final: depois de aplicar o ajuste de complexidade, recomendo adicionar testes unitários cobrindo:
- exemplos do enunciado,
- casos limites (n = 1, n grande com k = 0 e k = n),
- sequências com movimentos que alternam direções,
- casos aleatórios com verificação por força bruta para n pequeno.