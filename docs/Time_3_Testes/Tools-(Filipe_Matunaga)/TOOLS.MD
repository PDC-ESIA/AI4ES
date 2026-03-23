# 🛠️ Documentação das Tools do Agente de Testes

Este documento descreve os dois arquivos de tools criados para compor o pipeline do agente inteligente de testes e correção de código.

---

## Visão geral do pipeline

```
log de erro
    ↓
log_parser_tool.py       → parseia e estrutura a entrada do erro
    ↓
code_fix_prompt_tool.py  → monta o prompt para o agente corretor
    ↓
Agente LLM               → analisa, corrige e retorna o código
```

---

## 📄 `log_parser_tool.py`

Responsável por **receber linhas de log brutas e transformá-las em dados estruturados**, prontos para serem consumidos pelo restante do pipeline.

### Formatos de log suportados

| Formato   | Exemplo                                                                 |
|-----------|-------------------------------------------------------------------------|
| Padrão    | `2024-01-15T10:23:45 ERROR [auth] mensagem`                             |
| Log4j     | `2024-01-15 10:23:45,123 ERROR com.app.Service - mensagem`              |
| Syslog    | `Jan 15 10:23:45 host sshd[1234]: mensagem`                             |
| Python    | `ERROR:modulo:mensagem`                                                 |
| Nginx     | `192.168.1.1 - - [15/Jan/2024:10:23:45 +0000] "GET /api HTTP/1.1" 404` |
| JSON      | `{"level":"ERROR","module":"auth","message":"falha"}`                   |
| Raw       | Qualquer linha não vazia (fallback)                                     |

### Estrutura de saída (`LogEntry`)

Cada linha parseada retorna um dicionário com os campos:

| Campo       | Descrição                                              |
|-------------|--------------------------------------------------------|
| `timestamp` | Data e hora do evento                                  |
| `level`     | Nível de severidade (DEBUG, INFO, WARN, ERROR, etc.)   |
| `module`    | Módulo ou serviço que gerou o log                      |
| `message`   | Mensagem descritiva do evento                          |
| `raw`       | Linha original sem alteração                           |
| `format`    | Formato detectado (padrao, log4j, syslog, python, etc.)|

### Tools disponíveis

#### `parse_log_line(line)`
Parseia uma única linha de log. Retorna um dicionário com os campos acima ou `None` se a linha estiver vazia.

#### `parse_log_lines(lines)`
Parseia uma lista de linhas. Linhas vazias são automaticamente ignoradas.

#### `parse_log_text(text)`
Parseia um bloco de texto com múltiplas linhas separadas por `\n`. Internamente chama `parse_log_lines`.

#### `filter_by_level(entries, level)`
Filtra uma lista de entradas pelo nível de severidade. Ex: retorna apenas entradas `ERROR`.

#### `filter_by_module(entries, module)`
Filtra uma lista de entradas pelo nome do módulo. Ex: retorna apenas entradas do módulo `auth`.

#### `execute_tool(tool_name, tool_input)`
Dispatcher central — executa qualquer tool pelo nome, sem precisar importá-la diretamente.

```python
from log_parser_tool import execute_tool

entry = execute_tool("parse_log_line", {
    "line": "2024-01-15T10:23:45 ERROR [auth] Failed to connect"
})
# → {"timestamp": "2024-01-15T10:23:45", "level": "ERROR", "module": "auth", ...}
```

---

## 📄 `code_fix_prompt_tool.py`

Responsável por **receber a descrição de um erro e montar um prompt estruturado** para ser enviado a um agente LLM de correção de código.

### Estrutura do prompt gerado

O prompt é dividido em seções bem delimitadas:

| Seção                    | Conteúdo                                                                 |
|--------------------------|--------------------------------------------------------------------------|
| 🎯 Papel                 | Define o papel do agente corretor e suas responsabilidades               |
| 🐛 Erro reportado        | A descrição do erro ou traceback                                         |
| 📄 Código original       | O código-fonte que precisa ser corrigido *(opcional)*                    |
| 🧪 Testes que falharam   | O código dos testes que falharam *(opcional)*                            |
| 📌 Contexto adicional    | Informações extras sobre o comportamento esperado *(opcional)*           |
| 📋 Instruções            | Regras que o agente deve seguir ao corrigir                              |
| 📤 Formato de saída      | Estrutura esperada da resposta: causa, linhas modificadas e código       |

### Formato de saída esperado pelo agente corretor

```
**Causa do erro:** <explicação curta>

**Linhas modificadas:**
**Código corrigido:**
\`\`\`python
<código corrigido aqui>
\`\`\`
```

### Tools disponíveis

#### `build_fix_prompt_from_error(error_description, original_code?, test_code?, context?, language?)`
Gera o prompt a partir de uma descrição textual do erro (mensagem de exceção ou traceback).

```python
from code_fix_prompt_tool import execute_tool

result = execute_tool("build_fix_prompt_from_error", {
    "error_description": "AssertionError: assert entry.module == 'auth'",
    "original_code": "def parse_python(raw): ...",
    "test_code": "def test_modulo(): assert entry.module == 'auth'",
})

print(result["prompt"])    # prompt pronto para enviar ao LLM
print(result["metadata"])  # informações sobre o que foi incluído
```

#### `build_fix_prompt_from_log_entry(log_entry, original_code?, test_code?, language?)`
Gera o prompt a partir de uma entrada de log já parseada — encadeia diretamente com `log_parser_tool`.

```python
from log_parser_tool import execute_tool as log_tool
from code_fix_prompt_tool import execute_tool as fix_tool

entry = log_tool("parse_log_line", {
    "line": "ERROR:auth:Failed to connect"
})

result = fix_tool("build_fix_prompt_from_log_entry", {
    "log_entry": entry,
    "original_code": "def parse_python(raw): ...",
})

print(result["prompt"])
```

#### `execute_tool(tool_name, tool_input)`
Dispatcher central — mesmo padrão do `log_parser_tool`.

---

## 🔗 Usando os dois arquivos juntos

```python
from log_parser_tool import execute_tool as log_tool
from code_fix_prompt_tool import execute_tool as fix_tool

# 1. Parseia o log de erro
entry = log_tool("parse_log_line", {
    "line": "2024-01-15T10:23:45 ERROR [auth] Failed to connect to DB"
})

# 2. Gera o prompt para o agente corretor
result = fix_tool("build_fix_prompt_from_log_entry", {
    "log_entry": entry,
    "original_code": "...",
    "test_code": "...",
})

# 3. Envia o prompt para o LLM (ex: API do Claude)
prompt = result["prompt"]
```

---

## 📦 Dependências

Nenhuma dependência externa. Ambos os arquivos usam apenas a biblioteca padrão do Python:

- `re` — expressões regulares para os parsers
- `json` — parse de logs em formato JSON
- `dataclasses` — estrutura `LogEntry`
- `typing` — anotações de tipo (`Optional`)
