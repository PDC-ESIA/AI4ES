# QA Agent

## Descrição
O `qa_agent` transforma requisitos funcionais em testes automatizados utilizando `pytest`. A partir de artefatos de entrada, o agente interpreta requisitos, gera o código de teste e segue um padrão consistente de estrutura de QA.

## Estrutura de Teste Atual (caso base)
Os seguintes arquivos devem ser utilizados como **entrada (INPUT)**:

- `hu_autenticacao.md` (História de Usuário)
- `prompt_qa_testing.md` (Diretrizes de geração)
- `test_scenario.py` (Código-fonte de referência)

> Recomendação: mantenha esses arquivos em `adk/agents/roles/qa_agent/testesLocal/` apenas como organização do repositório (não como “fonte automática” para o agente).

## Pré-requisitos
- Python 3.12+
- `uv` instalado
- Ambiente configurado na pasta `adk/`

## Setup do Ambiente
Na raiz `adk/`, execute:

```bash
uv sync
source .venv/bin/activate
cp .env.example .env
```

**⚠️ IMPORTANTE:** No arquivo `.env`, a variável abaixo deve estar configurada:
`ADK_AGENTS_DIR=agents/roles`

## Executando o QA Agent

### 1) Subir o servidor
```bash
export ADK_AGENTS_DIR=agents/roles
uvicorn app.main:app --reload --port 8081
```

