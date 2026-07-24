# Catálogo de Tools — `workflow_coding_review`

Inventário das ferramentas (`FunctionTool`) usadas pelos quatro agentes do pipeline
`coding_review_pipeline` (`agent.py`): `cr_context_engineer` → `LoopAgent[cr_coder ↔ cr_executor]` → `cr_reviewer` (analyzer).

A coluna **Origem** traz o caminho do arquivo onde a função da tool está definida..


## 1. `cr_context_engineer` (`cr_context_engineer.py`)


| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `_tool_salvar_task_cr` (`FunctionTool` como `_tool_salvar_task_cr_adk`) | `src/agents/workflow_coding_review/cr_context_engineer.py` | `task_id: str`, `task_json: str` | `dict {sucesso, erro, caminho, task_id} ou dict {sucesso, erro, caminho}` | Valida via `SalvarTaskSchema`, faz `json.loads` do conteúdo e grava `<task_id>.json` em `workspace_output/coder/tasks/`. Cópia local de `tool_salvar_task`, mudando só o diretório de destino. |

---

## 2. `cr_coder` (`cr_coder.py`)

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `tool_criar_arquivo` | `shared/tools/filesystem.py` | `caminho: str`, `conteudo: str`, `base_dir` (existe na função original, mas bound por closure a `workspace_output/coder/src/` — invisível ao LLM) | `dict {sucesso, caminho, bytes_escritos, erro} ou dict {sucesso, erro, caminho}` | Cria/sobrescreve arquivo completo. Valida extensão (whitelist) e bloqueia diretórios protegidos (`.git`, `.venv`, etc.). Única forma de persistir código — texto solto na resposta é descartado. |
| `tool_ler_arquivo` | `shared/tools/filesystem.py` | `caminho: str`, `base_dir` (bound a `workspace_output/coder/src/` — invisível ao LLM) | `str` (conteúdo do arquivo, ou `"Erro: ..."`) | Lê arquivo existente como texto UTF-8. Usado nas re-execuções para inspecionar o arquivo apontado como causa do erro. |
| `tool_substituir_trecho` | `shared/tools/filesystem.py` | `caminho: str`, `trecho_antigo: str`, `trecho_novo: str`, `base_dir` (bound a `workspace_output/coder/src/` — invisível ao LLM) | `str` (mensagem `"Sucesso: ..."` ou `"Erro: ..."`) | Substitui a **primeira** ocorrência exata (byte-a-byte) de `trecho_antigo` por `trecho_novo`. Preferida a recriar o arquivo inteiro nas correções pós-falha. |
---

## 3. `cr_executor` (`cr_executor.py`)

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `tool_verificar_docker` | `src/agents/workflow_coding_review/cr_executor.py` | — | `dict {disponivel, versao, erro}` | Checa conectividade com o Docker daemon. Primeiro passo obrigatório — se indisponível, reporta falha sem tentar buildar. |
| `tool_listar_arquivos_coder` | `src/agents/workflow_coding_review/cr_executor.py` | — | `dict {arquivos: list[str], total: int}` | Lista (recursivo, ignorando `__pycache__`) os arquivos em `workspace_output/coder/src/`. Confirma que há código antes do build. |
| `tool_executar_em_docker` | `src/agents/workflow_coding_review/cr_executor.py` | `tool_context` (injetado) | `dict {status, logs_build, logs_runtime, entrypoint, dockerfile, report_path, duracao_segundos, mensagem, container_name, access_url} ou dict {status, logs_build, logs_runtime, entrypoint, dockerfile, report_path, duracao_segundos, mensagem}` | Copia o workspace do coder p/ diretório de build isolado, reaproveita o `Dockerfile` do coder ou gera fallback, builda a imagem (timeout 300s) e roda o container (limite 512m/50% CPU, porta 8000). Healthcheck em 3 fases (container "running" → grace period + estabilidade → HTTP em `/docs` e na rota principal descoberta via `/openapi.json`). Em sucesso mantém o container rodando; em falha, derruba. Sempre persiste relatório em `coder/execution/execution_report.md` e grava status em `tool_context.state["_last_exec_status"]`. |
| `tool_exit_loop_se_sucesso` | `src/agents/workflow_coding_review/cr_executor.py` | `tool_context` (injetado) | `dict {encerrado: bool, motivo: str}` | Substitui o `exit_loop` padrão com trava de segurança: só seta `tool_context.actions.escalate = True` se `state["_last_exec_status"] == "sucesso"`; caso contrário bloqueia e o loop volta ao coder. |

