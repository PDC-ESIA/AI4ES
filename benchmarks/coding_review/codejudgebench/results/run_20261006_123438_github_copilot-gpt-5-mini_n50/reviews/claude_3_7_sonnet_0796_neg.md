## Status: BLOQUEADO

## Issues

- Severity: CRITICAL  
  File: solution.py — layer: arquitetura  
  Descrição: Complexidade algorítmica inaceitável para os limites do problema. O código executa uma BFS do grafo para cada vértice candidato a central (loop over central in 1..N), resultando em tempo O(N^2) no pior caso. Com N até 3·10^5 isso é impraticável (TLE / uso excessivo de CPU/memória). Esta é uma barreira de execução independente da correção lógica e bloqueia a entrega.

- Severity: CRITICAL  
  File: solution.py — layer: corretude  
  Descrição: Lógica incorreta para construir/avaliar um Snowflake Tree. O código assume que x (número de vértices de nível médio) é simplesmente o número de vizinhos do vértice central (tudo ou nada) e que as folhas possíveis são exatamente os vértices na distância 2 do central. Não permite escolher um subconjunto de vizinhos como níveis médios nem contabiliza folhas que podem ser obtidas após deletar vértices internos — ambos necessários para encontrar a solução ótima. Como consequência, o algoritmo pode retornar valores incorretos (já observado).

- Severity: CRITICAL  
  File: solution.py — layer: corretude  
  Descrição: Cálculo de y está errado/insuficiente: y_max = dist_counts[2] // x pressupõe uma distribuição uniforme das possíveis folhas entre todos os vizinhos do central. Isso ignora que alguns vizinhos podem prover mais folhas que outros e que podemos escolher apenas alguns vizinhos como mid-level para maximizar a estrutura final. Essa simplificação leva a respostas incorretas.

- Severity: WARNING  
  File: solution.py — layer: completude  
  Descrição: Não há testes automatizados ou casos de unidade no repositório que verifiquem as várias configurações (happy path e casos limites). A entrega inclui apenas o código-fonte; acrescentar testes seria necessário para validação contínua e prevenção de regressões.

- Severity: WARNING  
  File: solution.py — layer: arquitetura  
  Descrição: Estrutura do código mistura leitura de I/O, lógica e tentativa de busca de parâmetros em um só bloco. Falta modularização que facilitaria escrita de testes e otimizações (por exemplo: funções para contar folhas potenciais por vizinho, tentativa de selecionar melhores x para um y dado, etc.).

## Resumo

A solução entregue em solution.py contém problemas críticos que bloqueiam a aceitação: (1) complexidade quadrática por executar BFS para cada vértice central, inviável para N ≤ 3·10^5; (2) lógica incorreta que simplifica em demasia como x e y são avaliados (assumindo que todos os vizinhos do central serão usados como mid-level e que folhas são apenas os nós na distância 2), o que produz respostas erradas. Além disso não há testes automatizados. Antes de prosseguir no pipeline é preciso reimplementar a estratégia: para cada candidato a central considerar os tamanhos das "subárvores" de cada vizinho (quando a árvore é enraizada no central), determinar quantos vértices cada vizinho pode fornecer como folhas para um dado y e então escolher os melhores x vizinhos — e tudo isso com uma abordagem global que evite iterar BFS O(N) vezes (por exemplo, escolhendo um conjunto reduzido de centrais plausíveis ou computando informações em tempo linear/linear-logarítmico com DP/agrupamentos). Após corrigir a lógica e garantir complexidade adequada, incluir testes que cubram os casos citados no enunciado.