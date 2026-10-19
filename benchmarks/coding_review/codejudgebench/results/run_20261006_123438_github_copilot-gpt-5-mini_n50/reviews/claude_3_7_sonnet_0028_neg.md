## Status: BLOQUEADO

## Issues

- CRITICAL — solution.py / camada: corretude  
  Descrição: Condição de remoção no laço principal está errada (off-by-one) e leva a indexação negativa em dp. A linha
  ```
  if i > freq * num:
      dp[i] = (dp[i] + dp[i - num] - dp[i - (freq + 1) * num]) % MOD
  ```
  deveria checar se i >= (freq + 1) * num antes de indexar dp[i - (freq + 1) * num]. No estado atual, quando i é menor que (freq + 1) * num mas maior que freq * num, o índice fica negativo (em Python passa a referenciar elementos do fim), produzindo resultados incorretos e comportamento indefinido. Isso provoca respostas erradas e viola CA-01.

- CRITICAL — solution.py / camada: corretude  
  Descrição: Tratamento de zeros está incorreto. O código multiplica o resultado por (zeros + 1):
  ```
  result = (result * (zeros + 1)) % MOD
  ```
  Cada zero pode ser incluído ou excluído independentemente, logo o fator correto é 2**zeros (mod MOD), não (zeros + 1). Uso atual gera contagens erradas sempre que zeros > 0 — falha direta nos critérios de aceitação.

- WARNING — solution.py / camada: corretude / arquitetura  
  Descrição: A atualização do vetor dp é feita in-place em ordem crescente de i. A fórmula usada assume uma certa semântica dos valores à direita (dp[i - num] e dp[i - (freq+1)*num]). Mesmo corrigindo o off-by-one, essa abordagem é delicada e fácil de tornar incorreta devido à dependência entre valores já atualizados e valores que deveriam corresponder ao estado anterior ao processamento do item atual. Recomenda-se usar uma cópia (dp_prev/ndp) ou a técnica por classes de resto com janela deslizante (sliding window) corretamente implementada para cada resto modulo num — isso torna a lógica clara e robusta. Atualmente há risco real de contagem incorreta por causa dessa ambiguidade.

- WARNING — solution.py / camada: completude  
  Descrição: Não há arquivos de teste entregues no workspace. Não existem testes unitários cobrindo casos básicos (ex.: ausência de zeros, presença de zeros, casos limite de i = (freq+1)*num, caso com muitos repetições de um mesmo valor). Ausência de testes impede validação automatizada de CA-01/CA-02 nesta revisão.

- INFO — solution.py / camada: arquitetura  
  Descrição: O código funciona como uma única função grande; separar a lógica de contagem de frequência e a atualização de dp em funções auxiliares aumentaria legibilidade e facilitará testes. (Sem impacto funcional imediato.)

## Resumo

A implementação atual contém dois erros funcionais graves que a tornam incorreta: (1) condição off-by-one que leva a indexação negativa em dp e resultados errados; (2) fator incorreto para o efeito de zeros — usa (zeros + 1) em vez de 2**zeros (mod MOD). Além disso, a técnica de atualização in-place do dp é frágil e propensa a erros; recomendo reescrever usando uma cópia dp_prev/ndp ou implementar corretamente a versão por restos com janela deslizante. Não há testes fornecidos para validar correções. Por esses motivos a entrega fica BLOQUEADA até corrigir os bugs críticos e adicionar testes que comprovem correção (incluindo casos com zeros e limites para as subtrações de janelas).  

Sugestões rápidas de correção:
- Substituir multiplicação por zeros por pow(2, zeros, MOD).
- Corrigir a condição para somente subtrair quando i >= (freq + 1) * num.
- Preferível: reimplementar a passagem por cada valor usando um dp_prev (cópia antes do item) ou a técnica por classes de resto com sliding window (como na solução padrão para bounded knapsack), garantindo que os índices usados na subtração referenciem o estado anterior ao processamento do elemento.