# ADK — agentes e orquestração

## Estrutura

```text
adk/
├── app/
│   └── main.py                 # Entry point FastAPI + ADK (default agents_dir=src/agents)
├── src/
│   └── agents/                 # ← caminho padrão escaneado pelo adk web
│       ├── architect/
│       ├── coder/
│       ├── design_architect/
│       ├── design_orchestrator/
│       ├── finalizer/
│       ├── io_agent/
│       ├── markdown_specialist/
│       ├── mermaid_specialist/
│       ├── orchestrator/
│       ├── qa_agent/
│       ├── requirements/
│       ├── reviewer/
│       ├── test_planner/
│       ├── validator/
│       ├── workflow_coding/             # pipeline SDLC completo
│       ├── workflow_coding_review/      # pipeline enxuto requisitos→coder→review
│       └── workflow_design_pipeline/    # pipeline de design
├── shared/
│   └── tools/                  # tools compartilhadas (git, filesystem, slicer, etc)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── evals/
├── .env
├── .env.example
└── pyproject.toml
```

Cada subpasta de `src/agents/` é um agente runnável pelo ADK Dev UI. O `__init__.py` de cada agente exporta `root_agent`; a implementação principal vive em `agent.py`.

## Execução local

Na raiz do diretório `adk/`:

```bash
uv sync
```

Copie `.env.example` para `.env` e preencha. Modelo padrão: **`github_copilot/gpt-4`** (sobrescreva com `ADK_LLM_MODEL`).

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8081
```

Dev UI: `http://127.0.0.1:8081/dev-ui/?app=<nome_do_agente>`

Exemplos:
- `?app=orchestrator` — orquestrador completo
- `?app=workflow_coding` — pipeline SDLC sequencial
- `?app=qa_agent` — agente de QA isolado
- `?app=requirements` — agente de requisitos com glossário

### Override de diretório (avançado)

Por padrão `app/main.py` escaneia `src/agents/`. Para apontar para outro diretório:

```bash
export ADK_AGENTS_DIR=outro/caminho
```

### Workspace de saída dos agentes

Todos os artefatos produzidos pelos agentes (requisitos, design, código, relatórios, testes) são gravados em um diretório de workspace configurável via variável de ambiente:

```bash
# .env
WORKSPACE_OUTPUT_DIR=./workspace_output   # default
```

Aceita caminhos absolutos (`/opt/ai4se/output`), relativos ao CWD (`workspace_output`), e com `~` (`~/ai4se_output`).

Estrutura criada automaticamente:

```text
$WORKSPACE_OUTPUT_DIR/
├── .ai4se_workspace          # marker de segurança (não remova)
├── requirements/             # Time 1 — HUs, RFs, RNFs, glossário
├── design/                   # Time 2 — análises técnicas
│   ├── diagrams/             #   diagramas Mermaid
│   ├── reports/              #   relatórios Markdown
│   ├── staging/              #   staging do io_agent
│   └── validation/           #   validações
├── tasks/                    # Time 4 — tasks contextualizadas (JSON)
├── coder/                    # Time 4 — código gerado
├── review/                   # Time 4 — relatórios de revisão
├── tests/                    # Time 3 — testes e QA
│   ├── inputs/               #   requisitos recebidos pelo QA
│   ├── planning/             #   planejamento de testes
│   └── fixes/                #   correções automáticas
└── ...
```

O workspace e limpo e recriado pelo **orchestrator** no inicio de cada fresh run. Um marker `.ai4se_workspace` e gravado na raiz para evitar que `init_workspace()` apague acidentalmente um diretorio que nao seja workspace.

## Execução com Docker

Pré-requisito: **Docker** (e Docker Compose) instalados. Copie `.env.example` para `.env` e preencha.

**Opção A — sem build** (monta o código como volume, instala deps a cada start):

```bash
docker compose up
```

**Opção B — com build** (dependências embutidas na imagem, starts mais rápidos):

```bash
docker compose -f docker-compose.build.yml up --build
```

Acesse `http://localhost:8081/dev-ui/?app=orchestrator`.

### Primeira execução — autenticação obrigatória

Na **primeira vez** que o container subir, o LiteLLM iniciará o fluxo de autenticação OAuth do GitHub Copilot. Para completá-lo:

