# Regras de consistência

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
