## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A lógica principal está incorreta: o código apenas garante que exista exatamente n//2 elementos estritamente menores que k, mas não garante que o elemento mediano valha k. Em muitos casos isso faz o método retornar 0 mesmo quando o mediano não é k (ex.: nums = [10], k = 1 → target_less_k = 0, len(less_than_k)=0 → retorna 0, mas é necessário 9 operações; nums = [0,10,10], k = 5 → len(less_than_k)=1 igual ao target, retorna 0 embora mediano = 10). Ou seja, falta assegurar que haja pelo menos um elemento igual a k na posição mediana (ou que um elemento da metade direita/mediana seja ajustado para k). Esta falha produz respostas incorretas e bloqueia a correta aceitação.

- severity: warning  
  file: solution.py  
  layer: testes  
  description: Não foram fornecidos arquivos de teste unitários no workspace para validar cenários (happy path e edge cases). Recomenda-se incluir testes automatizados cobrindo casos como: único elemento, todos maiores que k, todos menores que k, mistura com counts igualando n//2 mas sem k presente, pares de tamanho par, etc.

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: A implementação atual usa contagens e três sublistas + ordenações parciais para decidir aumentos/decrescimentos, o que torna a lógica mais complexa e suscetível a erros conceituais. Uma abordagem mais simples e robusta é: ordenar nums, definir mid = n // 2 e somar os ajustes necessários para índices >= mid (somente aumentos até k) e para índices < mid (somente decreases até k). Essa versão é mais direta, menos propensa a omissões e aceita no problema original.

## Resumo
A solução entregue não é correta: ela confere apenas a quantidade de elementos menores que k em vez de garantir que o elemento mediano seja exatamente k, o que causa resultados incorretos em casos comuns (por exemplo arrays onde a contagem de elementos menores coincide com n//2 mas o mediano não é k). Há também ausência de testes automatizados e a implementação é mais complexa do que o necessário. Por conter um defeito de corretude que produz respostas erradas, o status é BLOQUEADO.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A lógica principal está incorreta: o código apenas garante que exista exatamente n//2 elementos estritamente menores que k, mas não garante que o elemento mediano valha k. Em muitos casos isso faz o método retornar 0 mesmo quando o mediano não é k (ex.: nums = [10], k = 1 → target_less_k = 0, len(less_than_k)=0 → retorna 0, mas é necessário 9 operações; nums = [0,10,10], k = 5 → len(less_than_k)=1 igual ao target, retorna 0 embora mediano = 10). Ou seja, falta assegurar que haja pelo menos um elemento igual a k na posição mediana (ou que um elemento da metade direita/mediana seja ajustado para k). Esta falha produz respostas incorretas e bloqueia a correta aceitação.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram fornecidos arquivos de teste unitários no workspace para validar cenários (happy path e edge cases). Recomenda-se incluir testes automatizados cobrindo casos como: único elemento, todos maiores que k, todos menores que k, mistura com counts igualando n//2 mas sem k presente, pares de tamanho par, etc.",
      "file": "solution.py",
      "layer": "testes"
    },
    {
      "severity": "warning",
      "description": "A implementação atual usa contagens e três sublistas + ordenações parciais para decidir aumentos/decrescimentos, o que torna a lógica mais complexa e suscetível a erros conceituais. Uma abordagem mais simples e robusta é: ordenar nums, definir mid = n // 2 e somar os ajustes necessários para índices >= mid (somente aumentos até k) e para índices < mid (somente decreases até k). Essa versão é mais direta, menos propensa a omissões e aceita no problema original.",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```