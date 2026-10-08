## Status: BLOQUEADO

## Issues

- Severity: critical  
  File: solution.py — Camada: corretude  
  Descrição: A lógica central está incorreta: o código trata qualquer vizinho de um vértice de nível-médio como um candidato a folha sem considerar o custo de deletar o respectivo subárvore. Ele só conta o número de filhos imediatos (children_counts = len(rooted_tree[child])) e aceita um par (x,y) sempre que cada um desses counts >= y, assumindo então que o tamanho final será 1 + x + x*y. Na realidade, para que um vizinho seja uma folha no Snowflake final, é necessário deletar toda a subárvore daquele vizinho (todos os seus descendentes) — o custo de deletar depende do tamanho da subárvore, não apenas da existência de vizinhos. Logo, o algoritmo pode subestimar o número de deleções necessárias (o que explica o WA observado) e produzir respostas incorretas.

- Severity: critical  
  File: solution.py — Camada: arquitetura / corretude (complexidade)  
  Descrição: Complexidade assintótica inaceitável para os limites do problema. O código tenta para cada possível vértice central (n possibilidades) construir uma árvore enraizada (DFS O(n)) e então itera sobre x e y de forma ingênua (y até n), resultando em comportamento cúbico/pires e trabalhos repetidos que explodirão o tempo para N até 3e5. A solução conhecida para este tipo de problema exige abordagens lineares ou quase-lineares (DP por árvore, consideração limitada de centrais relevantes, uso de tamanhos de subárvores e seleção ótima por custo), não iterações n^2/n^3. Esse ponto torna a solução impraticável (provável TLE / estouro de recursos) — bloqueante.

- Severity: warning  
  File: solution.py — Camada: completude  
  Descrição: Não foram fornecidos arquivos de teste/unitários nem exemplos de regressão. O repositório contém apenas solution.py. Falta um conjunto de testes que cubra os casos do enunciado (os samples e casos limites) para validar a correção e desempenho.

- Severity: info  
  File: solution.py — Camada: arquitetura  
  Descrição: build_rooted_tree reconstrói a estrutura enraizada do grafo do zero para cada escolha de central, levando a trabalho repetido. Também retorna um dicionário com listas para todos os vértices mesmo quando muitos não são usados; isto gera overhead de memória/tempo desnecessário. Uma arquitetura mais eficiente reutilizaria informações de subárvores ou faria uma única DFS para computar tamanhos e relações parent/child e depois avaliaria candidatos sem reconstruir tudo repetidamente.

- Severity: info  
  File: solution.py — Camada: corretude  
  Descrição: A função DFS ignora o parâmetro parent (não é necessário porque usa visited), mas a assinatura dfs(node, parent) confunde a intenção. Além disso, o algoritmo usa um limite de y arbitrário (1..n) — sem poda baseada em tamanhos de subárvore — o que é ineficiente.

## Resumo

O arquivo solution.py entrega uma solução conceitualmente insuficiente e não escalável. A implementação comete dois erros críticos: (1) modela erroneamente o custo para transformar vizinhos em folhas (ignora o tamanho das subárvores e o custo de deletá-las) e (2) tem complexidade algorítmica inaceitável (iterações aninhadas e reconstrução da árvore para cada central), o que a torna inviável para os limites N ≤ 3·10^5. Além disso, não há testes automatizados entregues. Por esses motivos a tarefa está BLOQUEADA — é necessário reformular o algoritmo para contabilizar tamanhos de subárvores e custo mínimo de remoção (uso de DP/seleção por custo), reduzir significativamente a complexidade (não tentar y até n para cada central) e adicionar testes que incluam os exemplos do enunciado e casos limites.