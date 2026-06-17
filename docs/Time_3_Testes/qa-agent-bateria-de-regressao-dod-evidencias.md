# QA Agent - Bateria de Regressao DoD e Evidencias

## 1. DoD

```text
DOD: TESTES REPRODUZIVEIS + EVIDENCIA LOCAL/CI
Plug imediato no CI para garantir nao-regressao.
```

| Item | Status | Evidencia |
| --- | --- | --- |
| Testes reproduziveis | Atendido | Comandos registrados por etapa. |
| Evidencia local | Atendido | Bateria focada: `39 passed, 2 warnings in 0.25s`. |
| Plug no CI | Atendido | Step `Run QA HITL integration test` no `.github/workflows/ci.yml`. |
| Nao-regressao | Configurado | CI roda `tests/unit/` e `tests/integration/test_hitl_e2e.py`. |

## 2. Ambiente

| Campo | Valor |
| --- | --- |
| Data | 2026-06-03 |
| Diretorio | `~\adk` |
| Sistema | Windows local |
| Python | 3.14.4 |
| Pytest | 9.0.3 |
| Executor | `uv run` |

## 3. Etapas e Evidencias

### Etapa 1 - EMPTY RESPONSE

Tarefa:

```text
Neutralizar falhas de resposta vazia no planner.
```

Comando:

```powershell
uv run pytest tests/unit/test_planner_wrapper.py -v --tb=short
```

Evidencia:

```text
tests/unit/test_planner_wrapper.py::test_is_empty_string_vazia PASSED
tests/unit/test_planner_wrapper.py::test_is_empty_none PASSED
tests/unit/test_planner_wrapper.py::test_is_empty_apenas_whitespace PASSED
tests/unit/test_planner_wrapper.py::test_is_empty_apenas_backticks PASSED
tests/unit/test_planner_wrapper.py::test_is_empty_json_valido_pequeno PASSED
tests/unit/test_planner_wrapper.py::test_is_empty_json_valido_grande PASSED
tests/unit/test_planner_wrapper.py::test_fallback_blocked_json_e_parseavel PASSED
tests/unit/test_planner_wrapper.py::test_invoke_once_retorna_texto_do_evento PASSED
tests/unit/test_planner_wrapper.py::test_invoke_once_exception_retorna_marker_de_erro PASSED
tests/unit/test_planner_wrapper.py::test_invocar_retorna_first_quando_valido PASSED
tests/unit/test_planner_wrapper.py::test_invocar_tenta_segunda_quando_first_empty PASSED
tests/unit/test_planner_wrapper.py::test_invocar_fallback_quando_ambas_empty PASSED
tests/unit/test_planner_wrapper.py::test_invocar_retry_suffix_adicionado_na_segunda_call PASSED
tests/unit/test_planner_wrapper.py::test_workflow_qa_usa_function_tool_e_nao_agent_tool_para_planner PASSED
tests/unit/test_planner_wrapper.py::test_workflow_qa_instruction_menciona_invocar_planejamento_qa PASSED
```

Status: PASS.

### Etapa 2 - INVALID CODE

Tarefa:

```text
Prevenir bugs de pass e codigo invalido.
```

Comando:

```powershell
uv run pytest tests/unit/test_receive_requirements_sanitizer.py tests/unit/test_receive_requirements_generation_guards.py -v --tb=short
```

Evidencia:

```text
tests/unit/test_receive_requirements_sanitizer.py::test_sanitiza_pass_ctrl63_para_pass PASSED
tests/unit/test_receive_requirements_sanitizer.py::test_sanitiza_return_placeholder PASSED
tests/unit/test_receive_requirements_sanitizer.py::test_sanitiza_continue_break_raise PASSED
tests/unit/test_receive_requirements_sanitizer.py::test_codigo_invalido_apos_sanitizacao_levanta_valueerror PASSED
tests/unit/test_receive_requirements_sanitizer.py::test_codigo_valido_passa_intocado PASSED
tests/unit/test_receive_requirements_sanitizer.py::test_string_contendo_placeholder_nao_e_sanitizada PASSED
tests/unit/test_receive_requirements_generation_guards.py::test_gerar_pytest_via_llm_rejeita_resposta_vazia PASSED
tests/unit/test_receive_requirements_generation_guards.py::test_processar_artefato_nao_salva_codigo_invalido PASSED
tests/unit/test_receive_requirements_generation_guards.py::test_processar_artefato_esqueleto_sem_pass_isolado PASSED
```

Status: PASS.

### Etapa 3 - HITL RESUME

Tarefa:

```text
Validar fluxo completo de Pausa -> Resume.
```

Comando:

