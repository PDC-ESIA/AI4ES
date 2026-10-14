## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: Algoritmo com complexidade O(n^2) no pior caso — o código tenta todos os finais j e faz transformação O(n) para cada um, o que causa Time Limit Exceeded para entradas grandes (n até 3·10^5). A solução deve ser O(n) (algoritmo guloso que decrementa o bloco contínuo de caracteres não-'a' a partir do primeiro não-'a', ou então altera apenas o último caractere quando toda a string é 'a').

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: Implementação faz busca exaustiva sobre substrings apesar de existir uma solução gulosa simples e linear. Recomenda-se refatorar para aplicar diretamente a regra conhecida: começando no primeiro caractere != 'a', decrementar cada caractere consecutivo enquanto for != 'a' (parar ao encontrar o primeiro 'a'); se toda a string for 'a', trocar o último caractere por 'z'. Isso elimina o laço duplo e simplifica a lógica.

- severity: warning  
  file: (workspace)  
  layer: testes  
  description: Não foram entregues testes automatizados (casos unitários) para validar correção e desempenho (happy path, todo-'a', alternância de caracteres e casos grandes que comprovem ausência de TLE). Criar testes que incluam entradas máximas ajudará a prevenir regressões de performance.

## Resumo
O arquivo solution.py está funcionalmente correto para muitos casos (inclui o tratamento especial para toda a string ser 'a' e aplica a transformação definida), mas a implementação atual realiza uma busca exaustiva que leva a complexidade quadrática e falha em entradas grandes causando Time Limit Exceeded — isto bloqueia a aceitação. Recomendo refatorar para a abordagem gulosa linear descrita na issue de arquitetura e adicionar testes que verifiquem tanto a correção quanto o desempenho em grandes entradas.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "Algoritmo com complexidade O(n^2) no pior caso — o código tenta todos os finais j e faz transformação O(n) para cada um, o que causa Time Limit Exceeded para entradas grandes (n até 3·10^5). A solução deve ser O(n) (algoritmo guloso que decrementa o bloco contínuo de caracteres não-'a' a partir do primeiro não-'a', ou então altera apenas o último caractere quando toda a string é 'a').",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Implementação faz busca exaustiva sobre substrings apesar de existir uma solução gulosa simples e linear. Recomenda-se refatorar para aplicar diretamente a regra conhecida: começando no primeiro caractere != 'a', decrementar cada caractere consecutivo enquanto for != 'a' (parar ao encontrar o primeiro 'a'); se toda a string for 'a', trocar o último caractere por 'z'. Isso elimina o laço duplo e simplifica a lógica.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues testes automatizados (casos unitários) para validar correção e desempenho (happy path, todo-'a', alternância de caracteres e casos grandes que comprovem ausência de TLE). Criar testes que incluam entradas máximas ajudará a prevenir regressões de performance.",
      "file": "(workspace)",
      "layer": "testes"
    }
  ]
}
```