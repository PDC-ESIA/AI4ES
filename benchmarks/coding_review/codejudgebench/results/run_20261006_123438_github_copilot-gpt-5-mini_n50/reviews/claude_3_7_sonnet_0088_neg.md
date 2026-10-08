## Status: BLOQUEADO

## Issues

- CRITICAL — solution.py / camada=corretude  
  Descrição: A construção do palíndromo consome incorretamente as frequências dos dígitos. No backtrack de can_form_k_palindrome o código sempre decrementa remaining_freq[digit] em 1 mesmo quando está colocando o mesmo dígito em duas posições espelhadas distintas (par de posições). Para posições não-middle (mirror_pos != pos) é necessário consumir 2 unidades do dígito; no código atual um único contador é reduzido, permitindo formar palíndromos que usam mais ocorrências do dígito do que as fornecidas pela frequência — isto leva a respostas incorretas (ex.: o caso n=3,k=5 falhou).  
  Localização aproximada: função can_form_k_palindrome -> backtrack, remoção/restauração de remaining_freq.

- CRITICAL — solution.py / camada=corretude  
  Descrição: Há uma inconsistência na interpretação dos índices de posição para calcular a contribuição modular (potências de 10). pow10_mod_k[i] foi definido como 10^i mod k, mas o backtrack trata pos==0 como a posição mais significativa (usa check de leading zero com pos==0). Ao mesmo tempo usa pow10_mod_k[pos] como se pos fosse o expoente correto — isto mistura MSB/LSB e produz soma modular errada. Correção: ao colocar um dígito na posição pos (contando do MSB como 0), a contribuição deve ser digit * 10^(n-1-pos). O espelho deve usar expoente pos (ou usar mapeamento explícito de expoentes).  
  Localização aproximada: can_form_k_palindrome -> backtrack, linhas que calculam new_val com pow10_mod_k[pos] e pow10_mod_k[mirror_pos].

- WARNING — solution.py / camada=completude  
  Descrição: Não existem arquivos de teste no workspace. Não há testes unitários cobrindo o exemplo(s) do enunciado nem casos de borda (n=1, n máximo, k várias bases). Entregas de correção algorítmica como esta devem incluir pelo menos testes que validem os exemplos e alguns casos limites para evitar regressões.  
  Recomendação: adicionar um arquivo de testes (pytest ou simples main) cobrindo os exemplos dados e casos adicionais.

- INFO — solution.py / camada=arquitetura  
  Descrição: A estratégia geral (enumerar todos os números por posições mantendo frequência de dígitos e verificar se a frequência pode formar algum palíndromo divisível por k) é válida para n <= 10, e memoização reduz estados. Contudo a separação de responsabilidades poderia melhorar: extrair a construção/verificação do palíndromo (incluindo cálculo modular) em funções menores e documentar claramente a convenção de índices (MSB vs LSB) para evitar a mistura vista. Não é bloqueante, mas melhora manutenção.

## Resumo

O código atual falha em dois pontos lógicos fundamentais dentro de can_form_k_palindrome: (1) consumo incorreto das ocorrências dos dígitos ao colocar pares espelhados (deve diminuir 2 unidades para um par, 1 unidade para o meio em n ímpar) e (2) uso incorreto das potências de 10 (confusão MSB/LSB ao indexar pow10_mod_k), o que torna a verificação de divisibilidade por k incorreta. Essas falhas explicam o Wrong Answer observado (ex.: [3,5]). Além disso, não há testes fornecidos para validar os exemplos ou casos de borda. Até que os dois defeitos lógicos sejam corrigidos e cobertos por testes, a entrega não pode ser aceita — por isto o status é BLOQUEADO.

Sugestões de correção imediata:
- Ao tentar colocar um dígito em pos:
  - calcule contribuições com pow10_mod_k[n-1-pos] para a posição atual (MSB-based) e pow10_mod_k[pos] para o espelho;
  - se mirror_pos != pos, só permita usar o dígito se remaining_freq[digit] >= 2 e então subtraia 2; se mirror_pos == pos subtraia 1.
- Restaure corretamente remaining_freq ao voltar (adicionando 2 ou 1 conforme o caso).
- Adicionar testes automatizados que verifiquem os exemplos do enunciado e vários casos de borda para evitar regressões futuras.