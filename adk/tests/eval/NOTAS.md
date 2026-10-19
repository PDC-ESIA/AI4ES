# Notas da avaliação de agentes

O que foi medido ao montar esta suíte e sustenta o
[ADR 0001](../../../docs/adr/0001-avaliacao-de-agentes-com-agentevaluator.md). Os números têm
data. O ADK é o 1.33.0 e, salvo indicação, o modelo é o `github_copilot/gpt-5.3-codex`.

## 1. Olhar só os passos não basta

No primeiro experimento, o `implementation_validator` rodou sem o estado de sessão que o caso
exige. Sem `task_id` no estado, a proteção do validador recusa o caminho do relatório de execução,
e o agente reprova por falta de evidência. Mesmo assim, ele chama `tool_ler_arquivo` com o
caminho certo, então os passos são idênticos aos do caminho feliz. A métrica nativa de trajetória
(`tool_trajectory_avg_score`) deu 1.0, e o caso **passou** com o agente degradado. O mesmo caso,
ancorado na resposta, reprova (`response_match_score` 0,255 contra limiar 0,7, em 16/09).

Daí a regra de que todo caso se ancora no resultado: uma resposta montada em Python e comparada
por inteiro, marcadores literais na resposta ou o que o agente deixou no disco, conferido pelo
próprio teste. Os dois eval sets desse experimento e os testes que os rodavam estão no histórico
do PR #419, no commit `56c9c37`, em `adk/tests/eval/evalsets/armadilha_*` e em
`test_eval_implementation_validator.py`.

## 2. Uma pausa para humano some da trajetória

Todo ponto em que o pipeline espera uma pessoa é um `LongRunningFunctionTool`:
`aguardar_resolucao_bloqueio` na codificação, `aguardar_resolucao_doubt` no design,
`aguardar_aprovacao_humana` no QA e `aguardar_decisao_validacao` no `validator`.

No ADK, `Event.is_final_response()` devolve `True` assim que o evento tem `long_running_tool_ids`
(`events/event.py`). Já `_convert_events_to_invocations` (`evaluation/evaluation_generator.py`)
monta os passos intermediários sem o evento final. Assim, a chamada da tool que pausa vai parar em
`final_response` e some de `intermediate_data`, que é de onde toda métrica de trajetória lê.

Medido: o caso do protocolo de bloqueio do `cr_context_engineer` mostrava, em 4 de 4 execuções, a
sequência parando em `tool_emitir_manifesto_bloqueado`. O mesmo agente, num `Runner` sem a
avaliação, fez as três chamadas, com `long_running_tool_ids` preenchido. O agente estava certo; a
leitura da trajetória é que estava incompleta. O script dessa verificação é o
`adk/tests/eval/_probe_longrunning.py`, no commit `56c9c37`.

Consequência: a métrica nativa de trajetória dá falso negativo em todo caso com pausa para humano.
Por isso a `ai4es_tool_sequence_in_order` lê também as chamadas do `final_response`.

## 3. O estado da sessão é invisível ao framework

`Invocation` não carrega o estado da sessão, e os eventos intermediários guardam só `author` e
`content`. O modelo `EvalCase` tem `final_session_state`, mas nenhuma métrica o lê. Por isso o que
os agentes da codificação passam uns aos outros pelo estado (`tasks`, `validation`,
`task_iteration_summary`) não se avalia por métrica. É um limite da ferramenta: quando o contrato
está no estado ou no disco, quem confere é o próprio teste, depois da avaliação.

## 4. O prompt e as ferramentas oferecidas são visíveis

`Invocation.app_details.agent_details[].instructions` e `tool_declarations` vêm preenchidos a
partir da requisição real ao modelo, também com `LiteLlm`. Medido com o Copilot: 8.789
caracteres de instrução no `implementation_validator`. Dá para conferir o prompt e as ferramentas
oferecidas ao modelo sem subir servidor. É o que a `ai4es_contrato_de_tools` faz: pega tool
removida, renomeada ou acrescentada, que muda o que o agente pode fazer sem quebrar nenhum teste
unitário. A métrica que fez essa medição (`sonda`, em `metrics.py`) e o teste que a rodava estão
no commit `56c9c37`.

## 5. O que a suíte já pegou

- **Mudança de comportamento do validador (PR #406, 16/09).** O PR #406 passou a decidir o status
  só pela execução, e o julgamento do LLM por critério virou registro. A suíte, rodada como estava
  (fixture e resposta esperada de 07/09) sobre a `develop` já com o #406, reprovou o caminho feliz
  do validador: `response_match_score` 0,609 contra limiar 0,7, com trajetória 1.0 e contrato de
  tools 1.0. Nenhum teste unitário acusou, e o #406 entrou com 412 testes novos, todos verdes.
- **Limiar frouxo esconde mudança.** Na mesma rodada, o caso do caminho de falha **passou** com
  limiar 0,7, embora o texto da resposta tivesse mudado. Onde a resposta é montada em Python de
  ponta a ponta, o limiar passou para 1.0.
- **Mudança de política no context engineer (PR #411, 23/09).** O PR acabou com o bloqueio pelo nome
  do arquivo de design. O caso que exigia o bloqueio foi invertido e confirmou a política nova com
  LLM real, em 2 de 2 execuções. Não foi medido se a versão anterior do caso teria reprovado antes
  da atualização.
- **O coder encerra o turno sem fazer nada (01/10).** O caso do `cr_coder_agent` reprovou em 2 de 4
  execuções em 01/10, e em 4 de 6 somando as rodadas de 05/10 e 13/10. Todas as falhas foram iguais: uma
  chamada ao modelo, nenhuma tool e o turno encerrado com texto. A causa está no prompt do coder
  (a frase que pergunta se o bloco está vazio), não no caso.

Um caso que falha pode querer dizer "o sistema regrediu" ou "a regra mudou de propósito". Só quem
lê o PR que mudou o sistema sabe qual das duas. Se a regra mudou, o eval set muda junto, e o diff
dele registra a mudança.

## 6. Relação com os benchmarks do coder

Os benchmarks de `benchmarks/coding_review/` também rodam o `cr_coder_agent` isolado, mas medem
capacidade: `pass@k` sobre centenas de problemas, com os testes oficiais de cada conjunto. Para
isso, impõem regras próprias ao coder (um único `solution.py`, `surface: none`) e não avaliam
`run.json` nem `README.md`. O caso do coder desta suíte mede o contrário: se ele lê o contrato da
task, fica nas suas tools e entrega o que o executor exige para rodar. As duas perguntas se
complementam, e nenhuma substitui a outra.
