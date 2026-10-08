## Status: APROVADO

## Issues

- WARNING — arquivo: solution.py — camada: corretude / arquitetura  
  Descrição: O algoritmo atual faz, para cada pessoa, uma varredura por todos os boxes ordenados desde o início (loop aninhado implícito), o que degenera para O(N * M) no pior caso. Com N, M até 2e5 isso leva a Time Limit Exceeded (como já observado). Recomendação: implementar a estratégia clássica O((N+M) log N): ordenar os requisitos das pessoas em ordem decrescente, ordenar os boxes também (por A), avançar um ponteiro em A para inserir na estrutura (min-heap) somente os boxes que atendem ao requisito corrente e então extrair o menor preço disponível. Complexidade esperada O((N + M) log N).

- WARNING — arquivo: solution.py — camada: arquitetura  
  Descrição: A implementação atual reescaneia a lista boxes desde o início para cada pessoa (mesmo quando a maior parte das caixas já foi considerada/descartada). Isso revela falta de separação entre iteração sequencial (ponteiro único) e seleção (estrutura de prioridade). Uso de set para marcar índices é desnecessário se adotada a estratégia com ponteiro + heap. Recomendação: usar índice único sobre A ordenado e um heap para candidatos, evitando sets e re-scans.

- WARNING — arquivo: solution.py — camada: completude  
  Descrição: Não há arquivos de teste ou verificação automática no workspace. Os exemplos do enunciado não estão incluídos como testes unitários/automáticos para validar correções (CA-02 exige que o TLE observado seja eliminado). Recomendação: adicionar testes que incluam os casos limites (N, M grandes) e os exemplos fornecidos para validar desempenho e corretude.

- WARNING — arquivo: solution.py — camada: testes  
  Descrição: Os cenários críticos (happy path + casos limites de performance) não estão cobertos por testes. Sem testes automatizados, regressões ou mudanças futuras podem voltar a introduzir o mesmo TLE. Recomendação: incluir testes automatizados que cubram: (i) exemplos do enunciado, (ii) casos onde M == N grande, (iii) casos onde nenhum box atende a algum requisito (deve retornar -1).

## Resumo
O arquivo solution.py implementa uma lógica que é funcional em entradas pequenas, mas mantém um loop que re-varre todos os boxes para cada pessoa, resultando em complexidade O(N*M) e levando a TLE nas entradas grandes. Não há testes automatizados no workspace. A correção recomendada é reescrever a seleção usando o padrão ponteiro + heap: ordenar B em ordem decrescente, ordenar A (boxes) em ordem decrescente ou ascendente com ponteiro apropriado, empilhar candidatos num min-heap e escolher o menor preço disponível para cada pessoa — isso reduz a complexidade para O((N+M) log N) e resolve o problema de tempo. Após aplicar essa mudança e adicionar testes de performance e casos de borda, a solução deverá atender os critérios de aceite.