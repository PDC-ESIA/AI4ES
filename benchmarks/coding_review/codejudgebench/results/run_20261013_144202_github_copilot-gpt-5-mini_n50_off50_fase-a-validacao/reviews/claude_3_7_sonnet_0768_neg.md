## Status: BLOQUEADO

## Issues

- Severity: critical  
  File: solution.py — camada: corretude / arquitetura  
  Descrição: Algoritmo com complexidade O(N * M) (duplo loop: para cada r itera v de 0..M-1). Com N e M até 2×10^5 isso é impraticável e causa Time Limit Exceeded. A implementação atual falha em atender o critério de aceite CA-02 (eliminar a falha observada) e portanto não produz solução utilizável para os limites do problema. Recomenda-se implementar uma solução O(N log M) usando uma Fenwick Tree (BIT) ou segment tree para manter, entre os prefixos já vistos, (1) contagem por valor módulo e (2) soma dos valores módulo; para cada S_r calcular:
    contribution = cnt_prev * S_r - sum_prev + M * cnt_gt
  onde cnt_prev = número de prefixos anteriores, sum_prev = soma dos valores dos prefixos anteriores (em [0..M-1]), cnt_gt = número de prefixos anteriores com valor > S_r. Esse cálculo pode ser obtido com duas BITs (uma de contagens, outra de somas) em O(log M) por passo.

- Severity: warning  
  File: solution.py — camada: completude  
  Descrição: Não há arquivos de teste entregues no workspace (nenhum teste unitário/integração). O DoD explícito pede correção do TLE e verificação com entradas válidas; sem testes automatizados não é possível comprovar a correção. Adicionar testes (incluindo casos máximos) é necessário para validar a solução.

- Severity: info  
  File: solution.py — camada: arquitetura  
  Descrição: O código faz uso de um grande laço sobre todas as classes de resto v (0..M-1) dentro do loop sobre r; isso indica escolha de algoritmo equivocada (abordagem por frequência explícita) em vez de usar estrutura de dados para consultas acumuladas. Também há um bloco de imports no topo marcado como "AMBIENTE DE EXECUÇÃO" — conforme instrução, esse trecho é pré-carregado pela plataforma e deve ser ignorado na revisão da lógica; entretanto, o restante do módulo depende conceitualmente desse ambiente e não apresenta problemas de namespace.

## Resumo

A solução entregue calcula corretamente a fórmula por definição, mas o método usado (para cada r iterar todos os resíduos v de 0..M-1) tem complexidade O(N·M) e não escala para os limites do problema — por isso falha com Time Limit Exceeded. Isso viola diretamente o critério de aceite automatizável (CA-02). Para aprovar a entrega é necessário reimplementar a parte central usando uma estrutura de dados (por exemplo, duas Fenwick Trees: uma para contagens e outra para somas) para obter O(N log M) e adicionar testes que cubram casos pequenos e os limites máximos. Enquanto não for corrigido, o pipeline deve ficar bloqueado.