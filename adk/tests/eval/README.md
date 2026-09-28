# Avaliação de agentes com o pacote `evaluation` do ADK

PoC que usa o `AgentEvaluator` nativo do ADK 1.33.0 para testar **três agentes do Time 4**
em nível de comportamento — trajetória de ferramentas, resposta final e contrato de tools —,
que é o que a suíte unitária não alcança por construção.

> **Estes testes gastam chamadas de LLM reais.** São opt-in: sem `AI4ES_EVAL=1` tudo é
> pulado, inclusive num `uv run pytest` nu. Isso importa porque `testpaths = ["tests"]`
> coleta este diretório junto com o resto.

## Como rodar

```bash
cd adk

# tudo menos o juiz (6 testes)
AI4ES_EVAL=1 uv run --group eval pytest tests/eval -q

# um caso só
AI4ES_EVAL=1 uv run --group eval \
  pytest tests/eval/test_eval_context_engineer.py::test_protocolo_de_bloqueio_emite_as_tres_tools -q

# incluindo a camada de juiz LLM (7 testes; mais cara — ver abaixo)
AI4ES_EVAL=1 AI4ES_EVAL_JUIZ=1 uv run --group eval pytest tests/eval -q

# saída detalhada do ADK (tabela por invocação)
AI4ES_EVAL=1 AI4ES_EVAL_DETALHE=1 uv run --group eval pytest tests/eval -q
```

| Variável | Efeito | Default |
|---|---|---|
| `AI4ES_EVAL=1` | Liga a avaliação. Sem ela, tudo é pulado | desligado |
| `AI4ES_EVAL_JUIZ=1` | Liga também os casos com juiz LLM | desligado |
| `AI4ES_EVAL_JUDGE_MODEL` | Modelo-juiz (`{{JUDGE_MODEL}}` nos `test_config.json`). O juiz **não** herda o default do ADK (`gemini-2.5-flash`, sem credencial aqui) | o `ADK_LLM_MODEL` do `.env` — mesmo modelo do agente |
| `AI4ES_EVAL_NUM_RUNS` | Execuções por caso — limiar 1.0 exige conformidade em todas | `2` |
| `AI4ES_EVAL_DETALHE=1` | `print_detailed_results` do ADK | desligado |
| `AI4ES_EVAL_WORKSPACE` | Onde semear o workspace da avaliação | `tests/eval/workspace_output` |

### Por que o grupo `eval`

`pandas` e `rouge-score` **são obrigatórios para qualquer métrica**, mesmo as que não usam
nenhum dos dois: a cadeia de import de `metric_evaluator_registry` passa por
`vertex_ai_eval_facade` (pandas) e `final_response_match_v1` (rouge-score). `tabulate` só
entra com `AI4ES_EVAL_DETALHE=1`. O grupo `eval` do `pyproject.toml` não é instalado por
padrão, então quem não roda a avaliação não baixa nada disso. Sem o grupo, o `conftest`
pula tudo com a mensagem certa, em vez de a falta aparecer no meio da execução.

## O que cada caso prova

### `implementation_validator`

| Teste | O que prova |
|---|---|
| `test_aprova_report_verde_com_state_semeado` | Caminho feliz, com âncora de trajetória **e** de resposta |
| `test_reprova_quando_a_execucao_falhou` | `overall_status: falha` reprova mesmo se o LLM "aprovar" — a política é de `montar_veredito` |

Por que todo caso se ancora no resultado, e não só na trajetória: ver o
[ADR 0001](../../../docs/adr/0001-avaliacao-de-agentes-com-agentevaluator.md).

As fixtures de `ExecutionReport` (`fixtures/validator_*/coder/execution/`) seguem o contrato
do harness desde o #406: cada `criteria_evidence` traz `criterion_id`, `automatable`,
`outcome` e `linked_tests`, e o harness só emite `outcome: "nao_avaliado"`. Com isso
`montar_veredito` decide o status **só pela execução** e força todo critério a
`inconclusivo` com texto fixo — a resposta esperada do caminho feliz é determinística de
ponta a ponta. **Regressão pega por aqui:** em 16/09, rodada como estava (fixture e resposta
de 07/09) sobre a `develop` já com o #406, o caminho feliz reprovou em
`response_match_score` (0.609 < 0.7, trajetória 1.0). Nenhum teste unitário acusou a
mudança de política.

### `cr_context_engineer`

| Teste | O que prova |
|---|---|
| `test_protocolo_de_bloqueio_emite_as_tres_tools` | As 3 tools do protocolo de bloqueio ocorrem na ordem, incluindo o `LongRunningFunctionTool` que **pausa** o pipeline |
| `test_nao_bloqueia_por_nome_de_arquivo_do_design` | Não bloqueia quando a análise técnica tem nome fora da convenção — a promessa do #391, que acabou com o portão por nome (`analise_tecnica_*`) |
| `test_caminho_feliz_age_em_vez_de_narrar` | O agente **age** em vez de escrever "Agora vou criar as tasks…" e encerrar o turno |

