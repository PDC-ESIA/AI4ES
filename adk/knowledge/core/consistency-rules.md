# Regras de consistência

## O nome importado tem de ser o nome que o módulo de origem define

Antes de escrever `from meu_modulo import Simbolo`, confirme qual nome `meu_modulo`
**realmente declara**. O nome no `import` e o nome à esquerda do `=` no módulo de origem
são o mesmo texto, caractere por caractere — não há inferência.

É o modo de falha mais caro do pipeline porque **não aparece no build**: a imagem sobe
normalmente e a aplicação morre no import da primeira requisição, com
`ImportError: cannot import name 'X' from 'meu.modulo'`. O healthcheck só consegue
reportar "aplicação não inicializou", sem apontar o arquivo culpado — e a correção às
cegas costuma mexer no módulo errado.

Vale para qualquer símbolo entre módulos do projeto: função, classe, router, engine,
`Base` do ORM, instância de configuração.

Ao criar um pacote com vários módulos irmãos, **escolha uma convenção de nome e repita em
todos**. Ou cada módulo expõe `router`, ou cada módulo expõe `<dominio>_router`. Misturar
as duas é o que produz o erro, porque o arquivo que importa "adivinha" a forma do vizinho.

Correto: módulo define `router = APIRouter()` → `from app.controllers.galeria import router as galeria_router`
Errado: módulo define `router = APIRouter()` → `from app.controllers.galeria import galeria_router`

## Imports precisam constar no manifesto de dependências

Todo `import X` / `from X import ...` de um pacote de terceiros DEVE ter uma linha
correspondente no manifesto de dependências da stack (`requirements.txt`, `package.json`,
`go.mod`, ...). Nome de import raramente é igual a nome de pacote — confira antes de
assumir.

*(esta regra já tem um fiscal automático: o estágio `verificacao_estatica` do harness a
confere antes do build)*

## Dockerfile — COPY só o que existe

`COPY`/`ADD` no Dockerfile só deve referenciar arquivos ou diretórios que você de fato
criou nesta sessão via tool de escrita. Verifique a estrutura criada antes de escrever a
instrução — um `COPY` para um caminho inexistente derruba o build inteiro.

## Porta consistente entre Dockerfile e docker-compose

A porta mapeada no `docker-compose.yml` DEVE corresponder à porta exposta/usada no `CMD` e
no `EXPOSE` do Dockerfile (o padrão do pipeline é 8000 — ver `conventions.md`). `CMD` deve
referenciar o módulo EXATO onde o entrypoint da aplicação é instanciado.
