## Status: BLOQUEADO

## Issues
- critical — solution.py — corretude  
  Descrição: Algoritmo atual é O(N * M): para cada prato principal o código varre todos os M acompanhamentos para determinar o máximo válido. Com N, M até 10^5 isso provoca Time Limit Exceeded em entradas grandes (o problema observado continua). O uso de um set para pares proibidos é correto para consultas O(1), mas não reduz a complexidade quadrática do loop aninhado; portanto a correção exigida pelo enunciado (eliminação do TLE) não foi alcançada.

- warning — solution.py — arquitetura  
  Descrição: A lógica calcula o máximo válido percorrendo todos os acompanhamentos por cada prato principal em vez de usar uma estratégia eficiente (ex.: ordenar os acompanhamentos por custo decrescente e, para cada prato principal, procurar o primeiro acompanhamento não proibido; ou usar uma heap de candidatos soma_max = a_i + b_j e, ao retirar um par proibido, enfileirar o próximo candidato para aquele prato). A estrutura de dados para pares proibidos (set de tuplas) é adequada para checagens, mas a estratégia de iteração é a causa da ineficiência.

- warning — solution.py — completude  
  Descrição: Não foram fornecidos testes automatizados no workspace para validar o comportamento (cenários pequenos, casos limites e o caso grande que causou TLE). Ausência de testes impede validação automatizada da correção.

- info — solution.py — testes  
  Descrição: Não há arquivo(s) de teste (ex.: test_solution.py). Recomenda-se incluir casos unitários que cubram: L = 0, L = NM-1 (apenas um par permitido), exemplos do enunciado e um caso grande com L limitado para checar performance.

## Resumo
O arquivo solution.py lê corretamente a entrada e usa um set para representar pares proibidos, o que é correto para consultas de pertencimento. No entanto, a implementação ainda itera sobre todos os M acompanhamentos para cada um dos N pratos principais (complexidade O(N*M)), o que causa Time Limit Exceeded nas instâncias maiores — exatamente o problema reportado inicialmente. Para aprovar a entrega é necessário alterar a estratégia de iteração para evitar a varredura completa por prato (por exemplo: ordenar acompanhamentos por custo decrescente e, para cada prato, testar os acompanhamentos do topo até achar um permitido; ou usar uma heap de candidatos soma máxima e avançar pelo próximo acompanhamento de um prato quando um par proibido for retirado). Também faltam testes automatizados que atestem correção funcional e desempenho.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "Algoritmo atual é O(N * M) e causa Time Limit Exceeded em entradas grandes — a solução não eliminou a falha observada.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "Lógica percorre todos os acompanhamentos por prato em vez de usar uma estratégia eficiente (ordenar acompanhamentos decrescentemente ou usar heap de candidatos). A representação dos pares proibidos está OK, mas o padrão de iteração é ineficiente.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "warning",
      "description": "Não foram fornecidos testes automatizados no workspace para validar correção e desempenho (casos do enunciado e casos limites).",
      "file": "solution.py",
      "layer": "completude"
    },
    {
      "severity": "info",
      "description": "Ausência de arquivo(s) de teste. Recomenda-se incluir testes cobrindo L=0, L=NM-1, exemplos do enunciado e um caso grande representativo.",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```