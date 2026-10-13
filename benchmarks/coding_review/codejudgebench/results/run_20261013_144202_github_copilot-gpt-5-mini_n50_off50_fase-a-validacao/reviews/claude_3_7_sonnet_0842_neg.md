## Status: BLOQUEADO

## Issues

- CRITICAL — solution.py — camada=corretude  
  Descrição: A implementação atual está incorreta para o problema. Ela faz apenas:
  if s is palindrome return s else return s + s[:-1][::-1]
  isto é, sempre anexa o reverso de s excluindo o último caractere. Isto produz respostas maiores que o mínimo necessário em muitos casos. Exemplo concreto: para s = "AABA" a saída atual é "AABABAA" (tamanho 7) enquanto a resposta correta e mínima é "AABAA" (tamanho 5). A ideia correta é encontrar o maior sufixo de s que já seja palíndromo e apenas anexar o reverso do prefixo restante. Uma forma eficiente é usar prefix-function (KMP) sobre rev_s + '#' + s para obter o comprimento L do maior sufixo palindrômico; então devolver s + rev_s[:n-L]. Sem essa correção, a solução produz WA (não atende CA-01 e CA-02).

- WARNING — solution.py — camada=completude  
  Descrição: Não foram entregues testes automatizados (unit tests ou casos de exemplo). O enunciado e a falha observada (incluída na task) indicam entradas que deveriam ser usadas como regressão; pelo menos esses casos (por exemplo "ABC" e "AABA") deveriam ter sido codificados como testes para prevenir regressões.

- INFO — solution.py — camada=arquitetura  
  Descrição: O arquivo contém bloco grande de imports do "ambiente" (marcado como pré-carregado). A instrução da task pede para não considerar esse trecho como parte da solução — isso é meramente informativo. Fora isso, a função está num escopo claro e há uma única responsabilidade (entrada → processamento → saída), adequado para um utilitário CLI simples.

- WARNING — solution.py — camada=testes  
  Descrição: Não há casos de teste cobrindo caminhos críticos (happy path + edge cases) — por exemplo strings já palíndromas, strings com grande sufixo palindrômico, e casos pequenos (len=1, len grande). Testes determinísticos e independentes são necessários para validar correções.

## Resumo
A entrega contém um erro lógico bloqueante: a estratégia de formar o palíndromo está equivocada (anexação ingênua de s[:-1][::-1]), o que leva a resultados não mínimos e WA em várias entradas (ex.: "AABA"). Por isso o status é BLOQUEADO. Recomendo substituir a lógica por uma que encontre o maior sufixo palindrômico e anexe apenas o reverso do prefixo restante — uma implementação eficiente usa a prefix-function (KMP) sobre rev_s + '#' + s para obter o comprimento L do sufixo palindrômico e retorna s + rev_s[:n-L]. Além disso, acrescente testes que cobrem os exemplos do enunciado e casos de borda para evitar regressões.

Sugestão de correção (esboço de implementação segura):
- Calcular rev_s = s[::-1]
- Construir combined = rev_s + '#' + s
- Calcular prefix-function (lps) sobre combined
- L = lps[-1]
- Retornar s + rev_s[:len(s)-L]

Por favor aplique essa correção e adicione testes que cobrem:
- exemplos do enunciado (ABC → ABCBA, Z → Z, TREE → TREERT),
- o contraexemplo detectado (AABA → AABAA),
- casos pequenos (len=1) e casos onde s já é palíndromo.