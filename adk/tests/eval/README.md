# Avaliação de agentes com o `AgentEvaluator` do ADK

Um caso é um pedido feito a um agente do pipeline de codificação, junto com o que deve estar
no disco antes e o resultado esperado. A suíte roda o agente de verdade, com LLM, e compara o
que ele fez e respondeu com o esperado.

Por que fazemos assim: [ADR 0001](../../../docs/adr/0001-avaliacao-de-agentes-com-agentevaluator.md).
O que foi medido para chegar aqui: [NOTAS.md](NOTAS.md).

## Como rodar

De `adk/`. **Gasta LLM real**: sem `AI4ES_EVAL=1`, tudo é pulado. Rode a suíte sozinha, não
junto de `tests/unit`, porque o conftest redireciona o `WORKSPACE_OUTPUT_DIR`.

```bash
AI4ES_EVAL=1 uv run --group eval pytest tests/eval -q                    # 7 testes
AI4ES_EVAL=1 AI4ES_EVAL_JUIZ=1 uv run --group eval pytest tests/eval -q  # 8, com o juiz
```

O grupo `eval` do `pyproject.toml` traz `pandas`, `rouge-score` e `tabulate`, que o pacote de
avaliação do ADK exige, e não é instalado por padrão. Ao final, a rodada imprime chamadas de
LLM, tokens e tempo.

## Quando rodar

Nenhum workflow roda esta suíte. Ela só pega uma piora se quem muda o agente lembrar de rodá-la.
Rode quando:

- mudar o prompt, as tools ou os callbacks de um dos agentes da tabela abaixo;
- trocar o modelo ou o provedor de LLM;
- atualizar o ADK;
- mudar um schema que as fixtures usam (`ExecutionReport`, `Task`, `MacroContext`);
- for aprovar um PR que mexa nesses agentes.

## O que está garantido

| Agente | Casos | Garante |
|---|---|---|
| `implementation_validator` | 3 (um com juiz LLM) | Aprova a execução verde e reprova a que falhou, com a resposta exata |
| `cr_context_engineer` | 3 | Segue o protocolo de bloqueio até pausar o pipeline e, com requisitos e design completos, grava contexto e tasks válidos em vez de só anunciar |
| `cr_coder_agent` | 1 | Lê o contrato da task e entrega um projeto que o gate do executor aceita |
| `cr_review_analyzer` | 1 | Lê o código antes de opinar e, sem cobertura comprovada, sai BLOQUEADO |

O detalhe de cada caso está na docstring do teste. Quatro casos conferem também as tools
oferecidas ao modelo: tool removida, renomeada ou acrescentada reprova o caso.

## Como adicionar um caso

Um caso tem quatro peças. Exemplo: o caminho feliz do validador.

1. **A fixture: o que o agente encontra no disco.** `fixtures/validator_verde/` tem o relatório
   de execução que o validador vai ler. Antes de rodar, o teste apaga o workspace da avaliação e
   copia a pasta para dentro dele.
2. **O eval set: o pedido e o gabarito.** `evalsets/validator_aprovado/validator_aprovado.test.json`
   tem a mensagem do usuário, o estado inicial da sessão, as tools que o agente deve chamar, a
   resposta esperada e as tools que o modelo deve receber. `{{WORKSPACE}}` vira o caminho real do
   workspace. O `description` começa dizendo qual fixture o caso usa e qual teste a copia.
3. **O `test_config.json`, na mesma pasta: os critérios.** Cada métrica com seu limiar. Uma
   métrica própria (`ai4es_*`) também precisa de uma entrada em `custom_metrics` com o caminho da
   função em `metrics.py`.
4. **O teste Python: o único lugar que junta as peças.**
   `test_eval_implementation_validator.py::test_aprova_report_verde_com_state_semeado` copia a
   fixture, prepara o eval set e roda o agente:

   ```python
   workspace_semeado("validator_verde")
   await rodar_eval(evalset("validator_aprovado"), agent_module=MODULO)
   ```

   Quando o resultado fica no disco ou no estado da sessão, que as métricas não enxergam, a
   conferência mora aqui, depois da avaliação (veja `test_eval_context_engineer.py`).

