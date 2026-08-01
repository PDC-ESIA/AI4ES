# Catálogo de Tools — `workflow_coding_review`

Inventário das ferramentas (`FunctionTool`) usadas pelos quatro agentes do pipeline
`coding_review_pipeline` (`adk/src/agents/workflow_coding_review/agent.py`): `cr_context_engineer` → `LoopAgent[cr_coder ↔ cr_executor]` → `cr_reviewer` (analyzer).

**Todas as tools exclusivas deste fluxo (`cr_*` + agentes "de fora" equivalentes) vivem
em `adk/shared/tools/coding_tools/`.** Tools genuinamente compartilhadas com outros fluxos
(ex.: `tool_salvar_artefato_requisito`, usada pelo Time de requisitos; `pytest_runner.py`, usada também
pelo QA) ficam em `shared/tools/`.

A coluna **Origem** traz o caminho do arquivo onde a função da tool está definida.

## Estrutura de `shared/tools/coding_tools/`

| Arquivo | Conteúdo |
|---|---|
| `filesystem_coding.py` | `tool_criar_arquivo`, `tool_ler_arquivo`, `tool_substituir_trecho`, `tool_salvar_relatorio` |
| `git.py` | `tool_git_add`, `tool_git_commit`, `tool_git_checkout`, `tool_ler_diff`, `tool_preparar_commit`, `tool_confirmar_commit` |
| `context_engineer_tools.py` | `tool_salvar_task`/`tool_salvar_task_adk` (canônica) + `_tool_salvar_task_cr`/`_tool_salvar_task_cr_adk` (variante do `cr_context_engineer`) |
| `review_tools.py` | Callbacks/helpers do `cr_reviewer`: `_inject_static_findings`, `_persist_review`, `_discover_coder_files`, `_format_findings_block`, `_bind` |
| `harness_docker.py` | Helpers determinísticos de Docker (`_detect_entrypoint`, `_generate_dockerfile`, `_discover_main_route` etc.) — sucessor do antigo build/run embutido no executor |
| `harness_execucao.py` | `executar_harness_validacao` / `executar_harness_tool` — os 9 estágios do harness de validação usados pelo `cr_executor`/`executor` |

---

## 1. `cr_context_engineer` (`cr_context_engineer.py`)

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `_tool_salvar_task_cr` (`FunctionTool` como `_tool_salvar_task_cr_adk`) | `adk/shared/tools/coding_tools/context_engineer_tools.py` | `task_id: str`, `task_json: str` | `dict {sucesso, erro, caminho, task_id} ou dict {sucesso, erro, caminho}` | Valida via `SalvarTaskSchema`, faz `json.loads` do conteúdo e grava `<task_id>.json` em `workspace_output/coder/tasks/`. Variante de `tool_salvar_task`, mudando só o diretório de destino. |
---

