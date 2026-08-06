# Convenções de código — core (agnóstico de stack)

> Escopo: `core`. Entra em TODO `context_pack`, independente da stack escolhida pelo
> `cr_context_engineer`. Fonte: princípios já vigentes no prompt canônico do coder
> (`src/agents/coder/prompt.py`, seção "DIRETRIZES DE CODIFICAÇÃO"), consolidados aqui como
> conhecimento versionado em vez de string hardcoded — ver relatório §12.5.

## Responsabilidade Única (SRP)

Nunca gere arquivos monolíticos. Cada arquivo, classe ou módulo deve ter apenas um propósito.
Se um script passar de **150–200 linhas**, divida-o.

## Reuso antes de nova dependência

Antes de escrever código ou adicionar uma dependência nova, analise o contexto já fornecido
(`requirements.txt`, árvore de diretórios existente). Reutilize bibliotecas e funções já
presentes no projeto. Só proponha uma dependência nova se for estritamente necessária, e
justifique o porquê.

## Qualidade e resiliência

Todo código deve incluir tratamento de erros adequado, logs claros onde aplicável, e tipagem
estrita quando a linguagem suportar.

## Entrega executável obrigatória (topology lock)

Independente da stack, a entrega DEVE ser executável via `docker compose up --build` sem
configuração extra, expondo a aplicação na porta **8000**. Isso não é detalhe de
implementação — é a trava de topologia (Lei de Ashby, relatório §3.1) que reduz a variedade
que o harness de execução precisa administrar: o harness testa exatamente esse contrato
(build → deploy → start → smoke). Artefatos mínimos, na raiz do workspace do coder:

- `Dockerfile` — imagem base enxuta da linguagem/stack escolhida, instala dependências
  declaradas, copia só o que foi de fato criado, expõe 8000, `CMD` aponta pro entrypoint real.
- `docker-compose.yml` — serviço com build local (`context: .`), porta `8000:8000` mapeada,
  variáveis de ambiente necessárias declaradas.
- `README.md` — só a URL de acesso (`http://localhost:8000` + rota principal, se não for `/`).
  Sem instruções de instalação manual — o Docker cuida disso.

## Um arquivo por responsabilidade

Ao planejar os arquivos do projeto, consolide outputs que se repetem entre tasks — não crie
dois arquivos para a mesma responsabilidade só porque duas tasks a mencionam.
