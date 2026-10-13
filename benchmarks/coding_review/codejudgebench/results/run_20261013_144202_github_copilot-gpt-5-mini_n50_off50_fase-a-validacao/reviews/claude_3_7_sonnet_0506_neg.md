## Status: BLOQUEADO

## Issues

- critical — corretude — solution.py  
  Descrição: A implementação copia os arrays dp_count e dp_sum em cada iteração (old_count = dp_count.copy(), old_sum = dp_sum.copy()). Como max(nums) pode ser ~1e5 e len(nums) também ~1e5, isso torna a complexidade O(n * max_val) e provoca Time Limit Exceeded nas entradas grandes. Isso bloqueia a aceitação pois não atende ao critério CA-02 (eliminar a falha de TLE).  
  Sugestão: Não copie os arrays inteiros a cada iteração. Leia os valores antigos necessários em variáveis locais antes de atualizar dp_count[num] / dp_sum[num]. Por exemplo:
  - c_same = dp_count[num]; s_same = dp_sum[num]
  - c_minus = dp_count[num-1] if num>0 else 0; s_minus = dp_sum[num-1] if num>0 else 0
  - c_plus = dp_count[num+1] if num<max_val else 0; s_plus = dp_sum[num+1] if num<max_val else 0  
  Em seguida calcule os novos valores usando essas variáveis e escreva apenas dp_count[num] e dp_sum[num]. Isso reduz a complexidade para O(n + max_val).

- warning — arquitetura — solution.py  
  Descrição: O código usa arrays de tamanho max_val+1 (baseado em max(nums)). Isso é aceitável dentro dos limites do problema (max_val ≤ 1e5), porém torna a cópia inteira ainda mais custosa. Também há cópia desnecessária (old_count/old_sum) que indica acoplamento entre leitura e escrita do mesmo buffer.  
  Sugestão: além de evitar cópias por iteração, considere manter a iteração final para soma do resultado (sum(dp_sum)) — está OK. Alternativa: usar dicionários e atualizar em place lendo valores antigos em variáveis locais (útil quando max_val fosse muito maior ou muito esparso).

- warning — completude — solution.py  
  Descrição: Não há arquivos de teste entregues no workspace. Embora a task não obrigasse explicitamente testes, a ausência de testes automatizados impede verificação programática da correção e da regressão do problema de TLE.  
  Sugestão: adicione testes unitários cobrindo casos pequenos (ex.: exemplos do enunciado), casos com repetições, e um caso grande para medir performance. Isso ajuda a garantir que a correção elimina o TLE.

## Resumo
A solução funcionalmente modela corretamente o DP para contar e somar subsequências "good". No entanto, a implementação copia os vetores dp_count e dp_sum em cada iteração, gerando complexidade proibitiva (O(n * max_val)) que causa Time Limit Exceeded nas entradas grandes. Isso é um bloqueio crítico: é necessário refatorar para ler apenas os valores antigos necessários em variáveis locais e atualizar apenas as posições afetadas (ou outra estratégia equivalente) para reduzir a complexidade para O(n + max_val) e assim atender aos critérios de aceitação. Além disso, recomendo adicionar testes automatizados para prevenir regressões.