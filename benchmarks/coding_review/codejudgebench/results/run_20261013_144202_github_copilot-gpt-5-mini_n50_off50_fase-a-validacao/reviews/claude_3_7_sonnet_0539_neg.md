## Status: BLOQUEADO

## Issues

- CRITICAL — solution.py — corretude  
  Descrição: A fórmula que calcula a soma das diferenças absolutas está incorreta: o código usa o inverso modular de 3 (pow(3, MOD-2, MOD)) ao invés do inverso modular de 6. A soma fechada correta para linhas é m*(m-1)*(m+1)/6 (e análoga para colunas). O uso de 1/3 em vez de 1/6 faz com que o resultado final fique multiplicado por 2, produzindo respostas erradas e quebrando o critério CA-01. Exemplo: m=2,n=2,k=2 deveria retornar 8; a implementação atual retorna 16.

- WARNING — solution.py — completude  
  Descrição: Não há arquivos de teste (unit tests) entregues no workspace. Não foram fornecidos testes automatizados cobrindo casos exemplo, limites e casos grandes (por exemplo m*n máximo). Isso impede verificação automática e regressão futura. (layer="completude", requisito CA-01/CA-02 endereçável por testes).

- WARNING — solution.py — arquitetura / performance  
  Descrição: A função comb(n, k) faz pow(i, MOD-2, MOD) dentro de um laço para cada i de 1..k, recalculando inversos repetidamente. Para os limites possíveis (até ~1e5) isso é funcional mas subótimo; uma abordagem com pré-cálculo de fatorial e inv-fatorial é mais eficiente e padrão em competições. Também o nome do parâmetro n em comb sombreia o nome global potencialmente confuso (não é bug funcional, só estilo). (layer="arquitetura")

- INFO — solution.py — robustez  
  Descrição: O código assume k >= 2 (condição do enunciado); caso fosse diferente, comb(m*n-2, k-2) poderia receber parâmetros inválidos — comb trata alguns casos, mas vale documentar a precondição. (layer="corretude")

## Resumo
A solução proposta segue a abordagem correta em alto nível (usar combinatória: multiplicar a soma das distâncias entre todas as células pela quantidade de formas de escolher os outros k-2 lugares), porém contém um erro matemático crítico: foi usado inv(3) ao invés de inv(6) ao calcular a soma fechada das diferenças por linha/coluna. Esse bug causa resultados incorretos (por exemplo dobra o valor esperado) e bloqueia a aceitação automática (status BLOQUEADO). Recomendações imediatas: corrigir a divisão por 6 (usar pow(6, MOD-2, MOD) ou inv6) ao computar row_sum/col_sum; opcionalmente, otimizar comb usando fatoriais/inversos pré-calculados; e adicionar uma suíte de testes cobrindo exemplos e limites.