Escolha o critério da resposta pelo que é fixo nela:

- **Resposta montada em Python, sem texto do modelo:** `response_match_score` com limiar 1.0.
  É o caso do validador.
- **Só parte da resposta é fixa:** um marcador por linha, com `ai4es_resposta_contem`. É o caso do
  reviewer.
- **Nada na resposta é fixo:** não avalie a resposta. Confira no disco, no teste.

Para fechar, rode só o caso novo com `AI4ES_EVAL_DETALHE=1` e rode
`uv run pytest tests/unit/test_eval_caminhos_das_metricas.py`, que confere sem LLM se os
`test_config.json` apontam para funções que existem. A Dev UI do ADK ajuda a rascunhar o eval set
a partir de uma sessão real, mas grava o estado inicial vazio, e ele tem de ser preenchido à mão.

## Variáveis

| Variável | Efeito | Default |
|---|---|---|
| `AI4ES_EVAL=1` | Liga a avaliação | desligado |
| `AI4ES_EVAL_JUIZ=1` | Liga também o caso com juiz LLM | desligado |
| `AI4ES_EVAL_JUDGE_MODEL` | Modelo-juiz (`{{JUDGE_MODEL}}` nos `test_config.json`) | o `ADK_LLM_MODEL` do `.env` |
| `AI4ES_EVAL_NUM_RUNS` | Execuções por caso; limiar 1.0 exige conformidade em todas | `2` |
| `AI4ES_EVAL_DETALHE=1` | Tabela por invocação do ADK (`print_detailed_results`) | desligado |
| `AI4ES_EVAL_WORKSPACE` | Onde semear o workspace da avaliação | `tests/eval/workspace_output` |

## Métricas próprias (`metrics.py`)

| Métrica | O que mede |
|---|---|
| `ai4es_tool_sequence_in_order` | As tools esperadas ocorrem na ordem, tolerando extras; compara só nomes, e chamada que devolveu erro não conta |
| `ai4es_contrato_de_tools` | As tools oferecidas ao modelo são exatamente as esperadas |
| `ai4es_resposta_contem` | Cada linha da resposta esperada aparece na obtida, para respostas só em parte determinísticas |

Uma chamada conta como erro quando a tool devolve `sucesso: False` ou um texto que começa com
"Erro", que é a convenção das tools dos agentes acima. Tools de outros pipelines sinalizam erro de
outro jeito; um caso de outro pipeline precisa antes estender o `_falhou` de `metrics.py`.

## Custo

A última rodada completa, em 01/10, com os 8 testes (juiz incluído), `github_copilot/gpt-5.3-codex`
e duas execuções por caso: 74 chamadas de LLM, 553.575 tokens, 5min11s.

- O caso com juiz custa cerca de 3 vezes um caso sem juiz, porque o juiz é consultado 5 vezes por
  resposta.
- `AI4ES_EVAL_NUM_RUNS` multiplica o custo de todos os casos.
- O `AgentEvaluator` não reporta custo; o conftest imprime chamadas, tokens e tempo ao fim de cada
  rodada. Ao mudar a suíte, atualize o número acima.

## Quando um caso falha

- **Leia o PR que mudou o sistema antes de mexer no eval set.** A falha pode ser regressão ou
  mudança de regra feita de propósito; no segundo caso, o eval set muda junto, e o diff registra.
- **Sequência de tools divergente:** o log de `metrics.py` imprime o esperado e o obtido.
- **Falha intermitente** (por exemplo, uma de duas execuções): é variação do agente, não do caso.
  Não baixe o limiar. Registre numa issue do agente a taxa medida, a data, o modelo e a resposta da
  falha (rode com `AI4ES_EVAL_DETALHE=1` para vê-la). Exemplo: a falha do caso do coder, descrita
  em `NOTAS.md`.
- **429 do Copilot:** não é da suíte. O registro de modelos em `app/main.py` anula as subclasses de
  `shared/llm.py`, e o header `X-Initiator: user` não chega a ser enviado.
