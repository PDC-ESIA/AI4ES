# probe — cliente HTTP estático injetável

Binário Go estático (`CGO_ENABLED=0`) que bate nas rotas **de dentro** do
container implantado, sem depender de `curl`/`wget`/`python` estarem na imagem
(funciona até em `scratch`/distroless). É injetado via `docker cp`
(`put_archive`) e executado via `docker exec` — ver `shared/tools/probe.py`.

## Contrato de I/O

Entrada: arquivo JSON com uma lista de requisições. Saída: JSON no stdout, uma
entrada por requisição, **mesma ordem**.

```json
// entrada (request-spec.json)
[
  {"method": "GET",  "path": "/users/1", "timeout_ms": 2000},
  {"method": "POST", "path": "/users", "body": "{\"name\":\"teste\"}", "timeout_ms": 2000}
]
```

```json
// saída (stdout)
[
  {"method":"GET","path":"/users/1","status":200,"latency_ms":1,"error":null,"body":"..."},
  {"method":"POST","path":"/users","status":201,"latency_ms":0,"error":null,"body":"{\"id\":42}"}
]
```

`error` só é preenchido em falha de **transporte** (conexão recusada, timeout,
DNS). Qualquer resposta HTTP recebida — inclusive `4xx`/`5xx` — tem
`error: null`: não é erro do probe, é dado para quem chama decidir. `status: 0`
só ocorre junto com `error`. O `body` é capturado até 64KB.

Uso: `probe <request-spec.json> [base_url]` (base_url default: `http://localhost`).

## Build

```bash
./build.sh            # usa Go local se houver; senão, imagem golang no Docker
```

Gera `probe-linux-amd64` e `probe-linux-arm64` (estáticos). Equivalente manual:

```bash
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o probe-linux-amd64 .
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o probe-linux-arm64 .
```

Go não é necessário onde o harness roda — apenas para (re)gerar os binários.

> **Os binários NÃO são versionados** (ver `.gitignore`): são artefatos de
> build. Rode `./build.sh` antes do harness (ou pluge-o no build da imagem/CI),
> senão `shared/tools/probe.py` levanta `ProbeError` apontando este script.