1. Abra os logs do container em um terminal:

```bash
docker compose logs -f
```

2. Procure por uma linha contendo um **código** e a URL `https://github.com/login/device`.
3. Abra a URL no navegador, cole o código e autorize.
4. Após a autorização, os tokens são salvos no volume `copilot-tokens` e **não será necessário repetir** este passo em execuções futuras.

> **Sem Docker:** o mesmo fluxo ocorre no terminal onde o `uvicorn` está rodando.

## Exemplo end-to-end: site de fotógrafo via Dev UI

Receita reproduzível para gerar (e deixar funcional) um site FastAPI de organização de fotos usando o agente `orchestrator` pelo **Dev UI do ADK**. O `orchestrator` cobre **requirements → design → coding_review → qa**, mas o `coder` hoje pula templates Jinja2 e tests — esta receita inclui o gap-fill manual no fim.

### 1. Pré-requisitos

- `adk/.venv/` criado com `uv sync` (vide seção "Execução local")
- `GOOGLE_API_KEY` em `adk/.env` — o orchestrator usa `gemini-2.5-flash` via Google AI direto. Pegue em <https://aistudio.google.com/app/apikey>.

### 2. Subir o servidor dos agentes

A partir de `adk/`:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8081
```

Deixe esse terminal aberto — você precisa ver os logs durante a run.

### 3. Abrir o Dev UI no agente `orchestrator`

No navegador:

```
http://127.0.0.1:8081/dev-ui/?app=orchestrator
```

Você verá um chat com o título "orchestrator".

### 4. Colar o prompt do fotógrafo

Cole o texto abaixo na caixa de mensagem do Dev UI e envie:

````markdown
Sou fotógrafo profissional (retratos e casamentos) e preciso de um site simples para organizar minhas fotos e montar álbuns para entregar aos clientes. Hoje uso pastas no Drive e é uma bagunça — quero algo onde eu carregue as fotos de uma sessão e consiga curar um álbum final.

## O que preciso (use seu bom senso para o resto)

**Fluxo principal (caso de uso real):**
1. Crio um novo "Ensaio" (ex: "Casamento Joana & Pedro - Mai/2026") com data e cliente.
2. Faço upload em lote das fotos brutas do ensaio (JPEG/PNG, dezenas a centenas).
3. Visualizo as fotos do ensaio em galeria (thumbnails, clicáveis para ver maior).
4. Marco fotos como "selecionada para álbum" (favoritar/curar).
5. Crio um "Álbum" a partir do ensaio, contendo só as fotos selecionadas, com título e ordem.
6. Vejo a página final do álbum montado (capa + grid das fotos escolhidas) — essa é a entrega ao cliente.

**Stack — fique à vontade, mas tente algo simples e moderno:**
- Backend Python (FastAPI é minha preferência por ser leve)
- Frontend pode ser server-side rendering (Jinja2 + HTMX) OU SPA leve — você decide o que entrega mais valor com menos código
- Armazenamento local em disco para as imagens (não preciso de S3 nessa primeira versão)
- SQLite para metadados (ensaios, fotos, álbuns) — sem precisar subir Postgres

**Requisitos não-funcionais que importam pra mim:**
- Tem que rodar localmente com `uvicorn` em um comando
- Upload tem que aguentar pelo menos 50 fotos de uma vez sem travar
- Thumbnails gerados automaticamente (não quero carregar full-res na galeria)
- Visual minimalista e elegante (sou fotógrafo, o produto é a foto — interface não pode competir)

**O que NÃO preciso nessa versão:**
- Autenticação de usuário (só eu uso, localhost)
- Compartilhamento por link público
- Edição de imagem (corte/filtro)
- Marca d'água

## Critérios de aceite

- Consigo criar um Ensaio via interface web
- Consigo subir múltiplas fotos para esse Ensaio
- Vejo a galeria com thumbnails das fotos
- Marco fotos como selecionadas (toggle visível)
- Crio um Álbum a partir das fotos selecionadas
- Vejo a página final do álbum renderizada

## Como quero que vocês trabalhem

Passem pelo SDLC completo: requisitos → arquitetura/design → planejamento de testes → código → review → QA → finalização. Sejam criativos no design da arquitetura, mas mantenham simples — não preciso de microserviços nem de message broker. Quero um app monolítico bem feito.

Se vocês tiverem alguma dúvida estrutural, decidam vocês mesmos pelo caminho mais pragmático — confio no julgamento de vocês. O que eu preciso é que ao final eu tenha um repositório funcional que eu consiga subir e usar.
````

### 5. Acompanhar a execução

A run dura **3 a 5 minutos**. No Dev UI você vê tool calls e textos intermediários. No terminal do uvicorn aparecem 4 sub-runs encadeadas:

```
App name mismatch detected. The runner is configured with app name "requirements_pipeline" ...
App name mismatch detected. The runner is configured with app name "design_pipeline" ...
App name mismatch detected. The runner is configured with app name "coding_review_pipeline" ...
App name mismatch detected. The runner is configured with app name "qa_pipeline" ...
```

Esses warnings são **benignos** (o ADK só está sinalizando que o `root_agent` veio de outro módulo). A run termina quando o orchestrator devolve mensagem final no Dev UI — costuma incluir o relatório de revisão e algumas dúvidas em aberto do QA.

### 6. Inspecionar o que cada estágio produziu

Em outro terminal, dentro de `adk/`:

```bash
find workspace_output -type f | sort
```

Esperado:

| Subpasta | Origem | Conteúdo |
|---|---|---|
| `workspace_output/requirements/` | `requirements_pipeline` | `HUs/`, `RFs/`, `RNFs/`, `RNs/`, `Glossario.md` |
| `workspace_output/design/` | `design_pipeline` | `analise_tecnica_HU-*.md` + doubt artifacts |
| `workspace_output/coder/` | `coding_review_pipeline` | `app/main.py`, `app/models.py`, `app/routers/`, `requirements.txt` |
| `workspace_output/review/` | `coding_review_pipeline` | `verificacao_revisao.md` (relatório do reviewer) |
| `workspace_output/tests/` | `qa_pipeline` | **geralmente vazio** — `action_planner` trava em HITL antes de gerar |

> **Importante**: `workspace_output/` é apagado e recriado pelo `orchestrator` no início de cada fresh run. Antes de qualquer reexecução, copie para fora se quiser preservar:
>
> ```bash
> cp -r workspace_output /tmp/fotografo-app
> ```

### 7. Gap-fill: templates Jinja2 + fix em `main.py`

O `coder` consistentemente:
- Referencia `Jinja2Templates(directory="app/templates")` nos routers, mas **não cria os arquivos HTML**
- Faz `@app.get("/")` retornar `templates.TemplateResponse("index.html", ...)` **sem passar a variável `ensaios`** que o template precisa

Vá até a cópia do código:

```bash
cd /tmp/fotografo-app/coder
```

Veja quais templates são esperados:

```bash
grep -rhoE 'TemplateResponse\("[^"]+"' app | sort -u
# Saída esperada:
#   TemplateResponse("album_detail.html"
#   TemplateResponse("create_ensaio.html"
#   TemplateResponse("ensaio_detail.html"
#   TemplateResponse("index.html"
```

Crie `app/templates/` com 5 arquivos: `base.html` (layout compartilhado) + os 4 listados acima. Mantenha CSS inline — Tailwind/Bootstrap são overkill aqui. O fotógrafo pediu visual minimalista; fundo escuro com acento dourado funciona bem.

Estrutura mínima de cada template:

- **`base.html`** — head com `<style>` e header com navegação para `/ensaios/` e `/ensaios/create/`; block `content` no `<main>`.
- **`index.html`** — lista `ensaios` (cada item com link para `/ensaios/{id}`) + botão "Novo ensaio".
- **`create_ensaio.html`** — form POST para `/ensaios/` com campos `titulo`, `cliente`, `data` (type=date).
- **`ensaio_detail.html`** — header com `ensaio.titulo` + contagem de fotos selecionadas; form de upload (POST `/ensaios/{id}/upload_fotos/` com `enctype="multipart/form-data"` e `<input type="file" name="files" multiple>`); galeria iterando `fotos` (cada foto é um `<form>` POST para `/fotos/{id}/toggle_selecao/`); se há `selecionadas`, mostra form de criar álbum (POST `/ensaios/{id}/create_album/`).
- **`album_detail.html`** — capa centralizada com `album.titulo` + grid das `fotos` em alta.

Substitua o handler raiz em `app/main.py`:

```python
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.routers import ensaios, fotos, albuns
import os