## 2. `cr_coder` (`cr_coder.py`)

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `tool_criar_arquivo` | `adk/shared/tools/coding_tools/filesystem_coding.py` | `caminho: str`, `conteudo: str`, `base_dir` (bound por closure a `workspace_output/coder/src/` — invisível ao LLM) | `dict {sucesso, caminho, bytes_escritos, erro} ou dict {sucesso, erro, caminho}` | Cria/sobrescreve arquivo completo. Valida extensão (whitelist) e bloqueia diretórios protegidos (`.git`, `.venv`, etc.). Única forma de persistir código — texto solto na resposta é descartado. |
| `tool_ler_arquivo` | `adk/shared/tools/coding_tools/filesystem_coding.py` | `caminho: str`, `base_dir` (bound a `workspace_output/coder/src/` — invisível ao LLM) | `str` (conteúdo do arquivo, ou `"Erro: ..."`) | Lê arquivo existente como texto UTF-8. Usado nas re-execuções para inspecionar o arquivo apontado como causa do erro. |
| `tool_substituir_trecho` | `adk/shared/tools/coding_tools/filesystem_coding.py` | `caminho: str`, `trecho_antigo: str`, `trecho_novo: str`, `base_dir` (bound a `workspace_output/coder/src/` — invisível ao LLM) | `str` (mensagem `"Sucesso: ..."` ou `"Erro: ..."`) | Substitui a **primeira** ocorrência exata (byte-a-byte) de `trecho_antigo` por `trecho_novo`. Preferida a recriar o arquivo inteiro nas correções pós-falha. |
| `tool_ler_workspace` | `adk/shared/tools/filesystem.py` (**não** faz parte de `coding_tools/` — compartilhada com o fluxo de requisitos) | `caminho: str`, `base_dir` (bound à **raiz** do workspace, não a `coder/src/` — invisível ao LLM) | `str` (conteúdo, ou `"Erro: ..."`) | Lê arquivo de **qualquer** subpasta do workspace global. Usada pelo coder pra ler as Tasks contextualizadas em `coder/tasks/TASK-XXX.json`, escritas pelo `cr_context_engineer`, fora do seu próprio subdiretório. |
| `tool_listar_workspace` | `adk/shared/tools/filesystem.py` (idem) | `caminho: str = "."`, `base_dir` (bound à raiz do workspace — invisível ao LLM) | `list[str]` ou `str` (`"Erro: ..."`) | Lista arquivos/diretórios de qualquer subpasta do workspace. Usada pelo coder na ETAPA 0 (plano) pra descobrir as Tasks em `coder/tasks/` antes de ler cada uma. |
---

## 3. `cr_executor` (`cr_executor.py`)

O executor compõe um harness determinístico + um agente de validação (via `AgentTool`) +
`exit_loop`. É um **espelho** do agente consolidado `src/agents/executor/` (mesma relação que
`cr_reviewer` tem com `reviewer`): a instrução (fluxo + salvaguarda) é reusada verbatim de
`executor/prompt.py`, não redefinida aqui.

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `executar_harness_tool` (exposta como `FunctionTool`; internamente chama `executar_harness_validacao`) | `adk/shared/tools/coding_tools/harness_execucao.py` | `task_id: str`, `iteration: int = 1`, `tool_context` (injetado) | `dict` — `ExecutionReport` serializado (estágios, evidências, `report_path`) | Roda os 9 estágios determinísticos do harness (preparação → implantação → coleta de logs → inicialização → testes automatizados → validações do work item → consolidação → geração do relatório) sobre o artefato do coder. **Apenas coleta evidências — nunca decide se um critério de aceite foi atendido.** Diretórios de trabalho (coder/src, coder/execution, coder/tasks) são resolvidos em tempo de chamada via `get_agent_workspace`, não injetados pelo LLM. |
| `AgentTool(agent=implementation_validator)` | `src/agents/implementation_validator/agent.py` (**mesma instância** usada pelo `executor` "de fora" — não é uma cópia `cr_`) | Acionado pelo LLM do executor como uma tool comum | Texto (JSON do `ValidationVerdict`, via `after_agent_callback` do validador) | Julga os critérios de aceite a partir do `ExecutionReport` e devolve um veredito (`aprovado`/`reprovado`) determinístico — ver seção 3.1. |
| `exit_loop` | `google.adk.tools` (tool nativa do ADK, não é código do repositório) | — | — | Encerra o `LoopAgent`. O encerramento é condicionado pela **instrução** do agente, que só instrui a chamar `exit_loop` quando o veredito do validador é `aprovado` (ou no encerramento por estagnação). |

### Callback (não é tool, não é chamado pelo LLM)

| Callback | Quando roda | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `montar_error_report` (`after_agent_callback`) | Depois do turno do executor | `callback_context` (injetado) | `types.Content` (substitui a saída do turno) ou `None` (preserva a saída original) | Quando o veredito (`state['validation']`) é `'reprovado'` e não é encerramento por estagnação, monta um `ErrorReport` determinístico a partir do veredito real e do `ExecutionReport` em disco — **sem síntese do LLM** — e o devolve como saída do turno, no lugar da prosa gerada pelo modelo. É esse JSON que o `cr_coder` recebe em `{execution_result?}` na re-execução. |

