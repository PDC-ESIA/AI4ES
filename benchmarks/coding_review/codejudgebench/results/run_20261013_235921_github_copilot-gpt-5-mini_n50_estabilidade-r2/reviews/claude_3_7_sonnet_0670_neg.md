## Status: BLOQUEADO

## Issues

- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A solução atual usa collections.deque para representar as N posições e indexa com positions[p-1] em cada consulta do tipo 2. Em Python, deque.__getitem__ é O(k) (linear no índice), e armazenar N tuplas (N ≤ 10^6) também é muito custoso em memória/objeto. Com os limites do problema (N até 10^6, Q até 2×10^5) isso leva a Time Limit Exceeded e possivelmente uso excessivo de memória. Em suma: escolha de estrutura e acesso tornam o algoritmo inaceitavelmente lento/insustentável para os casos máximos.

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: Inicializar uma deque de N tuplas (uma por parte) cria muitos objetos Python (tuplas + inteiros), o que é ineficiente em memória. Além disso, a solução mistura armazenamento explícito de todas as posições com operações de leitura aleatória caras; a responsabilidade de manter apenas o histórico mínimo necessário não foi adotada.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não há arquivos de teste no workspace. Nenhum teste automatizado foi entregue para validar correções e evitar regressões (por ex. casos limites de desempenho e consultas com p grande). Isso dificulta comprovar que a correção resolve o TLE observado.

- severity: info  
  file: solution.py  
  layer: testes  
  description: Os prints e parsing de input estão corretos para o formato, mas a implementação atual não provê testes unitários ou de integração; recomenda-se incluir testes que reproduzam o caso limite que causou TLE.

## Resumo

A implementação entregou uma versão funcional em cenários pequenos, mas é incapaz de satisfazer os limites do problema: o uso de deque com indexing O(k) e a alocação de N tuplas tornam a solução proibitivamente lenta e pesada em memória para N até 10^6 e Q até 2×10^5. Isso explica o Time Limit Exceeded observado. Como correção, recomendo não armazenar todas as N posições explicitamente. Uma abordagem eficiente e simples é manter apenas o histórico das posições da cabeça (lista de comprimento ≤ Q+1) e, ao responder uma consulta p no tempo k (número de movimentos já feitos), devolver:
- se p-1 ≤ k: head_positions[k - (p-1)]
- caso contrário: (p - k, 0)
Essa solução responde cada consulta em O(1) e usa memória O(Q), encerrando a causa do TLE. Também sugiro adicionar testes que comprovem comportamento em limites (p≈N, muitos queries tipo 2, grandes N).

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A solução atual usa collections.deque e indexa positions[p-1] em consultas; deque.__getitem__ é O(k) e armazenar N tuplas (N ≤ 10^6) é custoso em memória. Isso causa TLE/MLE para os limites do problema.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Inicializar uma deque com N tuplas cria muitos objetos Python (tuplas e inteiros) e é ineficiente em memória. A estrutura escolhida não separa bem responsabilidades e não minimiza o estado necessário.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não há arquivos de teste no workspace. Não foram entregues testes automatizados que verifiquem correção e desempenho (casos limites).",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "Parsing e output estão corretos para o formato do problema, mas faltam testes; recomenda-se incluir casos limites e casos de stress.",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```