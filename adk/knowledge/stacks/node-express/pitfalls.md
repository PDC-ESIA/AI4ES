# Pitfalls — stack `node-express`

## CommonJS vs ES Modules — não misture `require` e `import`

O modo do projeto é decidido pelo campo `"type"` do `package.json`
(`"commonjs"` — o default se o campo não existir — ou `"module"`). Misturar
`require(...)` num arquivo `.js` de um projeto `"type": "module"` (ou
vice-versa) quebra com `SyntaxError: Cannot use import statement outside a
module` ou `ReferenceError: require is not defined in ES module scope`.

Escolha um modo no início e use em todos os arquivos do projeto.

## Erro assíncrono dentro de rota do Express não é capturado sozinho

Uma `Promise` rejeitada dentro de um handler `async (req, res) => {...}` sem
`try/catch` não chega ao middleware de erro do Express (isso só mudou por
padrão no Express 5 — não assuma). O processo Node não crasha, mas a
requisição fica pendurada sem resposta até o cliente dar timeout.

Correto:
```js
app.get("/ensaios/:id", async (req, res, next) => {
  try {
    const ensaio = await buscarEnsaio(req.params.id);
    res.json(ensaio);
  } catch (err) {
    next(err); // repassa pro middleware de erro
  }
});
```

## `.env` precisa ser carregado ANTES de qualquer módulo que leia `process.env`

`require("dotenv").config()` (ou `import "dotenv/config"`) tem que rodar antes
de qualquer `import`/`require` que dependa de uma variável de ambiente — se um
módulo de configuração de banco é importado antes do `dotenv` carregar, ele lê
`undefined` silenciosamente, sem erro.

## Porta e host consistentes entre Dockerfile e docker-compose

Mesmo princípio do `core/consistency-rules.md`: a porta em `EXPOSE`/`CMD` do
Dockerfile precisa bater com o mapeamento do `docker-compose.yml`. Além disso,
o servidor Node precisa escutar em `0.0.0.0`, não em `localhost`/`127.0.0.1` —
dentro do container, `localhost` não expõe a porta pra fora.
