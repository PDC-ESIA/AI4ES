# Regras de consistência — core (agnóstico de stack)

> Escopo: `core`. Regras que verificam a coerência ENTRE artefatos que o coder produz — não
> convenções de estilo. Uma delas (import↔requirements) já tem contraparte executável no
> harness (`verificacao_estatica`, fail-open exceto no caso inequívoco — ver §8.3 do
> relatório); as demais ainda são só texto (feedforward sem sensor pareado, relatório §3.2) —
> candidatas naturais a virar gate no futuro se a taxa de repetição de erro justificar (§12.2).

---

```yaml
trigger:       import de terceiro sem entrada correspondente no manifesto de dependências
granularidade: estrategia
corpo: >
  Todo `import X` / `from X import ...` de um pacote de terceiros DEVE ter uma linha
  correspondente no manifesto de dependências da stack (requirements.txt, package.json,
  go.mod, ...). Nome de import raramente é igual a nome de pacote — confira antes de
  assumir. Verificação executável equivalente: estágio `verificacao_estatica` do harness.
evidencia:     shared/tools/coding_tools/verificacao_dependencias.py
escopo:        core
status:        ativo
proveniencia:  semente manual (destilado do gate implementado na issue #303)
```

---

```yaml
trigger:       instrução Dockerfile referenciando arquivo/diretório
granularidade: evento
corpo: >
  `COPY`/`ADD` no Dockerfile só deve referenciar arquivos ou diretórios que você de fato
  criou nesta sessão via tool de escrita. Verifique a estrutura criada antes de escrever a
  instrução — um `COPY` para um caminho inexistente derruba o build inteiro.
evidencia:     null
escopo:        core
status:        ativo
proveniencia:  semente manual
```

---

```yaml
trigger:       porta declarada em mais de um artefato de entrega
granularidade: evento
corpo: >
  A porta mapeada no `docker-compose.yml` DEVE corresponder à porta exposta/usada no `CMD`
  e no `EXPOSE` do Dockerfile (ver core/conventions.md — porta 8000 é o padrão do pipeline).
  `CMD` deve referenciar o módulo EXATO onde o entrypoint da aplicação é instanciado.
evidencia:     null
escopo:        core
status:        ativo
proveniencia:  semente manual
```
