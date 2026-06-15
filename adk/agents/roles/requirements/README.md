# Requirements Agent — Analista de Requisitos

## 1. O que é o Agente (Visão Geral)

### Identificação

| Campo | Valor |
|---|---|
| **Nome interno** | `requirements_agent` |
| **Role** | `requirements` |
| **Tipo** | `LlmAgent` (Google ADK) |
| **Pacote** | `adk/agents/roles/requirements/` |
| **Exportação** | `root_agent` via `__init__.py` |

### Propósito

O Requirements Agent é o **primeiro agente** do pipeline de Engenharia de Software do AI4ES. Ele atua como um **Analista de Requisitos sênior** que transforma descrições em linguagem natural, documentos de requisitos (PRDs) ou visões de projeto em **artefatos técnicos estruturados, atômicos e verificáveis**.

Ele resolve o problema de **tradução entre a visão de negócio e a especificação técnica**, garantindo que requisitos sejam claros, rastreáveis e livres de ambiguidades antes de avançarem para os próximos agentes do pipeline (architect, coder, reviewer, etc).

O agente se alinha ao processo de ES nas etapas de **Elicitação**, **Análise**, **Especificação** e **Validação** de requisitos.

### Stacks, Tecnologias e Frameworks

| Tecnologia | Uso |
|---|---|
| **Python 3.10+** | Linguagem principal |
| **Google ADK** (`google-adk`) | Framework de agentes (LlmAgent, AgentTool, FunctionTool) |
| **LiteLLM** | Abstração de modelos LLM (permite uso de múltiplos providers) |
| **Pydantic** | Validação e definição de schemas de saída |
| **PyMuPDF** (`fitz`) | Extração de texto de arquivos PDF (dependência opcional) |
| **Docker / Docker Compose** | Execução e teste via interface web do ADK |

---

## 2. Funcionalidades

### Responsabilidades

O agente é responsável por:

- **Extrair e classificar requisitos** a partir de texto em linguagem natural, produzindo:
  - Histórias de Usuário (HU)
  - Requisitos Funcionais (RF)
  - Requisitos Não Funcionais (RNF)
  - Casos de Uso (UC)
  - Regras de Negócio (RN)
- **Construir um glossário técnico** automaticamente a partir do documento-matriz, delegando ao sub-agente de glossário.
- **Validar a qualidade dos artefatos gerados** contra critérios SMART e de consistência, delegando ao sub-agente de validação.
- **Registrar dúvidas e ambiguidades** em Doubt Artifacts quando o contexto é insuficiente ou contraditório.
- **Persistir todos os artefatos** em formato Markdown no diretório `docs/Time_1_Requisitos/`.

### Limites de Atuação

O agente **NÃO**:
- Implementa código.
- Sugere arquitetura de sistema.
- Toma decisões de design técnico.
- Resolve ambiguidades por conta própria — registra como dúvida para revisão humana (Human-in-the-Loop).

### Arquitetura Interna (3 Agentes)

O pacote implementa uma hierarquia de 3 agentes:

```
requirements_agent (Principal)
├── glossario_agent (Sub-agente via AgentTool)
└── validacao_agent (Sub-agente via AgentTool)
```

#### Agente Principal — `requirements_agent`

Coordena todo o fluxo de análise. Recebe texto no prompt, aplica a Cadeia de Pensamento (Chain of Thought), gera artefatos, salva em disco e delega a validação.

- **Modelo**: configurável via `ADK_LLM_MODEL` (padrão: `github_copilot/gpt-4`)
- **output_key**: `analysis_result`

#### Sub-Agente de Glossário — `glossario_agent`

Focado em ler o documento-matriz (em `data/matrix/`), identificar termos técnicos e construir o glossário formal em `knowledge/glossario.md`.

- **Modelo**: configurável via `ADK_LLM_MODEL` (padrão: `github_copilot/gpt-4o`)
- **Fluxo**: Lê documento → Identifica termos → Fatia em chunks → Busca definições → Alimenta glossário
- Nunca inventa definições — extrai apenas do documento-matriz.

#### Sub-Agente de Validação — `validacao_agent`

Analisa criticamente os artefatos já persistidos em disco e emite um parecer formal de qualidade.

