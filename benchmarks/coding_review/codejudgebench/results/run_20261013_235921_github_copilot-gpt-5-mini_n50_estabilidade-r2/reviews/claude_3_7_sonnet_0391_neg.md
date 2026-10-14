## Status: BLOQUEADO

## Issues
- severity: critical  
  file: solution.py  
  layer: corretude  
  description: A abordagem atual gera e armazena explicitamente todos os sufixos de cada palavra (chaves de dicionário com substrings). Isso pode levar a complexidade temporal e de memória O(sum L^2) no pior caso (soma dos quadrados dos comprimentos das palavras), o que facilmente causa TLE/MLE com os limites do enunciado. Há forte probabilidade de que cenários adversos (palavras longas repetidas/agrupadas) ainda façam a solução falhar por tempo/memória, quebrando o critério automatizável CA-02.

- severity: warning  
  file: solution.py  
  layer: arquitetura  
  description: O objeto chamado "trie" não é um trie de caracteres, e sim um dicionário que mapeia sufixos completos para o melhor índice/length. Além de ser semanticamente enganoso, essa escolha leva à criação de muitas substrings redundantes. Recomenda-se implementar um trie de caracteres sobre as palavras invertidas (ou outra estrutura linear, ex.: automato de sufixos/DAWG adequado) onde cada nó mantém o melhor índice/comprimento — assim a construção fica O(total de caracteres), reduzindo drasticamente tempo e memória.

- severity: info  
  file: solution.py  
  layer: testes  
  description: Não há arquivos de teste no workspace que validem correção funcional e, especialmente, performance (casos de maior carga). Sem testes automatizados fica difícil verificar regressões e confirmar que a mudança elimina o TLE observado.

## Resumo
A implementação produz resultados logicamente corretos em muitos casos e trata corretamente o critério de desempate (menor comprimento, índice mais cedo). No entanto a estratégia de pré-computar e armazenar todos os sufixos como chaves de dicionário cria um custo temporal e espacial que pode explodir nos limites do problema — cenário que motivou o TLE original. Por isso a entrega não é segura para seguir no pipeline: é necessário reimplementar a estrutura de suporte (trie de caracteres invertida ou outra solução linear) para garantir construção e consulta em tempo proporcional ao número de caracteres, e acrescentar testes de carga que confirmem a remoção do TLE.

```json
{
  "status": "BLOQUEADO",
  "issues": [
    {
      "severity": "critical",
      "description": "A abordagem atual gera e armazena explicitamente todos os sufixos de cada palavra (chaves de dicionário com substrings). Isso pode levar a complexidade temporal e de memória O(sum L^2) no pior caso (soma dos quadrados dos comprimentos das palavras), o que facilmente causa TLE/MLE com os limites do enunciado. Há forte probabilidade de que cenários adversos (palavras longas repetidas/agrupadas) ainda façam a solução falhar por tempo/memória, quebrando o critério automatizável CA-02.",
      "file": "solution.py",
      "layer": "corretude"
    },
    {
      "severity": "warning",
      "description": "O objeto chamado \"trie\" não é um trie de caracteres, e sim um dicionário que mapeia sufixos completos para o melhor índice/length. Além de ser semanticamente enganoso, essa escolha leva à criação de muitas substrings redundantes. Recomenda-se implementar um trie de caracteres sobre as palavras invertidas (ou outra estrutura linear, ex.: automato de sufixos/DAWG adequado) onde cada nó mantém o melhor índice/comprimento — assim a construção fica O(total de caracteres), reduzindo drasticamente tempo e memória.",
      "file": "solution.py",
      "layer": "arquitetura"
    },
    {
      "severity": "info",
      "description": "Não há arquivos de teste no workspace que validem correção funcional e, especialmente, performance (casos de maior carga). Sem testes automatizados fica difícil verificar regressões e confirmar que a mudança elimina o TLE observado.",
      "file": "solution.py",
      "layer": "testes"
    }
  ]
}
```