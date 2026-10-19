## Status: BLOQUEADO

## Issues

- Severity: critical  
  File: solution.py — Camada: corretude / arquitetura  
  Descrição: O algoritmo atual ainda faz uma busca linear sobre range(1, N+1) para encontrar a pessoa à frente em cada um dos M eventos. Isso resulta em complexidade O(N * M) no pior caso e mantém a falha observada (Time Limit Exceeded) para os limites do problema (N, M ≤ 2·10^5). A solução, portanto, não atende ao critério CA-02 de eliminar o TLE e também falha em CA-01 para entradas grandes. É necessário usar uma estrutura de dados que permita obter, em tempo logarítmico ou amortizado constante, o menor índice de pessoa presente na fila (ex.: um heap/priority queue de pessoas disponíveis com manutenção lazy, ou um conjunto ordenado).  

  Sugestão de correção: manter dois heaps:
  - returns: min-heap de (return_time, person) — já presente;
  - available: min-heap com índices das pessoas atualmente na fila. Inicializar available com 1..N (heapify). Ao processar um evento:
    - primeiro, processar todos os retornos (remover pessoa de out_of_row e heappush(person) em available);
    - antes de dar W, limpar o topo de available descartando while available and available[0] in out_of_row: heappop(available);
    - se available vazio → ninguém recebe; caso contrário heappop(available) para obter front_person, marcar como out_of_row e agendar retorno em returns.
  Essa abordagem reduz a complexidade para O((M + total_returns) log N), adequada aos limites do problema.

- Severity: warning  
  File: solution.py — Camada: completude  
  Descrição: Não foram entregues testes automatizados (arquivos de teste). Embora a entrega pedida fosse apenas solution.py, a ausência de testes torna difícil verificar automaticamente regressões e os casos-limite que causaram TLE. Recomenda-se adicionar testes unitários ou casos de integração com entradas pequenas e grandes (incluindo o caso de stress) para validar desempenho e corretude.

- Severity: warning  
  File: solution.py — Camada: arquitetura / corretude  
  Descrição: Uso de out_of_row.remove(person) ao processar retornos. Em caso de inconsistência (entrada corrupta ou estado inesperado) isso levantaria KeyError. É mais seguro usar out_of_row.discard(person), que não dispara se o elemento não estiver presente. Embora não seja a causa principal do problema atual, é uma robustez simples a ser aplicada.

- Severity: info  
  File: solution.py — Camada: arquitetura / style  
  Descrição: Há imports redundantes e reimportação de heapq (o ambiente já pré-carrega vários imports). Além disso há advertências de lint (module-level import não no topo, redefinição). Não afeta a correção funcional, mas limpar imports melhora legibilidade e evita avisos estáticos.

## Resumo

O arquivo solution.py está funcional para entradas pequenas, mas mantém uma busca linear por pessoa à frente em cada evento, levando a complexidade O(N*M) e reproduzindo o Time Limit Exceeded reportado. Isso é um bloqueio funcional: a correção precisa substituir a varredura 1..N por uma estrutura de dados eficiente (por exemplo, um min-heap de pessoas disponíveis mantido de forma “lazy” juntamente com o heap de retornos) para satisfazer os requisitos de performance (CA-01 e CA-02). Também recomendo pequenas melhorias de robustez (usar discard em vez de remove) e adicionar testes automatizados. Até que a complexidade seja corrigida, o status deve ser BLOQUEADO.