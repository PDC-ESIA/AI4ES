# Requisito Funcional — Módulo Calculadora

## RF-CALC-001: Operações Aritméticas Básicas

**Módulo:** calculadora
**Criticidade:** alta
**Tipo:** RF

### Descrição

O módulo `calculadora.py` deve fornecer quatro operações aritméticas básicas:
`somar`, `subtrair`, `multiplicar` e `dividir`.

### Critérios de Aceitação

1. **Soma:** `somar(a, b)` deve retornar `a + b` para quaisquer dois números válidos.
2. **Subtração:** `subtrair(a, b)` deve retornar `a - b` para quaisquer dois números válidos.
3. **Multiplicação:** `multiplicar(a, b)` deve retornar `a * b` para quaisquer dois números válidos.
4. **Divisão:** `dividir(a, b)` deve retornar `a / b` quando `b ≠ 0`.
5. **Divisão por zero:** `dividir(a, 0)` deve lançar `ZeroDivisionError` com mensagem descritiva.
6. **Validação de tipo:** Todas as funções devem lançar `TypeError` quando qualquer operando não for numérico (ex: string, None, lista).
7. **Números negativos:** Todas as operações devem funcionar corretamente com números negativos.
8. **Números decimais (float):** Todas as operações devem funcionar corretamente com valores de ponto flutuante.
