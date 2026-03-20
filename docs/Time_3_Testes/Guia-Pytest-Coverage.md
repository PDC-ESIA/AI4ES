# Guia de Pytest e Coverage — Do Zero ao Primeiro Teste

## 1. Os Dois Tipos de Pytest Neste Projeto

Antes de tudo, é importante entender que pytest aparece em **dois contextos diferentes** neste projeto:

| # | Tipo | O que testa | Quem escreve | Onde fica |
|---|---|---|---|---|
| 1 | **Pytest de produto** | O código da aplicação | O **Agente QA** gera automaticamente | `adk/src/agents/qa_agent/artefactsTests/` |
| 2 | **Pytest de eval** | O próprio **Agente QA** | O **desenvolvedor do time** escreve | `adk/src/agents/qa_agent/evalsTest/` |

Este guia cobre os fundamentos que se aplicam aos dois tipos.

---

## 2. O Que é Pytest?

Imagine que você tem uma função `somar(a, b)` e quer ter certeza de que ela sempre retorna o resultado correto — hoje, amanhã, e depois que outra pessoa modificar o código.

**Pytest** é uma ferramenta que automatiza essa verificação. Em vez de rodar o programa na mão e conferir o resultado, você escreve uma "prova" (o teste), e o pytest executa todas as provas de uma vez e diz quais passaram e quais falharam.

```
Sem pytest:                          Com pytest:
1. Rodar o programa                  1. Escrever o teste uma vez
2. Inserir dados manualmente         2. Rodar: pytest
3. Conferir o resultado              3. Ver: "5 passed in 0.12s" ✅
4. Repetir para cada cenário
5. Torcer para não esquecer nada
```

---

## 3. O Que é Coverage (Cobertura)?

Suponha que sua função tem um `if` e um `else`. Se você só testa o caminho do `if`, a parte do `else` pode ter um bug que nunca será descoberto.

**Coverage** mede: *"De todo o código que existe, qual porcentagem foi executada pelos testes?"*

```
Cobertura 100% → cada linha foi executada ao menos uma vez pelos testes
Cobertura   0% → nenhuma linha foi testada
Meta inicial → 70–80% já é um bom começo para projetos novos
```

Exemplo de relatório gerado no terminal:

```
Name                         Stmts   Miss  Cover
-------------------------------------------------
src/autenticacao.py             45      7    84%
src/pagamentos.py               32      0   100%
src/relatorios.py               18     18     0%   ← nunca testado!
-------------------------------------------------
TOTAL                           95     25    74%
```

---

## 4. Instalação

```bash
# Conforme README do projeto PDC-AI4SE:
cd adk/
pip install -e ".[dev]"

# Confirmar:
pytest --version
```

---

## 5. Estrutura de Pastas

```
adk/
│
├── src/
│   └── agents/
│       └── qa_agent/
│           ├── agent.py                ← definição do agente
|           ├── server_test.py          ← arquivo temporário para teste do agente
│           ├── tools/                  ← ferramentas do agente
│           ├── prompts/                ← prompts do agente
│           │
│           ├── artefactsTests/         ← pytest de PRODUTO (gerado pelo agente)
│           │   ├── __init__.py
│           │   ├── test_rf_001.py      ← gerado automaticamente
│           │   └── test_rf_002.py      ← gerado automaticamente
│           │
│           ├── evalsTest/              ← pytest de EVAL (escrito pelo time)
│           │   ├── __init__.py
│           │   └── test_qa_agent.py    ← você escreve este
│           │
│           └── doubt_artifacts/        ← Doubt_Artifact.md gerados em bloqueios
│
└── docs/
    └── Time3_Testes/
        ├── Protocolo-Supervisor-QA.md
        ├── Fluxo-TDD.md
        ├── Guia-Pytest-Coverage.md
        └── Pyproject_Toml.md          ← documentação que explica algumas dependências
```

> **Regra de ouro:** arquivos de teste devem começar com `test_`. Funções de teste também devem começar com `test_`. O pytest encontra automaticamente qualquer arquivo que siga esse padrão.

---

## 6. Seu Primeiro Teste — Passo a Passo

### O código que vamos testar

```python
# Exemplo genérico de função a ser testada
# [ PREENCHER: substitua pelo módulo real da sua aplicação ]

def validar_entrada(valor: str) -> bool:
    """
    Valida uma entrada.
    Retorna True se válida, False se inválida.
    Lança ValueError se a entrada estiver vazia.
    """
    if not valor:
        raise ValueError("O valor não pode ser vazio.")
    return len(valor) >= 3
```

