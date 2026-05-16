# Requisito Funcional — Módulo de Validação de Usuário

## RN-USUARIO-002: Regras de Validação de Senha

**Módulo:** autenticacao
**Criticidade:** alta
**Tipo:** RN

### Descrição

O sistema deve validar a senha do usuário durante o cadastro. A senha será considerada válida apenas se atender a todos os critérios de segurança simultaneamente.

### Regras de Negócio

1. **Tamanho Mínimo:** A senha deve ter no mínimo 8 caracteres de comprimento.
2. **Letra Maiúscula:** A senha deve conter pelo menos uma letra maiúscula (A-Z).
3. **Número:** A senha deve conter pelo menos um dígito numérico (0-9).
4. **Caractere Especial:** A senha deve conter pelo menos um dos seguintes caracteres especiais: `!`, `@`, `#`, `$`, `%`, `&`.

### Exceções

- Se a senha fornecida violar qualquer uma das regras acima, o sistema deve lançar uma exceção do tipo `ValueError`.
- A mensagem da exceção deve indicar claramente qual foi a primeira regra violada (ex: "A senha deve conter no mínimo 8 caracteres").
