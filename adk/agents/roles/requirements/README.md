# Requirements Agent

**Time:** Requisitos
**Modelo padrão:** `github_copilot/gpt-4`
**Override:** `ADK_LLM_MODEL`

## Objetivo

O Requirements Agent transforma solicitações em linguagem natural, PRDs e documentos de requisitos em uma análise estruturada para o pipeline de engenharia.

O agente não implementa código, não define arquitetura e não escreve testes. Ele produz artefatos de requisitos claros, verificáveis e rastreáveis.

## Contrato de Saída

A saída principal do agente é `analysis_result`, seguindo o schema `AnalystOutput`:

```json
{
  "status": "concluido",
  "user_stories": [],
  "functional_requirements": [],
  "non_functional_requirements": [],
  "use_cases": [],
  "business_rules": [],
  "glossary": [],
  "doubt_generated": false,
  "summary": "Resumo objetivo do processamento."
}
```

Esse contrato substitui a saída simplificada baseada apenas em `requirements`.

## Estrutura

```text
agents/roles/requirements/
├── __init__.py
├── agent.py
├── prompt.py
├── schemas.py
├── few_shot.py
├── data/
│   ├── chunks/
│   └── matrix/
├── knowledge/
│   └── glossario.md
└── README.md
```

## Funcionamento

O agente opera em duas camadas:

1. `requirements_agent`: coordena a análise global e gera HUs, RFs, RNFs, UCs, regras de negócio, glossário e resumo.
2. `glossario_agent`: sub-agente especializado em extrair termos técnicos e manter `knowledge/glossario.md`.

## Tipos de Entrada

### Texto direto

Use para pedidos simples ou descrições curtas:

```text
Preciso de um sistema de login com recuperação de senha por e-mail.
```

### PRD como texto

Use para documentos colados diretamente no prompt:

```text
Módulo: Autenticação
O sistema deve permitir cadastro, login, logout e recuperação de senha.
```

### Documento em arquivo

Use um caminho para `.md`, `.txt` ou `.pdf` quando o conteúdo estiver em arquivo:

```text
Analise o documento em: agents/roles/requirements/data/matrix/prd.md
```

Para documentos grandes, coloque o arquivo em `agents/roles/requirements/data/matrix/` e use as tools de fatiamento.

## Tools

As tools seguem um modelo misto:

- Tools reutilizáveis ficam em `shared/tools`.
- Lógica estritamente específica do papel Requirements pode ficar no diretório do agente.

Tools usadas pelo agente:

| Tool | Uso |
| --- | --- |
| `extract_text` | Ler `.md`, `.txt`, `.pdf` ou primeiro arquivo suportado em um diretório. |
| `run_slicer` | Fragmentar documentos grandes em chunks. |
| `ler_chunk` | Ler um chunk específico. |
| `run_search` | Buscar termos nos chunks. |
| `gerar_doubt_artifact` | Registrar ambiguidades, contradições ou lacunas. |
| `tool_salvar_artefato_requisito` | Persistir HU, RF, RNF, RN, UC ou glossário em Markdown. |
| `check_glossary` | Verificar se um termo já existe no glossário. |
| `add_to_glossary` | Adicionar ou atualizar termos no glossário. |
| `glossario_agent` | Delegar extração e validação de termos técnicos. |

## Configuração

No ambiente `adk/`, configure:

```env
ADK_LLM_MODEL=github_copilot/gpt-4
ADK_AGENT_DATA_DIR=agents/roles/requirements
```

`ADK_AGENT_DATA_DIR` define a base para `data/matrix`, `data/chunks` e `knowledge/glossario.md`.

## Doubt Artifact

Quando a entrada tiver ambiguidade ou lacuna que impeça especificação confiável, o agente deve usar `gerar_doubt_artifact` e marcar `doubt_generated=true`.

Se o bloqueio afetar apenas parte do escopo, o agente pode gerar os itens seguros e registrar a pendência no `summary`.

## Como Testar

### Pedido simples

```text
Crie requisitos para uma funcionalidade de login com e-mail e senha.
```

Resultado esperado: `analysis_result` com HUs e RFs coerentes.

### Entrada ambígua

```text
Faça o sistema funcionar melhor e ser mais rápido.
```

Resultado esperado: Doubt Artifact gerado e `status` como `bloqueado` ou pendência documentada.

### Documento-matriz

1. Coloque um `.md`, `.txt` ou `.pdf` em `agents/roles/requirements/data/matrix/`.
2. Peça a análise do documento.
3. Verifique chunks em `data/chunks/`, glossário em `knowledge/glossario.md` e saída `analysis_result`.

## Decisões de Merge

Este agente preserva a proposta completa do Time 1.

O commit `a1791fdd32c1eaad06e1691c63be8e5a84e4756e` foi usado como referência seletiva para padronizações, especialmente documentação, organização de tools e abandono das antigas Context Windows. A simplificação para `RequirementsOutput` com apenas `id`, `description` e `acceptance_criteria` não foi mantida como contrato principal.