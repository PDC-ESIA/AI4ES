## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A lógica está incorreta: o código usa apenas contagens por distância (nós a distância 1 e 2 do candidato central) e calcula y como dist_counts[2] // x. Isso não respeita a distribuição por subárvore de cada vizinho do central — para cada vizinho (potencial mid-level) devemos checar quantos filhos imediatos ele tem (degree-1 no lado da subárvore) e só vizinhos com pelo menos y filhos podem ser usados. O algoritmo atual pode contar vizinhos que não têm filhos suficientes e assim produzir respostas erradas (ex.: o caso já reportado), além de não considerar selecionar um subconjunto ótimo de vizinhos quando necessário.
- severity: critical  
  file: solution.py  
  layer: arquitetura  
  description: Complexidade inadequada para as restrições: o código faz um BFS por cada vértice candidato a central (O(N^2) em geral). Com N até 3e5 isso não é viável (provável TLE / execução impraticável). A solução conhecida do problema exige análise por raiz candidatas limitada e / ou processamento por subárvores com complexidade total O(N log N) ou O(N).
- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram entregues testes (unitários / de integração) ou um runner para validar a solução contra os exemplos e casos limites. Pelo enunciado esperava-se pelo menos os exemplos do problema como testes automatizados.
- severity: warning  
  file: solution.py  
  layer: testes  
  description: Os exemplos do enunciado não estão codificados como testes nem executados no arquivo. Sem testes fica difícil validar regressões como a falha previamente reportada.

## Resumo
O arquivo solution.py não implementa corretamente a transformação do input numa Snowflake Tree: ele agrupa nós por distância do central e obtém y como uma divisão inteira global, negligenciando a necessidade de garantir que cada vizinho do central tenha pelo menos y filhos imediatos para ser um mid-level válido. Além disso, a estratégia de tentar cada vértice como central com um BFS completo por vértice produz complexidade O(N^2), inviável para N até 3e5. Devido a essas falhas funcionais e de escala que provocam respostas incorretas e/ou TLE, a entrega fica BLOQUEADA. Recomendações: reimplementar a verificação por central considerando, para cada vizinho, o número de filhos imediatos (degree-1 na subárvore), computando custos por vizinho e avaliando y com base no mínimo disponível entre vizinhos (ou testando y e contando apenas vizinhos com m >= y), e otimizar para complexidade linear ou N log N; adicionar testes cobrindo exemplos e casos limites.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A lógica está incorreta: o código usa apenas contagens por distância (nós a distância 1 e 2 do candidato central) e calcula y como dist_counts[2] // x. Isso não respeita a distribuição por subárvore de cada vizinho do central — para cada vizinho (potencial mid-level) devemos checar quantos filhos imediatos ele tem (degree-1 no lado da subárvore) e só vizinhos com pelo menos y filhos podem ser usados. O algoritmo atual pode contar vizinhos que não têm filhos suficientes e assim produzir respostas erradas (ex.: o caso já reportado), além de não considerar selecionar um subconjunto ótimo de vizinhos quando necessário.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "critical",
      "description": "Complexidade inadequada para as restrições: o código faz um BFS por cada vértice candidato a central (O(N^2) em geral). Com N até 3e5 isso não é viável (provável TLE / execução impraticável).",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues testes (unitários / de integração) ou um runner para validar a solução contra os exemplos e casos limites.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "warning",
      "description": "Os exemplos do enunciado não estão codificados como testes nem executados no arquivo. Sem testes fica difícil validar regressões como a falha previamente reportada.",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```