## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A implementação atual usa um algoritmo O(n^2) (dois loops aninhados) que irá estourar o tempo limite para entradas com n até 1e5. O enunciado e o caso de falha indicam Time Limit Exceeded; a solução correta precisa contar subarrays contendo pelo menos k ocorrências do elemento máximo global em O(m) ou O(n) tempo, onde m é o número de ocorrências do máximo (por exemplo, percorrendo apenas os índices onde o máximo aparece e somando (left_options * right_options) para cada janela de tamanho k). Como está, o código não atende ao critério de aceite CA-02 e falhará em entradas grandes — bloqueio da entrega.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram fornecidos arquivos de teste/unitários no workspace. Falta cobertura automatizada que valide casos principais (happy path) e o caso de limite que causou TLE. Adicionar testes que incluam: arrays grandes com poucas/muitas ocorrências do máximo, k maior que o número de ocorrências e exemplos do enunciado.

## Resumo
O arquivo solution.py compila e implementa a semântica básica (contagem de subarrays em que o máximo global aparece pelo menos k vezes), mas o método é quadrático e portanto impraticável para os limites do problema — resultando no TLE observado. Para aceitar a entrega é necessário reimplementar a lógica de forma eficiente (gerar a lista de índices onde o máximo aparece e somar, para cada janela de k ocorrências consecutivas, o produto das opções à esquerda e à direita), e acrescentar testes automatizados que validem o caso grande que causou a falha.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A implementação atual usa um algoritmo O(n^2) (dois loops aninhados) que irá estourar o tempo limite para entradas grandes; reimplemente usando os índices das ocorrências do máximo e soma combinatória (left_options * right_options) por janela de tamanho k.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram fornecidos arquivos de teste/unitários no workspace; faltam testes que cubram casos grandes, k > ocorrências e os exemplos do enunciado.",
      "file": "solution.py",
      "layer": "completude"
    }
  ]
}
```