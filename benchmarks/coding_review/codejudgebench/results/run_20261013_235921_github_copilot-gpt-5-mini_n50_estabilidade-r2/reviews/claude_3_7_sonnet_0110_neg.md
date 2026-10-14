## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A solução usa programação dinâmica com complexidade O(n * k). Para os limites do problema (n, k até 10^5) isso é inviável e levará a Time Limit Exceeded em muitos casos (por exemplo n=100000, k ~ 50000). Embora haja special-cases que cobrem k == n-1, k == 0 e m == 1, a implementação geral ainda falha em entradas grandes e, portanto, não atende o critério de aceite CA-01 (correção para toda entrada válida). Recomenda-se usar a fórmula combinatória fechada count = C(n-1, k) * m * (m-1)^(n-1-k) mod 1e9+7, implementando fatorial e inversos modulares para O(n) pré-processamento ou O(log MOD) per escolha, garantindo execução eficiente para os limites dados.

- severity: warning  
  file: solution.py  
  layer: testes  
  description: Não foram entregues arquivos de teste/unitários para validar os casos críticos (happy path, limites grandes, casos de borda como n=1, m=1, k=0, k=n-1). A ausência de testes automatizados dificulta a detecção regressiva de TLEs ou de mudanças incorretas na implementação.

## Resumo
O código em solution.py produz resultados corretos nos casos cobertos por special-cases e a recursão DP está logicamente correta, mas a estratégia algorítmica principal é O(n*k) e não escala para os limites do enunciado. Isso viola o critério de aceite relacionado a correção para toda entrada válida (CA-01) e deixa a solução sujeita a Time Limit Exceeded em muitos cenários. Além disso faltam testes automatizados. Recomendo reimplementar usando a fórmula combinatória C(n-1, k) * m * (m-1)^(n-1-k) com pré-cálculo de fatorial e inversos mod 1e9+7, e adicionar um conjunto de testes cobrindo limites e bordas.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A solução usa programação dinâmica com complexidade O(n * k). Para os limites do problema (n, k até 10^5) isso é inviável e levará a Time Limit Exceeded em muitos casos (por exemplo n=100000, k ~ 50000). Embora haja special-cases que cobrem k == n-1, k == 0 e m == 1, a implementação geral ainda falha em entradas grandes e, portanto, não atende o critério de aceite CA-01 (correção para toda entrada válida). Recomenda-se usar a fórmula combinatória fechada count = C(n-1, k) * m * (m-1)^(n-1-k) mod 1e9+7, implementando fatorial e inversos modulares para O(n) pré-processamento ou O(log MOD) per escolha, garantindo execução eficiente para os limites dados.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues arquivos de teste/unitários para validar os casos críticos (happy path, limites grandes, casos de borda como n=1, m=1, k=0, k=n-1). A ausência de testes automatizados dificulta a detecção regressiva de TLEs ou de mudanças incorretas na implementação.",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```