### O teste correspondente

```python
# [ PREENCHER: caminho do arquivo de teste ]

import pytest
# [ PREENCHER: from <modulo> import <funcao> ]


# ─── CAMINHO FELIZ ────────────────────────────────────────────────────────────

def test_entrada_valida_retorna_true():
    """Entrada correta deve retornar True."""
    # [ PREENCHER: substitua pela chamada real ]
    resultado = validar_entrada("abc")
    assert resultado is True


# ─── ENTRADAS INVÁLIDAS ───────────────────────────────────────────────────────

def test_entrada_curta_retorna_false():
    """Entrada com menos de 3 caracteres deve ser inválida."""
    resultado = validar_entrada("ab")
    assert resultado is False


# ─── CASOS DE BORDA ───────────────────────────────────────────────────────────

def test_entrada_vazia_lanca_excecao():
    """Entrada vazia deve lançar ValueError."""
    with pytest.raises(ValueError) as info:
        validar_entrada("")
    assert "vazio" in str(info.value)
```

### Explicação dos conceitos usados

| Conceito | O que faz |
|---|---|
| `def test_nome()` | Define um teste. O nome descreve exatamente o que está sendo verificado. |
| `assert X == Y` | Verifica se X é igual a Y. Se não for, o teste falha com mensagem clara. |
| `assert X is True` | Verifica se X é exatamente `True` (não apenas "verdadeiro"). |
| `pytest.raises(Excecao)` | Verifica que uma exceção específica foi lançada. O teste **passa** se a exceção ocorrer. |
| `pytest.approx(valor)` | Comparação com tolerância — use sempre que comparar números decimais (float). |
| `info.value` | O objeto da exceção capturada — você pode inspecionar a mensagem de erro. |

---

## 7. Executando os Testes

```bash
# Rodar todos os testes
pytest

# Com mais detalhes (recomendado)
pytest -v

# Rodar apenas os testes de produto (gerados pelo agente)
pytest adk/src/agents/qa_agent/artefactsTests/ -v

# Rodar apenas os testes de eval (do agente)
pytest adk/src/agents/qa_agent/evalsTest/ -v

# Parar no primeiro erro (útil durante desenvolvimento)
pytest -x

# Filtrar por nome de teste
pytest -k "login"

# Mostrar print() dentro dos testes
pytest -s
```

### Interpretando a saída

```
======================== test session starts ========================
collected 3 items

tests/test_exemplo.py::test_entrada_valida_retorna_true   PASSED  [ 33%]
tests/test_exemplo.py::test_entrada_curta_retorna_false   PASSED  [ 66%]
tests/test_exemplo.py::test_entrada_vazia_lanca_excecao   PASSED  [100%]

========================= 3 passed in 0.14s =========================
```

- **PASSED** = ✅ passou
- **FAILED** = ❌ falhou (pytest mostra onde e por quê)
- **ERROR** = erro no próprio código de teste (ex: import errado)

---

## 8. Medindo a Cobertura

```bash
# Relatório no terminal
pytest --cov=adk/src/agents/qa_agent adk/src/agents/qa_agent/artefactsTests/ -v

# Relatório HTML — mostra linhas não cobertas em vermelho
pytest --cov=adk/src/agents/qa_agent --cov-report=html adk/src/agents/qa_agent/artefactsTests/
open htmlcov/index.html       # Linux/macOS
# start htmlcov/index.html    # Windows
```

---

## 9. Testando Código Assíncrono (Agentes ADK)

Os agentes ADK usam `async/await`. Para testá-los, use `pytest-asyncio`:

```python
# adk/src/agents/qa_agent/evalsTest/test_qa_agent.py

import pytest

@pytest.mark.asyncio
async def test_agente_processa_artefato():
    """
    Teste de eval: verifica se o agente processa um artefato corretamente.
    """
    from adk.src.agents.qa_agent.qa_agent import _processar_artefato

    artefato = {
        "id_artefato": "RF-001",
        "tipo": "RF",
        "conteudo": "[ PREENCHER: texto do requisito de teste ]",
        "modulo": "[ PREENCHER: módulo a testar ]",
    }

    resultado = await _processar_artefato(artefato)

    assert resultado["status"] == "sucesso"
    assert resultado["arquivo_gerado"] is not None


@pytest.mark.asyncio
async def test_agente_nao_trava_com_artefato_invalido():
    """
    Teste de eval: agente deve lidar com artefatos malformados sem travar.
    """
    from adk.src.agents.qa_agent.qa_agent import _processar_artefato

    resultado = await _processar_artefato({})  # artefato vazio

    # O agente não deve lançar exceção — deve retornar status bloqueado ou falha
    assert resultado["status"] in ("bloqueado", "falha")
```

