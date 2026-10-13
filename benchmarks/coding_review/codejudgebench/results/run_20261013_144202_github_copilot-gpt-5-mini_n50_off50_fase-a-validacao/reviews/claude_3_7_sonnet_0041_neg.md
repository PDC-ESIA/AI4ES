## Status: BLOQUEADO

## Issues

- Severidade: critical  
  Arquivo: solution.py — Camada: corretude  
  Descrição: A implementação calcula o custo para cada palíndrome iterando por toda a lista nums em cada iteração (cost = sum(abs(num - p) for num in nums)). Há ~110k palíndromos possíveis (< 10^9) e n pode chegar a 10^5, então o algoritmo tem complexidade O(m * n) ≈ 1e10 ops no pior caso e TLE em entradas grandes. Isso faz com que a solução não cumpra o critério CA-02 (remover Time Limit Exceeded) — a correção é necessária para ser considerada válida.

- Severidade: major  
  Arquivo: solution.py — Camada: arquitetura  
  Descrição: A escolha algorítmica não explora propriedades matemáticas óbvias do problema (norma L1). A soma de distâncias |nums[i] - p| é minimizada por qualquer mediana dos nums; portanto não é necessário testar todos os palíndromos: basta escolher o(s) palíndromo(s) mais próximos da mediana. Alternativamente, ao testar múltiplos candidatos, o custo por candidato pode ser computado em O(log n) com prefix sums+binary search em vez de O(n). A implementação atual falha em aplicar essas estratégias eficientes.

- Severidade: warning  
  Arquivo: workspace (expectativa de entrega) — Camada: completude / testes  
  Descrição: Não foram incluídos arquivos de teste unitários no workspace para validar correção e desempenho (por exemplo, testes com arrays grandes que reproduzam TLE). Embora os testes não sejam estritamente obrigatórios pela tarefa, a ausência dificulta confirmar automaticamente os critérios CA-01/CA-02.

## Resumo

O código em solution.py produz a resposta correta em entradas pequenas, mas ainda é inaceitavelmente lento para os limites do problema porque computa a soma absoluta para cada palíndrome gerado (complexidade O(number_of_palindromes * n)). Para corrigir basta aplicar uma abordagem eficiente: calcular a mediana de nums e buscar o palíndrome mais próximo (ou os candidatos imediatos) — testar apenas esses poucos palíndromos reduz a complexidade para O(n log n) para ordenar + O(n) para calcular custos em poucos candidatos; ou, se preferir testar todos os palíndromos, calcular custo por palíndrome em O(log n) usando prefix sums e binary search, resultando em O(n log n + m log n) total. Enquanto não for aplicada uma dessas otimizações, a solução continuará a falhar em entradas grandes e não cumpre os critérios de aceite; por isso o status é BLOQUEADO.

Sugestões de correção (resumo prático)
- Ordenar nums e obter a mediana (se n par, use média ou considere ambos medians).  
- Gerar e ordenar a lista de palíndromos (a geração atual é aceitável; ~110k elementos).  
- Usar bisect para localizar a posição da mediana na lista de palíndromos e testar apenas os vizinhos imediatos (pos-1, pos, possivelmente pos+1). Calcular custo para esses poucos candidatos com uma única passagem por nums (ou com prefix sums se preferir).  
- Alternativa: construir prefix sums de nums ordenados e, para cada palíndrome, calcular custo em O(log n) via binary search, se quiser varrer todos os palíndromos.

Se desejar, eu posso produzir um patch completo aplicando uma das estratégias (ex.: mediana + busca binária em palíndromos) com complexidade e justificativa.