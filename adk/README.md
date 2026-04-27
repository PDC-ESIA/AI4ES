# AI4ES — Pipeline de Análise de HUs

## Pré-requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Conta GitHub

---

## Primeira execução

### 1. Criar e ativar o ambiente virtual

```bash
python -m venv venv
```

Linux/macOS:
```bash
source venv/bin/activate
```

Windows:
```bash
venv\Scripts\activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Autenticação — GitHub Copilot (OAuth)

Não é necessária nenhuma chave de API. A autenticação é feita via GitHub na primeira execução:

1. Inicie o servidor normalmente (próxima seção)
2. Nos logs do uvicorn, aparecerá uma mensagem solicitando autenticação com um **link e um código de ativação**
3. Acesse o link indicado nos logs
4. Insira o código exibido e autorize o acesso via GitHub
5. Após autorização, o servidor continuará normalmente

> A autenticação é via OAuth — nenhuma chave precisa ser configurada manualmente.  

---

## Executando o servidor

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Acesse a interface em:
```
http://localhost:8000/dev-ui
```

Selecione o agente **orchestrator** na interface.

---

## Como usar

Envie um lote de HUs no chat. O pipeline executa automaticamente:

1. Valida e padroniza as HUs
2. Gera decisões de arquitetura e diagramas `.mmd`
3. Valida os artefatos gerados
4. Salva os resultados em `temp/staging/`

### Resultado sem dúvidas — promover para entrega

Quando o agente não identificar lacunas, um relatório `.md` será gerado em `temp/staging/`. Para promover para entrega final:

1. Abra o relatório em `temp/staging/`
2. Altere `**Status:** Em análise` para `**Status:** Aprovado`
3. Solicite no chat: `promova os artefatos para artifacts`

### Resultado com dúvidas — `Doubt Artifact`

Quando o agente identificar ambiguidades ou lacunas nas HUs, um arquivo `Doubt_Artifact_*.md` será gerado em `temp/staging/` no lugar do relatório.

O arquivo contém:

- O problema identificado
- A informação necessária para prosseguir

Corrija a HU com a informação faltante e reenvie o lote.

---

## Dicas

- Exemplos de HUs testadas estão em `prompt-test.md`, com exemplos de resultados esperados presentes.
- HUs vagas ou sem critérios de aceite detalhados **geram Doubt Artifacts**
- O agente não inventa informações — lacunas bloqueiam o pipeline
