## Status: BLOQUEADO

## Issues
- critical — solution.py — corretude  
  Descrição: A implementação só ajusta o número de elementos estritamente menores que k (len(less_than_k)) para igualar n//2, mas isso não garante que o elemento mediano (posição m = n//2, 0-based) seja exatamente k. Cenários em que já existem exatamente m elementos < k e nenhum elemento igual a k fazem a função retornar 0 embora o mediano possa ser maior que k. Exemplo que quebra a solução: nums = [1,2,3,5,6,7], k = 4 (n=6, m=3). less_than_k tem tamanho 3 == n//2, o código retorna 0, porém o mediano (elemento na posição 3 em array ordenado) é 5 — resposta correta seria 1 (reduzir 5 para 4). Portanto o algoritmo está logicamente incorreto e produz respostas erradas em casos reais.

- warning — solution.py — arquitetura  
  Descrição: A solução opera apenas em contagens das três classes (<k, ==k, >k) e escolhe elementos a modificar sem considerar suas posições no array ordenado (i.e., não usa ordenação para localizar o índice mediano). Essa modelagem por contagem é insuficiente para garantir a propriedade do elemento mediano e torna o algoritmo frágil frente a distribuições onde o m-ésimo menor elemento não é = k embora contagens coincidam.

- warning — workspace — completude  
  Descrição: Não foram entregues arquivos de teste (unit tests) que verifiquem comportamento correto da função, incluindo casos limites e os cenários que causam a falha descrita (por exemplo arrays onde len(less_than_k) == n//2 mas nenhum elemento é igual a k). Arquivos de teste esperados não foram criados.

- warning — workspace — testes  
  Descrição: Ausência de testes automatizados no workspace. Sem testes, não há validação automatizada das correções e regressões (happy path e edge cases não cobertos).

## Resumo
A submissão altera corretamente a definição de target_less_k para n//2, mas o algoritmo permanece incorreto: ajustar apenas a contagem de elementos < k não garante que o elemento mediano (índice m = n//2) seja igual a k. Há ao menos um caso concreto que produz saída errada. Além disso, não há testes fornecidos para capturar esse e outros casos limites. Devido à falha lógica que pode gerar respostas incorretas, a entrega está BLOQUEADA — é necessária correção do algoritmo (recomendo ordenar o array e aplicar o padrão comprovado que soma as diferenças apenas nas metades relevantes relativas ao índice mediano) e inclusão de testes que cubram os cenários críticos.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A implementação só ajusta a contagem de elementos < k para n//2, mas isso não assegura que o elemento mediano (posição m = n//2) seja igual a k. Ex.: nums = [1,2,3,5,6,7], k = 4 → código retorna 0, resposta correta é 1.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Abordagem por contagem (<k, ==k, >k) ignora posições relativas no array ordenado; isso cria fragilidade lógica e viola a garantia necessária sobre o elemento mediano.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não foram entregues arquivos de teste que validem a função, incluindo casos limites e cenários que expõem a falha observada.",
      "file": "",
      "layer": "completude"
    },
    {
      "severity": "warning",
      "description": "Ausência de testes automatizados no workspace; falta cobertura de happy path e edge cases.",
      "file": "",
      "layer": "testes"
    }
  ]
}
```