## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: Lógica incorreta ao assumir que len(less_than_k) == n//2 implica que a mediana já é k. O código retorna 0 quando o número de elementos estritamente menores que k coincide com n//2, mesmo que não exista nenhum elemento igual a k — nesse caso a mediana pode ser > k e é necessário operar. Exemplo simples: nums = [1,2,6,7,8], k = 5 (n=5, n//2=2). less_than_k = [1,2] => len == target, o método devolve 0, mas o resultado correto é 1 (decrementar 6→5). Essa falha causa Wrong Answer em entradas válidas e quebra os critérios CA-01/CA-02.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram fornecidos testes automatizados (arquivo(s) de teste) para validar a correção; a tarefa exigia corrigir a solução que falhava em testes e não há suite de testes entregue para garantir que a regressão foi resolvida.

- severity: info  
  file: solution.py  
  layer: arquitetura  
  description: A implementação cria três listas separadas (less_than_k, equal_to_k, greater_than_k) o que aumenta uso de memória para n até 3n. Uma alternativa mais simples e clara é ordenar e somar as diferenças apenas nas posições necessárias (complexidade O(n log n) tempo, O(1) ou O(n) memória dependendo da abordagem), além de evitar a lógica de contagem que levou ao erro lógico.

- severity: warning  
  file: solution.py  
  layer: testes  
  description: Ausência de testes que cubram casos chave/limites (ex.: casos sem elementos iguais a k, já com contagem de menores = n//2; pares de paridade, n=1; valores grandes). Sem esses testes não é possível confiar na correção da solução entregue.

## Resumo
A entrega contém uma implementação plausível mas logicamente incorreta: a checagem que considera satisfeito o caso len(less_than_k) == n//2 é insuficiente para garantir que a mediana seja k (é necessário também haver elementos iguais a k para posicioná-lo no índice da mediana). Esse defeito gera respostas erradas em entradas válidas (exemplo fornecido). Além disso não foram entregues testes automatizados para validar a correção. Devido à falha de corretude, o status é BLOQUEADO até que o algoritmo seja corrigido e coberto por testes relevantes.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "Lógica incorreta ao assumir que len(less_than_k) == n//2 implica que a mediana já é k. O código retorna 0 quando o número de elementos estritamente menores que k coincide com n//2, mesmo que não exista nenhum elemento igual a k — nesse caso a mediana pode ser > k e é necessário operar. Exemplo simples: nums = [1,2,6,7,8], k = 5 (n=5, n//2=2). less_than_k = [1,2] => len == target, o método devolve 0, mas o resultado correto é 1 (decrementar 6→5). Essa falha causa Wrong Answer em entradas válidas e quebra os critérios CA-01/CA-02.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram fornecidos testes automatizados (arquivo(s) de teste) para validar a correção; a tarefa exigia corrigir a solução que falhava em testes e não há suite de testes entregue para garantir que a regressão foi resolvida.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "A implementação cria três listas separadas (less_than_k, equal_to_k, greater_than_k) o que aumenta uso de memória para n até 3n. Uma alternativa mais simples e clara é ordenar e somar as diferenças apenas nas posições necessárias, além de evitar a lógica de contagem que levou ao erro lógico.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Ausência de testes que cubram casos chave/limites (ex.: casos sem elementos iguais a k, já com contagem de menores = n//2; pares de paridade, n=1; valores grandes). Sem esses testes não é possível confiar na correção da solução entregue.",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```