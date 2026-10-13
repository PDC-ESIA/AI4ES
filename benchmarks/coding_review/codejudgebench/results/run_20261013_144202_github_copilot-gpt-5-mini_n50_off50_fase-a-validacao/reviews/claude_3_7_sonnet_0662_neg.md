## Status: BLOQUEADO

## Issues

- Severity: critical  
  File: solution.py — Camada: corretude  
  Descrição: A função count_trees calcula incorretamente k_min (menor k inteiro tal que A + kM >= L). A expressão usada
  para o caso não divisível
  ```
  if (L - A) % M == 0:
      k_min = (L - A) // M
  else:
      k_min = (L - A) // M + (1 if L - A > 0 else 0)
  ```
  produz resultados errados quando L - A é negativo e não divisível por M (ex.: L-A = -1, M = 3). Isso causa off-by-one e explica a falha observada (caso de teste fornecido). Correção segura e exata para M > 0: usar a identidade inteira
  k_min = ceil((L-A)/M) = -floor((A-L)/M), o que em Python com divisão inteira positiva M pode ser escrito como
  ```
  k_min = -((A - L) // M)
  ```
  Substituir a lógica atual por essa expressão corrige os casos com numeradores negativos sem recorrer a float. Exemplo: A=49465410047628331, M=469187475, L=-846698840563822393, R=636146833650564707 deverá então produzir 3160454516 (corrigindo o erro relatado).

- Severity: warning  
  File: solution.py — Camada: completude  
  Descrição: Não há arquivos de teste entregues juntamente com a implementação (nenhum test_*.py). A DoD pede apenas a correção em solution.py, mas critérios de aceite automatizáveis (CA-01, CA-02) existem e deveriam ter testes que verifiquem especialmente o caso extremo que falhou. Recomenda-se incluir testes que cobrem: casos com L-A negativo e positivo, divisibilidade exata, limites extremos de A, L, R (valores ~1e18), e o caso sample que falhou.

- Severity: info  
  File: solution.py — Camada: arquitetura  
  Descrição: O topo do arquivo contém novo import de math apesar do ambiente já ter carregado math; isso não causa erro funcional mas é redundante. A função tem responsabilidade única e é pequena — boa separação de concerns.

- Severity: warning  
  File: solution.py — Camada: testes  
  Descrição: Além da ausência de testes automatizados, não há validações ou comentários que demonstrem cobertura de casos de borda (por exemplo, L == R, L e R muito distantes, A muito negativo). Incluir testes unitários aumentará confiança e evitará regressões futuras.

## Resumo

O código entregue tem um erro de lógica na forma de computar k_min quando (L - A) é negativo e não divisível por M, o que produz contagens incorretas (off-by-one) em entradas grandes — isto é a causa direta do "wrong answer" relatado. A correção é simples e determinística: calcular k_min por meio de divisão inteira com a identidade k_min = -((A - L) // M) (para M > 0). Não foram fornecidos testes automatizados para validar a correção; isso deve ser adicionado. Enquanto a correção de lógica não for aplicada, a task fica BLOQUEADA.