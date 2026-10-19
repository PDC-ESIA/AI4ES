## Status: APROVADO

## Issues
- {"severity": "info", "file": "solution.py", "layer": "completude", "description": "Nenhum arquivo de teste/unitário foi fornecido no workspace. A task não exigia explicitamente testes, mas adicionar testes automatizados (casos limites e exemplos) ajudaria a evitar regressões."}
- {"severity": "info", "file": "solution.py", "layer": "arquitetura", "description": "Cálculo do binomial usa inverso modular por pow(...) dentro de um laço; isso é correto e suficiente para os limites (n ≤ 1e5), porém poderia ser levemente otimizado com pré-cálculo de fatoriais e inversos se desejado."}

## Resumo
A solução em solution.py implementa corretamente a fórmula combinatória fechada C(n-1, k) * m * (m-1)^(n-k-1) derivada do raciocínio sobre blocos (runs) e elimina o DP que causava TLE. Tratamentos de casos especiais (k == 0 e k == n-1) e bordas (n = 1, m = 1) estão corretos. A implementação usa inversos modulares via pow(..., MOD-2, MOD), que é seguro com MOD primo (1e9+7) e eficiente o bastante para os limites do problema. Não há problemas críticos ou bloqueantes. Recomenda-se, como melhoria opcional, adicionar testes automatizados e (se desejar micro-otimizar) usar pré-cálculo de fatoriais/inversos para reduzir chamadas a pow em laços longos.

```json
{
  "status": "APROVADO",
  "issues": [
    {"severity": "info", "description": "Nenhum arquivo de teste/unitário foi fornecido no workspace. A task não exigia explicitamente testes, mas adicionar testes automatizados (casos limites e exemplos) ajudaria a evitar regressões.", "file": "solution.py", "layer": "completude"},
    {"severity": "info", "description": "Cálculo do binomial usa inverso modular por pow(...) dentro de um laço; isso é correto e suficiente para os limites (n ≤ 1e5), porém poderia ser levemente otimizado com pré-cálculo de fatoriais e inversos se desejado.", "file": "solution.py", "layer": "arquitetura"}
  ]
}
```