### Helpers internos (não são tools, não são chamados pelo LLM)

Usados internamente por `tool_executar_em_docker`:

| Helper | Entrada | Retorno | Descrição |
|---|---|---|---|
| `_detect_entrypoint(src_dir)` | `src_dir: Path`  | `str` — caminho relativo do arquivo de entrada | Procura, em ordem, os candidatos `app/main.py`, `main.py`, `src/main.py`, `src/app/main.py`, `app.py`, `server.py`, `run.py`, `manage.py`. Se nenhum existir, varre todo `.py` do diretório procurando `"FastAPI"` ou `"uvicorn"` no conteúdo. Se nada for encontrado, retorna `"main.py"` como fallback (mesmo sem esse arquivo existir). |
| `_detect_requirements(src_dir)` | `src_dir: Path` | `str \| None` — caminho relativo do arquivo de dependências, ou `None` | Procura `requirements.txt`, `requirements/base.txt`, `requirements/prod.txt`, nessa ordem; retorna o primeiro que existir. |
| `_has_pyproject(src_dir)` | `src_dir: Path` | `bool` | Só checa se `pyproject.toml` existe na raiz do diretório. |
| `_generate_dockerfile(src_dir)` | `src_dir: Path` | `str` — conteúdo completo do Dockerfile gerado | Só roda quando o coder não criou um `Dockerfile` próprio. Usa `_detect_entrypoint`, `_detect_requirements` e `_has_pyproject` para montar um Dockerfile `python:3.12-slim` com `pip install` (via `requirements.txt`, `pyproject.toml`, ou uma lista fixa de pacotes comuns como último recurso), expõe a porta 8000 e monta o `CMD` do `uvicorn` apontando pro módulo do entrypoint detectado. |
| `_write_report(report_path, content)` | `report_path: Path`, `content: str` | `None` (efeito colateral: grava o arquivo) | Cria os diretórios intermediários se necessário e escreve `content` em `report_path` — usada em todos os pontos de saída de `tool_executar_em_docker` (sucesso e cada tipo de falha) para persistir `execution_report.md`. |
| `_cleanup_container(client, name)` | `client: docker.DockerClient`, `name: str` | `None` | Remove um container existente com aquele nome antes de subir um novo (evita conflito de nome entre execuções). Silencia `docker.errors.NotFound`; loga um warning em qualquer outra exceção, sem propagá-la. |
| `_discover_main_route(base_url, http_mod)` | `base_url: str` (ex: `"http://localhost:8000"`), `http_mod` (módulo `requests`, passado por parâmetro) | `str \| None` — rota principal para o teste funcional | Busca `/openapi.json`, filtra rotas GET excluindo `/docs`, `/docs/oauth2-redirect`, `/openapi.json`, `/redoc`. Prioriza `"/"` se existir; senão retorna a primeira rota GET na ordem declarada no código. Retorna `None` só se a app não tiver nenhuma rota GET (API pura sem HTML). Em qualquer erro ao consultar `/openapi.json`, faz fallback retornando `"/"`. |

---

## 4. `cr_reviewer` (`cr_reviewer.py`)

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `tool_ler_arquivo` | `shared/tools/filesystem.py` | `caminho: str`, `base_dir` (existe na função original, mas bound por closure a `workspace_output/coder/src/` — invisível ao LLM) | `str` (conteúdo do arquivo, ou `"Erro: ..."`) | Lê cada arquivo listado em `ARQUIVOS A REVISAR`. |

Além da tool acima, duas funções Python puras rodam como **callbacks** (não são `FunctionTool`s, o LLM não as chama):

| Callback | Quando roda | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `_inject_static_findings` (`before_agent_callback`) | Antes do LLM analisar | `callback_context` (injetado) | `None` (efeito colateral: grava `state["static_findings_block"]`) | Roda **Ruff** e **Bandit** em paralelo via `run_capabilities` sobre o workspace do coder; até 30 findings formatados e injetados no prompt como ponto de partida da revisão. Falha de uma ferramenta não quebra a outra. |
| `_persist_review` (`after_agent_callback`) | Depois do LLM produzir a análise | `callback_context` (injetado) | `None` (levanta `RuntimeError` se a gravação falhar) | Lê `state["review_analysis"]` e chama `tool_salvar_relatorio` diretamente em Python (não como tool), gravando `verificacao_revisao.md`. |

### Helpers internos (não são tools, não são chamados pelo LLM)

