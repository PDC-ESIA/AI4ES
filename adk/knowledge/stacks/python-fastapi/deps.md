# Dependências — stack `python-fastapi`

> Escopo: `stack:python-fastapi`. Allowlist curada, não um `requirements.txt` pinado único
> (decisão D1 — relatório §10.2: um `requirements.txt` de referência amarraria o pipeline a
> uma stack fixa, contrariando a intenção de remover a trava de stack). Fonte: o bloco
> `# ERROS COMUNS` original do `cr_coder.py` + a tabela de alias de
> `shared/tools/coding_tools/verificacao_dependencias.py::ALIAS_IMPORT_PARA_PACOTE`, mantidas
> em sincronia manual — se a tabela do gate mudar, atualize aqui também.

## Pacotes conhecidamente bons para este stack

| Pacote | Uso |
|---|---|
| `fastapi` | framework web |
| `uvicorn[standard]` | servidor ASGI |
| `jinja2` | templates server-side |
| `sqlalchemy` | ORM |
| `python-multipart` | parsing de upload multipart/form-data |
| `aiofiles` | I/O de arquivo assíncrono |
| `pydantic` | validação/schemas |
| `pydantic-settings` | configuração via env vars |
| `alembic` | migrações de schema |
| `httpx` | cliente HTTP (inclusive em testes) |
| `pytest` | testes |

## Nome de import ≠ nome de pacote PyPI

Nenhuma tabela de alias fica completa — por isso o gate (`verificacao_estatica`) trata
divergência de nome como `info`, não como bloqueio (D9). Os conhecidos hoje:

| `import X` | Pacote PyPI |
|---|---|
| `jose` | `python-jose` |
| `dotenv` | `python-dotenv` |
| `jwt` | `PyJWT` |
| `multipart` | `python-multipart` |
| `PIL` | `Pillow` |
| `yaml` | `PyYAML` |
| `bs4` | `beautifulsoup4` |
| `sklearn` | `scikit-learn` |
| `cv2` | `opencv-python` |

## NÃO são pacotes PyPI — nunca coloque no requirements.txt

HTMX, Alpine.js, Tailwind CSS, Bootstrap e jQuery são bibliotecas **JavaScript**, servidas via
CDN (`<script src="https://...">`) ou como arquivo estático — não via `pip`.

Nomes que parecem certos mas **não existem no PyPI**: `htmx.org`, `htmx`, `tailwindcss`,
`alpinejs`, `bootstrap`, `jquery`.

Regra prática: se não se instala com `pip install NOME`, não entra no `requirements.txt`.
