## Status: BLOQUEADO

## Issues

- CRITICAL — arquivo: solution.py — camada: corretude  
  Descrição: Fórmula incorreta quando s == t e existem múltiplas rotações que produzem t (count > 1). O código multiplica a fórmula da diagonal (caso i == j) por `count`, o que é errado. A soma correta sobre todas as rotações que produzem t é:
  - total = diag + (count - 1) * offdiag  (quando a rotação 0 está entre as correspondências),
  - total = count * offdiag               (quando 0 não está entre as correspondências).
  O código atual usa `count * diag` no caso s == t, produzindo resultados errados para k > 1 em strings com simetria (ex.: strings periódicas). Exemplo (falha potencial): s = "aa...aa" (repetição) ou outras strings periódicas com count>1.

- CRITICAL — arquivo: solution.py — camada: arquitetura / performance  
  Descrição: Busca de todas as rotações que igualam t é feita com cortando fatias double_s[i:i+n] em um laço for i in range(n). Isso é O(n^2) no pior caso (comparações de strings de tamanho n repetidas n vezes) e vai falhar por TLE para n até 5·10^5. É necessário usar um algoritmo linear (ex.: KMP / prefix-function) para encontrar todas as ocorrências de t em s+s restritas a posições 0..n-1 em O(n).

- WARNING — arquivo: solution.py — camada: tests / completude  
  Descrição: Não há arquivos de teste entregues junto com a implementação. Não foram fornecidos testes unitários cobrindo casos essenciais (strings periódicas, k grande, limites de entrada). Recomenda-se incluir testes que validem: (i) strings sem correspondência; (ii) s == t com várias simetrias; (iii) s != t com correspondências múltiplas; (iv) grandes n para verificar performance.

- INFO — arquivo: solution.py — camada: estilo / manutenção  
  Descrição: Pequeno detalhe de legibilidade: a variável `l` foi usada em uma compreensão (sum(1 for l in ...)) — ruff/E741 sinalizou ambiguidade em nomes simples. Não é crítico, mas trocar para `shift` melhora clareza.

## Resumo

A implementação atual corrige parcialmente o problema anterior (agora conta múltiplas rotações), mas contém dois defeitos bloqueantes: (1) uma fórmula incorreta no caso em que s == t e há mais de uma rotação que produz t (leva a respostas erradas para k > 1); (2) busca ingênua de ocorrências por slicing, que é O(n^2) e vai TLE nas restrições do problema (n até 5·10^5). Para liberar o pipeline, corrija a fórmula somando corretamente os contribuintes diagonal e off-diagonal, e substitua a busca por uma versão O(n) (KMP / prefix-function) para encontrar todas as rotações equivalentes a t. Adicionalmente, adicionar testes que cubram casos periódicos e limites ajudará a evitar regressões.