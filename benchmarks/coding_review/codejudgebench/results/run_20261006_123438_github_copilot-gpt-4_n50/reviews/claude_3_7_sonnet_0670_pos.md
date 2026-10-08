## Status: APROVADO

## Issues

### warning

- solution.py / arquitetura:
    - [ruff/E402] Module level import not at top of file — Importação de módulo (collections.deque) após comentários e bloco ambiente, não afeta funcionamento mas pode ser considerado desvio de estilo.
- solution.py / arquitetura:
    - Pequena duplicidade: o import de deque é feito explicitamente mesmo já disponível via bloco ambiente, mas não gera impacto funcional ou de desempenho.

## Resumo

O código entregue resolve o principal problema de desempenho da solução anterior, usando uma deque para registrar a posição do "rastro" do dragão somente até o comprimento N, tornando as operações de movimentação e consulta em tempo constante/amortizado. Não há problemas de lógica visíveis: cada parte consulta corretamente o histórico da cabeça ou, caso não tenha se movido, calcula sua posição inicial conforme esperado. Todos os artefatos necessários foram entregues — apenas solution.py é esperado. Pequenos desvios de estilo não impactam a execução. Não há testes explícitos entregues, mas como se trata de código para problema de competição e o core está correto e otimizado, a submissão está aprovada.