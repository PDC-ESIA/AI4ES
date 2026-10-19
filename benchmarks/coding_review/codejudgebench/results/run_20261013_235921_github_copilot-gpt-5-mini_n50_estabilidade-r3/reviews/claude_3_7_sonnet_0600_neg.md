## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A implementação faz shifts (x << k, sibling << remaining_steps) usando k ou remaining_steps diretamente. Pelo enunciado K pode ser tão grande quanto ~1e18; tentar deslocar por valores tão grandes cria inteiros enormes e pode travar ou esgotar memória/tempo. É necessário limitar os deslocamentos / evitar construir 2^k quando k é grande (por exemplo, detectar que k > 60 implica que qualquer x<<k > N e pular a operação). Sem essa proteção a solução pode falhar por exaustão de recursos em entradas válidas.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram adicionados testes automatizados (arquivos de teste). Pelo fluxo isso é requerido para comprovar correção em vários casos, inclusive limites (N grande, K grande, casos de subárvore vs subir/descer). Recomenda-se incluir um conjunto de testes unitários / casos de integro incluindo os samples e casos limites.

- severity: info  
  file: solution.py  
  layer: arquitetura  
  description: A lógica está organizada numa função solve(n, x, k) clara e com responsabilidades separadas, porém cálculos repetidos de ancestor/child são feitos com loops de divisão inteira. Isso é aceitável (complexidade baixa), mas poderia ser simplificado usando shifts com limites seguros ou pré-cálculo de potências de 2 até 60 para maior clareza e eficiência.

## Resumo
O código corrige a lógica funcional que contava nós a distância K da vértice X (casos: ancestral, descendentes e caminhos que sobem e depois descem por um ramo irmão). Em termos de corretude algorítmica a abordagem está correta nos pequenos e médios valores de K (e passa os exemplos), mas há um problema crítico de robustez: o código realiza deslocamentos por K diretamente, sem limitar K, o que, dado que K pode ser extremamente grande (até ~1e18 segundo o enunciado), resulta em criação de inteiros gigantes e possível esgotamento de tempo/memória. Por isso a entrega fica BLOQUEADA até que essas operações sejam protegidas (por exemplo, truncando K/remaining_steps por 60 ou checando condições que garantam start_idx > n sem realizar o shift). Também foi observado que não há testes automatizados acompanhando a correção (warning).

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A implementação faz shifts (x << k, sibling << remaining_steps) usando k ou remaining_steps diretamente. Pelo enunciado K pode ser tão grande quanto ~1e18; tentar deslocar por valores tão grandes cria inteiros enormes e pode travar ou esgotar memória/tempo. É necessário limitar os deslocamentos / evitar construir 2^k quando k é grande (por exemplo, detectar que k > 60 implica que qualquer x<<k > N e pular a operação). Sem essa proteção a solução pode falhar por exaustão de recursos em entradas válidas.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Não foram adicionados testes automatizados (arquivos de teste). Pelo fluxo isso é requerido para comprovar correção em vários casos, inclusive limites (N grande, K grande, casos de subárvore vs subir/descer). Recomenda-se incluir um conjunto de testes unitários / casos de integro incluindo os samples e casos limites.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "A lógica está organizada numa função solve(n, x, k) clara e com responsabilidades separadas, porém cálculos repetidos de ancestor/child são feitos com loops de divisão inteira. Isso é aceitável (complexidade baixa), mas poderia ser simplificado usando shifts com limites seguros ou pré-cálculo de potências de 2 até 60 para maior clareza e eficiência.",
      "file": "solution.py",
      "layer": "arquitetura"
    }
  ]
}
```