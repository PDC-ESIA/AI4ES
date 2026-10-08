## Status: BLOQUEADO

## Issues

- [CRITICAL] solution.py — camada="corretude"
  - Descrição: A solução mantém um deque com N tuplas (uma por parte) e faz indexação direta positions[p-1] para responder queries do tipo 2. Em Python, deque suporta indexação, mas é O(k) — acesso aleatório é linear no deslocamento. Com N até 10^6 e Q até 2·10^5, isso pode tornar queries tipo 2 muito lentas e causar Time Limit Exceeded. Além disso, manter N tuples em memória é desnecessário: as posições que importam são apenas o histórico do caminho da cabeça (no máximo Q+1 posições).
  - Impacto: falha em atender os critérios de aceitação automáticos (produzir saída dentro dos limites de tempo/memória). Bloqueia a entrega até correção.
  - Sugestão de correção: não mantenha um array com N entradas atualizadas a cada movimento. Em vez disso:
    - Guarde apenas o histórico das posições da cabeça em uma lista heads (heads[0] = posição inicial da cabeça; cada movimento faz heads.append(nova_posição)). Então, no momento atual com m = len(heads)-1 movimentos:
      - se p-1 <= m: a posição da parte p é heads[m - (p-1)] (ou heads[len(heads)-p]),
      - caso contrário, a parte nunca foi "empurrada" pelo caminho da cabeça e permanece em sua posição inicial (p, 0).
    - Assim cada operação é O(1) e o armazenamento é O(Q) (≤ 2·10^5), evitando TLE/MLE.

- [WARNING] solution.py — camada="completude"
  - Descrição: Não há arquivos de teste automatizados no workspace (nenhum test_*.py foi entregue). Os critérios automáticos (CA-01/CA-02) exigem confirmação por execução; sem testes, a verificação automatizada não pode confiar na correção final.
  - Sugestão: adicionar testes unitários ou um script de integração que cobre:
    - casos simples (pequeno N, várias movimentações),
    - casos extremos (p = 1, p = N, zero movimentos, muitos movimentos),
    - casos de performance (N grande, Q grande com muitas queries tipo 2) para validar comportamento em tempo.

- [INFO] solution.py — camada="arquitetura"
  - Descrição: O arquivo contém a seção de pré-carregamento com muitos imports (isso foi indicado como parte do ambiente), e então importa deque novamente. Não há separação entre lógica e parsing (tudo em top-level script), o que é aceitável para solução de competição, mas limita testabilidade.
  - Sugestão: isolar a lógica principal em funções (por exemplo, process_queries(input_lines) -> outputs) para facilitar teste e leitura.

- [INFO] solution.py — camada="corretude"
  - Descrição: Há um aviso de análise estática (ruff/E402) sobre import não estar no topo — proveniente da seção de ambiente + import após o comentário. Não é funcionalmente crítico, mas pode ser limpo se desejar aderir a linters.

## Resumo

A implementação atual trabalha corretamente em termos de semântica (as atualizações com appendleft/pop modelam o deslocamento das partes), mas é inviável em escala por dois motivos principais: (1) indexação de deque é O(n), tornando queries tipo 2 potencialmente lentas; (2) manter N entradas completas é desnecessário e pode consumir memória excessiva. Essas falhas levam a Time Limit Exceeded nos testes de aceitação, portanto a entrega está bloqueada até a correção do algoritmo (usar histórico da cabeça ou outra estrutura que permita acesso em O(1) por query e armazenamento O(Q) em vez de O(N)). Além disso, não foram entregues testes automatizados — recomendo adicionar uma suíte mínima para evitar regressões e verificar a solução corrigida.