## Status: BLOQUEADO

## Issues

- CRITICAL — solution.py — camada: corretude/performance  
  Descrição: A solução atual calcula o custo da janela (sum |nums[i] - median|) recomputando por loops aninhados sempre que a janela muda. Isso resulta em complexidade quadrática ou pior (no pior caso O(n^2) ou mais), o que não satisfaz as restrições do problema (n até 10^5). Em entradas grandes a implementação irá exceder o tempo limite e, portanto, não atende ao critério CA-01 ("Produzir a saída correta para toda entrada válida"), porque embora logicamente correta para pequenos insumos, é inviável no limite declarado.

- MAJOR — solution.py — camada: arquitetura  
  Descrição: A implementação mistura a lógica principal com recomputação completa do custo para cada ajuste da janela em vez de usar estruturas/estratégias para custo incremental (prefix sums, soma acumulada, ou estrutura que mantenha soma à esquerda/direita do mediano). Isso torna o módulo ineficiente e de responsabilidade mal separada — falta uma função utilitária para atualizar custos incrementalmente ou o uso de prefix sums para consultas em O(1).

- WARNING — solution.py — camada: corretude (algorítmica/otimização do alvo)  
  Descrição: O autor usa o valor da mediana do intervalo como alvo (x) e minimiza a soma de distâncias L1, o que é conceitualmente correto para minimizar operações quando se pode aumentar ou diminuir elementos. No entanto, a forma atual de verificação/atualização do custo não explora essa propriedade de forma eficiente. Recomenda-se utilizar prefix sums e o índice do mediano para calcular custos em O(1) por ajuste de janela, ou adotar outra estratégia adequada (dois heaps balanceados, ou alinhar a janela ao elemento da direita com fórmula baseada em soma prefixada caso o problema aceitasse apenas incrementos).

- INFO — solution.py — camada: testes / completude  
  Descrição: Não há arquivos de teste no workspace fornecido. Nenhum caso unitário foi entregue para validar cenários pequenos, limites e casos de performance (por exemplo, n = 1e5 com distribuições adversas). Isso impede validar automaticamente se uma versão corrigida resolve tanto corretude quanto desempenho. Registrar como falta de completude (CA-01/CA-02 não comprováveis automaticamente sem testes).

## Resumo

O código implementa uma abordagem conceitualmente correta (minimizar soma de distâncias para a mediana) para o problema de maximizar a frequência, e passa em exemplos pequenos — por isso a correção lógica está alinhada com a ideia correta. Entretanto, a implementação atual recalcula custos por iteração de maneira ingênua, levando a complexidade quadrática que não é aceitável para n até 10^5; por isso a entrega não atende integralmente ao critério CA-01 e deve ser considerada bloqueante. Recomendo reimplementar o controle de custo usando prefix sums (precompute prefix sum dos nums ordenados e, para cada right, buscar o menor left tal que custo <= k; custo pode ser obtido em O(1) usando prefixes e a posição do mediano) ou usar uma estrutura de dois heaps/contadores para manter soma dos elementos à esquerda e à direita do mediano e atualizar custo de forma incrementa. Além disso, incluir um conjunto de testes automatizados cobrindo: exemplos dados, casos triviais, casos com todos elementos iguais, e um caso de grande escala para garantir desempenho.