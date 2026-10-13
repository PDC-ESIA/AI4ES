## Status: BLOQUEADO

## Issues

- [CRITICAL] solution.py / camada=corretude  
  Descrição: A lógica de programação dinâmica está incorreta e permite reutilizar o mesmo índice várias vezes e/ou não alcançar estados com operações aplicadas. Problemas concretos:
  - O DP usa apenas as contagens de operações (used_op1, used_op2) como estado, sem rastrear quais índices já foram processados; isso permite aplicar, em efeito, várias vezes a mesma operação a um mesmo índice ao combinar transições, violando a restrição "no máximo uma vez por índice por operação".
  - A direção das transições está invertida/incoerente: o código inicializa dp[0][0] = sum(nums) e tenta transitar de um estado (used_op1, used_op2) para (new_op1 = used_op1 - req_op1, new_op2 = used_op2 - req_op2). Partindo de (0,0) isso nunca alcança estados com used_op1>0 ou used_op2>0, então os estados úteis permanecem inacessíveis e o resultado é incorreto (por exemplo, retorna o somatório original para muitos testes). Esses dois pontos explicam o Wrong Answer observado (ex.: [2,4,3], k=3, op1=2, op2=1).
  Impacto: bloqueia a correção funcional do problema — a função não produz a resposta mínima conforme o enunciado.

- [MAJOR / arquitetura] solution.py / camada=arquitetura  
  Descrição: A construção do vetor `operations` com quatro entradas por índice (no-op, op1, op2, both) não é, por si só, errada, mas é usada com um DP que não discrimina índices, levando ao problema acima. Além disso:
  - A variável `n = len(nums)` é definida e nunca usada (ruído).
  - A abordagem atual mistura representação de operações com contagem global de uso de forma inconsistente — a separação correta seria um DP por índice (i.e., para cada índice escolher uma das 4 opções, acumulando custos e consumindo orçamentos de op1/op2).
  Impacto: dificulta a compreensão e manutenção; favorece introdução de bugs de corretude.

- [WARNING / completude] solution.py / camada=completude  
  Descrição: Não há arquivos de testes/unitários no workspace. Não foram entregues testes automatizados que verifiquem o caso observado nem outros casos relevantes (happy path e edge cases).  
  Impacto: falta de evidência de que a correção proposta passe em uma bateria de casos; isso obriga a reavaliação manual/execução de testes.

- [INFO / corretude] solution.py / camada=corretude  
  Descrição: A verificação das combinações "ambas operações" calcula candidate values razoavelmente (tenta ambas ordens e toma o mínimo) e respeita a condição "aplicar Op2 somente se valor >= k" na maior parte do cálculo. Contudo, isso não compensa as falhas estruturais do DP.  
  Impacto: explica porque partes do cálculo individual por índice estão corretas, mas a forma agregada é incorreta.

## Resumo

A implementação entrega uma tentativa de programação dinâmica, mas o estado do DP não considera os índices processados e as transições estão estruturadas de forma que estados com operações aplicadas ficam inacessíveis. Isso permite reutilizar um mesmo índice várias vezes e produz respostas incorretas (o exemplo fornecido falha). Como este é um erro funcional que impede que a função cumpra o requisito principal (retornar a soma mínima válida), a entrega está BLOQUEADA até que a estratégia seja corrigida. Recomendações para correção: implementar um DP por índice (por exemplo iterar índices e atualizar um dp[a][b] que representa custo mínimo acumulado usando a op1 = a e op2 = b até aquele índice), ou usar uma versão de mochila/DP 3D (índice × op1_usados × op2_usados) ou um DP 2D com roll-forward por índice, garantindo que cada índice contribua exatamente uma vez. Também adicionar testes que cubram o caso fornecido e casos limites (tamanho 1, zeros, op counts = 0, op counts = n).