### Helpers internos de `harness_execucao.py`/`harness_docker.py` (não são tools, não são chamados pelo LLM)

| Helper | Origem | Descrição |
|---|---|---|
| `_detect_entrypoint(src_dir)` | `harness_docker.py` | Procura, em ordem, `app/main.py`, `main.py`, `src/main.py`, `src/app/main.py`, `app.py`, `server.py`, `run.py`, `manage.py`; se nada existir, varre `.py` procurando `"FastAPI"`/`"uvicorn"`; fallback `"main.py"`. |
| `_detect_requirements(src_dir)` | `harness_docker.py` | Procura `requirements.txt`, `requirements/base.txt`, `requirements/prod.txt`, nessa ordem. |
| `_has_pyproject(src_dir)` | `harness_docker.py` | Checa se `pyproject.toml` existe na raiz. |
| `_generate_dockerfile(src_dir)` | `harness_docker.py` | Gera Dockerfile fallback quando o coder não criou um próprio. |
| `_write_report(report_path, content)` | `harness_docker.py` | Persiste conteúdo de relatório em disco, criando diretórios intermediários. |
| `_cleanup_container(client, name)` | `harness_docker.py` | Remove container existente com aquele nome antes de subir um novo. |
| `_discover_main_route(base_url, http_mod)` | `harness_docker.py` | Descobre a rota principal via `/openapi.json` pra teste funcional. |
| `_como_content(report)` | `cr_executor.py` | Serializa o `ErrorReport` como `types.Content`, usado por `montar_error_report`. |
| `_carregar_execution_report(callback_context)` | `cr_executor.py` | Lê o `ExecutionReport` do disco a partir de `state["report_path"]`, validando o caminho com `_report_path_valido` (anti-traversal). |

---

## 3.1 `implementation_validator` (`src/agents/implementation_validator/agent.py`)

Não é um `cr_*` nem tem variante "de fora" separada — é **a mesma instância** (`root_agent`)
usada como `AgentTool` tanto pelo `cr_executor` (dentro do pipeline) quanto pelo `executor`
standalone. Julga os critérios de aceite a partir do `ExecutionReport` do harness.

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `tool_ler_arquivo` | `adk/shared/tools/coding_tools/filesystem_coding.py` | `caminho: str`, `base_dir=None` (sem `agent_subdir` — o validador lê o `report_path` **absoluto** que o executor grava no state; `base_dir=None` é o único jeito de `_resolver_caminho` aceitar caminho absoluto) | `str` (conteúdo, ou `"Erro: ..."`) | Lê o `ExecutionReport` (`coder/execution/{task_id}.report.json`) para o LLM julgar os critérios. Único acesso a disco do validador — ele é read-only. |

### Callback + helpers (não são tools, não são chamados pelo LLM)

| Função | Descrição |
|---|---|
| `_parse_e_aplicar_politica` (`after_agent_callback`) | Parseia o markdown que o LLM produziu (um bloco `### CRITERIO` por critério), valida o `report_path` (state ou eco na resposta, com anti-traversal), e aplica `montar_veredito` como *enforcement* — a política determinística nunca fica só na mão do texto do LLM. |
| `montar_veredito(report, criteria_verdicts)` | Codificação determinística da política de veredito: **Camada 1** reprova imediatamente se `overall_status` do `ExecutionReport` for `erro`/`falha` (execução precede julgamento); **Camada 2** agrega os vereditos por critério — só `aprovado` se **todos** estiverem `atendido`. |
| `agregar_status`, `_extrair_criterios`, `_report_path_valido`, `_como_content` | Helpers de suporte à política e à validação anti-traversal do caminho do report. |

---

