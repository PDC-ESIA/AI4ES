## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: arquitetura  
  description: A implementação itera com for i in range(1, N). Como N pode ser até 2×10^9, isso torna o algoritmo O(N) e impraticável (vai TLE ou nem iniciar em entradas grandes). O problema exige uma solução O(M log M) ou O(M) em M (número de posições fornecidas), portanto a escolha atual de percorrer todas as células é bloqueante.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não há arquivos de teste no workspace que verifiquem correção e limites (casos pequenos, amostras e casos extremos com N muito grande / M pequeno). Os critérios de aceite (CA-01, CA-02) mencionam comportamento automatizável — sem testes entregues, a validação automatizada não está completa.

- severity: info  
  file: solution.py  
  layer: arquitetura  
  description: A lógica funcional (verificação de soma total, acumular excesso de pedras, devolver -1 quando não há pedras suficientes e acumular operações) parece correta para a abordagem por célula, mas deveria ser adaptada para pular grandes intervalos sem pedras (processar apenas posições presentes em X ordenadas), usando fórmulas fechadas para somar operações em gaps. Recomenda-se iterar sobre X ordenado e computar, para cada intervalo de comprimento d, a contribuição em O(1): ops += d*e - d*(d+1)//2, onde e é o excesso antes do intervalo; verificar e >= d.

## Resumo
A solução implementa corretamente a lógica de distribuição de pedras em termos de correção funcional para entradas pequenas (a ideia de "excess" e contabilização de operações está adequada), e corrige o erro de saída observada no caso de teste fornecido. Contudo, a implementação atual itera por todas as posições de 1 até N, o que é inaceitável com N até 2×10^9 — isto é um bloqueador crítico: a solução vai falhar por tempo/exaustão de recursos em instâncias válidas de grande escala. Além disso, não foram entregues testes automatizados para validar a correção nos limites. Recomenda-se reescrever a iteração para percorrer apenas as M posições dadas (ordenadas) e calcular eficientemente a contribuição de intervalos entre posições.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A implementação itera com for i in range(1, N). Como N pode ser até 2×10^9, isso torna o algoritmo O(N) e impraticável (vai TLE ou nem iniciar em entradas grandes). O problema exige uma solução O(M log M) ou O(M) em M (número de posições fornecidas), portanto a escolha atual de percorrer todas as células é bloqueante.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não há arquivos de teste no workspace que verifiquem correção e limites (casos pequenos, amostras e casos extremos com N muito grande / M pequeno). Os critérios de aceite (CA-01, CA-02) mencionam comportamento automatizável — sem testes entregues, a validação automatizada não está completa.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "A lógica funcional (verificação de soma total, acumular excesso de pedras, devolver -1 quando não há pedras suficientes e acumular operações) parece correta para a abordagem por célula, mas deveria ser adaptada para pular grandes intervalos sem pedras (processar apenas posições presentes em X ordenadas), usando fórmulas fechadas para somar operações em gaps. Recomenda-se iterar sobre X ordenado e computar, para cada intervalo de comprimento d, a contribuição em O(1): ops += d*e - d*(d+1)//2, onde e é o excesso antes do intervalo; verificar e >= d.",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```