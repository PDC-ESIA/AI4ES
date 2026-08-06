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

## Política de escrita (D7, D8 — grow-and-refine, não orçamento fixo)

- **`conventions.md` / `consistency-rules.md` / `deps.md` / `pitfalls.md`**: editados manualmente
  via PR, como qualquer arquivo de documentação versionado. Estáveis — não sofrem escrita
  automática.
- **`lessons.md`** (core ou stack): populado pela destilação `ExecutionReport → lição`
  (Estágio 3 do relatório, §12.4) — **ainda não implementada** nesta issue. Quando existir:
  acumula por padrão (nunca reescreve o arquivo inteiro), com dedup e deprecação; toda
  promoção para `core/lessons.md` exige o mesmo padrão observado em **duas stacks
  diferentes**; curadoria humana obrigatória antes de qualquer escrita.
- **`cr_feedforward` acumula por padrão** (long-context, D7) — o pack cresce, não é
  comprimido por orçamento arbitrário de tokens. Truncar por budget fixo é o anti-padrão que
  o relatório aponta no `_build_input` do orchestrator (truncamento cego de 8.000 chars).

## Formato de item de conhecimento (§12.3 do relatório)

Onde o item é uma regra ou lição pontual (não prosa livre, como em `conventions.md`), o
frontmatter abaixo é o padrão adotado — inspirado no CODESKILL (`trigger → corpo`), com os
campos de governança do Memp/GovMem:

```yaml
trigger:       assinatura do erro ou contexto de ativação
granularidade: evento | estrategia
corpo:         instrução acionável
evidencia:     <task_id>.report.json / teste que a validou / commit
escopo:        core | stack:<nome>
status:        ativo | deprecado
proveniencia:  run/PR de origem, ou "semente manual" para itens hand-curated
```

`proveniencia` é o campo que distingue, dentro do mesmo `stacks/<stack>/`, o que é semente
manual (`pitfalls.md`) do que foi destilado de execuções reais (`lessons.md`).

## Stacks disponíveis

Hoje só `python-fastapi` está semeada. Isso não é uma limitação de design da KB — é um
reflexo direto do **G8** (`shared/tools/coding_tools/harness_execucao.py`, estágio
`preparacao_ambiente`): o harness aborta qualquer workspace sem arquivo `.py`, então só uma
stack é executável (e portanto testável) enquanto essa trava não for corrigida. Adicionar uma
nova stack depois é só criar o diretório — o `cr_feedforward` seleciona por `tech_stack`, sem
precisar de código novo.