## 4. `cr_reviewer` (`cr_reviewer.py`)

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `tool_ler_arquivo` | `adk/shared/tools/coding_tools/filesystem_coding.py` | `caminho: str`, `base_dir` (bound por closure a `workspace_output/coder/src/` — invisível ao LLM) | `str` (conteúdo do arquivo, ou `"Erro: ..."`) | Lê cada arquivo listado em `ARQUIVOS A REVISAR`. |

Além da tool acima, duas funções Python puras rodam como **callbacks** (não são `FunctionTool`s, o LLM não as chama), definidas em `shared/tools/coding_tools/review_tools.py`:

| Callback | Quando roda | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `_inject_static_findings` (`before_agent_callback`) | Antes do LLM analisar | `callback_context` (injetado) | `None` (efeito colateral: grava `state["static_findings_block"]`) | Roda **Ruff** e **Bandit** em paralelo via `run_capabilities` sobre o workspace do coder; até 30 findings formatados e injetados no prompt como ponto de partida da revisão. Falha de uma ferramenta não quebra a outra. |
| `_persist_review` (`after_agent_callback`) | Depois do LLM produzir a análise | `callback_context` (injetado) | `None` (levanta `RuntimeError` se a gravação falhar) | Lê `state["review_analysis"]` e chama `tool_salvar_relatorio` diretamente em Python (não como tool), gravando `verificacao_revisao.md`. |

### Helpers internos (`review_tools.py`, exceto `_analyzer_instruction_provider` que fica em `cr_reviewer.py`)

| Helper | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `_bind(tool, agent_ws)` | `review_tools.py` | `tool` — a `FunctionTool` (ou callable) original; `agent_ws: str` — workspace a bindar | `FunctionTool` com `base_dir`/`cwd` injetado por closure | Wrapper local que chama `_bind_tool_to_workspace(tool, agent_ws, _WORKSPACE_ROOT)` (`shared/agent_factory.py`). Usada para bindar `tool_ler_arquivo` ao workspace do `cr_coder` (`_CODER_WS`), não ao do próprio `cr_reviewer`. |
| `_discover_coder_files()` | `review_tools.py` | Nenhum parâmetro | `str` — lista em formato bullet (`"- arquivo1\n- arquivo2..."`) | Lista (recursivo, ignorando `__pycache__`) todos os arquivos em `_CODER_WS`, ordenados. Roda no momento da invocação do agente (chamada de dentro de `_analyzer_instruction_provider`), não em import-time. |
| `_format_findings_block(findings)` | `review_tools.py` | `findings: list[Finding]` — achados retornados por `run_capabilities` | `str` — bloco de texto legível, uma tool/regra por linha | Formata cada `Finding` como `"[SEVERIDADE] origem/regra — arquivo:linha\n  mensagem"`. Se `findings` estiver vazio, retorna a string fixa `"Nenhum problema identificado pelas ferramentas de análise estática."`. |
| `_analyzer_instruction_provider(ctx)` | `cr_reviewer.py` (fica aqui, não em `review_tools.py`, por depender de `_ANALYZER_INSTRUCTION_TEMPLATE`, montado a partir do prompt específico deste agente) | `ctx` — `ReadonlyContext` injetado pelo ADK (dá acesso a `ctx.state`) | `str` — instrução final montada para o LLM naquele turno | É o `instruction` do `_analyzer` (um `InstructionProvider`, não uma string estática): lê `ctx.state["static_findings_block"]` e substitui os placeholders `__STATIC_FINDINGS__`, `__CODER_WS__` e `__FILES__` (via `_discover_coder_files()`) no template. Roda a cada invocação do agente. |

---

# Agentes "de fora" (`src/agents/coder`, `context_engineer`, `reviewer`, `executor`)

## `coder` (`src/agents/coder/agent.py`)