### `cr_review_analyzer`

| Teste | O que prova |
|---|---|
| `test_gate_de_cobertura_sobrepoe_o_veredito_do_llm` | O reviewer **leu** o código, e o gate de cobertura sobrepôs o status que o LLM escreveu |

## Métricas próprias (`metrics.py`)

A métrica nativa `tool_trajectory_avg_score` compara **nome E argumentos** com igualdade
exata de dict. Serve onde o argumento é determinístico (um caminho ecoado do prompt), e não
serve para o `cr_context_engineer`, cujos argumentos são texto livre do LLM. Daí as próprias,
registradas via o ponto de extensão oficial (`custom_metrics` no `test_config.json`):

| Métrica | O que mede |
|---|---|
| `ai4es_tool_sequence_in_order` | Tools esperadas na ordem esperada, tolerando extras |
| `ai4es_contrato_de_tools` | As tools **declaradas ao modelo** são exatamente as esperadas (o que foi *oferecido*, não o que foi *chamado*) |
| `ai4es_resposta_contem` | Cada linha da resposta esperada aparece na obtida — para quando parte da resposta é determinística e o resto é prosa |

## Duas limitações do ADK que a PoC teve de contornar

**1. `LongRunningFunctionTool` some da trajetória.** `Event.is_final_response()` devolve
`True` assim que o evento tem `long_running_tool_ids` (`events/event.py:91-92`), e
`evaluation_generator._convert_events_to_invocations` **descarta o evento final** dos
intermediários (`:315-317`). O `function_call` da tool long-running vai parar em
`final_response` e some de `intermediate_data`.

Medido: a avaliação do protocolo de bloqueio reportava, em **4 de 4 execuções**, a sequência
parando em `tool_emitir_manifesto_bloqueado`. O mesmo agente num `Runner` cru, sem o eval,
mostrou as três chamadas e o `long_running_tool_ids` preenchido — **o agente estava certo;
a leitura da trajetória é que era incompleta**. Como reproduzir: ver o ADR 0001. `nomes_das_tools` em `metrics.py`
inclui as chamadas do `final_response` justamente por isso. Sem esse cuidado,
`tool_trajectory_avg_score` dá **falso negativo em todo caso de HITL** — e o HITL do Time 4
*é* um `LongRunningFunctionTool`.

**2. O framework não enxerga o session state.** `EvalCase.final_session_state` existe mas
nenhuma métrica o lê; `Invocation` não carrega state; e os `InvocationEvent` guardam só
`author` + `content`, descartando o `actions.state_delta`. Como os handoffs do Time 4 são
por state (`state["tasks"]`, `state["validation"]`, `state["task_iteration_summary"]`),
**esse nível não é avaliável por aqui**. É teto da ferramenta, não desta PoC.

## Um teste vermelho aqui nem sempre é bug da PoC

| Sintoma | Leitura |
|---|---|
| Sequência de tools divergente | O log de `metrics.py` imprime esperado × obtido. Confira antes de mexer no eval set — pode ser achado sobre o pipeline |
| Caso pontua 0.5 com `num_runs=2` | Não-determinismo real, quantificado. É informação, não *flakiness* a esconder |
| `response_match_score` baixo | O ROUGE-1 pune divergência de prosa. Baixe o limiar **e registre o número observado** — não suba o limiar até passar |
| `429 user_global_rate_limited` | Não é da PoC: `app/main.py:13-15` registra de novo os prefixos de modelo com a `LiteLlm` base, anulando as subclasses de `shared/llm.py`, e o header `X-Initiator: user` nunca é enviado |

## Notas de mecânica

- O `conftest.py` define `WORKSPACE_OUTPUT_DIR` **antes** de qualquer import de agente,
  porque `review_tools.py:35-37` congela `_CODER_WS` em tempo de import — o
  `cr_review_analyzer` não é isolável por `monkeypatch`. Há uma guarda que falha alto se
  o binding cair fora do workspace da avaliação.
- O `conftest.py` importa `app.main` logo em seguida, como o uvicorn faz. Sem isso o
  `load_dotenv` não roda, os agentes nascem com `gemini-2.5-flash`, e o `LLMRegistry`
  (que é `@lru_cache`) resolve na ordem errada.
- Os eval sets são versionados com o placeholder `{{WORKSPACE}}`, resolvido em runtime,
  para o JSON não carregar caminho absoluto de máquina.
- A PoC **não corrige** o registro de modelos de `app/main.py` citado acima: roda como
  produção roda.
