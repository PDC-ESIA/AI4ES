## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: Lógica de transição incorreta — há dupla contagem das contribuições ao calcular dp[i][0]. O código separa "no_cut" (dp[i-1][0]) e "cut" (cut_dp0), mas cut_dp0 é calculado como a soma sobre todos os dp[j][0] (sum_dp0 - target_dp0), o que já inclui dp[i-1][0]. Assim dp[i-1][0] é somado duas vezes quando o segmento correspondente não soma a K. Exemplo simples: N=1, A=[1], K=3. Resultado correto = 1, o código atual produz 2. Essa falha torna os resultados incorretos e bloqueia a entrega.

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: Variável/estrutura não utilizada: ps_to_dp1 é mantido e atualizado, mas nunca é consultado em qualquer transição. Isso adiciona complexidade desnecessária e confunde a responsabilidade do módulo.

- severity: warning  
  file: solution.py  
  layer: completude  
  description: Não foram incluídos arquivos de teste automatizados (unit tests) cobrindo casos simples e limites (p.ex. N=1, todos zeros, mix de positivos/negativos). Entregar testes aumentaria confiança e ajudaria a detectar regressões.

## Resumo
A implementação visa otimizar a DP para O(N) usando mapas de soma prefixa, o que é adequado para o requisito de desempenho. Porém existe um bug lógico crítico na forma como as contribuições anteriores são agregadas: o código soma explicitamente dp[i-1] (como "no_cut") e também soma uma agregação que já contém dp[i-1], causando dupla contagem e resultados incorretos. Essa falha é bloqueante. Além disso há uma estrutura (ps_to_dp1) atualizada mas nunca lida, e não há testes fornecidos. Recomenda-se corrigir as transições para as fórmulas corretas:
- dp[i][0] = (sum_dp0 - target_dp0) % MOD
- dp[i][1] = (sum_dp1 + target_dp0) % MOD
removendo a adição separada de dp[i-1], e então validar com testes de borda e os exemplos do enunciado.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "Lógica de transição incorreta — dupla contagem ao computar dp[i][0]; o código soma dp[i-1] e também uma agregação que já inclui dp[i-1], resultando em contagens erradas (ex.: N=1, A=[1], K=3 produz 2 em vez de 1).",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Estrutura ps_to_dp1 é atualizada mas nunca utilizada; código tem complexidade/estado desnecessário.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues testes automatizados (unit tests) cobrindo casos básicos e limites; acrescentar testes ajuda a detectar esse tipo de regressão.",
      "file": "solution.py",
      "layer": "completude"
    }
  ]
}
```