Sem `agent_subdir` → `create_se_agent` pula todo o bloco de binding. Isso significa que `base_dir`/`cwd` **continuam parâmetros reais na assinatura** dessas funções (com default `None`) e por isso aparecem no schema exposto ao LLM — diferente dos `cr_*`, onde a closure remove o parâmetro da assinatura antes de gerar o schema.

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `tool_criar_arquivo` | `shared/tools/coding_tools/filesystem_coding.py` | `caminho: str`, `conteudo: str`, `base_dir: str \| None = None` | `dict {sucesso, caminho, bytes_escritos, erro}` | Igual ao `cr_coder`, mas `base_dir` não é bound — fica visível ao LLM; se omitido (`None`), grava relativo ao CWD. |
| `tool_git_add` | `shared/tools/coding_tools/git.py` | `arquivos: str`, `cwd: str \| None = None` | `dict {sucesso, stdout, stderr, returncode}` | Executa `git add <arquivos>` ou `git add .`. |
| `tool_git_commit` (`require_confirmation=True`) | `shared/tools/coding_tools/git.py` | `mensagem: str` , `cwd: str \| None = None` | `dict {sucesso, stdout, stderr, returncode}` ou `{sucesso: False, mensagem}` | Executa `git commit -m` diretamente após validar que há stage (`git diff --staged`). Sem stage, falha sem efeito. |
| `tool_git_checkout` | `shared/tools/coding_tools/git.py` | `branch: str`, `criar: bool = False`, `cwd: str \| None = None` | `dict {sucesso, comando, stdout, stderr, returncode}` | `git checkout <branch>`, ou `git checkout -b <branch>` se `criar=True`. |
| `tool_ler_arquivo` | `shared/tools/coding_tools/filesystem_coding.py` | `caminho: str`, `base_dir: str \| None = None` | `str` (conteúdo ou `"Erro: ..."`) | Igual ao `cr_coder`, mas `base_dir` visível/não bound. |
| `tool_substituir_trecho` | `shared/tools/coding_tools/filesystem_coding.py` | `caminho: str`, `trecho_antigo: str`, `trecho_novo: str`, `base_dir: str \| None = None` | `str` (`"Sucesso: ..."` ou `"Erro: ..."`) | Igual ao `cr_coder`, mas `base_dir` visível/não bound. |
| `tool_ask_clarification` | `shared/tools/clarification.py`, auto-injetada | `titulo, secao, descricao, impacto, sugestao, nome_arquivo: str`, `base_dir: str \| None = None` | `dict {sucesso, erro, caminho, título, status}` | Gera Doubt Artifact em Markdown e sinaliza que o agente deve parar e devolver controle ao supervisor. `base_dir` visível/não bound aqui — se omitido, grava relativo ao CWD. |
---

## `context_engineer` (`src/agents/context_engineer/agent.py`)

Passa `agent_subdir="context_engineer"` → tools **bound**. `AGENT_DIRS["context_engineer"] = "tasks"`, grava em `workspace_output/tasks/` (não `coder/tasks/`, que é onde o `cr_context_engineer` grava).

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `tool_salvar_task_adk` | `shared/tools/coding_tools/context_engineer_tools.py` | `task_id: str`, `task_json: str` | `dict {sucesso, erro, caminho, task_id}` | Versão canônica; `cr_context_engineer` usa a variante `_tool_salvar_task_cr` do mesmo arquivo. Valida `task_id` (deve iniciar com `"TASK-"`), faz `json.loads` e grava `<task_id>.json` via `get_agent_workspace("context_engineer")`. |
| `tool_ask_clarification` | `shared/tools/clarification.py`, auto-injetada | `titulo, secao, descricao, impacto, sugestao, nome_arquivo: str`, `base_dir` (existe na função original, mas bound por closure a `workspace_output/tasks/` — invisível ao LLM) | `dict {sucesso, erro, caminho, título, status}` | Igual ao `coder`, mas bound ao workspace do agente (`workspace_output/tasks/`). |
---

## `reviewer` (`src/agents/reviewer/agent.py`, nome interno `review_agent`)

