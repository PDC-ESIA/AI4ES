## Status: BLOQUEADO

## Issues

- CRITICAL — solution.py / camada: corretude  
  Descrição: A função get_time_required usa a fórmula energy = factor * mid * (mid + 1) // 2 (soma triangular) para estimar a energia acumulada em mid minutos. Isso está conceitualmente incorreto para o enunciado: enquanto Bob não quebra um cadeado, a energia cresce linearmente a cada minuto adicionando sempre o mesmo valor (o fator atual). A energia após t minutos com fator f é f * t, portanto o tempo mínimo para atingir lock_energy é ceil(lock_energy / f). O uso da soma triangular leva a resultados errados e faz a função devolver tempos incorretos (violando CA-01 e CA-02). Exemplo: para um bloqueio que pede energy E e fator f, o código atual retorna t tal que f * t*(t+1)/2 >= E em vez do correto t = ceil(E / f).

- WARNING — solution.py / camada: completude  
  Descrição: Não foram adicionados arquivos de teste unitários no workspace que verifiquem os casos críticos (ex.: o caso informado que gerou TLE e outros casos com valores grandes e permutações). A ausência de testes automatizados impede comprovar regressões e correção da solução. (aceitação CA-01/CA-02 não verificáveis localmente sem testes)

- INFO — solution.py / camada: arquitetura  
  Descrição: Pequena redundância/import deslocado: o ambiente já pré-carrega muitos imports; o import itertools dentro do arquivo é desnecessário mas inofensivo. Também existe um bound arbitrário right = 2000000 na busca binária que não é justificado (além de não ser usado pois a fórmula está errada). Considerar usar cálculo direto (t = (lock_energy + factor - 1)//factor) para simplicidade e clareza.

## Resumo

O código entregue possui um defeito funcional crítico: a função que calcula o tempo necessário para romper cada cadeado usa uma soma triangular em vez de considerar que a energia cresce linearmente por minuto com o fator constante entre quebras. Esse erro faz a saída incorreta e impede atender aos critérios de aceite (inclusive a falha observada originalmente não está resolvida pela correção atual). Além disso faltam testes automatizados que comprovem a correção para os casos limites. Recomendações rápidas: substituir get_time_required por um cálculo direto t = ceil(lock_energy / factor) (ex.: (lock_energy + factor - 1) // factor), manter a enumeração de permutações (n <= 8 é factível) ou usar DP por bitmask para maior eficiência e adicionar conjuntos de testes que cubram os exemplos e casos limites. Depois da correção funcional e inclusão de testes, reavalie.