> **Nota:** Se o `asyncio_mode = "auto"` estiver configurado no `pyproject.toml` (ver documento 04), o decorator `@pytest.mark.asyncio` pode ser omitido — o pytest detecta funções async automaticamente.

---

## 10. Fixtures — Reutilizando Configurações

Quando vários testes precisam do mesmo dado de entrada, use fixtures para não repetir código:

```python
# adk/src/agents/qa_agent/evalsTest/conftest.py

import pytest

@pytest.fixture
def artefato_basico():
    """Artefato RF mínimo para os testes de eval."""
    return {
        "id_artefato": "RF-001",
        "tipo": "RF",
        "conteudo": "[ PREENCHER: texto do requisito de teste ]",
        "modulo": "[ PREENCHER: módulo a testar ]",
        "criticidade": "alta",
    }

@pytest.fixture
def lista_artefatos():
    """Lista de artefatos para testar o processamento paralelo."""
    return [
        # [ PREENCHER: adicione artefatos de teste ]
    ]
```

```python
# Usando a fixture — o pytest injeta pelo nome do parâmetro:
@pytest.mark.asyncio
async def test_processar_lista(lista_artefatos):
    from adk.src.agents.qa_agent.qa_agent import _processar_todos_em_paralelo

    resultados = await _processar_todos_em_paralelo(lista_artefatos)

    assert len(resultados) == len(lista_artefatos)
```

---

## 11. Template de Teste Gerado pelo Agente QA

Padrão que o Agente QA deve seguir ao gerar testes de produto:

```python
"""
Testes gerados automaticamente pelo QA Agent
Artefato: {id_artefato} ({tipo})
Módulo: {modulo}
Requisito: {conteudo}
"""

import pytest
# [ gerado pelo agente: importar módulo da aplicação ]


class Test{Tipo}{Id}:
    """Suite de testes para {id_artefato}"""

    def test_caminho_feliz(self):
        """Comportamento correto com entradas válidas."""
        # Arrange — preparar dados
        # Act     — executar ação
        # Assert  — verificar resultado
        pass  # [ gerado pelo agente ]

    def test_entrada_invalida(self):
        """Comportamento com entradas incorretas."""
        with pytest.raises(Exception):
            pass  # [ gerado pelo agente ]

    def test_caso_de_borda(self):
        """Comportamento em casos extremos (vazio, zero, máximo, etc.)."""
        pass  # [ gerado pelo agente ]
```

---

## 12. Referência Rápida de Comandos

```bash
# Instalar (conforme README do projeto)
cd adk/
pip install -e ".[dev]"

# Executar
pytest                                                          # todos os testes
pytest -v                                                       # verbose
pytest -x                                                       # parar no 1º erro
pytest -s                                                       # mostrar print()
pytest -k "nome"                                                # filtrar por nome

# Coverage
pytest --cov=adk/src/agents/qa_agent artefactsTests/            # terminal
pytest --cov=adk/src/agents/qa_agent --cov-report=html artefactsTests/  # HTML
pytest --cov=adk/src/agents/qa_agent --cov-fail-under=70 artefactsTests/ # falha se < 70%

# Por tipo de pytest
pytest adk/src/agents/qa_agent/artefactsTests/ -v   # testes de produto
pytest adk/src/agents/qa_agent/evalsTest/ -v        # testes de eval
```

---

## 13. Glossário

| Termo | Significado simples |
|---|---|
| **Pytest** | Framework para escrever e executar testes em Python |
| **Pytest de produto** | Testa o código da aplicação; gerado pelo Agente QA |
| **Pytest de eval** | Testa o Agente QA em si; escrito pelo time |
| **Assert** | "Afirmo que isto é verdade" — falso = teste falha |
| **Fixture** | Configuração reutilizável injetada automaticamente nos testes |
| **Coverage** | Porcentagem do código executada pelos testes |
| **pytest-asyncio** | Plugin que permite testar funções `async` com pytest |
| **Caminho feliz** | Teste com dados válidos, tudo funcionando normalmente |
| **Caso de borda** | Teste com valores extremos (vazio, zero, máximo) |
| **conftest.py** | Arquivo especial onde fixtures compartilhadas são definidas |# Guia de Pytest e Coverage — Do Zero ao Primeiro Teste