| Helper | Entrada | Retorno | Descrição |
|---|---|---|---|
| `_bind(tool, agent_ws)` | `tool` — a `FunctionTool` (ou callable) original; `agent_ws: str` — workspace a bindar | `FunctionTool` com `base_dir`/`cwd` injetado por closure | Wrapper local que chama `_bind_tool_to_workspace(tool, agent_ws, _WORKSPACE_ROOT)` (`shared/agent_factory.py`). Usada para bindar `tool_ler_arquivo` ao workspace do `cr_coder` (`_CODER_WS`), não ao do próprio `cr_reviewer`. |
| `_discover_coder_files()` | Nenhum parâmetro | `str` — lista em formato bullet (`"- arquivo1\n- arquivo2..."`) | Lista (recursivo, ignorando `__pycache__`) todos os arquivos em `_CODER_WS`, ordenados. Roda no momento da invocação do agente (chamada de dentro de `_analyzer_instruction_provider`), não em import-time — por isso reflete o estado real do workspace do coder naquele momento. Se o diretório do coder ainda não existir, retorna `"- (nenhum arquivo ainda — coder será executado antes de você)"`; se existir mas estiver vazio, retorna `"- (workspace vazio)"`. |
| `_format_findings_block(findings)` | `findings: list[Finding]` — achados retornados por `run_capabilities` | `str` — bloco de texto legível, uma tool/regra por linha | Formata cada `Finding` como `"[SEVERIDADE] origem/regra — arquivo:linha\n  mensagem"`. Se `findings` estiver vazio, retorna a string fixa `"Nenhum problema identificado pelas ferramentas de análise estática."`. |
| `_analyzer_instruction_provider(ctx)` | `ctx` — `ReadonlyContext` injetado pelo ADK (dá acesso a `ctx.state`) | `str` — instrução final montada para o LLM naquele turno | É o `instruction` do `_analyzer` (um `InstructionProvider`, não uma string estática): lê `ctx.state["static_findings_block"]` (gravado por `_inject_static_findings`) e substitui os placeholders `__STATIC_FINDINGS__`, `__CODER_WS__` e `__FILES__` (via `_discover_coder_files()`) no template `_ANALYZER_INSTRUCTION_TEMPLATE`. Roda a cada invocação do agente, então sempre reflete o estado mais recente do workspace do coder e dos findings estáticos. |

---

# Agentes "de fora" (`src/agents/coder`, `context_engineer`, `reviewer`)

## `coder` (`src/agents/coder/agent.py`)

Sem `agent_subdir` → `create_se_agent` pula todo o bloco de binding. Isso significa que `base_dir`/`cwd` **continuam parâmetros reais na assinatura** dessas funções (com default `None`) e por isso aparecem no schema exposto ao LLM — diferente dos `cr_*`, onde a closure remove o parâmetro da assinatura antes de gerar o schema. 

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `tool_criar_arquivo` | `shared/tools/filesystem.py` | `caminho: str`, `conteudo: str`, `base_dir: str \| None = None` | `dict {sucesso, caminho, bytes_escritos, erro}` | Igual ao `cr_coder`, mas `base_dir` não é bound — fica visível ao LLM; se omitido (`None`), grava relativo ao CWD. |
| `tool_git_add` | `shared/tools/git.py` | `arquivos: str`, `cwd: str \| None = None` | `dict {sucesso, stdout, stderr, returncode}` | Executa `git add <arquivos>` ou `git add .`. |
| `tool_git_commit` (`require_confirmation=True`) | `shared/tools/git.py` | `mensagem: str` , `cwd: str \| None = None` | `dict {sucesso, stdout, stderr, returncode}` ou `{sucesso: False, mensagem}` | Executa `git commit -m` diretamente após validar que há stage (`git diff --staged`). Sem stage, falha sem efeito. |
| `tool_git_checkout` | `shared/tools/git.py` | `branch: str`, `criar: bool = False`, `cwd: str \| None = None` | `dict {sucesso, comando, stdout, stderr, returncode}` | `git checkout <branch>`, ou `git checkout -b <branch>` se `criar=True`. |
| `tool_ler_arquivo` | `shared/tools/filesystem.py` | `caminho: str`, `base_dir: str \| None = None` | `str` (conteúdo ou `"Erro: ..."`) | Igual ao `cr_coder`, mas `base_dir` visível/não bound. |
| `tool_substituir_trecho` | `shared/tools/filesystem.py` | `caminho: str`, `trecho_antigo: str`, `trecho_novo: str`, `base_dir: str \| None = None` | `str` (`"Sucesso: ..."` ou `"Erro: ..."`) | Igual ao `cr_coder`, mas `base_dir` visível/não bound. |
| `tool_ask_clarification` | `shared/tools/clarification.py`, auto-injetada | `titulo, secao, descricao, impacto, sugestao, nome_arquivo: str`, `base_dir: str \| None = None` | `dict {sucesso, erro, caminho, título, status}` | Gera Doubt Artifact em Markdown e sinaliza que o agente deve parar e devolver controle ao supervisor. `base_dir` visível/não bound aqui — se omitido, grava relativo ao CWD. |
---

