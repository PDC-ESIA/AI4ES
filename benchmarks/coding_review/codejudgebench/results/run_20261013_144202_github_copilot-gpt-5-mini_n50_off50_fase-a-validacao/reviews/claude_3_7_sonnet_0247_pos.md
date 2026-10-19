## Status: APROVADO

## Issues

- warning — completude — solution.py  
  Descrição: Não foram entregues arquivos de teste automatizados (nenhum teste unitário / caso de validação no workspace). A DoD implicitamente pede correção do código; entretanto, critérios de aceite automatizáveis (CA-01, CA-02) não têm cobertura de testes entregues aqui. Recomenda-se adicionar um conjunto de testes que cubra os casos do enunciado (casos com todos ímpares, todos pares, alternância perfeita, valores negativos, n = 1, etc.).

- info — arquitetura — solution.py  
  Descrição: A implementação usa arrays dp_odd / dp_even de tamanho n — correto e simples, mas pode ser otimizada para O(1) memória mantendo apenas os valores para a posição anterior. Não é um problema funcional, apenas uma sugestão de otimização de memória.

- info — robustez de entrada — solution.py  
  Descrição: O parser usa input().strip() para ler linhas inteiras; isso funciona com entradas bem-formadas do judge, mas pode falhar/levantar ValueError se houver linhas em branco inesperadas no fluxo de entrada. Para maior robustez em ambientes que inserem linhas em branco, recomenda-se usar leitura por tokens (ex.: iter(sys.stdin.read().split())) — não é obrigatório para o judge padrão, só sugerido.

## Resumo

A correção entregue em solution.py implementa corretamente a lógica para encontrar a soma máxima de uma subarray não vazia cujos elementos alternam em paridade adjacente. A DP está correta: para cada posição o código considera iniciar uma nova subarray ou estender apenas a subarray que termina imediatamente antes com paridade oposta, o que respeita a restrição de contiguidade e alternância. Não foram encontrados erros de lógica nem casos críticos (nenhuma vulnerabilidade, possibilidade de retorno de -inf, ou violação das restrições de tempo/memória para os limites dados). As observações são apenas recomendações — falta de testes automatizados (warning) e sugestões de otimização/robustez (info). Com isso, a entrega é aprovada para prosseguir no pipeline.