Sem `agent_subdir` → mesma situação do `coder`: `cwd`/`base_dir` continuam parâmetros reais e visíveis ao LLM (default `None`). Revisa por **diff Git** (o `cr_reviewer` revisa por arquivos do workspace + análise estática).

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `tool_ler_diff` | `shared/tools/coding_tools/git.py` | `branch_alvo: str = "main"`, `cwd: str \| None = None` | `dict {sucesso, erro, diff}` | Executa `git diff <branch_alvo>`  |
| `tool_salvar_relatorio` | `shared/tools/coding_tools/filesystem_coding.py` | `conteudo: str`, `nome_arquivo: str = "doubt_artifact_revisao.md"`, `base_dir: str \| None = None` | `dict {sucesso, caminho, bytes_escritos, erro}` | Mesma tool que o `cr_reviewer` usa via callback (sem exposição ao LLM); aqui é `FunctionTool` normal, o LLM decide quando chamá-la  |
| `tool_ask_clarification` | `shared/tools/clarification.py`, auto-injetada | `titulo, secao, descricao, impacto, sugestao, nome_arquivo: str`, `base_dir: str \| None = None` | `dict {sucesso, erro, caminho, título, status}` | Igual às anteriores, `base_dir` visível/não bound aqui. |
---

## `executor` (`src/agents/executor/agent.py`) — espelho do `cr_executor`

Sem `agent_subdir`. Compõe as mesmas três peças que o `cr_executor`: harness, validador (`AgentTool`) e `exit_loop`. A instrução (fluxo + salvaguarda) fica em `executor/prompt.py` e é reusada VERBATIM pelo `cr_executor` — diferente de `coder`/`reviewer`, aqui não há ajuste de seções entre a versão "de fora" e a `cr_`.

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `executar_harness_tool` | `shared/tools/coding_tools/harness_execucao.py` | `task_id: str`, `iteration: int = 1`, `tool_context` (injetado) | `dict` — `ExecutionReport` serializado | Idêntica à usada pelo `cr_executor` (seção 3). |
| `AgentTool(agent=implementation_validator)` | `src/agents/implementation_validator/agent.py` | Acionado pelo LLM como tool | JSON do `ValidationVerdict` | Mesma instância usada pelo `cr_executor` — ver seção 3.1. |
| `exit_loop` | `google.adk.tools` (nativa do ADK) | — | — | Fora de um `LoopAgent`, `exit_loop` não tem efeito de encerrar loop nenhum — mas continua exposta pra manter o agente "de fora" espelhando exatamente as tools do `cr_executor`. |

Este agente **não tem** `after_agent_callback` de `montar_error_report` — essa lógica de montar `ErrorReport` é específica de quando o executor está dentro do `LoopAgent` do pipeline (`cr_executor.py`); a versão "de fora" não tem coder pra devolver o relatório.

---

## Cobertura: todas as tools envolvidas (`cr_*` + agentes "de fora" + `implementation_validator`)

**Status**: `ativa` (usada por ≥1 agente), `não utilizada` (definida em `coding_tools/` mas sem
nenhum agente com ela em `tools=[...]` hoje — candidata a remoção ou a documentar propósito
futuro).

