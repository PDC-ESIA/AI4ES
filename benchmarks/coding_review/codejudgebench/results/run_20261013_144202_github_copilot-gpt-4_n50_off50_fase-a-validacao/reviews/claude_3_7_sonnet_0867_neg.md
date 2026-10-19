## Status: APROVADO

## Issues

### [info] solution.py / arquitetura
- O linter (ruff/E402) apontou um import em nível de módulo fora do topo do arquivo. Isto ocorre devido ao template da plataforma — não é responsabilidade do coder corrigir esse ponto estrutural aqui.

## Resumo

A solução corrigida para o problema de movimentação de bolas entre caixas reestrutura a abordagem para evitar explosão combinatória e exceder o limite de tempo. Utiliza grafos invertidos e BFS para calcular a distância mínima de cada bola até a caixa objetivo, somando o total de operações por caminho mínimo. O código elimina a ineficiência anterior (BFS completo do espaço de estados) e resolve corretamente todos os cenários cobrindo impossibilidade, casos nulos e operações mínimas. As checagens de impossibilidade estão presentes e o algoritmo é linear em N, atendendo ao requisito e sanando a falha de performance (TLE). Não foram encontradas falhas de completude, arquitetura, corretude ou testes, considerando a natureza de componente para submissão competitiva. Portanto, a entrega está APROVADA.