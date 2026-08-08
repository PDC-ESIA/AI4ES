# Dependências — stack `node-express`

> Semeada só o suficiente para o braço B (long-context) do protocolo de validação
> (relatório §11.2) ter algo real pra despejar além de `python-fastapi` — hoje o
> harness só executa Python (G8), então esta stack não é testável de ponta a
> ponta ainda. Conteúdo genuíno, não placeholder.

## Pacotes conhecidamente bons para este stack

| Pacote | Uso |
|---|---|
| `express` | framework web |
| `cors` | middleware de CORS |
| `dotenv` | variáveis de ambiente a partir de `.env` |
| `morgan` | log de requisições HTTP |
| `helmet` | headers de segurança básicos |
| `mongoose` | ODM para MongoDB (se a stack usar Mongo) |
| `pg` | driver PostgreSQL (se a stack usar Postgres) |
| `nodemon` | reload em desenvolvimento — nunca em produção/Docker final |

## NÃO são pacotes npm — nunca coloque no package.json por engano

`body-parser` — desde o Express 4.16, `express.json()` e `express.urlencoded()`
já vêm embutidos; adicionar o pacote separado é redundante, não incorreto (mas
sinaliza desatualização). Não é um erro fatal como no caso do FastAPI/PyPI, só
inchaço de dependência.
