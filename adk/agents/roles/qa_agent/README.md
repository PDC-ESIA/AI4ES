# QA Agent

## 1. O que é o Agente (Visão Geral)

### Identificação
**Nome:** QA Agent (Time 3 — PDC-AI4SE)  
**Domínio:** Engenharia de Requisitos e Testes de Software  

### Propósito
O **QA Agent** resolve o problema de criar suítes de testes baseadas em especificações funcionais. Ele transforma requisitos (RF, HU, UC, RNF, RN) e o código-fonte correspondente em testes automatizados completos. Seu propósito no ciclo de Engenharia de Software (ES) é garantir que o código desenvolvido atenda exatamente aos critérios de aceitação estipulados, reduzindo o esforço manual da equipe de QA e garantindo padronização e cobertura.

### Stacks, Tecnologias, Frameworks utilizados
- **Linguagem:** Python 3.12+
- **Gerenciamento de Pacotes:** `uv`
- **Frameworks de Agente:** Google ADK Framework (LlmAgent, LiteLlm)
- **Testes:** `pytest`
- **Servidor Web / Interface:** `uvicorn`, Dev UI (ADK)

---

## 2. Funcionalidades

O QA Agent possui responsabilidades bem definidas focadas na automação de testes de qualidade:

- **Análise de Requisitos e Código:** Interpreta vários tipos de artefatos de requisitos (HU, RF, UC, RNF, RN), regras de negócio e código-fonte, mapeando os critérios de aceitação para testes.
- **Geração Automática de Testes:** Cria de forma autônoma scripts de testes utilizando `pytest`, abrangendo testes unitários, de integração e validações de segurança.
- **Execução e Validação:** Executa os testes gerados diretamente contra o ambiente local através da ferramenta `pytest_runner`.
- **Autocorreção (Code Fix):** Através de seus subagentes (`action_planner`, `code_fix_agent`), ele planeja ações e tenta corrigir os códigos de teste gerados caso haja falhas na execução.
- **Limites de Atuação:** O agente não implementa funcionalidades no código-fonte principal; sua atuação é estritamente limitada à criação, correção e execução do código de **testes**.

---

## 3. Como executar ou testar o Agente

### Pré-requisitos
- Python 3.12+
- Ferramenta `uv` instalada.
- Chaves de API necessárias para o modelo LLM (`ADK_LLM_MODEL`) configuradas no arquivo `.env`.

### Instalação
Na raiz do projeto (`adk/`), execute os seguintes comandos para criar e ativar o ambiente:

```bash
uv sync
source .venv/bin/activate
cp .env.example .env
```

**⚠️ IMPORTANTE:** No arquivo `.env`, certifique-se de configurar o diretório dos agentes:
```env
ADK_AGENTS_DIR=agents/roles
```

### Comando de Execução
Para rodar o ambiente de desenvolvimento e acessar a interface do agente:

```bash
export ADK_AGENTS_DIR=agents/roles
uvicorn app.main:app --reload --port 8081
```

Acesse pelo navegador: [http://127.0.0.1:8081/dev-ui/?app=qa_agent](http://127.0.0.1:8081/dev-ui/?app=qa_agent)

### Suíte de Testes
O agente é validado fornecendo-se casos de uso reais com códigos fontes prontos e documentação de requisitos (conforme exemplo no passo 5, e presente no seguinte diretório: `adk/agents/roles/qa_agent/testesLocal/`). A validação ocorre quando o agente consegue escrever e passar o código no `pytest` sem intervenção humana.

---

## 4. Possíveis Entradas e Saídas

**Entradas:**
- Arquivos de requisitos, como HU, RF, UC, RNF, RN, em Markdown (`.md`) ou formato equivalente.
- Arquivos de código-fonte em Python (`.py`) correspondentes à funcionalidade a ser testada OU não para gerar casos de teste.
- Prompt de instruções especificando quais níveis de teste e coberturas são desejadas.

**Saídas:**
- Arquivo de testes gerado automaticamente (ex: `test_autenticacao_auto.py`).
- Logs de execução do `pytest` exibindo se os testes passaram ou falharam (relatório de cobertura).
- Artefatos de dúvida (`DoubtArtifact`) caso o agente identifique falta de contexto ou ausência de arquivos anexados.

---

## 5. Cenário de Teste Específico

### Validando a Autenticação
Este cenário valida se o agente opera conforme o esperado ao criar testes para um sistema de login.

**Passo 1 — Saudação:**
Cole na interface da Dev UI:
```text
Olá, tudo bem? Está funcionando corretamente?
```

**Passo 2 — Anexar os arquivos:**
Usando o botão de **upload** (ícone de clipe), anexe os arquivos locais de teste (use de preferência o que está em `adk/agents/roles/qa_agent/testesLocal/`):
1. `main_scenario.py` (Código fonte de referência)
2. `hu_autenticacao.md` (Requisitos de negócio)

**Passo 3 — Colar o prompt de execução:**
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

O sucesso do caso de uso ocorre se o arquivo de teste for criado pelo agente e a ferramenta `pytest_runner` validar com sucesso todos os cenários.

---

## 6. Lista de Erros Identificados

| Problema / Erro | Causa Comum | Como Resolver |
| --- | --- | --- |
| **Erro de módulo / agente não aparece na Dev UI** | A variável de ambiente não foi configurada corretamente. | Confirme que `ADK_AGENTS_DIR=agents/roles` está no seu `.env` e faça o `export` no terminal antes de rodar o `uvicorn`. |
| **Agente responde com "Doubt Artifact" e "conteúdo vazio"** | O agente não tem acesso local de leitura direta ao texto. | Isso indica que os arquivos não foram anexados. Anexe explicitamente os arquivos através da Dev UI (botão de upload local file). |
| **Testes gerados falham por importação incorreta (ModuleNotFoundError)** | O agente gerou caminhos relativos incompatíveis ou faltam arquivos `__init__.py` na estrutura de pacotes. | Confirme que o código gerado faz importações coerentes com o arquivo anexado. Assegure-se de que as pastas locais de teste possuem os arquivos `__init__.py` para que o Python reconheça como pacote. |
| **Lentidão na Resposta** | O uso dos subagentes gera encadeamento demorado de chamadas de LLM. | É esperado. A arquitetura de múltiplos agentes (recepção, planejamento, correção e pytest) pode levar alguns minutos para finalizar. |
| **Agente gerou um código de teste esqueleto (vazio ou comentado)** | Falha na propagação do contexto dos arquivos ou limite de tokens da janela de contexto atingido. | Certifique-se de anexar novamente os arquivos. Se os arquivos forem muito longos, tente reduzir ou dividi-los. Se o problema persistir, pode ser um erro de propagação de contexto no subagente `receive_requirements`. |
| **Pytest falha dizendo "arquivo de teste não encontrado"** | O agente gerou o conteúdo do código em texto, mas não escreveu o arquivo `.py` fisicamente no diretório antes de chamar o `pytest_runner`. | Peça ao agente explicitamente no prompt: "Certifique-se de salvar o código no arquivo antes de rodar os testes" ou envie o diretório para o agente.|
| **Erro de Timeout ou Limite de Taxa (Rate Limit)** | O excesso de subagentes comunicando-se simultaneamente (Code Fix + Action Planner) estourou o limite de quota da API do modelo configurado. | Aguarde alguns minutos antes de enviar a mensagem novamente ou altere a variável de ambiente `ADK_LLM_MODEL` para um modelo com cota maior. |