> Salve em: `docs/Time3_Testes/`
> Revisor do PR: Ernesto

---

## 1. Os Dois Tipos de Pytest Neste Projeto

Antes de tudo, é importante entender que pytest aparece em **dois contextos diferentes** neste projeto:

| # | Tipo | O que testa | Quem escreve | Onde fica |
|---|---|---|---|---|
| 1 | **Pytest de produto** | O código da aplicação | O **Agente QA** gera automaticamente | `adk/src/agents/qa_agent/artefactsTests/` |
| 2 | **Pytest de eval** | O próprio **Agente QA** | O **desenvolvedor do time** escreve | `adk/src/agents/qa_agent/evalsTest/` |

Este guia cobre os fundamentos que se aplicam aos dois tipos.

---

## 2. O Que é Pytest?

Imagine que você tem uma função `somar(a, b)` e quer ter certeza de que ela sempre retorna o resultado correto — hoje, amanhã, e depois que outra pessoa modificar o código.

**Pytest** é uma ferramenta que automatiza essa verificação. Em vez de rodar o programa na mão e conferir o resultado, você escreve uma "prova" (o teste), e o pytest executa todas as provas de uma vez e diz quais passaram e quais falharam.

```
Sem pytest:                          Com pytest:
1. Rodar o programa                  1. Escrever o teste uma vez
2. Inserir dados manualmente         2. Rodar: pytest
3. Conferir o resultado              3. Ver: "5 passed in 0.12s" ✅
4. Repetir para cada cenário
5. Torcer para não esquecer nada
```

---

## 3. O Que é Coverage (Cobertura)?

Suponha que sua função tem um `if` e um `else`. Se você só testa o caminho do `if`, a parte do `else` pode ter um bug que nunca será descoberto.

**Coverage** mede: *"De todo o código que existe, qual porcentagem foi executada pelos testes?"*

```
Cobertura 100% → cada linha foi executada ao menos uma vez pelos testes
Cobertura   0% → nenhuma linha foi testada
Meta inicial → 70–80% já é um bom começo para projetos novos
```

Exemplo de relatório gerado no terminal:

```
Name                         Stmts   Miss  Cover
-------------------------------------------------
src/autenticacao.py             45      7    84%
src/pagamentos.py               32      0   100%
src/relatorios.py               18     18     0%   ← nunca testado!
-------------------------------------------------
TOTAL                           95     25    74%
```

---

## 4. Instalação

```bash
# Conforme README do projeto PDC-AI4SE:
cd adk/
pip install -e ".[dev]"

# Confirmar:
pytest --version
```

---

## 5. Estrutura de Pastas

```
adk/
│
├── src/
│   └── agents/
│       └── qa_agent/
│           ├── agent.py                ← definição do agente
│           ├── tools/                  ← ferramentas do agente
│           ├── prompts/                ← prompts do agente
│           │
│           ├── artefactsTests/         ← pytest de PRODUTO (gerado pelo agente)
│           │   ├── __init__.py
│           │   ├── test_rf_001.py      ← gerado automaticamente
│           │   └── test_rf_002.py      ← gerado automaticamente
│           │
│           ├── evalsTest/              ← pytest de EVAL (escrito pelo time)
│           │   ├── __init__.py
│           │   └── test_qa_agent.py    ← você escreve este
│           │
│           └── doubt_artifacts/        ← Doubt_Artifact.md gerados em bloqueios
│
└── docs/
    └── Time3_Testes/
        ├── 01_protocolo_supervisor_qa.md
        ├── 02_fluxo_geracao_paralela.md
        ├── 03_guia_pytest_coverage.md
        └── 04_pyproject_toml.md
```

> **Regra de ouro:** arquivos de teste devem começar com `test_`. Funções de teste também devem começar com `test_`. O pytest encontra automaticamente qualquer arquivo que siga esse padrão.

---

## 6. Seu Primeiro Teste — Passo a Passo

### O código que vamos testar

```python
# Exemplo genérico de função a ser testada
# [ PREENCHER: substitua pelo módulo real da sua aplicação ]

def validar_entrada(valor: str) -> bool:
    """
    Valida uma entrada.
    Retorna True se válida, False se inválida.
    Lança ValueError se a entrada estiver vazia.
    """
    if not valor:
        raise ValueError("O valor não pode ser vazio.")
    return len(valor) >= 3
```