### 2) Abrir a interface
Acesse: [http://127.0.0.1:8081/dev-ui/?app=qa_agent](http://127.0.0.1:8081/dev-ui/?app=qa_agent)

## Como testar o agente (fluxo oficial para professores)

### Passo 1 — Saudação (handshake)
Cole na Dev UI:

```text
Olá, tudo bem? Está funcionando corretamente?
```

### Passo 2 — Colar o prompt de execução
Cole **exatamente** o bloco abaixo na Dev UI (logo após a saudação):

````markdown
# OBJETIVO
Gerar testes pytest automatizados completos para a classe `SistemaAutenticacao` baseado no código fonte e nos requisitos da HU.

## ARQUIVOS DE ENTRADA
1. **Código Fonte**: `main_scenario.py` - Classe completa do sistema de autenticação
2. **Requisitos**: `hu_autenticacao.md` - História de usuário com critérios de aceitação e cenários

## TAREFA
Analisar ambos os arquivos e gerar um arquivo pytest completo (`test_autenticacao_auto.py`) com:

### 1. ANÁLISE DO CÓDIGO
- Extrair todos os métodos públicos da classe
- Identificar parâmetros e retornos
- Compreender a lógica de negócio

### 2. ANÁLISE DOS REQUISITOS
- Mapear critérios de aceitação para testes
- Identificar cenários de teste (feliz, misto, triste)
- Extrair dados de teste da HU

### 3. GERAÇÃO DE TESTES
Criar testes pytest que cubram:

**TESTES UNITÁRIOS (por método):**
- `registrar_usuario()` - validações, sucesso, falhas
- `login()` - credenciais corretas/incorretas, bloqueio
- `verificar_sessao()` - válida, expirada, inexistente
- `logout()` - remoção de sessão
- `gerar_codigo_2fa()` - geração e expiração
- `verificar_2fa()` - código correto/incorreto
- `solicitar_recuperacao_senha()` - email válido/inválido
- `redefinir_senha()` - token válido/inválido
- Funções de validação (`validar_email`, `validar_telefone`, `calcular_forca_senha`)

**TESTES DE INTEGRAÇÃO (cenários):**
- **Caminho Feliz**: Registro → Login → Sessão → Logout
- **Caminho Misto**: Login falha → Login sucesso → 2FA
- **Caminho Triste**: Validações falham consecutivamente

**TESTES DE SEGURANÇA:**
- Bloqueio por tentativas excessivas
- Expiração de sessões e tokens
- Validação de força de senha

### 4. CRITÉRIOS DE QUALIDADE
- ✅ 100% de cobertura dos métodos públicos
- ✅ Todos os critérios de aceitação testados
- ✅ Cenários positivos e negativos
- ✅ Asserts específicos e descritivos
- ✅ Mensagens de erro validadas
- ✅ Dados de teste da HU utilizados
- ✅ Fixtures para setup e tearDown

### 5. FORMATO DE SAÍDA
Arquivo `test_autenticacao_auto.py` contendo:
```python
"""
Testes automatizados para SistemaAutenticacao
Gerado automaticamente baseado em código e requisitos
"""
import pytest
import time
from test_scenario import SistemaAutenticacao

# Fixtures
@pytest.fixture
def sistema():
    return SistemaAutenticacao()

@pytest.fixture
def sistema_com_dados(sistema):
    # Setup com dados da HU
    return sistema

# Testes unitários
# Testes de integração
# Testes de cenários
```

## DADOS DE TESTE DA HU
**Usuários válidos:**
- `joao.silva` / `SenhaForte123!` / `joao@email.com` / `(11) 99999-9999`
- `maria.santos` / `MariaSecure456@` / `maria@empresa.com` / `(21) 98888-8888`
- `admin` / `AdminSuper789#` / `admin@system.com` / `(31) 97777-7777`

**Usuário desativado:**
- `inativo.user` / `Inativo123$` / `inativo@test.com` / `(41) 96666-6666`

**Senhas de teste:**
- ❌ `fraca` (0/100)
- ❌ `senhasimples` (30/100)
- ✅ `Senha123` (62/100)
- ✅ `SenhaForte123!` (80/100)
- ✅ `A1b2C3d4E5f6G7h8!` (80/100)

## INSTRUÇÕES FINAIS
1. Analisar profundamente ambos os arquivos
2. Gerar testes completos e robustos
3. Validar que todos os requisitos estão cobertos
4. Garantir que os testes executem sem erros
5. Entregar arquivo pronto para execução

O resultado deve ser voce gerar os testes, testar e trazer o resultado.
````

### Passo 3 — Anexar os arquivos (obrigatório)
Depois de colar o prompt, **anexe os arquivos** usando o botão de upload (**ícone de clipe / “upload local file”**):

1. `adk/agents/roles/qa_agent/testesLocal/main_scenario.py`
2. `adk/agents/roles/qa_agent/testesLocal/hu_autenticacao.md`


## Nota técnica importante (sobre “caminho de arquivo”)
- O agente **não possui uma tool para localizar/abrir arquivos locais apenas pelo caminho informado em texto** (ex.: `adk/agents/.../hu_autenticacao.md`).
- Porém, a tool de execução de `pytest` **consegue rodar arquivos locais** porque existe lógica interna para **normalizar o caminho do arquivo** ao executar testes.

**Consequência prática:** para o agente gerar testes com base no conteúdo real, **deve-se anexar os arquivos** (Passo 3). Informar “paths” no texto **não substitui** o upload.

## O que validar no resultado
- ✅ **Geração:** se o arquivo `test_autenticacao_auto.py` foi criado.
- ✅ **Execução:** se os testes rodam com de falha ou não contra o `main_scenario.py`.

## Troubleshooting e boas práticas
- **Erro de módulo / agente não aparece:** confirme `ADK_AGENTS_DIR=agents/roles` no `.env` e no `export`.
- **Doubt Artifact “conteúdo vazio”:** isso normalmente indica que os arquivos **não foram anexados**.
- **Menos alucinação:** prefira anexar os artefatos completos (HU + código) em vez de resumir.

## Conclusão
O fluxo de teste do QA Agent garante que a transição entre requisito e código ocorra de forma padronizada. Ao anexar os artefatos de `testesLocal`, a validação mede não só se o agente “gera código”, mas se ele mantém rigor ao cobrir exceções e regras de segurança descritas na HU.

**OBSERVAÇÃO**: É normal demorar um pouco, arquitetura não está adequada por isso lavaram muito tempo para rodar.