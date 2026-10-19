## Status: APROVADO

## Issues
- { "severity": "warning", "file": "solution.py", "layer": "testes", "description": "Não há arquivos de teste no workspace. Recomenda-se adicionar testes unitários cobrindo os exemplos do enunciado e casos limites (p.ex. n=1, m=1, k=0; m=1 com k<n-1; valores grandes para n e k) para prevenir regressões." }
- { "severity": "info", "file": "solution.py", "layer": "arquitetura", "description": "Cálculo do coeficiente binomial usa a propriedade de simetria C(n-1,k)=C(n-1,n-1-k) e computa inversos modulares em cada iteração via pow(..., MOD-2, MOD). Isso está correto, porém a chamada repetida a pow poderia ser substituída por pré-cálculo de fatoriais/inversos se fosse necessário otimizar ainda mais para múltiplas consultas." }

## Resumo
A implementação entrega a fórmula combinatória correta e eficiente para o problema: answer = m * C(n-1, k) * (m-1)^(n-k-1) (com tratamento de casos borda), o que elimina o TLE da solução DP original. A solução trata corretamente os casos k=0 e k=n-1, usa inversos modulares com módulo primo 10^9+7 e tem complexidade O(min(k, n-1-k)). Não foram encontradas falhas críticas de corretude, segurança ou arquitetura. A única lacuna observada é a ausência de testes automatizados no workspace; isso não bloqueia a aceitação, mas recomenda-se adicionar testes para garantir regressões futuras não ocorram.

```json
{
  "status": "APROVADO",
  "issues": [
    {"severity": "warning", "description": "Não há arquivos de teste no workspace. Recomenda-se adicionar testes unitários cobrindo os exemplos do enunciado e casos limites (p.ex. n=1, m=1, k=0; m=1 com k<n-1; valores grandes para n e k) para prevenir regressões.", "file": "solution.py", "layer": "testes"},
    {"severity": "info", "description": "Cálculo do coeficiente binomial usa a propriedade de simetria C(n-1,k)=C(n-1,n-1-k) e computa inversos modulares em cada iteração via pow(..., MOD-2, MOD). Isso está correto, porém a chamada repetida a pow poderia ser substituída por pré-cálculo de fatoriais/inversos se fosse necessário otimizar ainda mais para múltiplas consultas.", "file": "solution.py", "layer": "arquitetura"}
  ]
}
```