### O teste correspondente

```python
# [ PREENCHER: caminho do arquivo de teste ]

import pytest
# [ PREENCHER: from <modulo> import <funcao> ]


# ─── CAMINHO FELIZ ────────────────────────────────────────────────────────────

def test_entrada_valida_retorna_true():
    """Entrada correta deve retornar True."""
    # [ PREENCHER: substitua pela chamada real ]
    resultado = validar_entrada("abc")
    assert resultado is True


# ─── ENTRADAS INVÁLIDAS ───────────────────────────────────────────────────────

def test_entrada_curta_retorna_false():
    """Entrada com menos de 3 caracteres deve ser inválida."""
    resultado = validar_entrada("ab")
    assert resultado is False


# ─── CASOS DE BORDA ───────────────────────────────────────────────────────────

def test_entrada_vazia_lanca_excecao():
    """Entrada vazia deve lançar ValueError."""
    with pytest.raises(ValueError) as info:
        validar_entrada("")
    assert "vazio" in str(info.value)
```

### Explicação dos conceitos usados

| Conceito | O que faz |
|---|---|
| `def test_nome()` | Define um teste. O nome descreve exatamente o que está sendo verificado. |
| `assert X == Y` | Verifica se X é igual a Y. Se não for, o teste falha com mensagem clara. |
| `assert X is True` | Verifica se X é exatamente `True` (não apenas "verdadeiro"). |
| `pytest.raises(Excecao)` | Verifica que uma exceção específica foi lançada. O teste **passa** se a exceção ocorrer. |
| `pytest.approx(valor)` | Comparação com tolerância — use sempre que comparar números decimais (float). |
| `info.value` | O objeto da exceção capturada — você pode inspecionar a mensagem de erro. |

---

## 7. Executando os Testes

```bash
# Rodar todos os testes
pytest

# Com mais detalhes (recomendado)
pytest -v

# Rodar apenas os testes de produto (gerados pelo agente)
pytest adk/src/agents/qa_agent/artefactsTests/ -v

# Rodar apenas os testes de eval (do agente)
pytest adk/src/agents/qa_agent/evalsTest/ -v

# Parar no primeiro erro (útil durante desenvolvimento)
pytest -x

# Filtrar por nome de teste
pytest -k "login"

# Mostrar print() dentro dos testes
pytest -s
```

### Interpretando a saída

```
======================== test session starts ========================
collected 3 items

tests/test_exemplo.py::test_entrada_valida_retorna_true   PASSED  [ 33%]
tests/test_exemplo.py::test_entrada_curta_retorna_false   PASSED  [ 66%]
tests/test_exemplo.py::test_entrada_vazia_lanca_excecao   PASSED  [100%]

========================= 3 passed in 0.14s =========================
```

- **PASSED** = ✅ passou
- **FAILED** = ❌ falhou (pytest mostra onde e por quê)
- **ERROR** = erro no próprio código de teste (ex: import errado)

---

## 8. Medindo a Cobertura

```bash
# Relatório no terminal
pytest --cov=adk/src/agents/qa_agent adk/src/agents/qa_agent/artefactsTests/ -v

# Relatório HTML — mostra linhas não cobertas em vermelho
pytest --cov=adk/src/agents/qa_agent --cov-report=html adk/src/agents/qa_agent/artefactsTests/
open htmlcov/index.html       # Linux/macOS
# start htmlcov/index.html    # Windows
```

---

## 9. Testando Código Assíncrono (Agentes ADK)

Os agentes ADK usam `async/await`. Para testá-los, use `pytest-asyncio`:

```python
# adk/src/agents/qa_agent/evalsTest/test_qa_agent.py

import pytest

@pytest.mark.asyncio
async def test_agente_processa_artefato():
    """
    Teste de eval: verifica se o agente processa um artefato corretamente.
    """
    from adk.src.agents.qa_agent.qa_agent import _processar_artefato

    artefato = {
        "id_artefato": "RF-001",
        "tipo": "RF",
        "conteudo": "[ PREENCHER: texto do requisito de teste ]",
        "modulo": "[ PREENCHER: módulo a testar ]",
    }

    resultado = await _processar_artefato(artefato)

    assert resultado["status"] == "sucesso"
    assert resultado["arquivo_gerado"] is not None


@pytest.mark.asyncio
async def test_agente_nao_trava_com_artefato_invalido():
    """
    Teste de eval: agente deve lidar com artefatos malformados sem travar.
    """
    from adk.src.agents.qa_agent.qa_agent import _processar_artefato

    resultado = await _processar_artefato({})  # artefato vazio

    # O agente não deve lançar exceção — deve retornar status bloqueado ou falha
    assert resultado["status"] in ("bloqueado", "falha")
```

