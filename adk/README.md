# Documentação — Agente de Design (AI4ES)

---

## 1. O que é o Sistema Agêntico (Visão Geral)

O **Agente de Design** é um sistema multi-agente construído sobre o **Google ADK (Agent Development Kit)** que automatiza a fase de design de software a partir de **Histórias de Usuário (HUs)**. O sistema recebe um lote de HUs em linguagem natural, analisa as decisões arquiteturais adequadas, gera diagramas Mermaid (`.mmd`) e produz um relatório técnico estruturado em Markdown.

O sistema é composto por **6 agentes especializados** com papéis bem definidos que se comunicam via protocolo orquestrado:

| Agente | Papel |
|---|---|
| **Orchestrator** | Coordenador central do pipeline |
| **Design Architect** | Análise arquitetural e identificação de lacunas |
| **Mermaid Specialist** | Geração de diagramas `.mmd` |
| **Validator** | Validação determinística de artefatos |
| **Markdown Specialist** | Geração do relatório final |
| **IO Agent** | Persistência, versionamento e promoção de artefatos |

---

## 2. Identificação

| Campo | Valor |
|---|---|
| **Nome do Projeto** | AI4ES |
| **Squad** | Time 2 |
| **Tipo** | Sistema Multi-Agente de Suporte ao Design de Software |
| **Linguagem** | Python 3.12 |
| **Gerenciador de Pacotes** | uv |
| **Servidor** | FastAPI + Uvicorn |
| **Interface** | Web UI via Google ADK Dev UI (`/dev-ui`) |
| **Diretório de Artefatos Temporários** | `temp/staging/` |
| **Diretório de Entrega Final** | `adk/artifacts/` |
| **Arquivo de Testes** | `prompt-test.md` |

---

## 3. Propósito

### Problema que resolve

Na Engenharia de Software, a fase de design é crítica e frequentemente negligenciada. HUs vagas ou incompletas chegam ao desenvolvimento sem que as decisões arquiteturais tenham sido formalizadas, gerando retrabalho, dívida técnica e ambiguidades que só aparecem em produção.

### Como se alinha ao processo de ES

O agente atua na **fase de Design** do ciclo de vida de desenvolvimento, posicionado entre o **levantamento de requisitos** e a **implementação**:

```
[Requisitos / HUs] → [Agente de Design] → [Relatório Técnico + Diagramas] → [Desenvolvimento]
```

Especificamente, o sistema:

- **Valida** se as HUs contêm informação suficiente para decisão arquitetural
- **Bloqueia** automaticamente HUs ambíguas gerando `Doubt_Artifacts` com as perguntas necessárias
- **Formaliza** as decisões de arquitetura com neutralidade
- **Gera** diagramas Mermaid padronizados por tipo (sequência, estado, classe, ER, C4Context, fluxograma)
- **Documenta** cobertura de critérios de aceite e gaps identificados
- **Produz** um relatório técnico padronizado com template oficial, pronto para revisão humana

---

## 4. Stacks, Tecnologias e Frameworks

| Categoria | Tecnologia | Versão | Uso |
|---|---|---|---|
| **Framework de Agentes** | Google ADK | ≥ 1.12.0 | Base do sistema multi-agente |
| **Linguagem** | Python | 3.12 | Linguagem principal |
| **LLM Provider** | GitHub Copilot / GPT-4 | — | Modelo padrão de todos os agentes |
| **Abstração de LLM** | LiteLLM | ≥ 1.72.2 | Camada de abstração para troca de modelos |
| **Orquestração LLM** | LangChain / LangChain-Core | ≥ 0.3.26 | Ferramentas auxiliares de LLM |
| **API Web** | FastAPI | ≥ 0.115.14 | Servidor HTTP e Dev UI |
| **Servidor ASGI** | Uvicorn | ≥ 0.35.0 | Servidor de desenvolvimento |
| **Validação de Dados** | Pydantic | ≥ 2.11.7 | Schemas e validação de I/O |