```powershell
uv run pytest tests/unit/test_hitl_tool.py tests/unit/test_workflow_qa_hitl.py tests/unit/test_orchestrator_hitl.py tests/integration/test_hitl_e2e.py -v --tb=short
```

Evidencia:

```text
tests/unit/test_hitl_tool.py::test_aguardar_aprovacao_humana_retorna_none_para_pausar_adk PASSED
tests/unit/test_hitl_tool.py::test_aguardar_aprovacao_humana_schema_compativel_com_gemini PASSED
tests/unit/test_hitl_tool.py::test_pause_reason_pode_ser_omitido PASSED
tests/unit/test_hitl_tool.py::test_aguardar_aprovacao_humana_reexportada_no_init PASSED
tests/unit/test_workflow_qa_hitl.py::test_workflow_qa_registra_aguardar_aprovacao_como_longrunning PASSED
tests/unit/test_workflow_qa_hitl.py::test_workflow_qa_instruction_menciona_aguardar_aprovacao PASSED
tests/unit/test_workflow_qa_hitl.py::test_workflow_qa_aguardar_aprovacao_schema_nao_quebra_gemini PASSED
tests/unit/test_orchestrator_hitl.py::test_fresh_run_sem_pausa_executa_4_pipelines PASSED
tests/unit/test_orchestrator_hitl.py::test_fresh_run_com_pausa_para_em_qa PASSED
tests/unit/test_orchestrator_hitl.py::test_resume_aprovar_envia_function_response_e_conclui PASSED
tests/unit/test_orchestrator_hitl.py::test_resume_rejeitar_preserva_comentario PASSED
tests/unit/test_orchestrator_hitl.py::test_resume_texto_invalido_yields_erro_e_mantem_pausa PASSED
tests/unit/test_orchestrator_hitl.py::test_resume_sem_live_runner_volta_erro_e_limpa_state PASSED
tests/unit/test_orchestrator_hitl.py::test_resume_com_pausa_encadeada_mantem_runner_e_atualiza_state PASSED
tests/integration/test_hitl_e2e.py::test_orchestrator_pausa_real_e_resume_via_runner_adk PASSED
```

Status: PASS.

### Etapa 4 - Bateria Focada Consolidada

Comando:

```powershell
uv run pytest tests/unit/test_planner_wrapper.py tests/unit/test_receive_requirements_sanitizer.py tests/unit/test_receive_requirements_generation_guards.py tests/unit/test_hitl_tool.py tests/unit/test_workflow_qa_hitl.py tests/unit/test_orchestrator_hitl.py tests/integration/test_hitl_e2e.py -v --tb=short
```

Evidencia:

```text
collected 39 items
39 passed, 2 warnings in 0.25s
```

Status: PASS.

### Etapa 5 - Integration HITL Isolada

Comando:

```powershell
uv run pytest tests/integration/test_hitl_e2e.py -v --tb=short
```

Evidencia:

```text
tests/integration/test_hitl_e2e.py::test_orchestrator_pausa_real_e_resume_via_runner_adk PASSED
1 passed, 2 warnings in 9.82s
```

Status: PASS.

### Etapa 6 - Suite Unit Completa

Comando:

```powershell
uv run pytest tests/unit/ -v --tb=short
```

Evidencia:

```text
6 failed, 197 passed, 1 warning in 19.53s
```

Status: FAIL parcial no Windows local.

## 4. CI

Arquivo:

```text
.github/workflows/ci.yml
```

Steps configurados:

```yaml
- name: Run unit tests
  run: uv run pytest tests/unit/ -v --tb=short

- name: Run QA HITL integration test
  run: uv run pytest tests/integration/test_hitl_e2e.py -v --tb=short
```

Status: CONFIGURADO.

## 5. Pendencias

| Item | Descricao | Status |
| --- | --- | --- |
| P-01 | Corrigir ou classificar as 6 falhas da suite unit completa no Windows. | Pendente |
| P-02 | Avaliar testes adicionais para `ERROR: ...`, strings com placeholders e `solicitar_ajustes`. | Opcional |

## 6. Fechamento

| Frente | Reprodutibilidade | Evidencia | Status |
| --- | --- | --- | --- |
| EMPTY RESPONSE | Etapa 1 | Testes do planner wrapper | PASS |
| INVALID CODE | Etapa 2 | Testes de sanitizer e guardrails | PASS |
| HITL RESUME | Etapa 3 | Testes unitarios + integration HITL | PASS |
| Bateria focada | Etapa 4 | `39 passed, 2 warnings in 0.25s` | PASS |
| CI unit | Workflow `ci.yml` | Step `Run unit tests` | CONFIGURADO |
| CI integration HITL | Workflow `ci.yml` | Step `Run QA HITL integration test` | CONFIGURADO |
