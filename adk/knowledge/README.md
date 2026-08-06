# `adk/knowledge/` — base de conhecimento da camada de Feedforward

Este diretório é a KB consumida pelo `cr_feedforward` (`src/agents/workflow_coding_review/`)
para montar o `context_pack` injetado no prompt do `cr_coder` via `{context_pack?}`.
Arquitetura completa, *rationale* e decisões (D1–D10): ver
`docs/Time_4_Codificacao/relatorio_camada_feedforward_agente_codificacao.md`, §8 e §10.

**Por que é consumida por injeção no prompt, não por tool:** as tools de leitura do coder
são presas ao `workspace_root` (`shared/agent_factory.py`) e `_resolver_caminho`
(`shared/tools/coding_tools/filesystem_coding.py`) rejeita caminho absoluto e `..`. A KB é
fisicamente inalcançável por tool do coder — não é preferência de design, é o que o código
permite (D3).

## Layout

```
knowledge/
├── core/                    ← agnóstico de stack, SEMPRE entra no pack
│   ├── conventions.md       ← convenções de código (SRP, limite de linhas, reuso de libs)
│   ├── consistency-rules.md ← regras cruzadas: import↔requirements, COPY↔arquivos, compose↔Dockerfile
│   └── lessons.md           ← só estratégias TRANSVERSAIS (observadas em 2+ stacks). Nasce vazio.
└── stacks/
    └── <stack>/              ← selecionado pelo `tech_stack` do contrato (macro_context)
        ├── deps.md           ← dependências conhecidamente boas + armadilhas de nome de pacote
        ├── pitfalls.md       ← semente manual, curada à mão, estável
        └── lessons.md        ← destino DEFAULT das lições destiladas desta stack. Nasce vazio.
```

## Como cada arquivo é escrito e consumido

- **`conventions.md` / `consistency-rules.md` / `deps.md` / `pitfalls.md`**: prosa curada à
  mão, editados manualmente via PR, como qualquer arquivo de documentação versionado.
  Estáveis — não sofrem escrita automática. Cada item é uma seção `##` simples
  (título + explicação); não carregam metadado de governança (ver por quê abaixo).
- **`lessons.md`** (core ou stack): **nasce vazio, de propósito.** Seria populado pela
  destilação `ExecutionReport → lição` (Estágio 3 do relatório, §12.4) — **ainda não
  implementada** nesta issue, é trabalho futuro. Quando existir: só escreve após validação
  executável (`state['validation'].status == "aprovado"`); acumula por padrão, nunca
  reescreve o arquivo inteiro (D7, evita *context collapse*); dedup e deprecação ativas;
  curadoria humana obrigatória antes de qualquer escrita (o GovMem mediu 0 de 133
  candidatos reais seguros para promoção automática); promoção para `core/lessons.md` só
  com o mesmo padrão observado em **duas stacks diferentes** (D8); chave de indexação
  primária é `stages[].error_code` do harness (granularidade acionada-por-evento).
- **`cr_feedforward` lê e concatena os `.md` como estão** — não parseia nada. O pack
  acumula por padrão (long-context, D7): não é comprimido por orçamento arbitrário de
  tokens. Truncar por budget fixo é o anti-padrão que o relatório aponta no `_build_input`
  do orchestrator (truncamento cego de 8.000 chars).

## Por que os itens não carregam frontmatter YAML (por enquanto)

O relatório (§12.3) especifica um formato `trigger → corpo` com campos de governança
(`granularidade`, `evidencia`, `escopo`, `status`, `proveniencia`) — mas esse formato existe
para resolver problemas que só aparecem quando o Estágio 3 (destilação automática) estiver
rodando: deduplicar itens, deprecar o que ficou obsoleto, decidir promoção entre stacks. Hoje
`lessons.md` está vazio, só existe uma stack semeada, e todo item de `pitfalls.md` é
igualmente "semente manual, ativo" — carregar esses campos por item não evita erro nenhum
agora, só adiciona texto que não ajuda o coder a escrever código. Quando o Estágio 3 for
implementado, ele usa este formato ao ESCREVER em `lessons.md`:

```yaml
trigger:       assinatura do erro ou contexto de ativação (ex.: error_code do harness)
granularidade: evento | estrategia
corpo:         instrução acionável
evidencia:     <task_id>.report.json / teste que a validou / commit
escopo:        core | stack:<nome>
status:        ativo | deprecado
proveniencia:  run/PR de origem
```

## Manutenção — sincronizar com o código

- `stacks/python-fastapi/deps.md`, seção "Nome de import ≠ nome de pacote PyPI": mesma
  tabela que `shared/tools/coding_tools/verificacao_dependencias.py::ALIAS_IMPORT_PARA_PACOTE`.
  Se um alias for adicionado/removido no gate, atualize os dois lugares.
- `core/consistency-rules.md`, regra de import↔requirements: já tem um fiscal automático
  pareado (estágio `verificacao_estatica` do harness, fail-open exceto no caso inequívoco —
  relatório §8.3). As outras regras deste arquivo ainda são só texto — candidatas a virar
  gate se a taxa de repetição de erro justificar (§12.2).

## Stacks disponíveis

Hoje só `python-fastapi` está semeada. Isso não é uma limitação de design da KB — é um
reflexo direto do **G8** (`shared/tools/coding_tools/harness_execucao.py`, estágio
`preparacao_ambiente`): o harness aborta qualquer workspace sem arquivo `.py`, então só uma
stack é executável (e portanto testável) enquanto essa trava não for corrigida. Adicionar uma
nova stack depois é só criar o diretório — o `cr_feedforward` seleciona por `tech_stack`, sem
precisar de código novo.
