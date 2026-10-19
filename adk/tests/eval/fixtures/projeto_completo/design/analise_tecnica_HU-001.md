# Análise técnica — HU-001

## Escopo

Serviço HTTP de consulta ao catálogo de livros, cobrindo RF-001 e RF-002.

## Stack

- Python 3.12 com FastAPI
- Persistência em SQLite via SQLAlchemy
- Testes com pytest

## Componentes

| Componente | Responsabilidade |
|---|---|
| `app/main.py` | Monta a aplicação e registra as rotas |
| `app/rotas.py` | `GET /livros`, com o parâmetro opcional `autor` |
| `app/modelos.py` | Modelo `Livro` (`id`, `titulo`, `autor`, `disponivel`) |
| `app/repositorio.py` | Consulta ao banco, ordenação por título e filtro por autor |

## Interfaces

- `GET /livros` → `200` com `[{"id": int, "titulo": str, "autor": str, "disponivel": bool}]`
- `GET /livros?autor=<texto>` → mesmo contrato, filtrado, comparação sem diferenciar caixa

## Decisões

- O filtro é aplicado no repositório, não na rota, para manter a rota fina.
- A ordenação por título é responsabilidade do repositório.
