## Status: BLOQUEADO

## Issues
- critical — solution.py — corretude  
  Descrição: Algoritmo gera todas as permutações (itertools.permutations) e mantém um set "seen" de strings únicas. Para entradas com todos os caracteres distintos e K != 2 (por exemplo N=10, K=3), o código irá gerar e armazenar 10! ≈ 3.6M strings, causando Time Limit Exceeded ou uso de memória excessivo. Há apenas uma otimização específica para (K==2 and all distinct); falta a otimização geral para "todos os caracteres distintos" ou uma abordagem combinatória/Dynamic Programming que evite enumeração completa.

- warning — solution.py — arquitetura  
  Descrição: Uso de permutations + seen causa acoplamento entre geração e deduplicação na memória (alta complexidade espaço-tempo). Mesmo quando há repetições de caracteres, o código ainda itera sobre n! tuplas (mesmo que as ignore depois), o que é ineficiente. A responsabilidade de geração de permutações únicas deveria ser tratada por uma rotina que gere permutações distintas diretamente ou, preferivelmente, por uma contagem combinatória/PD que evite enumeração.

- warning — solution.py — completude  
  Descrição: Não foram incluídos testes automatizados (unit tests / cases). A DoD pede correção e eliminação da falha observada; não há artefatos de teste para validar comportamento em casos limites (por exemplo N=10 com todos caracteres distintos e vários K), portanto falta cobertura de verificação automática.

- info — solution.py — corretude  
  Descrição: Há um retorno especial para k == 1 (return 0), mas no enunciado K ≥ 2 sempre; este ramo é inócuo com as constraints declaradas. Não é incorreto, apenas redundante.

- info — solution.py — testes  
  Descrição: Nenhum arquivo de teste entregue para reproduzir o Time Limit Exceeded observado originalmente; sem testes, regressões futuras podem passar despercebidas.

## Resumo
O código corrige o bug presente na solução anterior (a expressão que gerava um set de caracteres em vez de permutações) e adiciona uma otimização pontual para (K==2 and all distinct), mas a abordagem principal ainda enumera permutations(s) e armazena todas as permutações vistas. Isso deixa o programa vulnerável a TLE / OOM em casos permitidos pelos limites (N=10) quando não entra no ramo otimizado (por exemplo, todos caracteres distintos com K>2) ou em outros casos com alta cardinalidade de permutações únicas. Como esse problema impede a execução aceitável/eficiente para entradas válidas, a entrega fica bloqueada até que a enumeração completa seja evitada (soluções: detecção geral de "todos caracteres distintos" para qualquer K>=2, geração de permutações únicas sem criar n! intermediários, ou melhor ainda, uma solução combinatória/DP que conte as permutações válidas sem enumerá-las).

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "Algoritmo gera todas as permutações e mantém um set 'seen' de strings únicas. Para entradas com todos os caracteres distintos e K != 2 (ex.: N=10, K=3) o código gera e armazena 10! ≈ 3.6M strings, causando TLE ou uso de memória excessivo. Falta otimização geral para 'todos os caracteres distintos' ou abordagem sem enumeração.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Uso de permutations + seen causa alto custo de tempo/espaco; a deduplicação em memória e a iteração sobre n! tuplas é ineficiente. Recomenda-se gerar permutações distintas diretamente ou usar uma contagem combinatória/DP.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Nenhum teste automatizado foi incluído para validar correções e casos limites (p.ex. N=10 com chars distintos e vários K). Ausência de testes impede verificação automática da regressão observada.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "Ramo para k == 1 (return 0) é redundante, pois o enunciado garante K >= 2.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "info",
      "description": "Não foram fornecidos arquivos de teste no workspace para reproduzir o TLE observado; adicionar testes é recomendado.",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```