---

## 5. Funcionalidades

### Pipeline de Execução

```
HUs (input) 
   └─▶ Orchestrator
        ├─▶ Design Architect ─────────────────────┐
        │       ├─▶ [Análise Técnica → staging]   │
        │       └─▶ [Doubt_Artifact → staging] ◀── Lacuna identificada
        │
        ├─▶ Mermaid Specialist
        │       └─▶ [Diagrama .mmd → staging]
        │
        ├─▶ Validator
        │       ├─▶ [OK] ─────────▶ Markdown Specialist
        │       └─▶ [FALHA] ──────▶ Especialista responsável (reprocessa)
        │
        └─▶ Markdown Specialist
              └─▶ [Relatório .md → staging]
                    └─▶ [Aprovação manual] ──▶ artifacts/ (entrega final)
```

### Responsabilidades por Agente

#### Orchestrator
- Ponto de entrada do sistema — recebe o lote de HUs do usuário
- Valida e padroniza o formato das HUs (HU-ID, solicitante, ator, ação, critérios de aceite)
- Coordena a sequência de execução dos especialistas
- Monitora bloqueios ativos via `Doubt_Artifacts`
- Gerencia a promoção de artefatos para `artifacts/` após aprovação

**Limites:** Não interpreta o conteúdo arquitetural das HUs — delega ao Design Architect.

#### Design Architect
- Analisa o lote de HUs em 7 passos estruturados
- Decide o estilo arquitetural com trade-offs documentados
- Seleciona o tipo de diagrama por algoritmo de prioridade: `sequência > estado > classe > ER > C4Context > fluxograma`
- Identifica componentes, responsabilidades e dependências
- Gera tabela de cobertura (✅/❌) para cada critério de aceite
- Realiza gap analysis de riscos implícitos
- Emite `Doubt_Artifacts` para HUs com lacunas críticas

**Limites:** Não nomeia novos  produtos tecnológicos específicos (ex.: Kafka, Redis, JWT, AWS). Mantém neutralidade arquitetural obrigatória.

#### Mermaid Specialist
- Gera arquivos `.mmd` válidos e renderizáveis a partir da análise técnica
- Suporta 6 tipos de diagrama: `flowchart`, `sequenceDiagram`, `classDiagram`, `stateDiagram-v2`, `erDiagram`, `C4Context`
- Inclui cabeçalho obrigatório com tipo, autoria, solicitante e data
- Mantém consistência de nomes de componentes com a análise do Design Architect

**Limites:** Não decide o tipo de diagrama — usa o definido pelo Design Architect. Não renomeia componentes.

#### Validator
- Executa validação em **duas camadas**:
  - **Sintática (determinística via ferramenta):** gramática, estrutura, formato
  - **Semântica (via LLM):** consistência entre diagrama e análise, seções obrigatórias no relatório
- Roteia falhas automaticamente para o especialista responsável
- Retorna erros estruturados: tipo, mensagem, linha, sugestão de correção

**Limites:** Não corrige artefatos — apenas valida e roteia para reprocessamento.

#### Markdown Specialist
- Gera o relatório final usando o template oficial (`relatorio_template.md`)
- Preenche 7 seções: identificação das HUs, diagramas, decisões arquiteturais, componentes, bloqueios, cobertura e gap analysis
- Embute os diagramas `.mmd` em blocos ` ```mermaid ``` ` no relatório
- Gera relatório com `Status: Em análise` (requer aprovação manual para promoção)

**Limites:** Não gera diagramas — depende dos `.mmd` existentes no staging.

#### IO Agent
- Único ponto de I/O do sistema — todos os agentes leem/escrevem via IO Agent
- Persiste artefatos em `temp/staging/` com **versionamento automático** (backup por timestamp)
- Promove relatórios aprovados para `adk/artifacts/`
- Bloqueia promoção se `Status: Em análise` (requer aprovação manual)
- Protege contra path traversal
- Registra todas operações via IOLogger

