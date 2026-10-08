## Status: APROVADO

## Issues

- [info] solution.py / completude — O arquivo esperado (`solution.py`) foi entregue, implementando a função principal (`solve`) conforme a especificação.
- [info] solution.py / arquitetura — O código está segmentado corretamente, evitando loops ineficientes como no código original. Não há mistura de responsabilidades.
- [warning] solution.py / corretude — O linter detectou uma variável não utilizada na linha 41 (`N`), mas seu uso não é obrigatório fora da leitura do input neste contexto competitivo (sem relevância funcional).
- [info] solution.py / testes — Não há arquivos de teste explícitos, mas para problemas competitivos do tipo "CLI", testa-se pela execução direta; a função lê de `input()` e imprime no stdout seguindo o padrão do domínio.

## Resumo

A entrega corrige adequadamente a solução do problema proposto, otimizando a lógica para evitar loops excessivos e garantindo execução eficiente mesmo para entradas grandes, eliminando o erro de "Time Limit Exceeded". Todo o fluxo de execução foi encapsulado na função `solve()`, com leitura e processamento dos dados conforme descrito no enunciado, e o resultado é impresso. Não há testes automatizados, o que é típico para esse formato, e a única observação menor é a leitura desnecessária da variável `N`, que não compromete o funcionamento. A entrega pode ser aprovada.