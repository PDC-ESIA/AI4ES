# Execução Local

```bash
uv sync
```

Linux:

```bash
source .venv/bin/activate
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Windows:

```bash
.venv\Scripts\activate
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Teste

```url
http://localhost:8000/dev-ui
```

Selecione o agente **orchestrator** na interface.

## Como funciona

Envie um lote de HUs no chat. O pipeline executa automaticamente:

1. Valida e padroniza as HUs
2. Gera decisões de arquitetura e diagramas `.mmd`
3. Valida os artefatos gerados
4. Salva em `temp/staging/` para revisão

Para promover para `artifacts/` (entrega final):

- Abra o relatório `.md` em `temp/staging/` e altere `**Status:** Em análise` para `**Status:** Aprovado`
- Solicite no chat: `promova os artefatos para artifacts`

## Dicas

- Há prompts de exemplo em `prompt-test.md`