**Limites:** Só promove arquivos `.md` com `relatorio` no nome e `Status: Aprovado`.

---

## 6. Como Executar ou Testar o Agente

### Pré-requisitos

| Requisito | Versão | Observação |
|---|---|---|
| Python | 3.12+ | Verificar com `python --version` |
| uv | Qualquer | [Guia de instalação](https://docs.astral.sh/uv/getting-started/installation/) |
| Conta GitHub | — | Necessária para autenticação OAuth (GitHub Copilot) |

> **Variáveis de Ambiente:** Não é necessário o uso do .env, pois nenhuma chave é necessária — a autenticação é feita via OAuth (GitHub).

### Instalação

```bash
# 1. Clone o repositório
git clone <URL_DO_REPOSITORIO>
cd adk

# 2. Criar e ativar ambiente virtual (opcional com uv)
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

# 3. Instalar dependências com uv
uv sync
# ou com pip (se preferir)
pip install -r requirements.txt
```

### Comando de Execução
=======
## Primeira execução (dentro da pasta adk/)

### 1. Instalar dependências e preparar o ambiente

O projeto utiliza o **uv** para gerenciar dependências. Este comando criará o ambiente virtual e instalará todas as ferramentas necessárias, incluindo o **uvicorn**:

```bash
uv sync
```

### 2. Autenticação — GitHub Copilot (OAuth)

Não é necessária nenhuma chave de API. A autenticação é feita via GitHub na primeira execução:

1. Inicie o servidor normalmente (próxima seção)
2. Nos logs do uvicorn, aparecerá uma mensagem solicitando autenticação com um **link e um código de ativação**
3. Acesse o link indicado nos logs
4. Insira o código exibido e autorize o acesso via GitHub
5. Após autorização, o servidor continuará normalmente

> A autenticação é via OAuth — nenhuma chave precisa ser configurada manualmente.  

---

## Executando o servidor (dentro da pasta adk/)
>>>>>>> ab97cf61c1ac5a60dfaf8a0f97c33880093cd70d

```bash
# Iniciar o servidor de desenvolvimento
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

<<<<<<< HEAD
**Primeira execução — Autenticação GitHub Copilot:**
1. Nos logs do terminal, aparecerá um link e um código de ativação
2. Acesse o link e insira o código para autorizar via GitHub
3. Após autorização, o servidor continua automaticamente

**Acessar a interface:**
```
=======
Acesse a interface em:

```hyperlink
>>>>>>> ab97cf61c1ac5a60dfaf8a0f97c33880093cd70d
http://localhost:8000/dev-ui
```
- Selecione o agente **orchestrator** na interface
- Envie o lote de HUs no campo de chat

### Suíte de Testes

O arquivo [`prompt-test.md`](prompt-test.md) contém exemplos de HUs para validação manual do pipeline:

```bash
# Abrir o arquivo de testes para copiar os prompts de exemplo
cat prompt-test.md
```

**Casos de teste disponíveis:**

| ID | HU | Resultado Esperado |
|---|---|---|
| HU-001 | Login com JWT e refresh tokens | Diagrama de sequência + relatório |
| HU-002 | Reset de senha com auditoria | Diagrama de fluxo + relatório |
| HU-003 | Histórico de sessões com WebSocket | Doubt_Artifact (lacuna: definição de "tempo real") |
| HU-004 | Registro de usuário | Diagrama + relatório ou Doubt_Artifact |

**Para executar um teste:**
1. Copie o lote de HUs do `prompt-test.md`
2. Cole no chat do Dev UI com o agente **orchestrator** selecionado
3. Verifique os artefatos gerados em `temp/staging/`

---

## 7. Possíveis Entradas e Saídas

### Entradas

O sistema aceita lotes de HUs em formato de texto livre, preferencialmente estruturado:

```
HU-001
Solicitante: [Nome]
Como [ator], quero [ação] para que [benefício].
Critérios de Aceite:
- [critério 1]
- [critério 2]
- [critério n]

HU-002
...
```

**Requisitos de entrada para processamento sem bloqueio:**
- HU-ID identificável (ex.: HU-001, HU-002)
- Solicitante identificado
- Ator definido (quem executa a ação)
- Ação clara e específica
- Critérios de aceite detalhados (sem ambiguidades de integração, limites ou protocolos)

### Saídas

| Tipo | Localização | Condição de Geração |
|---|---|---|
| `analise_tecnica_<hu_ids>.md` | `temp/staging/` | Sempre que Design Architect conclui |
| `diagrama_<hu_id>_<descricao>.mmd` | `temp/staging/` | Sempre que Mermaid Specialist conclui |
| `relatorio_<hu_ids>_<YYYY-MM-DD>.md` | `temp/staging/` | Pipeline sem bloqueios |
| `Doubt_Artifact_<HU_ID>_<data>.md` | `temp/staging/` | HU com lacunas críticas |
| `relatorio_<hu_ids>_<YYYY-MM-DD>.md` | `adk/artifacts/` | Após aprovação manual + promoção |

**Estrutura do Relatório Final (`relatorio_*.md`):**

1. Identificação das HUs (tabela)
2. Diagramas de Arquitetura (blocos Mermaid por HU)
3. Decisões de Arquitetura (com alternativas consideradas)
4. Componentes (responsabilidades e dependências)
5. Bloqueios e Pendências (severidade 🔴/🟡/🟢 ou "Nenhum.")
6. Cobertura de HUs (✅/❌ com justificativas)
7. Gap Analysis (riscos implícitos identificados)



---

## 8. Cenário de Teste Específico

### Caso de Uso: Autenticação com JWT (HU-001)

**Objetivo:** Validar se o pipeline gera corretamente análise arquitetural, diagrama de sequência e relatório para uma HU de autenticação bem definida.

**Input:**

```
HU-001
Solicitante: Product Owner
Como usuário registrado, quero realizar login na plataforma utilizando e-mail e senha,
para que eu possa acessar as funcionalidades restritas.

Critérios de Aceite:
- O sistema deve autenticar o usuário e retornar um token de acesso (JWT) e um refresh token.
- O token de acesso deve expirar em 15 minutos.
- O refresh token deve expirar em 7 dias.
- Em caso de credenciais inválidas, o sistema deve retornar erro 401.
- O sistema deve implementar rate limiting: máximo 5 tentativas por IP em 10 minutos.
- Após 5 tentativas falhas, o IP deve ser bloqueado por 30 minutos.
```

**Execução:**
1. Inicie o servidor: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
2. Acesse `http://localhost:8000/dev-ui` → selecione **orchestrator**
3. Cole o lote de HUs acima no chat

**Resultado Esperado:**

```
temp/staging/
├── analise_tecnica_HU-001.md  
│     └─▶ análise com decisão arquitetural (sequência + stateless auth)
├── diagrama_HU-001_autenticacao.mmd 
│     └─▶sequenceDiagram com Frontend, AuthService, TokenService, RateLimiter
└── relatorio_HU-001_2026-05-06.md   
      └─▶ relatório completo com Status: Em análise
```

**Validação do Diagrama:** O `.mmd` deve conter:
- `sequenceDiagram` como tipo
- Cabeçalho com tipo, autoria e data
- Participantes: Frontend, AuthService, TokenService, RateLimiter (ou equivalentes neutros)
- Fluxo: tentativa de login → validação → geração de tokens → resposta
- Caminho alternativo: credenciais inválidas → 401
- Caminho alternativo: rate limit atingido → bloqueio

**Validação do Relatório:** O `.md` deve conter todas as 7 seções, cobertura ✅ para todos os critérios e `Gap Analysis` com riscos de persistência do estado de rate limiting entre instâncias (caso deploy distribuído).

---

