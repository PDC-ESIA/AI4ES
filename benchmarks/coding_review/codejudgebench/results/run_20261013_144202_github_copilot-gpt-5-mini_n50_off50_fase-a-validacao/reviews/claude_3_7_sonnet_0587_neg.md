## Status: BLOQUEADO

## Issues

- critical — solution.py — camada: corretude  
  Descrição: A lógica que resolve conflitos de tempos iguais é incorreta e insuficiente. O código apenas adiciona M uma vez a alguns tempos (t2 e t3) sob condições estáticas, sem garantir que os três tempos finais sejam distintos. Há casos de entrada válidos em que o programa retorna um resultado incorreto. Exemplo mínimo (contraprova):  
  Entrada:
  M = 1  
  S1 = "0"  
  S2 = "0"  
  S3 = "0"  
  Saída esperada: 2 (tempos distintos 0,1,2)  
  Saída do programa atual: 1  
  Por isso a solução produz respostas inválidas para instâncias legais do problema.

- warning — solution.py — camada: testes / completude  
  Descrição: Não há arquivos de teste no workspace. Não existem testes automatizados cobrindo casos críticos (p.ex. M=1, casos com múltiplas ocorrências por fita, colisões entre mais de dois tempos). A ausência de testes impede detectar regressões e o bug acima antes da entrega.

- info — solution.py — camada: arquitetura  
  Descrição: A abordagem atual itera todas as combinações de posições nas três fitas (até M^3 iterações) — isso é aceitável para M ≤ 100, mas o ajuste de conflitos é ad-hoc. Recomenda-se uma estratégia clara e comprovavelmente correta (ex.: tentar deslocamentos por múltiplos de M de 0..2 para cada escolha de restos, ou usar uma construção de contagem/atribuição por dígito). Também há muitos imports no topo porque o ambiente pré-carrega bibliotecas — isso é apenas informativo (conforme enunciado).

## Resumo

A implementação entregue não resolve corretamente a restrição de "apertar no máximo um botão por segundo": sua correção parcial para evitar tempos iguais não garante distinção entre os três tempos em todos os casos. Há um contraexemplo simples (M=1 com todas as fitas iguais) que produz saída incorreta, logo a solução está com bug funcional e não atende ao critério de aceite automatizável. Recomendo bloquear a entrega até corrigir a lógica de resolução de conflitos de tempos (ver sugestões abaixo) e adicionar testes unitários cobrindo casos limites (M=1, repetição completa, múltiplas ocorrências por fita, casos onde todas as fitas têm o mesmo padrão).

Sugestões de correção (práticas e simples)
- Solução simples e correta (modificação mínima): para cada dígito d:
  - obter listas pos1, pos2, pos3 (índices onde aparece d);
  - para cada combinação p1 ∈ pos1, p2 ∈ pos2, p3 ∈ pos3:
    - tentar todos os deslocamentos a,b,c ∈ {0,1,2} e construir t1 = p1 + a*M, t2 = p2 + b*M, t3 = p3 + c*M;
    - aceitar apenas tríades com tempos distintos; manter o mínimo de max(t1,t2,t3).
  - tomar o mínimo global entre dígitos.
  Justificativa: com 3 fitas, multiplicadores 0..2 são suficientes para separar por resto; é exaustivo e simples de provar correto. Complexidade máxima (~M^3 * 27) é aceitável para M ≤ 100, embora seja o pior caso pesado; funciona dentro dos limites típicos de competições.

- Alternativa mais eficiente: para cada dígito, para cada resto r em 0..M-1, construir quantos reels têm esse dígito naquele resto; então usar uma estratégia de atribuição/empacotamento de tempos por restos (ou uma busca/guloso comprovada). Essa abordagem exige cuidado para tratar múltiplas ocorrências por fita corretamente, mas pode levar a O(M * #dígitos) em vez de O(M^3).

Depois da correção, adicione testes unitários cobrindo:
- M=1 com todas as fitas iguais,
- casos onde cada fita tem o dígito em várias posições que colidem,
- os samples do enunciado,
- casos aleatórios para validar estabilidade.

Com o bug de corretude presente, a entrega atual não pode ser aprovada.