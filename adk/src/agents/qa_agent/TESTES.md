# Testes Conversacionais do code_fix_agent

## 1. Objetivo

Validar o comportamento do agente code_fix_agent em interacoes reais de chatbot, onde o usuario envia mensagens em linguagem natural descrevendo erros, logs ou trechos de codigo com falha.

## 2. Criterios gerais de aprovacao

A resposta do agente e considerada aprovada quando:

- Identifica a causa raiz do erro com base no texto enviado.
- Usa as ferrementas e tem a linha de racicínio correta.
- Gera um prompt de correcao estruturado (com secoes PAPEL, ERRO REPORTADO, INSTRUCOES e FORMATO DE SAIDA ESPERADO) ou indica que não tem informações suficientes quando, na verdade possui.
- Nao inventa informacoes que nao estavam na mensagem do usuario.
- Responde em portugues, de forma objetiva.
- Cria documentos de teste funcionais

A resposta e reprovada quando:

- Ignora a mensagem e responde de forma generica.
- Gera um prompt vazio ou incompleto.
- Alucina dados (arquivo, linha, funcao) que nao foram mencionados.
- Quebra sem resposta em mensagens parcialmente validas.
- Cria documentos de teste que não refletem os requisitos

## 3. Matriz de Cenarios

### 3.1 Correção de código:

| ID | Cenario | Perfil do usuario | Ferramenta esperada |
|---|---|---|---|
| C01 | Erro em texto livre, sem codigo | Desenvolvedor descrevendo o problema | build_fix_prompt_from_error |
| C02 | Erro + codigo colado no chat | Desenvolvedor com trecho de codigo | build_fix_prompt_from_error |
| C03 | Traceback completo de pytest colado | CI/CD ou desenvolvedor apos rodar testes | build_fix_prompt_from_pytest |
| C04 | Traceback incompleto ou truncado | Log cortado, sem linha ou arquivo | build_fix_prompt_from_pytest com fallback |
| C05 | Mensagem ambigua sem erro claro | Usuario nao sabe descrever o problema | Agente pede mais informacoes |
| C06 | Erro em linguagem diferente de Python | JavaScript, TypeScript, etc. | build_fix_prompt_from_error com language correto |
| C07 | Mensagem com erro + testes falhando | Desenvolvedor envia erro e teste junto | build_fix_prompt_from_error com test_code |

### 3.2 Criação de testes:

| ID | Cenario | Perfil do usuario | Ferramenta esperada |
|---|---|---|---|
|||||


## 4. Casos de Teste Detalhados

---

## 4.1 Correção de código:

### TC-C01 — Erro descrito em texto livre

**Mensagem do usuario:**

""
Meu codigo esta dando NameError: name 'total' is not defined. Nao sei de onde vem esse 
erro.
"""

**Output esperado:**

O agente responde confirmando o tipo do erro e entrega um prompt de correcao estruturado contendo:

- secao ERRO REPORTADO com a descricao do NameError
- secao INSTRUCOES orientando o agente de codificacao a identificar onde total deveria ter sido definido
- nenhuma referencia a arquivo ou linha (nao foram fornecidos)

**Reprovado se:** o agente inventar um arquivo ou linha de origem.

---

### TC-C02 — Erro com codigo colado

**Mensagem do usuario:**

"""
Esse codigo esta quebrando com TypeError: unsupported operand type(s) for +: int and str:

```python
def calcular(a, b):
    return a + b

calcular(1, "dois")
```
"""

**Output esperado:**

O agente gera prompt com:

- secao ERRO REPORTADO com o TypeError
- secao CODIGO ORIGINAL com o trecho exato colado pelo usuario
- secao INSTRUCOES indicando revisao de tipos nos parametros de calcular

**Reprovado se:** a secao CODIGO ORIGINAL estiver ausente tendo o usuario enviado o codigo.

---

### TC-C03 — Traceback completo de pytest

**Mensagem do usuario:**

"""
Rodei os testes e apareceu isso:

```
FAILED tests/test_calc.py::test_divisao_zero - ZeroDivisionError: division by zero

def test_divisao_zero():
>       assert dividir(10, 0) == 0
E       ZeroDivisionError: division by zero

tests/test_calc.py:21: ZeroDivisionError
```
"""

**Output esperado:**

O agente usa `build_fix_prompt_from_pytest` e entrega prompt com:

- `Arquivo: tests/test_calc.py`
- `Linha: 21`
- `Funcao: test_divisao_zero`
- `Tipo: ZeroDivisionError`
- `Mensagem: division by zero`

**Reprovado se:** algum desses campos estiver como `unknown` tendo sido fornecido no traceback.

---

### TC-C04 — Traceback incompleto ou truncado

**Mensagem do usuario:**

"""
O teste falhou mas nao consigo ver o traceback completo, so apareceu isso:

```
AssertionError
```
"""

**Output esperado:**

O agente usa `build_fix_prompt_from_pytest` e gera prompt com os campos disponiveis, preenchendo os ausentes com `unknown` ou `N/A`. Nao quebra nem alucina dados.

**Reprovado se:** o agente recusa a responder ou inventa arquivo e linha.

---

### TC-C05 — Mensagem ambigua sem erro claro

**Mensagem do usuario:**

"""
meu codigo nao funciona
"""

**Output esperado:**

O agente solicita mais informacoes ao usuario, perguntando ao menos:

- qual e a mensagem de erro (se houver)
- qual trecho do codigo esta falhando

Nao deve gerar prompt de correcao sem dados suficientes.

**Reprovado se:** o agente gerar um prompt generico sem pedir mais contexto.

---

### TC-C06 — Erro em linguagem diferente de Python

**Mensagem do usuario:**

"""
Esse codigo JavaScript esta dando ReferenceError: soma is not defined:

```javascript
console.log(soma(2, 3));
```
"""

**Output esperado:**

O agente identifica a linguagem como JavaScript e gera prompt com:

- blocos de codigo marcados como `javascript`
- secao `PAPEL` referenciando JavaScript explicitamente

**Reprovado se:** o prompt usar blocos `python` para codigo JavaScript.


---

### TC-C07 — Erro com teste falhando enviados juntos

**Mensagem do usuario:**

"""
Tenho esse erro AssertionError no meu teste. O codigo e o teste sao esses:

Codigo:
```python
def soma(a, b):
    return a - b
```

Teste:
```python
def test_soma():
    assert soma(1, 2) == 3
```
"""

**Output esperado:**

O agente gera prompt com:

- secao `CODIGO ORIGINAL` com a funcao `soma`
- secao `TESTES QUE FALHARAM` com `test_soma`
- secao `INSTRUCOES` apontando que o operador esta errado

**Reprovado se:** qualquer uma das duas secoes de codigo estiver ausente.


---

## 4.2 Criação de testes:

---

## 5. Checklist de Execucao Manual

### 5.1 Correção de código

- [ ] C01: erro em texto livre sem codigo
- [ ] C02: erro com codigo colado
- [ ] C03: traceback completo de pytest
- [ ] C04: traceback incompleto
- [ ] C05: mensagem ambigua — agente pede mais contexto
- [ ] C06: erro em JavaScript
- [ ] C07: erro + codigo + teste juntos

### 5.2 Criação de testes


## 6. Criterio de Pronto

O agente esta pronto para uso quando todos os casos acima forem aprovados e nenhum caso de rejeicao for observado em duas rodadas consecutivas de teste manual.