os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/thumbnails", exist_ok=True)

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Estúdio")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(ensaios.router)
app.include_router(fotos.router)
app.include_router(albuns.router)

@app.get("/")
async def root():
    return RedirectResponse(url="/ensaios/", status_code=303)
```

Garanta os `__init__.py` (sem eles os imports `app.routers.X` falham):

```bash
touch app/__init__.py app/routers/__init__.py app/utils/__init__.py
```

### 8. Subir o app gerado

```bash
cd /tmp/fotografo-app/coder
uv venv --python 3.12
VIRTUAL_ENV=$PWD/.venv uv pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8090
```

> `VIRTUAL_ENV=$PWD/.venv` força o `uv pip install` a usar o venv local. Sem isso, o `uv` enxerga o `.venv` do `adk/` pai e instala lá — sintoma é `Audited N packages` em vez de `+ pacote==versão`.

### 9. Validar o golden path no navegador

Abra <http://127.0.0.1:8090/> e exercite a sequência:

1. **Criar ensaio** — clique em "Novo ensaio", preencha (ex: "Casamento Joana & Pedro - Mai/2026", cliente "Joana & Pedro", data 17/05/2026) e envie. Você deve cair em `/ensaios/1` com a galeria vazia.
2. **Upload** — selecione 5 a 10 JPEGs/PNGs e envie. A galeria deve mostrar thumbnails (200×200) gerados pelo Pillow.
3. **Selecionar fotos** — clique em algumas fotos. Cada clique faz POST `/fotos/{id}/toggle_selecao/` e adiciona uma borda dourada (`class="photo selected"`).
4. **Criar álbum** — quando houver pelo menos 1 foto selecionada, o form "Montar álbum" aparece. Preencha o título e envie.
5. **Página final** — você é redirecionado para `/albuns/1`, que mostra capa + grid das fotos curadas em alta resolução.

Confira no disco que o estado bate:

```bash
ls static/uploads/      # arquivos originais
ls static/thumbnails/   # thumbs do mesmo nome
ls -la sql_app.db       # banco SQLite ~30KB depois do primeiro álbum
```

### 10. Caveats que você vai encontrar

- **`Album.fotos_ids` como string CSV** (`"1,3,5"`): o reviewer marca como Critical (viola 1ª forma normal). Refatorar implicaria uma tabela `album_fotos` many-to-many — fora do escopo de "deixar funcional".
- **Sem testes**: o `qa_pipeline` para em HITL checkpoint pedindo aprovação humana. Comportamento atual, não bug.
- **HEAD `/` retorna 405**: `RedirectResponse` está só em `@app.get`. Não importa para uso real (navegadores fazem GET).
- **Reviewer também aponta validação de data e duplicação na criação de diretórios** — vale ler `workspace_output/review/verificacao_revisao.md` para os detalhes; nada bloqueia o fluxo manual.

### 11. Reset para tentar de novo

Pare o uvicorn do `adk/` (Ctrl+C) e do app gerado, então:

```bash
rm -rf adk/workspace_output/   # limpa artefatos da run anterior
rm -rf /tmp/fotografo-app      # limpa o app gerado
```

Reinicie o uvicorn do `adk/`, reabra o Dev UI e cole o prompt de novo. O `orchestrator` executa `init_workspace()` no início de cada fresh run e recria `workspace_output/` zerado.

## GitHub Copilot (LiteLLM)

Os agentes usam o provedor **`github_copilot/`** via [LiteLLM](https://docs.litellm.ai/docs/providers/github_copilot).

1. **Requisito** — Conta com **GitHub Copilot** ativo.
2. **Primeira autenticação** — Na primeira chamada, siga o device flow no **terminal do uvicorn** (`https://github.com/login/device`).
3. **Tokens** — Salvos em `~/.config/litellm/github_copilot/` (configurável via `GITHUB_COPILOT_TOKEN_DIR`).