- **Modelo**: configurável via `ADK_LLM_MODEL` (padrão: `github_copilot/gpt-4o`)
- **output_key**: `validation_result`
- **Critérios avaliados**: SMART (Specific, Measurable, Achievable, Relevant, Time-bound), contradições, rastreabilidade (`hu_parent` de RFs)
- **Pareceres possíveis**: `APROVADO`, `APROVADO_COM_RESSALVAS`, `BLOQUEADO`

### Cadeia de Pensamento (Chain of Thought)

O agente principal segue obrigatoriamente 5 passos analíticos documentados na saída:

1. **Elicitação** — Identificar atores (stakeholders), processos e intenções.
2. **Análise Crítica** — Detectar ambiguidades, termos vagos ou contradições.
3. **Classificação** — Separar comportamento (RF), valor de negócio (HU), restrição técnica (RNF) ou regra lógica (RN).
4. **Especificação** — Redigir cada item de forma atômica. HUs devem ter Persona, Ação, Valor e Critérios de Aceite.
5. **Validação** — Garantir que todos os requisitos sejam SMART.

### Fluxo de Execução Completo

```
Entrada (texto/PRD)
    │
    ▼
┌─ Glossário ──────────────────────────────┐
│  Delega ao glossario_agent               │
│  (se houver documento em data/matrix/)   │
│  → Gera knowledge/glossario.md           │
└──────────────────────────────────────────┘
    │
    ▼
┌─ Análise (CoT 5 passos) ────────────────┐
│  Elicitação → Análise → Classificação   │
│  → Especificação → Validação SMART      │
│  Se ambiguidade → gerar_doubt_artifact   │
└──────────────────────────────────────────┘
    │
    ▼
┌─ Persistência ───────────────────────────┐
│  tool_salvar_artefato_requisito()        │
│  → docs/Time_1_Requisitos/{HUs,RFs,...}/ │
└──────────────────────────────────────────┘
    │
    ▼
┌─ Validação ──────────────────────────────┐
│  Delega ao validacao_agent com IDs       │
│  → Lê artefatos do disco                │
│  → Avalia SMART + contradições           │
│  → Emite parecer JSON                    │
│                                          │
│  APROVADO → encerra                      │
│  COM_RESSALVAS → registra doubts, encerra│
│  BLOQUEADO → corrige + re-valida (1x)    │
└──────────────────────────────────────────┘
    │
    ▼
Saída: AnalystOutput (JSON)
```

---

## 3. Como Executar ou Testar o Agente

### Pré-requisitos

1. **Python 3.10+** instalado.
2. **Dependências do projeto** instaladas (via `uv` ou `pip`):
   - `google-adk`
   - `litellm`
   - `pydantic`
   - `pymupdf` (opcional, para suporte a PDF)
3. **Variáveis de ambiente** configuradas no arquivo `.env` na raiz de `adk/`:

| Variável | Obrigatória | Descrição | Exemplo |
|---|---|---|---|
| `ADK_LLM_MODEL` | Sim | Modelo LLM a ser utilizado | `github_copilot/gpt-4o` |
| `ADK_AGENT_DATA_DIR` | Não | Base para `data/` e `knowledge/` | Path relativo ao CWD |
| `ADK_DOCS_DIR` | Não | Base para `docs/` (saída de artefatos) | `docs/` (padrão) |

> Um arquivo `.env.example` está disponível na raiz de `adk/` com as variáveis documentadas.

### Instalação

```bash
# Clonar o repositório
git clone <url-do-repositorio>
cd AI4ES/adk

# Instalar dependências (com uv)
uv sync

# Ou com pip
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas chaves de API
```

### Comando de Execução

Na raiz do projeto `adk/`, execute:

```bash
ADK_AGENTS_DIR=agents/roles uvicorn app.main:app --host 127.0.0.1
```

Após iniciar o servidor, acesse a interface web do ADK em `http://127.0.0.1:8000`.

