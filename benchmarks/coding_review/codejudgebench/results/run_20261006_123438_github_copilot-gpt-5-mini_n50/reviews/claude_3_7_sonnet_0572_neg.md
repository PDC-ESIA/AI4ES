## Status: BLOQUEADO

## Issues

- [CRITICAL] solution.py / camada: corretude
  - Descrição: Complexidade espacial/temporal impraticável: o código ainda itera explicitamente sobre todos os pares u (1..N1) e v (N1+1..N1+N2), causando O(N1 * N2) iterações (até ~2.25e10), o que gera Time Limit Exceeded para os limites do problema. A tentativa de mitigar com `existing_edges` só acelera a verificação de existência de aresta, mas não remove a iteração quadrática que é o ponto de estrangulamento. O resultado é que a solução não cumpre CA-01/CA-02 (produzir resultado eficiente / eliminar o TLE).

- [WARNING] solution.py / camada: arquitetura
  - Descrição: Estrutura desnecessária: o conjunto existing_edges e a verificação de existência de aresta entre u e v são supérfluos no contexto do enunciado. Pelo enunciado (cada subset é interno-conexo e 1 e N1+N2 são desconectados), não existem arestas entre os subconjuntos originalmente — portanto não há necessidade de filtrar pares que já têm aresta. Manter essa estrutura dá falsa sensação de otimização enquanto a complexidade dominante permanece O(N1*N2).

- [WARNING] solution.py / camada: completude
  - Descrição: Não foram entregues arquivos de teste automatizados nem casos de unidade/integração. A ausência de testes torna impossível verificar automaticamente regressões e a correção do desempenho (critério CA-02) no pipeline local. (Acceptance CA-01/CA-02 são automatizáveis; aqui falta artefato de teste.)

- [INFO] solution.py / camada: arquitetura
  - Descrição: O BFS implementado que restringe vizinhos por intervalo (subset_start/subset_end) é aceitável e correto para este problema. Há um pequeno linter warning (import não no topo) devido ao bloco de ambiente pré-carregado — não é um defeito funcional do código submetido.

## Resumo

A implementação atual calcula corretamente distâncias via BFS em cada subconjunto, mas ainda tenta maximizar a expressão dist1[u] + 1 + dist2[v] iterando por todos os pares possíveis (u, v), o que é inviável para os limites do problema e gera Time Limit Exceeded. A solução correta e eficiente é observar que, para maximizar dist1[u] + 1 + dist2[v], basta escolher u que maximize dist1[u] e v que maximize dist2[v]; logo o resultado é max(dist_from_1.values()) + 1 + max(dist_from_N1N2.values()). Substituir o laço duplo por essa fórmula reduz a complexidade para O(N+M) e resolve o TLE. Também é seguro remover a verificação/existing_edges porque, conforme as garantias do enunciado, não existem arestas entre os dois subconjuntos na entrada original. Até essas correções serem aplicadas, o problema permanece bloqueado para aceitação automática.

Sugestão de correção (conceitual):
- Calcular dist_from_1 e dist_from_N1N2 como feito.
- Responder com: answer = max(dist_from_1.values()) + 1 + max(dist_from_N1N2.values()).
- Remover iteração dupla e estrutura existing_edges desnecessária.
- Adicionar testes que cubram casos pequenos e o caso limite de performance (grande N1,N2,M com sem arestas entre subsets).