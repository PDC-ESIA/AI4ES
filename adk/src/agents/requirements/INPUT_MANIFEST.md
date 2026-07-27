# Manifesto de Entrada — Requirements Agent

## O que é

O manifesto de entrada é um arquivo JSON gerado pelo orchestrador **antes** de invocar o
`requirements_pipeline`. Ele descreve os arquivos enviados pelo usuário na sessão atual,
fornecendo ao `requirements_agent` os caminhos e metadados necessários para localizar e
processar os documentos de entrada (PRDs, documentos de requisitos, etc.).

É o par simétrico do manifesto de saída (`manifest.json`) — enquanto o de saída descreve
o que o agente **produziu**, o de entrada descreve o que o agente **vai consumir**.

## Responsabilidades

| Quem | O quê |
|------|-------|
| `app/main.py` | Recebe os arquivos via upload HTTP e os salva em `workspace_output/inputs/` |
| Orchestrador | Varre `workspace_output/inputs/`, gera o `input_manifest.json` e injeta o path no input do `requirements_pipeline` |
| `requirements_agent` | Lê o `input_manifest.json`, itera sobre `files` e usa `extract_text` ou `run_slicer` para processar cada arquivo |

## Localização

```
workspace_output/
└── inputs/
    ├── input_manifest.json   ← manifesto de entrada
    ├── documento.pdf
    └── requisitos.md
```

## Estrutura

```json
{
  "phase": "input",
  "session_id": "<id da sessão gerado pelo orchestrador>",
  "created_at": "<timestamp ISO 8601, ex: 2026-07-26T16:00:00Z>",
  "status": "ready",
  "files": [
    {
      "path": "inputs/documento.pdf",
      "filename": "documento.pdf",
      "type": "pdf",
      "size_bytes": 12345,
      "description": "Documento de requisitos do sistema TACO"
    }
  ],
  "summary": "1 arquivo(s) disponíveis para análise."
}
```

## Campos

### Raiz

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `phase` | `string` | Sempre `"input"`. Identifica o manifesto como sendo de entrada. |
| `session_id` | `string` | ID da sessão do orchestrador. Permite rastrear quais arquivos pertencem a qual execução. |
| `created_at` | `string` | Timestamp ISO 8601 de quando o manifesto foi gerado. |
| `status` | `string` | `"ready"` se há arquivos disponíveis. `"empty"` se nenhum arquivo foi enviado — o agente deve processar o texto do prompt normalmente, sem tentar ler arquivos. |
| `files` | `array` | Lista de objetos, um por arquivo enviado. Vazio (`[]`) quando `status` é `"empty"`. |
| `summary` | `string` | Mensagem legível resumindo o conteúdo do manifesto. |

### Objeto dentro de `files`

Cada arquivo enviado pelo usuário gera **um objeto** dentro do array `files`.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `path` | `string` | Caminho relativo ao `workspace_root` onde o arquivo foi salvo. Usado pelo agente para localizar o arquivo. |
| `filename` | `string` | Nome original do arquivo enviado pelo usuário. |
| `type` | `string` | Extensão do arquivo sem ponto: `"pdf"`, `"md"` ou `"txt"`. Indica ao agente qual estratégia de leitura usar. |
| `size_bytes` | `integer` | Tamanho do arquivo em bytes. Se o arquivo for grande, o agente deve usar `run_slicer` em vez de `extract_text` direto. |
| `description` | `string` | Descrição opcional fornecida pelo usuário no momento do upload. Pode ser vazia (`""`). |

## Exemplo com múltiplos arquivos

```json
{
  "phase": "input",
  "session_id": "sess-abc123",
  "created_at": "2026-07-26T16:00:00Z",
  "status": "ready",
  "files": [
    {
      "path": "inputs/prd_sistema.pdf",
      "filename": "prd_sistema.pdf",
      "type": "pdf",
      "size_bytes": 204800,
      "description": "PRD principal do sistema"
    },
    {
      "path": "inputs/glossario_cliente.md",
      "filename": "glossario_cliente.md",
      "type": "md",
      "size_bytes": 3200,
      "description": "Glossário de termos fornecido pelo cliente"
    }
  ],
  "summary": "2 arquivo(s) disponíveis para análise."
}
```

## Exemplo sem arquivos

```json
{
  "phase": "input",
  "session_id": "sess-xyz789",
  "created_at": "2026-07-26T17:00:00Z",
  "status": "empty",
  "files": [],
  "summary": "Nenhum arquivo enviado. O agente processará o texto do prompt diretamente."
}
```

## Notas de implementação

- O manifesto deve ser gerado **antes** de invocar o `requirements_pipeline`, como função determinística (zero LLM), análoga ao `emit_requirements_manifest`.
- O path injetado no input do `requirements_pipeline` deve ser o caminho absoluto do `input_manifest.json`.
- O `requirements_agent` deve verificar `status` antes de tentar processar `files` — se `"empty"`, deve processar o texto do prompt diretamente, sem tentar ler arquivos.
- O campo `size_bytes` é o critério sugerido para decidir entre `extract_text` (arquivos pequenos) e `run_slicer` (arquivos grandes). O threshold recomendado é **100KB**.