| Tool | Usada por | Status |
|---|---|---|
| `tool_criar_arquivo` | `cr_coder` (bound), `coder` (sem bind) | ativa |
| `tool_ler_arquivo` | `cr_coder` (bound), `cr_reviewer` (bound), `coder` (sem bind), `implementation_validator` (sem bind, `base_dir=None` de propósito — lê caminho absoluto) | ativa |
| `tool_substituir_trecho` | `cr_coder` (bound), `coder` (sem bind) | ativa |
| `tool_ler_workspace` / `tool_listar_workspace` | `cr_coder` (bound à raiz do workspace) — únicos consumidores; **não** fazem parte de `coding_tools/`, ficam em `shared/tools/filesystem.py` (compartilhadas com o fluxo de requisitos) | ativa |
| `tool_salvar_relatorio` | `cr_reviewer` (via callback, sem exposição ao LLM), `reviewer` (exposta ao LLM) | ativa |
| `tool_git_add` | `coder` | ativa |
| `tool_git_commit` (`require_confirmation=True`) | `coder` | ativa |
| `tool_git_checkout` | `coder` | ativa |
| `tool_ler_diff` | `reviewer` | ativa |
| `tool_ask_clarification` | `coder`, `context_engineer`, `reviewer` (auto-injetada) — ausente em todos os `cr_*` e no `executor`/`implementation_validator` | ativa |
| `_tool_salvar_task_cr` (variante) | `cr_context_engineer` | ativa |
| `tool_salvar_task` / `tool_salvar_task_adk` | `context_engineer` | ativa |
| `executar_harness_tool` / `executar_harness_validacao` | `cr_executor`, `executor` | ativa |
| `AgentTool(implementation_validator)` | `cr_executor`, `executor` (mesma instância nos dois) | ativa |
| `exit_loop` (nativa do ADK) | `cr_executor`, `executor` | ativa |
| `montar_error_report` (callback, local a `cr_executor.py`) | `cr_executor` (ausente em `executor` — só faz sentido dentro do `LoopAgent`) | ativa |
| `_parse_e_aplicar_politica` / `montar_veredito` (callback + policy, locais a `implementation_validator/agent.py`) | `implementation_validator` | ativa |
| `tool_preparar_commit` | Nenhum agente | **não utilizada** |
| `tool_confirmar_commit` | Nenhum agente | **não utilizada** |
| `trava_seguranca_git_commit` (helper interno, chamado só por `tool_git_commit`) | — (não é tool exposta) | ativa (como helper interno) |

---

## Análise de redundância (escopo: `shared/tools/coding_tools/`)

| # | Tools envolvidas | Sobreposição | Recomendação |
|---|---|---|---|
| R1 | `tool_salvar_task` × `_tool_salvar_task_cr` (`context_engineer_tools.py`) | Corpo idêntico — validação via `SalvarTaskSchema`, `json.loads`, grava `<task_id>.json`. A única diferença é a chave fixa passada a `get_agent_workspace(...)`: `"context_engineer"` numa, `"cr_context_engineer"` na outra. | **Unificar** numa única função parametrizada (`tool_salvar_task(task_id, task_json, workspace_key="context_engineer")`), com dois `FunctionTool` distintos fazendo bind do parâmetro por closure — mesmo padrão já usado pra `base_dir`/`cwd` no resto do repositório. |
| R2 | `tool_git_commit` × par `tool_preparar_commit`/`tool_confirmar_commit` (`git.py`) | Duas formas de commitar com aprovação: a primeira usa o mecanismo nativo do ADK (`FunctionTool(tool_git_commit, require_confirmation=True)`, já em uso pelo `coder`); a segunda é um protocolo prepare/confirm implementado à mão, que **nenhum agente usa hoje**. | **Manter uma, descontinuar a outra** — como o gate de aprovação do `tool_git_commit` via `require_confirmation=True` já resolve o caso de uso, o par `tool_preparar_commit`/`tool_confirmar_commit` é candidato a remoção. Confirmar com o time se há plano de uso antes de remover (pode ter sido feito pra um fluxo HITL que não chegou a ser ligado). |

---

## Plano de ação

| Ação | Esforço estimado |
|---|---|
| R2 — confirmar com o time se `tool_preparar_commit`/`tool_confirmar_commit` têm uso futuro planejado; se não, remover de `git.py` e dos re-exports (`shared/tools/__init__.py`, `agent_factory.py`) | ~30 min (código) + tempo de alinhamento com o time |
| R1 — confirmar se as `tool_salvar_task`/`_tool_salvar_task_cr` são realmente redundantes | tempo de alinhamento com o time |