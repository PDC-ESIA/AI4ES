# Avaliação de agentes com o `AgentEvaluator` do ADK

Casos que avaliam o **comportamento** de agentes do pipeline de codificação com LLM real:
trajetória de tools, resposta final e tools oferecidas ao modelo. Complementam a suíte
unitária, que não chama LLM. A decisão, as limitações do ADK e o que esta suíte já pegou
estão no [ADR 0001](../../../docs/adr/0001-avaliacao-de-agentes-com-agentevaluator.md).

## Como rodar

De `adk/`. **Gasta LLM real**: sem `AI4ES_EVAL=1`, tudo é pulado. Rode a suíte sozinha, não
junto de `tests/unit`, porque o conftest redireciona o `WORKSPACE_OUTPUT_DIR`.

```bash
AI4ES_EVAL=1 uv run --group eval pytest tests/eval -q                    # 6 testes
AI4ES_EVAL=1 AI4ES_EVAL_JUIZ=1 uv run --group eval pytest tests/eval -q  # 7, com o juiz
```

O grupo `eval` do `pyproject.toml` traz `pandas`, `rouge-score` e `tabulate`, que o pacote de
avaliação do ADK exige, e não é instalado por padrão. Ao final, a rodada imprime chamadas de
LLM, tokens e tempo.

## O que está garantido

| Agente | Teste | Garante |
|---|---|---|
| `implementation_validator` | `test_aprova_report_verde_com_state_semeado` | Com execução verde, lê o report pelo caminho do state e aprova com a resposta exata |
| `implementation_validator` | `test_reprova_quando_a_execucao_falhou` | Com a execução falha, reprova, qualquer que seja o julgamento do LLM |
| `implementation_validator` | `test_juiz_llm_aprova_o_veredito_correto` | Um juiz LLM considera a resposta do caminho feliz equivalente à referência (opt-in) |
| `cr_context_engineer` | `test_protocolo_de_bloqueio_emite_as_tres_tools` | Com requisitos bloqueados, chama as três tools do protocolo na ordem, até a que pausa o pipeline |
| `cr_context_engineer` | `test_nao_bloqueia_por_nome_de_arquivo_do_design` | Não bloqueia só porque a análise técnica tem nome fora da convenção |
| `cr_context_engineer` | `test_caminho_feliz_age_em_vez_de_narrar` | Com requisitos e design completos, lê as duas fases e persiste, em vez de só anunciar |
| `cr_review_analyzer` | `test_gate_de_cobertura_sobrepoe_o_veredito_do_llm` | Lê o código antes de opinar e, sem cobertura comprovada, o status sai BLOQUEADO |

O caminho feliz do validador, o protocolo de bloqueio e o reviewer conferem também as tools
oferecidas ao modelo: tool removida, renomeada ou acrescentada reprova o caso.

## Variáveis

| Variável | Efeito | Default |
|---|---|---|
| `AI4ES_EVAL=1` | Liga a avaliação | desligado |
| `AI4ES_EVAL_JUIZ=1` | Liga também o caso com juiz LLM (cerca de 3 vezes o custo de um caso) | desligado |
| `AI4ES_EVAL_JUDGE_MODEL` | Modelo-juiz (`{{JUDGE_MODEL}}` nos `test_config.json`) | o `ADK_LLM_MODEL` do `.env` |
| `AI4ES_EVAL_NUM_RUNS` | Execuções por caso; limiar 1.0 exige conformidade em todas | `2` |
| `AI4ES_EVAL_DETALHE=1` | Tabela por invocação do ADK (`print_detailed_results`) | desligado |
| `AI4ES_EVAL_WORKSPACE` | Onde semear o workspace da avaliação | `tests/eval/workspace_output` |

## Métricas próprias (`metrics.py`)

| Métrica | O que mede |
|---|---|
| `ai4es_tool_sequence_in_order` | As tools esperadas ocorrem na ordem, tolerando extras; compara só nomes |
| `ai4es_contrato_de_tools` | As tools oferecidas ao modelo são exatamente as esperadas |
| `ai4es_resposta_contem` | Cada linha da resposta esperada aparece na obtida, para respostas só em parte determinísticas |

## Quando um caso falha

- **Leia o PR que mudou o sistema antes de mexer no eval set.** A falha pode ser regressão ou
  mudança de regra feita de propósito; no segundo caso, o eval set muda junto, e o diff registra.
- **Sequência de tools divergente:** o log de `metrics.py` imprime o esperado e o obtido.
- **Caso com score 0.5 em duas execuções:** é não-determinismo do agente. Registre o número em vez
  de baixar o limiar.
- **429 do Copilot:** não é da suíte; o motivo está no ADR.
