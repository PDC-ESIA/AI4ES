# Suite de testes do ADK — 2 camadas de validação

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
| 1 | Infraestrutura | "O código faz o que deveria?" | [`infraestrutura/`](infraestrutura/) |
| 2 | Trajetória | "O agente decidiu as coisas certas, na ordem certa?" | [`trajetoria/`](trajetoria/) |

## Camada 1 — Infraestrutura

Testes determinísticos e rápidos: schemas Pydantic, ferramentas (`tool_*`),
resolução de workspace, geração de Dockerfile/detecção de entrypoint,
orquestração ADK (retry, HITL, discovery), cache do QA Agent. Não fazem
nenhum julgamento de qualidade — só afirmam contratos e efeitos
verificáveis (arquivo criado, exceção levantada, campo do schema
validado).

```bash
pytest -m infraestrutura
```

## Camada 2 — Trajetória

Reúne o que antes vivia em `tests/integration/`, mais dois exemplos novos
(`test_trajetoria_harness_exemplo.py` e
`test_trajetoria_convergencia_loop.py`). Valida a **sequência** de
decisões — não só o resultado final. Exemplos reais da suite: o harness de
execução persiste evidências ANTES do validador emitir veredito; o
Orchestrator só encerra (`exit_loop`) quando o veredito é `aprovado`,
nunca pelo status técnico isolado; um checkpoint HITL pausa e retoma
corretamente via `Runner` do ADK; o `LoopAgent` de correção de código
(`_code_execute_loop`) converge e para exatamente na iteração em que o
executor sinaliza aprovação (`escalate=True`), e encerra de forma
controlada em `max_iterations` quando o executor nunca aprova — sem
travar e sem produzir uma falsa aprovação.

O artefato central é o **trace**: eventos coletados durante a execução e
organizados em duas camadas (`tests/fixtures/trace_helpers.py`):

- **raw layer** — o evento como foi emitido (Event do ADK, resposta de
  LLM, dict de retorno de tool). Preservado para debug/replay.
- **canonical layer** — projeção normalizada e estável
  (`agente`, `acao`, `status`, `timestamp`, `metadata`), independente do
  SDK de origem. As asserções de trajetória são feitas sobre esta camada.

A fixture `trace_collector` (em `trajetoria/conftest.py`) grava
automaticamente o trace completo (`canonical` + `raw`) em JSON ao final de
cada teste, em `<tmp_path>/traces/<nome_do_teste>.json` — útil para
depurar uma trajetória inesperada sem precisar reproduzir o teste com
prints.

O projeto já depende de `langfuse` para observabilidade em produção, mas
os testes **não** chamam o serviço Langfuse real: `trace_collector` replica
a mesma forma canônica (spans com nome/status/metadata) para que um trace
de teste seja comparável a um trace de produção, sem acoplar a suite a uma
API key.

```bash
pytest -m trajetoria
```

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

# uma camada
pytest -m infraestrutura
pytest -m trajetoria

# um arquivo/teste específico, como sempre
pytest tests/infraestrutura/test_workspace.py -k til_expandido
```

### CI/CD

- **A cada commit/PR**: Camadas 1 e 2 (`pytest -m "infraestrutura or trajetoria"`).
  Rápidas, determinísticas, sem custo de LLM nem dependência de Docker real
  além do que já é mockado.

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
2. Coloque o arquivo em `test_*.py` na pasta da camada; se precisar de uma
   fixture nova específica da camada, adicione ao `conftest.py` local. Se
   for útil para mais de uma camada, mova para `tests/fixtures/`.
3. Marque a classe/módulo com o marker da camada quando não for óbvio pela
   pasta — normalmente não é necessário, pois `pytest -m` também pode
   selecionar por caminho (`pytest tests/infraestrutura/`), mas o marker
   ajuda quando se roda a suite inteira com `-m`.
4. Rode a suite completa antes de commitar — `infraestrutura/conftest.py`
   pré-carrega módulos para evitar que `test_git_tools.py` (que substitui
   `pydantic.BaseModel` em `sys.modules` para isolar testes de git)
   corrompa imports de outros testes; se adicionar um módulo de agente
   novo com schemas Pydantic, considere se ele precisa entrar nesse
   pré-cache (em `tests/conftest.py`, camada global).

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