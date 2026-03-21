# 🛠️ Documentação das Tools do Coder Agent

Este documento descreve as tools implementadas para compor o pipeline do agente autônomo de codificação e versionamento Git.

---

## Visão geral do pipeline

```
Solicitação do usuário
        ↓
tool_criar_arquivo.py   → cria ou sobrescreve arquivos no disco
        ↓
tool_git_add            → adiciona os arquivos ao staging area
        ↓
trava_seguranca         → valida se há alterações staged e gera o diff
        ↓
Aprovação humana        → usuário revisa e autoriza o commit
        ↓
tool_git_commit         → executa o commit no repositório
        ↓
tool_git_checkout       → troca ou cria branches conforme necessário
```

---

## 📄 `coder_agent.py`

Contém todas as tools de manipulação Git e a trava de segurança para aprovação humana.

---

### `tool_git_add`

Responsável por **adicionar arquivos ao staging area** do Git.

#### Parâmetros

| Parâmetro  | Tipo  | Descrição                                                                 |
|------------|-------|---------------------------------------------------------------------------|
| `arquivos` | `str` | Arquivos a adicionar, separados por espaço. String vazia executa `git add .` |

#### Retorno

| Campo        | Tipo   | Descrição                          |
|--------------|--------|------------------------------------|
| `sucesso`    | `bool` | `True` se o comando foi executado com sucesso |
| `stdout`     | `str`  | Saída padrão do comando Git        |
| `stderr`     | `str`  | Saída de erro do comando Git       |
| `returncode` | `int`  | Código de retorno do processo      |

#### Exemplo

```python
result = tool_git_add("src/utils/helpers.py")
# → {"sucesso": True, "stdout": "", "stderr": "", "returncode": 0}

result = tool_git_add("a.py b.py")
# → {"sucesso": True, ...}

result = tool_git_add("")   # equivale a git add .
# → {"sucesso": True, ...}
```

---

### `trava_seguranca_git_commit`

Responsável por **validar se há alterações staged** e retornar o diff completo para análise antes do commit.

#### Parâmetros

| Parâmetro  | Tipo  | Descrição                          |
|------------|-------|------------------------------------|
| `mensagem` | `str` | Mensagem de commit sugerida pelo agente |

#### Retorno — com alterações staged

| Campo      | Tipo   | Descrição                          |
|------------|--------|------------------------------------|
| `sucesso`  | `bool` | `True` — há alterações para commitar |
| `mensagem` | `str`  | Mensagem de commit recebida        |
| `diff`     | `str`  | Diff completo das alterações staged |

#### Retorno — sem alterações staged

| Campo      | Tipo   | Descrição                          |
|------------|--------|------------------------------------|
| `sucesso`  | `bool` | `False` — nada para commitar       |
| `mensagem` | `str`  | `"Nada para commitar"`             |

#### Exemplo

```python
result = trava_seguranca_git_commit("feat: add helpers")
# Com staged:
# → {"sucesso": True, "mensagem": "feat: add helpers", "diff": "diff --git ..."}

# Sem staged:
# → {"sucesso": False, "mensagem": "Nada para commitar"}
```

---

### `tool_git_commit`

Responsável por **executar o commit** no repositório, mas apenas após a trava de segurança liberar.

#### Parâmetros

| Parâmetro  | Tipo  | Descrição              |
|------------|-------|------------------------|
| `mensagem` | `str` | Mensagem do commit     |

#### Retorno — sucesso

| Campo        | Tipo   | Descrição                          |
|--------------|--------|------------------------------------|
| `sucesso`    | `bool` | `True` se o commit foi realizado   |
| `stdout`     | `str`  | Saída do comando Git               |
| `stderr`     | `str`  | Saída de erro                      |
| `returncode` | `int`  | Código de retorno                  |

#### Retorno — bloqueado pela trava

| Campo      | Tipo   | Descrição                              |
|------------|--------|----------------------------------------|
| `sucesso`  | `bool` | `False`                                |
| `mensagem` | `str`  | Motivo do bloqueio (sem staged, etc.)  |

#### Exemplo

```python
# Com arquivos staged:
result = tool_git_commit("feat: add helpers module")
# → {"sucesso": True, "stdout": "[main abc1234] feat: add helpers module", ...}

# Sem arquivos staged:
result = tool_git_commit("feat: tentativa")
# → {"sucesso": False, "mensagem": "Nada para commitar"}
```

---

### `tool_git_checkout`

Responsável por **trocar ou criar branches** no repositório.

#### Parâmetros

| Parâmetro | Tipo   | Descrição                                          |
|-----------|--------|----------------------------------------------------|
| `branch`  | `str`  | Nome da branch de destino                          |
| `criar`   | `bool` | Se `True`, cria a branch antes de trocar. Padrão: `False` |

#### Retorno

| Campo        | Tipo    | Descrição                          |
|--------------|---------|------------------------------------|
| `sucesso`    | `bool`  | `True` se o checkout foi realizado |
| `comando`    | `list`  | Comando exato executado            |
| `stdout`     | `str`   | Saída do comando Git               |
| `stderr`     | `str`   | Saída de erro                      |
| `returncode` | `int`   | Código de retorno                  |

#### Exemplo

```python
# Trocar para branch existente:
result = tool_git_checkout("develop")
# → {"sucesso": True, "comando": ["git", "checkout", "develop"], ...}

# Criar e trocar para nova branch:
result = tool_git_checkout("feature/nova-funcionalidade", criar=True)
# → {"sucesso": True, "comando": ["git", "checkout", "-b", "feature/nova-funcionalidade"], ...}

# Branch inexistente sem criar=True:
result = tool_git_checkout("branch-fantasma")
# → {"sucesso": False, "stderr": "error: pathspec ...", ...}
```