Na interface de chat:
1. Localize o seletor de **Agentes/**.
2. Escolha o agente `requirements`.
3. Envie uma descrição de projeto em texto para iniciar a análise.

### Suíte de Testes

Testes podem ser encontrados em `adk/tests/`. Para executar:

```bash
# Na raiz de adk/
python -m pytest tests/ -v
```

---

## 4. Possíveis Entradas e Saídas

### Entradas

O agente aceita **texto em linguagem natural** diretamente no prompt. Não é necessário fornecer arquivos — a entrada é sempre textual. Exemplos:

| Tipo de Entrada | Exemplo |
|---|---|
| **Descrição informal** | *"Preciso de um sistema que gerencie o cadastro de alunos e professores"* |
| **PRD detalhado** | Documento de requisitos completo em texto |
| **Conversa/dúvida inicial** | *"Quero fazer um sistema, por onde começo?"* → agente solicita mais contexto |
| **Texto vago/ambíguo** | *"O sistema deve ser rápido e bonito"* → agente registra Doubt Artifact |

Opcionalmente, um **documento-matriz** (PDF, TXT ou MD) pode ser colocado em `data/matrix/` para que o sub-agente de glossário extraia termos técnicos.

### Saídas

#### Saída Principal — `AnalystOutput` (JSON)

A saída final segue o schema Pydantic `AnalystOutput` definido em `schemas.py`:

```json
{
  "status": "concluido",
  "user_stories": [
    {
      "id": "HU-001",
      "title": "Título da funcionalidade",
      "persona": "Ator/Usuário",
      "action": "Ação desejada",
      "value": "Valor de negócio",
      "acceptance_criteria": ["CA-1: ...", "CA-2: ..."]
    }
  ],
  "functional_requirements": [
    {
      "id": "RF-001",
      "title": "Título do requisito",
      "description": "Descrição detalhada e não ambígua",
      "priority": "Alta",
      "hu_parent": "HU-001"
    }
  ],
  "non_functional_requirements": [
    {
      "id": "RNF-001",
      "title": "Título",
      "description": "Descrição",
      "category": "Performance"
    }
  ],
  "use_cases": [
    {
      "id": "UC-001",
      "title": "Título do caso de uso",
      "actor": "Ator principal",
      "description": "Breve descrição do fluxo",
      "pre_conditions": ["..."],
      "main_flow": ["Passo 1", "Passo 2"],
      "post_conditions": ["..."]
    }
  ],
  "business_rules": [
    {
      "id": "RN-001",
      "description": "Regra de negócio ou restrição lógica"
    }
  ],
  "glossary": [
    {
      "term": "OAuth2",
      "definition": "Protocolo de autorização...",
      "source": "Seção 1.3"
    }
  ],
  "doubt_generated": false,
  "summary": "Resumo executivo do processamento"
}
```

O campo `status` pode ser:
- `"concluido"` — análise finalizada com sucesso.
- `"bloqueado"` — contexto insuficiente, dúvidas críticas registradas.

#### Artefatos Persistidos em Disco

Além do JSON de saída, o agente persiste arquivos Markdown em:

```
docs/Time_1_Requisitos/
├── HUs/
│   ├── HU-001.md
│   └── HU-002.md
├── RFs/
│   ├── RF-001.md
│   └── RF-002.md
├── RNFs/
│   └── RNF-001.md
├── RNs/
│   └── RN-001.md
└── Doubt_Artifacts/
    └── Doubt_Artifact_D-001_20260612_120000_000000.md
```

#### Glossário

Gerado automaticamente pelo sub-agente em `knowledge/glossario.md` como tabela Markdown:

```markdown
| Termo | Definição | Fontes |
|-------|-----------|--------|
| OAuth2 | Protocolo de autorização... | chunk_001.txt, chunk_003.txt |
```

#### Parecer de Validação

Retornado pelo sub-agente de validação (armazenado em `validation_result`):

```json
{
  "parecer": "APROVADO_COM_RESSALVAS",
  "total_artefatos": 5,
  "problemas_criticos": 0,
  "problemas_nao_criticos": 2,
  "recomendacoes_prioritarias": ["Detalhar critério de aceite CA-3 do HU-001"]
}
```

---

## 5. Cenário de Teste Específico

### Cenário: Análise de um sistema de gestão acadêmica

**Objetivo**: Validar que o agente gera HUs, RFs e glossário completos a partir de um PRD simples, salva os artefatos em disco e obtém validação aprovada.

**Entrada (prompt)**:
```
O sistema TACO-IDE é uma plataforma de ensino de programação. O professor cria exercícios com enunciado em Markdown e casos de teste (entrada/saída). O aluno submete código que é executado em sandbox isolado via Docker. Uma IA baseada em LLM analisa o código e fornece feedback pedagógico. O sistema deve suportar autenticação via LDAP institucional e ter tempo de resposta inferior a 3 segundos para submissões.
```

**Resultado obtido**:

1. **Glossário**: não gerado — nenhum documento-matriz presente em `data/matrix/`. Etapa pulada pelo agente conforme instruído.

2. **Artefatos gerados**:
   - HU-001: Criação de Exercícios de Programação (persona: Professor)
   - HU-002: Submissão e Avaliação do Código pelo Aluno (persona: Aluno)
   - RF-001: Execução Segura de Código — sandbox Docker (hu_parent: HU-002, prioridade: Alta)
   - RF-002: Feedback Pedagógico com IA — análise via LLM (hu_parent: HU-002, prioridade: Alta)
   - RF-003: Autenticação Institucional — protocolo LDAP (sem hu_parent, prioridade: Alta)
   - RNF-001: Tempo de Resposta das Submissões — inferior a 3s, com métrica definida (prioridade: Alta)

3. **Validação**:
   - Parecer: `APROVADO_COM_RESSALVAS`
   - Problemas críticos: 0
   - Problemas não-críticos: 3 (termos sem definição no glossário)
   - Recomendações: adicionar definições de `sandbox`, `LLM` e `LDAP` ao glossário

4. **Doubt Artifacts gerados**:
   - D-VAL-001 (RF-001): termo `sandbox` sem definição formal no glossário — não bloqueante
   - D-VAL-002 (RF-002): termo `LLM` sem definição formal no glossário — não bloqueante
   - D-VAL-003 (RF-003): termo `LDAP` sem definição formal no glossário — não bloqueante

5. **Verificações adicionais**:
   - Arquivos `.md` criados em `docs/Time_1_Requisitos/HUs/`, `RFs/` e `RNFs/`
   - Nenhum Doubt Artifact bloqueante
   - Raciocínio documentado com prefixo `PASSO [N]:` antes do JSON

### Validação manual passo a passo

1. Coloque o texto acima como prompt na interface web (ou via código).
2. Verifique se o glossário foi populado em `knowledge/glossario.md`.
3. Confirme a criação dos arquivos em `docs/Time_1_Requisitos/{HUs,RFs,RNFs}/`.
4. Verifique que o `analysis_result` contém JSON válido com `status: "concluido"`.
5. Confirme que o parecer de validação não é `BLOQUEADO`.

---

## 6. Lista de Erros Identificados

### E-001: Validação falha por artefatos não salvos

| Campo | Detalhe |
|---|---|
| **Sintoma** | `validacao_agent` retorna "Nenhum artefato encontrado para validar" |
| **Causa** | O agente principal invocou a validação ANTES de salvar os artefatos com `tool_salvar_artefato_requisito` |
| **Solução** | Garantir que TODOS os artefatos estejam salvos antes de delegar ao `validacao_agent`. A instrução do prompt já especifica isso, mas o LLM pode falhar em seguir a ordem. |

### E-002: Glossário não gerado — arquivo não encontrado

| Campo | Detalhe |
|---|---|
| **Sintoma** | `glossario_agent` retorna erro de arquivo não encontrado em `data/matrix/` |
| **Causa** | Nenhum documento-matriz (PDF/TXT/MD) foi colocado na pasta `data/matrix/` |
| **Solução** | Colocar o documento de referência em `data/matrix/` antes de iniciar a sessão. Se não houver documento, o agente principal deve pular a etapa de glossário conforme instruído. |

### E-003: IDs duplicados ou fora do padrão

| Campo | Detalhe |
|---|---|
| **Sintoma** | `tool_salvar_artefato_requisito` retorna "id_req inválido. Use o padrão AAAA-999" |
| **Causa** | O LLM gerou IDs fora do padrão regex `^[A-Z]{1,4}-\d{3}$` (ex: `HU-01` ao invés de `HU-001`) |
| **Solução** | Os few-shot examples reforçam o padrão correto. Se persistir, ajustar o prompt com exemplos adicionais. |

### E-004: Modelo LLM não configurado

| Campo | Detalhe |
|---|---|
| **Sintoma** | Erro de autenticação ou modelo não encontrado ao iniciar o agente |
| **Causa** | Variável `ADK_LLM_MODEL` ausente ou configurada com modelo inválido |
| **Solução** | Configurar no `.env` com um modelo válido do LiteLLM (ex: `github_copilot/gpt-4o`). |

### E-005: Loop infinito de validação

| Campo | Detalhe |
|---|---|
| **Sintoma** | O agente fica preso corrigindo e revalidando indefinidamente |
| **Causa** | Bug em versões anteriores onde o retry de validação não tinha limite |
| **Solução** | Já corrigido — o prompt atual limita a **1 tentativa de correção**. Se após a correção o parecer ainda for BLOQUEADO, o agente encerra normalmente e os problemas ficam registrados nos Doubt Artifacts. |

### E-006: Suporte a PDF indisponível

| Campo | Detalhe |
|---|---|
| **Sintoma** | `ImportError: Suporte a PDF requer PyMuPDF` ao usar `extract_text` com PDF |
| **Causa** | Dependência `pymupdf` não instalada |
| **Solução** | Instalar com `pip install pymupdf`. Arquivos TXT e MD funcionam sem essa dependência. |

---

## 7. Ferramentas (Tools)

O agente utiliza ferramentas compartilhadas do módulo `shared/tools/`, registradas como `FunctionTool` ou `AgentTool`:

### Tools do Agente Principal

| Tool | Tipo | Descrição |
|---|---|---|
| `run_slicer` | FunctionTool | Fragmenta documentos grandes em chunks com overlap por parágrafos. Salva em `data/chunks/`. |
| `ler_chunk` | FunctionTool | Lê um chunk específico por índice numérico. |
| `gerar_doubt_artifact` | FunctionTool | Gera arquivo Markdown versionado em `docs/Time_1_Requisitos/Doubt_Artifacts/` registrando dúvida ou ambiguidade. |
| `tool_salvar_artefato_requisito` | FunctionTool | Persiste artefato (HU/RF/RNF/RN) como `.md` no diretório apropriado. Valida padrão de ID. |
| `check_glossary` | FunctionTool | Consulta se um termo já existe no glossário (busca case-insensitive). |
| `glossario_agent` | AgentTool | Delega ao sub-agente de glossário para extração de termos técnicos. |
| `validacao_agent` | AgentTool | Delega ao sub-agente de validação para análise de qualidade dos artefatos. |

### Tools do Sub-Agente de Glossário

| Tool | Descrição |
|---|---|
| `extract_text` | Extrai texto integral de PDF, TXT ou MD. Aceita diretório (usa o primeiro arquivo encontrado). |
| `run_slicer` | Fatia documento-matriz em chunks. |
| `run_search` | Busca case-insensitive de termos em todos os chunks, retornando trechos com contexto. |
| `add_to_glossary` | Adiciona ou atualiza termo na tabela Markdown do glossário. |
| `check_glossary` | Consulta glossário existente. |
| `gerar_doubt_artifact` | Registra dúvida se glossário ficar vazio. |

### Tools do Sub-Agente de Validação

| Tool | Descrição |
|---|---|
| `ler_artefatos_gerados` | Lê artefatos de `docs/Time_1_Requisitos/` por IDs específicos ou por tipo. Infere o tipo pelo prefixo do ID. |
| `check_glossary` | Verifica termos no glossário antes de classificá-los como ambíguos. |
| `gerar_doubt_artifact` | Registra cada problema encontrado durante a validação (campo `bloqueante` indica severidade). |

---

## 8. Estrutura de Arquivos do Pacote

```
requirements/
├── .adk/
│   └── session.db            # Banco de sessão SQLite gerenciado pelo ADK
├── agent.py                  # Definição dos 3 agentes e suas tools
├── prompt.py                 # System prompts (instruction + description + validação)
├── schemas.py                # Modelos Pydantic (AnalystOutput, UserStory, etc.)
├── few_shot.py               # 4 exemplos de referência (HU, RF, Doubt, Glossário)
├── __init__.py               # Exporta root_agent
├── README.md                 # Esta documentação
├── data/
│   ├── matrix/               # Documento-matriz de entrada (PDF/TXT/MD)
│   └── chunks/               # Chunks gerados automaticamente pelo slicer
└── knowledge/
    └── glossario.md           # Glossário de termos técnicos (tabela Markdown)
```

---

## 9. Variáveis de Ambiente

| Variável | Obrigatória | Default | Descrição |
|---|---|---|---|
| `ADK_LLM_MODEL` | Sim | `github_copilot/gpt-4o` | Modelo LLM utilizado por todos os agentes (principal, glossário e validação) |
| `ADK_AGENT_DATA_DIR` | Não | CWD | Diretório base para `data/` e `knowledge/` |
| `ADK_DOCS_DIR` | Não | `docs/` (relativo ao CWD) | Diretório base para saída de artefatos |

> **Nota**: Todos os agentes (principal, glossário e validação) usam o mesmo modelo configurado em `ADK_LLM_MODEL`.
