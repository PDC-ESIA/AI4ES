# ADR 0001 — Avaliação de agentes com o `AgentEvaluator` do ADK

- **Status:** proposto (issue #373, PR #419)
- **Data:** 2026-09-28
- **Escopo:** `adk/tests/eval/`; as limitações descritas valem para qualquer pipeline do projeto

## Contexto

A suíte de `adk/tests/` não chama LLM, por construção: os agentes aparecem por stubs e mocks, e
os prompts por asserções de substring. Ela cobre bem o código determinístico (tools, gates,
parsers, políticas em Python), mas não alcança o comportamento do agente: se ele chama as tools
do seu contrato, na ordem certa, e se a resposta final é a que a política manda.

A issue #373 pede avaliação desse comportamento no pipeline de codificação. O ADK (1.33.0) já
traz o pacote `google.adk.evaluation`: o `AgentEvaluator`, chamável do pytest, a CLI `adk eval`,
a aba Eval da Dev UI, métricas nativas e um ponto de extensão para métricas próprias
(`custom_metrics` no `test_config.json`).

## Decisão

1. **Usar o `AgentEvaluator` nativo, chamado do pytest**, em `adk/tests/eval/`. O pytest é o
   gate. A Dev UI serve só para rascunhar casos: a captura dela grava `session_input.state`
   vazio, e aqui o state faz parte do contrato do agente.
2. **Opt-in por `AI4ES_EVAL=1`.** Sem a variável, tudo é pulado, inclusive num `uv run pytest`
   sem argumentos. O juiz LLM é um segundo opt-in (`AI4ES_EVAL_JUIZ=1`), por custo.
3. **Todo caso se ancora no resultado, não só na trajetória:** resposta determinística
   (`response_match_score` com limiar 1.0), marcador literal (`ai4es_resposta_contem`) ou o que
   o agente deixou em disco, conferido pelo próprio teste.
4. **Métricas próprias onde a nativa não serve**, registradas pelo ponto de extensão oficial:
   `ai4es_tool_sequence_in_order` (nomes de tool em ordem, tolerando extras, porque a nativa
   exige igualdade exata de argumentos, e os argumentos aqui são texto livre do LLM),
   `ai4es_contrato_de_tools` (as tools oferecidas ao modelo) e `ai4es_resposta_contem`.
5. **As dependências do pacote de avaliação ficam num grupo `eval`** do `pyproject.toml`, fora
   do grupo padrão: `uv run --group eval`.

## Evidência

### 1. Trajetória sozinha não é gate

No primeiro experimento com a ferramenta, o `implementation_validator` rodou sem o
`session_input.state` que o caso exige. Sem `task_id` no state, o guard do validador rejeita o
caminho do report e o agente cai no fail-safe (reprova por falta de evidência). Mesmo assim ele
chama `tool_ler_arquivo` com o caminho certo, então a trajetória é idêntica à do caminho feliz:
`tool_trajectory_avg_score` marcou 1.0 e o caso **passou** com o agente degradado. O mesmo caso
ancorado na resposta reprova (`response_match_score` 0,255 contra limiar 0,7, em 16/09).

Por isso a decisão 3. Os dois eval sets do experimento e os testes que os rodavam estão no
histórico deste PR, no commit `56c9c37`, em `adk/tests/eval/evalsets/armadilha_*` e em
`test_eval_implementation_validator.py`.

### 2. Um `LongRunningFunctionTool` some da trajetória

No ADK 1.33.0, `Event.is_final_response()` devolve `True` assim que o evento tem
`long_running_tool_ids` (`events/event.py`), e `_convert_events_to_invocations`
(`evaluation/evaluation_generator.py`) monta os eventos intermediários excluindo o evento final.
A chamada da tool long-running acaba em `final_response` e some de `intermediate_data`, que é de
onde toda métrica de trajetória lê.

Medido: o caso do protocolo de bloqueio do `cr_context_engineer` reportava, em 4 de 4 execuções,
a sequência parando em `tool_emitir_manifesto_bloqueado`. O mesmo agente num `Runner` cru, sem o
eval, mostrou as três chamadas e o `long_running_tool_ids` preenchido: o agente estava certo, e a
leitura da trajetória é que estava incompleta. O script que faz essa verificação é o
`adk/tests/eval/_probe_longrunning.py` do commit `56c9c37`.

Consequência: `tool_trajectory_avg_score` dá falso negativo em todo caso de HITL, e todo HITL do
projeto é um `LongRunningFunctionTool` (`aguardar_resolucao_bloqueio` no pipeline de codificação,
`aguardar_resolucao_doubt` no de design, `aguardar_aprovacao_humana` no de QA,
`aguardar_decisao_validacao` no `validator`). A métrica `ai4es_tool_sequence_in_order` lê também
as chamadas do `final_response` por isso.

### 3. O session state é invisível ao framework

`Invocation` não carrega state, os eventos intermediários guardam só `author` e `content`, e
`EvalCase.final_session_state` existe no modelo, mas nenhuma métrica o lê. Os handoffs por state
do pipeline de codificação (`tasks`, `validation`, `task_iteration_summary`) não são avaliáveis
por métrica. É teto da ferramenta: quando o contrato está no state ou no disco, quem confere é o
próprio teste, depois da avaliação.

### 4. O prompt renderizado e as tools oferecidas são visíveis

`Invocation.app_details.agent_details[].instructions` e `tool_declarations` vêm preenchidos a
partir do `LlmRequest` real também com `LiteLlm` (medido com o Copilot: 8.789 caracteres de
instrução renderizada no `implementation_validator`). Dá para fazer asserções sobre o prompt e
sobre as tools oferecidas ao modelo sem servidor. O `ai4es_contrato_de_tools` usa isso: pega
tool removida, renomeada ou acrescentada, que muda o espaço de ações do agente sem quebrar
nenhum teste unitário. A métrica de instrumentação que fez essa medição (`sonda`, em
`metrics.py`) e o teste que a rodava estão no commit `56c9c37`.

### 5. O que a suíte já pegou

- **Mudança de comportamento do validador (PR #406, 16/09).** O #406 passou a decidir o status
  só pela execução, e o julgamento do LLM por critério virou registro. Rodada como estava (fixture
  e resposta esperada de 07/09) sobre a `develop` já com o #406, a suíte reprovou o caminho feliz
  do validador: `response_match_score` 0,609 contra limiar 0,7, com trajetória 1.0 e contrato de
  tools 1.0. Nenhum teste unitário acusou: o #406 entrou com 412 testes novos, todos verdes.
- **Limiar frouxo esconde mudança.** Na mesma rodada, o caso do caminho de falha **passou** com
  limiar 0,7, embora o texto da resposta tivesse mudado. Onde a resposta é gerada em Python de
  ponta a ponta, o limiar passou a 1.0.
- **Mudança de política no context engineer (PR #411, 23/09).** O PR acabou com o bloqueio por
  nome do arquivo de design. O caso que assertava o bloqueio foi invertido e confirmou a política
  nova com LLM real, em 2 de 2 execuções. Não foi medido se a suíte antiga teria reprovado antes
  da atualização.

Um caso que falha pode querer dizer "o sistema regrediu" ou "a regra mudou de propósito". Só
quem lê o PR que mudou o sistema sabe qual. No segundo caso o eval set se atualiza junto, e o
diff dele registra a mudança.

### 6. Custo

Em 23/09, a suíte de então (10 testes, com o juiz), com `github_copilot/gpt-5.3-codex` e duas
execuções por caso: 60 chamadas de LLM, 296.942 tokens, 3min36s, sem 429. O caso com juiz custa
cerca de 3 vezes um caso sem juiz (13 das 21 chamadas numa rodada de 16/09), porque o juiz
amostra 5 vezes por invocação. O `conftest.py` imprime chamadas, tokens e tempo ao fim de cada
rodada, porque o `AgentEvaluator` não reporta custo.

## Consequências

- Mudança de comportamento e de contrato de tools passa a ter onde aparecer, mas **só quando
  alguém roda a suíte**: ela é opt-in, gasta LLM e nenhum workflow a executa hoje.
- O custo cresce com cada caso novo. Com duas execuções por caso e limiar 1.0, o gate exige
  conformidade em todas: o não-determinismo aparece como falha, não como média. Duas execuções
  não medem dispersão.
- O juiz usa, por padrão, o mesmo modelo do agente (`ADK_LLM_MODEL`), a condição de
  auto-preferência descrita por Zheng et al. (2023). Fica declarado como limite. Outro modelo se
  escolhe por `AI4ES_EVAL_JUDGE_MODEL`.
- Risco de 429 do Copilot: `app/main.py` registra de novo os prefixos de modelo com a classe
  `LiteLlm` base, o que anula as subclasses de `shared/llm.py`, e o header `X-Initiator: user`
  não é enviado. A suíte não corrige isso: roda como a aplicação roda.
- Fixtures são contrato. Mudou o schema do `ExecutionReport` ou das tasks, as fixtures precisam
  ser revalidadas contra os modelos Pydantic.
