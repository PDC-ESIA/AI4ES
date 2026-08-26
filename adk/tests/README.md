# Suite de testes do ADK — 2 camadas × escopo por agente

Esta suite valida um sistema multiagente (Orchestrator com 4 pipelines —
`requirements → design → coding_review → qa` —, QA Agent, checkpoints
HITL, geração de código) construído sobre Google ADK + LangChain, com
Docker como sandbox de execução e Langfuse para observabilidade em
produção.

Testar sistemas agênticos baseados em LLM não se resume a "unit vs.
integration": um agente pode passar em todo teste determinístico e ainda
tomar decisões erradas ou na ordem errada. Por isso a suite é organizada
em **2 camadas**, cada uma respondendo a uma pergunta diferente sobre o
comportamento do sistema. O desenho segue três referências (ver
[Referências](#referências)):

| # | Camada | Pergunta que responde | Pasta |
|---|--------|------------------------|-------|
| 1 | Infraestrutura | "O código faz o que deveria?" | [`unit/`](unit/) |
| 2 | Trajetória | "O agente decidiu as coisas certas, na ordem certa?" | [`integration/`](integration/) |

Ortogonal a essas 2 camadas há uma **segunda dimensão, por escopo de
agente**: veja [Escopo por agente — `coder_isolado/`](#escopo-por-agente--coder_isolado)
mais abaixo.

## Camada 1 — Infraestrutura (`tests/unit/`)

Testes determinísticos e rápidos: schemas Pydantic, ferramentas (`tool_*`),
resolução de workspace, geração de Dockerfile/detecção de entrypoint,
orquestração ADK (retry, HITL, discovery), cache do QA Agent. Não fazem
nenhum julgamento de qualidade — só afirmam contratos e efeitos
verificáveis (arquivo criado, exceção levantada, campo do schema
validado).

```bash
pytest -m infraestrutura
```

## Camada 2 — Trajetória (`tests/integration/`)

Valida a **sequência** de decisões — não só o resultado final. Exemplo
real remanescente nesta pasta: o Orchestrator só encerra (`exit_loop`)
quando o veredito é `aprovado`, nunca pelo status técnico isolado; um
checkpoint HITL pausa e retoma corretamente via `Runner` do ADK. Os
exemplos de trajetória específicos do pipeline de coding (harness,
convergência do `LoopAgent`) vivem em
[`tests/coder_isolado/trajetoria/`](#escopo-por-agente--coder_isolado).

O artefato central é o **trace**: eventos coletados durante a execução e
organizados em duas camadas (`tests/fixtures/trace_helpers.py`):

- **raw layer** — o evento como foi emitido (Event do ADK, resposta de
  LLM, dict de retorno de tool). Preservado para debug/replay.
- **canonical layer** — projeção normalizada e estável
  (`agente`, `acao`, `status`, `timestamp`, `metadata`), independente do
  SDK de origem. As asserções de trajetória são feitas sobre esta camada.

A fixture `trace_collector` "básica" (sem dump) vive no `conftest.py`
global; a versão com dump automático em JSON (`<tmp_path>/traces/<nome_do_teste>.json`,
útil para depurar uma trajetória inesperada sem reproduzir o teste com
prints) vive hoje em [`tests/coder_isolado/conftest.py`](#escopo-por-agente--coder_isolado),
já que só os testes ali dependem dela.

O projeto já depende de `langfuse` para observabilidade em produção, mas
os testes **não** chamam o serviço Langfuse real: `trace_collector` replica
a mesma forma canônica (spans com nome/status/metadata) para que um trace
de teste seja comparável a um trace de produção, sem acoplar a suite a uma
API key.

```bash
pytest -m trajetoria
```

## Escopo por agente — `coder_isolado/`

Dimensão ortogonal às 2 camadas: reúne todo teste que exercita **somente**
o pipeline `workflow_coding_review` (seus subagentes context_engineer,
coder, executor, reviewer, e código `shared/` usado exclusivamente por
ele — ex.: `shared/execution/*`, o harness de execução). Testes que
também tocam outro agente (orchestrator, QA, design, requirements) ficam
fora daqui, em `tests/unit/`/`tests/integration/`, mesmo quando mencionam
coding_review de passagem.

```
tests/coder_isolado/
├── conftest.py          # fixtures compartilhadas: trace_collector com dump
│                         # (infraestrutura/trajetoria), workspace_fixture e
│                         # _requer_llm_real (evals/sandbox)
├── infraestrutura/       # equivalente à Camada 1, escopo coding_review
├── trajetoria/            # equivalente à Camada 2, escopo coding_review
├── evals/                 # Camada 3 — avaliação de qualidade com LLM real
│                           # (cr_review_analyzer isolado)
└── sandbox/                # Camada 4 — pipeline completo ponta-a-ponta,
                             # LLM real + execução real de código (sandbox)
```

Os testes em `infraestrutura/` e `trajetoria/` recebem o marker de camada
correspondente (`infraestrutura`/`trajetoria`) **e** o marker
`coder_isolado`, aplicados automaticamente pelo hook em
`tests/conftest.py` — não precisam de `@pytest.mark` explícito. `evals/`
e `sandbox/` recebem `evals`/`sandbox` + `coder_isolado` pelo mesmo hook,
mas por envolverem custo real de API também levam `@pytest.mark.evals`/
`@pytest.mark.sandbox` explícito em cada teste — redundante de propósito,
para o custo ficar óbvio lendo só o arquivo.

```bash
# todo o escopo coding_review (todas as camadas, incluindo evals/sandbox)
pytest -m coder_isolado

# só a fatia de infraestrutura do coding_review
pytest -m "infraestrutura and coder_isolado"

# só a fatia de trajetória do coding_review
pytest -m "trajetoria and coder_isolado"
```

### Camada 3 — Evals (`tests/coder_isolado/evals/`)

Diferente de tudo acima, **usa LLM real** (GitHub Copilot via LiteLLM) —
roda o `cr_review_analyzer` de produção isolado (não o pipeline inteiro)
para responder "o reviewer de verdade detecta problemas reais de
qualidade?", uma pergunta que nenhuma camada determinística responde. 1
chamada de LLM por teste. A saída real do reviewer é **markdown livre**
(`## Status: APROVADO|BLOQUEADO`, `## Issues`), não JSON validável contra
o schema `ReviewOutput` — os testes fazem parsing de texto sobre essa
saída, não `ReviewOutput.model_validate(...)`.

```bash
pytest -m evals
```

- **Skip automático** se não houver credencial real (fixture
  `_requer_llm_real`, que chama `shared.preflight.ensure_llm_ready()`
  diretamente — não é neutralizada pelo `_stub_llm_preflight` autouse
  global, que só intercepta a referência usada pelo orchestrator).
  Reautentique com `python adk/scripts/copilot_auth.py` se for pulado.
- **Custo real de API.** Não roda no CI padrão — sob demanda ou num job
  nightly separado.
- `@pytest.mark.timeout(180)` por teste.

### Camada 4 — Sandbox e2e (`tests/coder_isolado/sandbox/`)

Roda o pipeline `workflow_coding_review` **completo** com LLM real:
`context_engineer` → loop `[coder ↔ executor]` (com execução REAL de
código gerado, via `DirectSandbox`) → `reviewer`. Até ~12 chamadas de LLM
no pior caso, alguns minutos por teste.

```bash
pytest -m sandbox
```

- Mesmo gate de credencial (`_requer_llm_real`) e mesma ausência do CI
  padrão que a Camada 3, custo ainda maior.
- `@pytest.mark.timeout(900)` (15min) por teste.
- ⚠️ **Bug de ambiente conhecido em Windows local**: `shared/execution/sandbox.py`
  (`DirectSandbox`) usa `import resource` e `preexec_fn`, ambos POSIX-only.
  Em Windows isso quebra na importação — inclusive a do `tests/conftest.py`
  global, então hoje a suite inteira falha a coletar em Windows local, não
  só estes 2 testes. Não é falha do teste nem do LLM; correção fora do
  escopo desta camada.

## `tests/fixtures/` — utilitários compartilhados entre camadas

- `mocked_llm.py` — `MockLLM`/`AsyncMockLLM`/`MockResponse` para testar
  agentes sem chamar um modelo real.
- `trace_helpers.py` — `TraceCollector`, `normalize_trace`,
  `assert_trace_order` (base da Camada 2).
- `test_data.py` — manifestos, tasks e casos de exemplo, reaproveitados
  por mais de uma camada para não divergir gabaritos.

## Como rodar

```bash
# tudo
pytest

# uma camada (inclui a fatia correspondente de coder_isolado)
pytest -m infraestrutura
pytest -m trajetoria

# por pasta física, sem markers
pytest tests/unit/
pytest tests/integration/

# escopo coder_isolado, cruzado com camada
pytest -m coder_isolado
pytest -m "infraestrutura and coder_isolado"
pytest -m "trajetoria and coder_isolado"

# Camadas 3/4 — LLM REAL, custo de API, minutos de execução, NÃO rodam no
# CI padrão (skip automático se faltar credencial — reautentique com
# `python adk/scripts/copilot_auth.py`)
pytest -m evals
pytest -m sandbox

# um arquivo/teste específico, como sempre
pytest tests/unit/test_workspace.py -k til_expandido
```

### CI/CD

- **A cada commit/PR**: Camadas 1 e 2 (`pytest -m "infraestrutura or trajetoria"`).
  Rápidas, determinísticas, sem custo de LLM nem dependência de Docker real
  além do que já é mockado. Isso já exclui `evals`/`sandbox` (Camadas 3/4)
  automaticamente — nenhum teste ali carrega os markers `infraestrutura`/
  `trajetoria`. Rode `evals`/`sandbox` sob demanda ou num job nightly à
  parte, nunca a cada PR (custo real de API + minutos de execução).

Exemplo de step de CI (adaptar ao seu workflow):

```yaml
# a cada push/PR
- run: pytest -m "infraestrutura or trajetoria"
```

## Como adicionar um novo teste

1. **Decida a camada pela pergunta que o teste responde**, não pelo
   módulo testado — o mesmo agente pode ter testes nas 2 camadas.
   - "O retorno/schema/arquivo está certo?" → Camada 1.
   - "A ordem de chamadas/decisões está certa?" → Camada 2 (use
     `trace_collector`).
2. **Decida o escopo pelo que o teste EXERCITA de fato** (imports/chamadas
   reais, não menção em comentário) — se toca **somente**
   `workflow_coding_review` (e/ou `shared/` exclusivo dele), vai em
   `tests/coder_isolado/<camada>/`; se toca qualquer outro agente (mesmo
   junto com coding_review), vai em `tests/unit/`/`tests/integration/`.
3. Coloque o arquivo em `test_*.py` na pasta da camada (e escopo, se
   aplicável); se precisar de uma fixture nova específica dali, adicione
   ao `conftest.py` local. Se for útil em mais de um lugar, mova para
   `tests/fixtures/` (ou promova ao `conftest.py` global, se for
   genérica o bastante — evite duplicar).
4. Marque a classe/módulo com o marker da camada/escopo quando não for
   óbvio pela pasta — normalmente não é necessário, pois `pytest -m`
   também pode selecionar por caminho (`pytest tests/unit/`) e os
   markers de camada/`coder_isolado` já são aplicados automaticamente
   pelo hook em `tests/conftest.py` a partir do caminho do arquivo.
5. Rode a suite completa antes de commitar — `tests/conftest.py` (camada
   global) pré-carrega módulos de agente para evitar que `test_git_tools.py`
   (que substitui `pydantic.BaseModel` em `sys.modules` para isolar testes
   de git) corrompa imports de outros testes; se adicionar um módulo de
   agente novo com schemas Pydantic, considere se ele precisa entrar nesse
   pré-cache.

## Referências

O desenho de camadas segue:

- **MASEval** — framework de avaliação de sistemas multiagente que separa
  avaliação de *resultado* (task completion) de avaliação de *processo*
  (trajetória: sequência de ações/decisões dos agentes).
- **Survey ACL 2026 sobre avaliação de agentes LLM** — taxonomia que
  distingue avaliação determinística (comportamento verificável) de
  avaliação de trajetória (ordem/uso de ferramentas).
- **Testing LLM-Based Agents** — referência da pirâmide de testes
  aplicada a agentes (unit → integration → trace-based).