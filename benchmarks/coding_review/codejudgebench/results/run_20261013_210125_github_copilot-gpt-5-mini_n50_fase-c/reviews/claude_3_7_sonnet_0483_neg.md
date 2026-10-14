## Status: BLOQUEADO

## Issues
- critical — solution.py — corretude  
  Descrição: O código calcula reductions locais em `curr` mas NÃO atualiza `nums[i]` com o valor reduzido. Como o laço principal itera da direita para a esquerda e espera que reduções em posições mais à direita influenciem decisões para índices menores, a ausência da escrita de volta faz com que decisões subsequentes usem os valores originais em vez dos valores reduzidos. Isso leva a contagens de operações incorretas e a soluções incorretas para muitos casos (por exemplo, quando reduzir um elemento à direita torna necessário reduzir também o elemento à esquerda). Resultado: comportamento funcional incorreto (respostas erradas), portanto bloqueante.

- warning — solution.py — arquitetura  
  Descrição: A função greatest_proper_divisor faz fatoração por tentativa (itera até sqrt(n)) a cada vez que é chamada. Para limites máximos (nums.length = 1e5 e nums[i] até 1e6) isso pode funcionar mas é subótimo; uma abordagem mais robusta e escalável é pré-computar o menor fator primo (sieve de fatores) para todos valores até 1e6 (O(maxA) pré-processamento e O(1) por consulta). Recomendo trocar para um SPF-sieve para reduzir risco de TLE em casos adversos.

- warning — solution.py — completude / testes  
  Descrição: Não há arquivos de teste no workspace que verifiquem a correção do algoritmo para casos críticos (happy path, cadeias de dependência entre reduções, casos impossíveis, extremos). A ausência de testes automatizados dificulta validação e deve ser corrigida (criar unit tests que cubram os cenários do enunciado, inclusive o caso que levou ao TLE).

- info — solution.py — corretude (observação)  
  Descrição: A implementação de greatest_proper_divisor retorna 1 para números primos e para n==1, o que é consistente com a definição de divisor próprio; o código também detecta quando uma operação não altera o valor (new_curr == curr) e retorna -1 nessas situações, o que é conceitualmente correto quando o elemento ainda é maior que o alvo.

## Resumo
A implementação corrige a ineficiência extrema da versão anterior ao trocar a busca do maior divisor por tentativa até sqrt(n), e trata casos impossíveis ao detectar quando uma operação não altera o número. No entanto há um bug funcional crítico: as reduções computadas para uma posição não são escritas de volta em `nums`, portanto reduções em posições à direita não afetam verificações para índices menores. Isso produz respostas incorretas em casos onde múltiplos elementos precisam ser reduzidos em cadeia. Além disso, faltam testes automatizados e há oportunidade de otimização (pré-computar SPF) para evitar riscos de TLE em entradas adversas. Até que o bug de escrita em `nums` seja corrigido e testes adicionados, a entrega deve ser considerada bloqueada.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "O código calcula reductions locais em `curr` mas NÃO atualiza `nums[i]` com o valor reduzido. Como o laço principal itera da direita para a esquerda e espera que reduções em posições mais à direita influenciem decisões para índices menores, a ausência da escrita de volta faz com que decisões subsequentes usem os valores originais em vez dos valores reduzidos. Isso leva a contagens de operações incorretas e a soluções incorretas para muitos casos.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "A função greatest_proper_divisor faz fatoração por tentativa (itera até sqrt(n)) a cada chamada. É recomendável pré-computar o menor fator primo (sieve SPF) para todos os valores até 1e6 para obter consultas O(1) e evitar risco de TLE em entradas adversas.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não há arquivos de teste automatizados no workspace que validem os cenários críticos (happy path, cadeias de dependência entre reduções, casos impossíveis e limites). É necessário adicionar testes para garantir correção e prevenir regressões.",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "A função greatest_proper_divisor retorna 1 para números primos e para n==1, e o código detecta operações inócuas (new_curr == curr) retornando -1 quando apropriado — comportamento conceitualmente coerente.",
      "file": "solution.py",
      "layer": "corretude"
    }
  ]
}
```