---

## 10. Fixtures — Reutilizando Configurações

Quando vários testes precisam do mesmo dado de entrada, use fixtures para não repetir código:

```python
# adk/src/agents/qa_agent/evalsTest/conftest.py

import pytest

@pytest.fixture
def artefato_basico():
    """Artefato RF mínimo para os testes de eval."""
    return {
        "id_artefato": "RF-001",
        "tipo": "RF",
        "conteudo": "[ PREENCHER: texto do requisito de teste ]",
        "modulo": "[ PREENCHER: módulo a testar ]",
        "criticidade": "alta",
    }

@pytest.fixture
def lista_artefatos():
    """Lista de artefatos para testar o processamento paralelo."""
    return [
        # [ PREENCHER: adicione artefatos de teste ]
    ]
```

```python
# Usando a fixture — o pytest injeta pelo nome do parâmetro:
@pytest.mark.asyncio
async def test_processar_lista(lista_artefatos):
    from adk.src.agents.qa_agent.qa_agent import _processar_todos_em_paralelo

    resultados = await _processar_todos_em_paralelo(lista_artefatos)

    assert len(resultados) == len(lista_artefatos)
```

---

## 11. Template de Teste Gerado pelo Agente QA

Padrão que o Agente QA deve seguir ao gerar testes de produto:

```python
"""
Testes gerados automaticamente pelo QA Agent
Artefato: {id_artefato} ({tipo})
Módulo: {modulo}
Requisito: {conteudo}
"""

import pytest
# [ gerado pelo agente: importar módulo da aplicação ]


class Test{Tipo}{Id}:
    """Suite de testes para {id_artefato}"""

    def test_caminho_feliz(self):
        """Comportamento correto com entradas válidas."""
        # Arrange — preparar dados
        # Act     — executar ação
        # Assert  — verificar resultado
        pass  # [ gerado pelo agente ]

    def test_entrada_invalida(self):
        """Comportamento com entradas incorretas."""
        with pytest.raises(Exception):
            pass  # [ gerado pelo agente ]

    def test_caso_de_borda(self):
        """Comportamento em casos extremos (vazio, zero, máximo, etc.)."""
        pass  # [ gerado pelo agente ]
```

---

## 12. Referência Rápida de Comandos

```bash
# Instalar (conforme README do projeto)
cd adk/
pip install -e ".[dev]"

# Executar
pytest                                                          # todos os testes
pytest -v                                                       # verbose
pytest -x                                                       # parar no 1º erro
pytest -s                                                       # mostrar print()
pytest -k "nome"                                                # filtrar por nome

# Coverage
pytest --cov=adk/src/agents/qa_agent artefactsTests/            # terminal
pytest --cov=adk/src/agents/qa_agent --cov-report=html artefactsTests/  # HTML
pytest --cov=adk/src/agents/qa_agent --cov-fail-under=70 artefactsTests/ # falha se < 70%

# Por tipo de pytest
pytest adk/src/agents/qa_agent/artefactsTests/ -v   # testes de produto
pytest adk/src/agents/qa_agent/evalsTest/ -v        # testes de eval
```

---

## 13. Glossário

| Termo | Significado simples |
|---|---|
| **Pytest** | Framework para escrever e executar testes em Python |
| **Pytest de produto** | Testa o código da aplicação; gerado pelo Agente QA |
| **Pytest de eval** | Testa o Agente QA em si; escrito pelo time |
| **Assert** | "Afirmo que isto é verdade" — falso = teste falha |
| **Fixture** | Configuração reutilizável injetada automaticamente nos testes |
| **Coverage** | Porcentagem do código executada pelos testes |
| **pytest-asyncio** | Plugin que permite testar funções `async` com pytest |
| **Caminho feliz** | Teste com dados válidos, tudo funcionando normalmente |
| **Caso de borda** | Teste com valores extremos (vazio, zero, máximo) |
| **conftest.py** | Arquivo especial onde fixtures compartilhadas são definidas |