## `context_engineer` (`src/agents/context_engineer/agent.py`)

Passa `agent_subdir="context_engineer"` → tools **bound**. `AGENT_DIRS["context_engineer"] = "tasks"`, grava em `workspace_output/tasks/` (não `coder/tasks/`, que é onde o `cr_context_engineer` grava).

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `tool_salvar_task_adk` | `src/agents/context_engineer/tools.py` | `task_id: str`, `task_json: str` | `dict {sucesso, erro, caminho, task_id}` | Versão canônica que o `cr_context_engineer` copia e adapta. Valida `task_id` (deve iniciar com `"TASK-"`), faz `json.loads` e grava `<task_id>.json` via `get_agent_workspace("context_engineer")`. |
| `tool_ask_clarification` | `shared/tools/clarification.py`, auto-injetada | `titulo, secao, descricao, impacto, sugestao, nome_arquivo: str`, `base_dir` (existe na função original, mas bound por closure a `workspace_output/tasks/` — invisível ao LLM) | `dict {sucesso, erro, caminho, título, status}` | Igual ao `coder`, mas bound ao workspace do agente (`workspace_output/tasks/`). |
---

## `reviewer` (`src/agents/reviewer/agent.py`, nome interno `review_agent`)

Sem `agent_subdir` → mesma situação do `coder`: `cwd`/`base_dir` continuam parâmetros reais e visíveis ao LLM (default `None`). Revisa por **diff Git** (o `cr_reviewer` revisa por arquivos do workspace + análise estática).

| Tool | Origem | Entrada | Retorno | Descrição |
|---|---|---|---|---|
| `tool_ler_diff` | `shared/tools/git.py` | `branch_alvo: str = "main"`, `cwd: str \| None = None` | `dict {sucesso, erro, diff}` | Executa `git diff <branch_alvo>`  |
| `tool_salvar_relatorio` | `shared/tools/filesystem.py` | `conteudo: str`, `nome_arquivo: str = "doubt_artifact_revisao.md"`, `base_dir: str \| None = None` | `dict {sucesso, caminho, bytes_escritos, erro}` | Mesma tool que o `cr_reviewer` usa via callback (sem exposição ao LLM); aqui é `FunctionTool` normal, o LLM decide quando chamá-la  |
| `tool_ask_clarification` | `shared/tools/clarification.py`, auto-injetada | `titulo, secao, descricao, impacto, sugestao, nome_arquivo: str`, `base_dir: str \| None = None` | `dict {sucesso, erro, caminho, título, status}` | Igual às anteriores, `base_dir` visível/não bound aqui. |
---

## Cobertura: todas as tools envolvidas (`cr_*` + agentes "de fora")

| Tool | Usada por |
|---|---|
| `tool_criar_arquivo` | `cr_coder` (bound), `coder` (sem bind) |
| `tool_ler_arquivo` | `cr_coder` (bound), `cr_reviewer` (bound), `coder` (sem bind) |
| `tool_substituir_trecho` | `cr_coder` (bound), `coder` (sem bind) |
| `tool_salvar_relatorio` | `cr_reviewer` (via callback, sem exposição ao LLM), `reviewer` (exposta ao LLM) |
| `tool_git_add` | `coder` |
| `tool_git_commit` | `coder` |
| `tool_git_checkout` | `coder` |
| `tool_ler_diff` | `reviewer` |
| `tool_ask_clarification` | `coder`, `context_engineer`, `reviewer` (auto-injetada) — ausente em todos os `cr_*` |
| `_tool_salvar_task_cr` (local) | `cr_context_engineer` |
| `tool_salvar_task` / `tool_salvar_task_adk` | `context_engineer` |
| `tool_verificar_docker`, `tool_listar_arquivos_coder`, `tool_executar_em_docker`, `tool_exit_loop_se_sucesso` (locais) | `cr_executor` (sem equivalente "de fora" — este agente não existe fora do pipeline) |
