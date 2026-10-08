## Status: BLOQUEADO

## Issues

- Critical — solution.py — corretude / performance  
  Descrição: A implementação constrói e consulta todos os sufixos como strings separadas (suffix = word[-j:] e suffix = query[-j:]). Cada slice cria uma nova string cujo custo é proporcional ao comprimento do sufixo, portanto a construção e a consulta têm custo quadrático por palavra no pior caso (somatório de 1+2+...+L por palavra). Com os limites do problema (comprimentos somados até 5·10^5 e palavras com até 5·10^3), isso facilmente causa Time Limit Exceeded e/ou uso excessivo de memória. O problema original relatado (TLE) não foi eliminado — a solução atual permanece vulnerável a TLE/MLE.  
  Impacto: impede o atendimento do critério de aceite CA-02 (eliminar a falha observada) e do CA-01 em instâncias grandes.  
  Sugestão de correção: evitar criar todos os sufixos por cópia. Inserir as palavras invertidas num trie (nós por caractere) ou usar hashing incremental/rolling-hash sem criar substrings; cada nó do trie deve armazenar o índice do candidato ótimo (menor comprimento, menor índice) para o sufixo representado pelo caminho até aquele nó. Assim a construção e as consultas ficam em tempo linear no total de caracteres (O(sum |words| + sum |queries|)) e sem cópias quadráticas.

- Warning — solution.py — arquitetura  
  Descrição: O objeto chamado `trie` não é um trie real, mas um dicionário que armazena todos os sufixos como chaves. Isso é funcional para pequenas entradas, mas conduz a alto acoplamento entre lógica e representação (muitos objetos string duplicados) e consome muita memória. A intenção original (uso de trie reverso) seria melhor servida por uma estrutura por caractere (nós aninhados) que evita duplicação de substrings.  
  Sugestão: usar estrutura de trie por caractere ou outra técnica que permita buscar o maior sufixo comum sem materializar todos os sufixos.

- Warning — solution.py — completude / testes  
  Descrição: Não há arquivos de teste entregues. O repositório não inclui testes unitários que verifiquem casos críticos (instâncias pequenas, casos com empate por comprimento, ausência de sufixo comum, entradas grandes para validar desempenho).  
  Impacto: torna impossível validar automaticamente os critérios de aceite no pipeline.  
  Sugestão: acrescentar testes unitários que cubram: (1) casos do enunciado, (2) empates por comprimento e por índice, (3) consultas sem sufixo comum, (4) casos com entradas grandes para verificar desempenho e memória.

## Resumo

A solução tenta resolver corretamente a regra de desempate (maior sufixo comum; em empate escolher palavra de menor comprimento e, em empate novamente, menor índice), e a lógica de escolha por sufixo e inicialização para sufixo vazio está conceitualmente correta. Porém a implementação atual materializa todos os sufixos como strings e gera todos os sufixos de cada consulta por slicing, o que gera complexidade e alocação quadráticas em cada palavra e culmina em Time Limit Exceeded / uso excessivo de memória para entradas grandes. Como isso viola o requisito de eliminar o TLE observado (CA-02) e impede que o código esteja utilizável no limite do problema, a entrega fica BLOQUEADA até a adoção de uma abordagem sem cópias quadráticas (ex.: trie reverso por caractere ou hashing incremental) e inclusão de testes que comprovem a correção e a performance.