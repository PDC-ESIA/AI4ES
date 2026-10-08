## Status: BLOQUEADO

## Issues

- Critical — corretude — solution.py  
  Descrição: Implementação atual usa uma heurística inválida (itera os valores ordenados em ordem crescente e soma aqueles estritamente maiores que o total corrente). Essa estratégia produz respostas incorretas (ex.: rewardValues = [1,6,4,3,2] produz 7 em vez de 11). A falha coincide com a “Falha observada” do enunciado: a ordem de seleção pode exigir pular alguns valores pequenos para permitir escolher valores maiores depois; a abordagem atual não contempla essa escolha e gera um resultado sub-ótimo. Resultado: não atende CA-01 / CA-02 (saída incorreta para entradas válidas).

- Warning — completude — workspace  
  Descrição: Não há arquivos de teste associados (nenhum teste unitário ou caso que valide a correção entregue). Para esta entrega a correção esperada era apenas solution.py, mas ausência de testes automatizados dificulta regressões futuras e validação local. (layer="completude")

- Info — arquitetura — solution.py  
  Descrição: O arquivo é pequeno e segue uma única responsabilidade, mas há comentário enganoso do coder afirmando que a ordenação é o problema quando, na verdade, o algoritmo subjacente (greedy ascending pick-if-greater) é incorreto. Não há separação entre lógica e possíveis componentes de teste (não obrigatório, apenas observação). (layer="arquitetura")

## Resumo

O arquivo solution.py contém a mesma heurística descrita no enunciado como defeituosa: ordenar ascendentemente e somar cada valor se for maior que o total acumulado. Essa abordagem falha em entradas como [1,6,4,3,2] — onde pular valores intermediários permite obter um total maior — e, portanto, não resolve o problema conforme os critérios de aceite. A ausência de testes automatizados impede validação imediata de correções. Recomendo bloquear a entrega até que a função seja reescrita para garantir corretude (por exemplo, uma solução baseada em busca/DFS com poda e memoização ou um DP adequado), e que sejam adicionados casos de teste que cubram o exemplo falho e outros casos limites.