---

## 📄 `tool_criar_arquivo.py`

Responsável por **criar ou sobrescrever arquivos no disco** com validações de segurança.

### Validações de segurança

| Validação                  | Comportamento                                              |
|----------------------------|------------------------------------------------------------|
| Caminho vazio              | Rejeitado imediatamente                                    |
| Extensão não permitida     | Bloqueado — só extensões conhecidas são aceitas            |
| Diretório protegido        | Bloqueado — `.git`, `.venv`, `node_modules`, `__pycache__` |
| Diretórios intermediários  | Criados automaticamente se não existirem                   |

### Extensões permitidas

`.py` `.js` `.ts` `.html` `.css` `.json` `.md` `.txt` `.yaml` `.yml` `.toml`

### Parâmetros

| Parâmetro  | Tipo  | Descrição                                                        |
|------------|-------|------------------------------------------------------------------|
| `caminho`  | `str` | Caminho relativo ao diretório de trabalho (ex: `src/utils/helpers.py`) |
| `conteudo` | `str` | Conteúdo completo a ser escrito no arquivo                       |

### Retorno — sucesso

| Campo           | Tipo   | Descrição                              |
|-----------------|--------|----------------------------------------|
| `sucesso`       | `bool` | `True`                                 |
| `caminho`       | `str`  | Caminho absoluto do arquivo criado     |
| `bytes_escritos`| `int`  | Tamanho do conteúdo em bytes           |
| `erro`          | `None` | `None` em caso de sucesso              |

### Retorno — falha

| Campo    | Tipo   | Descrição                              |
|----------|--------|----------------------------------------|
| `sucesso`| `bool` | `False`                                |
| `erro`   | `str`  | Descrição do motivo da falha           |
| `caminho`| `str`  | Caminho que foi tentado                |

### Exemplo

```python
result = tool_criar_arquivo("src/utils/helpers.py", "def hello(): pass\n")
# → {"sucesso": True, "caminho": "/abs/path/src/utils/helpers.py", "bytes_escritos": 22, "erro": None}

result = tool_criar_arquivo("script.sh", "rm -rf /")
# → {"sucesso": False, "erro": "Extensão '.sh' não permitida. ...", "caminho": "script.sh"}

result = tool_criar_arquivo(".git/config", "conteudo")
# → {"sucesso": False, "erro": "Escrita não permitida em diretório protegido: {'.git'}", ...}
```

---

## 🔐 Fluxo de aprovação humana

O agente **não tem permissão de commitar de forma autônoma**. Antes de invocar `tool_git_commit`, o agente deve obrigatoriamente apresentar um resumo ao supervisor e aguardar autorização explícita.

### Fluxo completo

```
Agente cria arquivo       → tool_criar_arquivo(caminho, conteudo)
        ↓
Agente adiciona ao stage  → tool_git_add(arquivos)
        ↓
Agente apresenta resumo ao usuário:
  ┌─────────────────────────────────────────┐
  │ 📋 Resumo do commit para aprovação:     │
  │ - Mensagem: feat: add helpers module    │
  │ - Arquivos: src/utils/helpers.py        │
  │ - Motivo: criação do módulo de helpers  │
  │                                         │
  │ ⚠️ Posso realizar o commit? (sim/não)   │
  └─────────────────────────────────────────┘
        ↓
Usuário responde "sim"    → tool_git_commit(mensagem)  ✅
Usuário responde "não"    → agente corrige e reapresenta para aprovação 🔄
```

### Cenários

| Cenário   | Resposta do usuário | Ação do agente                                              |
|-----------|---------------------|-------------------------------------------------------------|
| Aprovado  | `"sim"`             | Executa `tool_git_commit` e conclui a tarefa               |
| Rejeitado | `"não"` + feedback  | Corrige o código, refaz `tool_git_add` e pede nova aprovação |

---

## 🧪 Testes unitários

Os testes cobrem todas as tools e são executados com `pytest`.

### Estrutura dos arquivos de teste

| Arquivo                      | Testes | O que cobre                                      |
|------------------------------|--------|--------------------------------------------------|
| `test_coder_agent.py`        | 19     | `tool_git_add`, `trava_seguranca`, `tool_git_commit`, `tool_git_checkout` |
| `test_tool_criar_arquivo.py` | 17     | `tool_criar_arquivo` — fluxo feliz e segurança   |

### Como executar

```bash
# Ativa o ambiente virtual
source .venv/bin/activate

# Entra na pasta das tools
cd adk/src/agents/coder_agent/tools

# Roda todos os testes
pytest test_coder_agent.py test_tool_criar_arquivo.py -v
```

### Resultado esperado

```
36 passed in X.XXs
```

### Estratégia de isolamento

- Cada teste cria um **repositório Git temporário** via `tmp_path` do pytest
- O repositório é destruído automaticamente ao final do teste
- Nenhum teste depende do repositório real do projeto
- O `monkeypatch.chdir` garante que os comandos Git rodam no ambiente isolado

---

## 📦 Dependências

Nenhuma dependência externa além do próprio Python e Git instalado no sistema.

| Módulo       | Uso                                              |
|--------------|--------------------------------------------------|
| `subprocess` | Execução dos comandos Git via `subprocess.run`   |
| `pathlib`    | Manipulação de caminhos de arquivos              |
| `re`         | Sem uso direto — disponível para extensões       |
| `pytest`     | Execução dos testes unitários (dev dependency)   |
