# Desacoplamento Prompts ↔ Tools — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refatorar prompts dos 5 agentes que citam tools por nome (`requirements`, `coder`, `reviewer`, `context_engineer`, `io_agent`) para descreverem capacidades semanticamente, e elevar todas as docstrings de tools a padrão GOOD (Purpose + Quando usar + Args + Returns).

**Architecture:** Prompts descrevem papel/workflow/protocolos em vocabulário de capacidade (verbos no infinitivo). Docstrings carregam toda a informação acionável sobre cada tool. ADK entrega `__doc__` ao LLM via `FunctionDeclaration.description`, então a docstring é a única fonte de verdade sobre a tool.

**Tech Stack:** Python 3.12, Google ADK, FastAPI/uvicorn, LiteLLM, pytest. Repositório em `adk/`.

**Referências:**
- Spec: `docs/superpowers/specs/2026-05-17-prompt-tool-decoupling-design.md`
- CLAUDE.md (seções "Gotchas e lições do orchestrator E2E" e "Verificação rápida de schemas de tool")

**Estrutura de arquivos afetados:**
- Prompts (modify): 5 arquivos sob `adk/src/agents/{requirements,coder,reviewer,context_engineer,io_agent}/prompt.py`
- Tools (modify, só docstring): `adk/shared/tools/{filesystem,git,slicer_tool,search_tool,clarification,design_filesystem,design_date}.py` + `adk/shared/tools/design_validate/*.py` + `adk/src/agents/qa_agent/tools/*.py`
- Sub-agent descriptions (modify): `adk/src/agents/requirements/agent.py` (glossario_agent), `adk/src/agents/qa_agent/agent.py` (subagents)

**Convenção de commit:** seguir o padrão do projeto (`docs:`, `update:`, `fix:`). Cada task termina em commit atômico.

**Não-objetivos:** mudar assinaturas, renomear funções, mexer em `agent_factory.py`, alterar comportamento de tools.

---

## Phase 0 — Inventário e baseline

### Task 0.1: Inventariar docstrings ausentes em qa_agent/tools e design_validate

**Files:**
- Read-only: `adk/shared/tools/design_validate/artifact_gatekeeper.py`
- Read-only: `adk/shared/tools/design_validate/contentValidator.py`
- Read-only: `adk/shared/tools/design_validate/gatekeeper_tool.py`
- Read-only: `adk/src/agents/qa_agent/tools/build_fix_prompt.py`
- Read-only: `adk/src/agents/qa_agent/tools/doubt_artifact.py`
- Read-only: `adk/src/agents/qa_agent/tools/doubt_tool.py`
- Read-only: `adk/src/agents/qa_agent/tools/log_parser_tool.py`
- Read-only: `adk/src/agents/qa_agent/tools/planner_tools.py`
- Read-only: `adk/src/agents/qa_agent/tools/pytest_runner.py`

- [ ] **Step 1: Listar funções públicas e classificar docstrings em cada arquivo**

Rodar:

```bash
cd adk && for f in shared/tools/design_validate/*.py src/agents/qa_agent/tools/*.py; do
  echo "=== $f ==="
  python -c "
import ast, sys
src = open('$f').read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
        doc = ast.get_docstring(node) or ''
        size = len(doc)
        flag = 'MISSING' if size == 0 else ('SHALLOW' if size < 80 else 'GOOD')
        print(f'  {node.name:40s} [{flag}] {size} chars')
"
done
```

Expected: lista de funções públicas com flag de qualidade.

- [ ] **Step 2: Anotar resultados num arquivo de trabalho temporário**

Salvar a saída do Step 1 em `/tmp/docstring-inventory.txt`. Esse arquivo é referência para as tasks da Phase 1 — não vai pro commit.

- [ ] **Step 3: Confirmar baseline rodando o verificador de prompts**

```bash
cd adk && rg -nP '\b(tool_[a-z_]+|run_slicer|ler_chunk|extract_text|run_search|gerar_doubt_artifact|check_glossary|add_to_glossary|check_active_blocks|current_date|save_artifact|promote_artifact|list_staging_files|tool_ask_clarification|tool_salvar_task)\b' \
   src/agents/requirements/prompt.py \
   src/agents/coder/prompt.py \
   src/agents/reviewer/prompt.py \
   src/agents/context_engineer/prompt.py \
   src/agents/io_agent/prompt.py | wc -l
```

Expected: número > 0 (mostra o baseline atual; este número precisa virar 0 ao fim do plano).

- [ ] **Step 4: Não commitar** (inventário é working memory)

---

## Phase 1 — Upgrade de docstrings

> Padrão GOOD a aplicar em todas as funções abaixo:
>
> ```python
> def tool_xyz(param1: str, param2: Optional[int] = None) -> dict:
>     """<Frase de propósito, uma linha, verbo no infinitivo>.
>
>     <Quando usar: gatilhos no workflow do agente, o que esta capacidade
>     resolve. 2-4 frases.>
>
>     <Quando NÃO usar / caveats — só se houver risco real. Opcional.>
>
>     Args:
>         param1: <semântica do parâmetro, não só tipo.>
>         param2: <idem.>
>
>     Returns:
>         <Forma do retorno; chaves do dict; shape em caso de erro.>
>     """
> ```
>
> Critério GOOD: docstring ≥ 80 chars, com propósito + Quando usar + Args + Returns. Não alterar a assinatura ou o corpo da função.

### Task 1.1: Elevar docstrings em `shared/tools/filesystem.py`

**Files:**
- Modify: `adk/shared/tools/filesystem.py`

Funções a tocar: `tool_criar_arquivo`, `tool_ler_arquivo`, `tool_substituir_trecho`, `tool_salvar_relatorio`, `tool_salvar_artefato_requisito`, `tool_ler_workspace`, `tool_listar_workspace`.

- [ ] **Step 1: Reescrever docstring de `tool_criar_arquivo`**

Substituir o bloco docstring atual por:

```python
    """Cria ou sobrescreve um arquivo no disco com o conteúdo fornecido.

    Use esta capacidade sempre que precisar materializar um arquivo do zero —
    código novo, documento, configuração. Se o arquivo já existir, o conteúdo
    é integralmente substituído (não é append). Diretórios intermediários são
    criados automaticamente.

    Não use para edição parcial de arquivos existentes; para isso há uma
    capacidade dedicada de substituição de trecho.

    Validações automáticas:
    - Só permite extensões: .py, .js, .ts, .html, .css, .json, .md, .txt,
      .yaml, .yml, .toml, .csv, .env.example.
    - Bloqueia escrita em .git, .venv, venv, node_modules, __pycache__, .env.

    Args:
        caminho: Caminho do arquivo. Quando há base_dir, é relativo a ele
            (não pode ser absoluto nem conter ".."). Sem base_dir, é relativo
            ao CWD do processo.
        conteudo: Texto completo a escrever (UTF-8).
        base_dir: Diretório base do agente injetado pela factory. Permite
            isolamento workspace-bound. Quando None, comportamento legado.

    Returns:
        dict com chaves: `sucesso` (bool), `caminho` (str do path resolvido
        ou input em caso de erro), `bytes_escritos` (int, só em sucesso),
        `erro` (str ou None). Em falha, `sucesso=False` e `erro` traz a
        mensagem.
    """
```

- [ ] **Step 2: Reescrever docstring de `tool_ler_arquivo`**

```python
    """Lê o conteúdo completo de um arquivo do disco como texto UTF-8.

    Use sempre que precisar do conteúdo atual de um arquivo antes de
    editá-lo, validar uma estrutura ou copiar trechos para outro local.
    Não use para arquivos binários (PDF, imagens) — esta capacidade lê
    como texto puro.

    Args:
        caminho: Caminho do arquivo. Relativo a base_dir se fornecido,
            senão ao CWD.
        base_dir: Diretório base do agente (injetado pela factory).

    Returns:
        str com o conteúdo do arquivo em UTF-8, ou string iniciada por
        "Erro:" descrevendo o problema (arquivo inexistente, path
        traversal, falha de leitura).
    """
```

- [ ] **Step 3: Reescrever docstring de `tool_substituir_trecho`**

```python
    """Substitui um trecho exato de um arquivo já existente por novo conteúdo.

    Use para editar arquivos preservando o restante intocado — refator
    cirúrgico, ajuste de assinatura, correção pontual. O 'trecho_antigo'
    DEVE ser uma cópia byte-a-byte do texto que está hoje no arquivo,
    incluindo indentação e quebras de linha; o casamento é exato, não
    fuzzy.

    Não use para criar arquivos novos (use a capacidade de criação de
    arquivo) nem para substituir conteúdo inteiro do arquivo.

    Args:
        caminho: Caminho do arquivo a editar. Relativo a base_dir se
            fornecido.
        trecho_antigo: Texto exato que está no arquivo hoje. Se não
            casar exatamente, a tool retorna erro sem alterar nada.
        trecho_novo: Texto que substituirá `trecho_antigo`.
        base_dir: Diretório base do agente (injetado pela factory).

    Returns:
        str com mensagem de sucesso indicando o arquivo alterado, ou
        string "Erro:" se: arquivo inexistente, trecho_antigo não
        encontrado, ou falha de I/O.
    """
```

- [ ] **Step 4: Reescrever docstring de `tool_salvar_relatorio`**

```python
    """Persiste um relatório de revisão em Markdown no disco.

    Use ao final de uma análise/revisão para deixar um artefato durável
    consumível por humanos ou por outros agentes (ex: reviewer salva o
    parecer técnico em verificacao_revisao.md). O nome do arquivo deve
    sempre terminar em .md.

    Args:
        conteudo: Texto Markdown completo do relatório.
        nome_arquivo: Nome do arquivo de saída. Default
            "doubt_artifact_revisao.md". Obrigatório terminar em .md.
        base_dir: Diretório base do agente (injetado pela factory).

    Returns:
        dict com chaves: `sucesso` (bool), `caminho` (str do path
        resolvido), `bytes_escritos` (int em sucesso), `erro` (str ou
        None). Em validação inválida ou I/O falho, `sucesso=False`.
    """
```

- [ ] **Step 5: Reescrever docstring de `tool_salvar_artefato_requisito`**

```python
    """Persiste um artefato estruturado de requisito (HU, RF, RNF, RN, Glossário).

    Use ao final da análise de cada requisito atômico para gravar o
    artefato em Markdown no subdiretório canônico do tipo. O subdiretório
    é escolhido automaticamente pelo `tipo`. IDs (exceto Glossário)
    seguem o padrão AAAA-999 (ex: HU-001, RF-002).

    Args:
        tipo: Tipo do artefato. Valores aceitos (case-insensitive): HU,
            RF, RNF, RN, GLOSSARIO. Outros tipos vão para "Outros".
        id_req: Identificador do requisito no formato AAAA-999 (não se
            aplica a GLOSSARIO, cujo arquivo é fixo "Glossario.md").
        conteudo_md: Texto Markdown completo do artefato.
        base_dir: Diretório base do agente. Quando informado, escreve
            em `<base_dir>/<subdir>/<id_req>.md`. Quando None, usa o
            caminho legado relativo ao CWD.

    Returns:
        str com mensagem "SUCESSO: <tipo> <id> salvo em <caminho>" em
        sucesso, ou "ERRO ao salvar artefato: <motivo>" em falha
        (id_req fora do padrão, path inválido, I/O).
    """
```

- [ ] **Step 6: Reescrever docstring de `tool_ler_workspace`**

```python
    """Lê arquivo de qualquer subpasta do workspace global (cross-agent, read-only).

    Diferente da capacidade de leitura escopada ao agente, esta permite
    que um agente consulte outputs gerados por outros agentes — ex:
    reviewer/qa consultam o que o coder produziu. Não permite escrita
    em workspace de outro agente.

    Args:
        caminho: Caminho relativo à raiz do workspace global
            (ex: 'coder/main.py').
        base_dir: Raiz do workspace (injetada pela factory como
            workspace_root). Obrigatório — sem ele a tool retorna erro.

    Returns:
        str com o conteúdo do arquivo, ou string "Erro:" descrevendo
        path traversal, arquivo inexistente ou base_dir ausente.
    """
```

- [ ] **Step 7: Reescrever docstring de `tool_listar_workspace`**

```python
    """Lista os arquivos e diretórios de um caminho do workspace global.

    Use para descobrir o que outros agentes produziram antes de
    consultar arquivos individuais com a capacidade de leitura.
    Retorna nomes ordenados alfabeticamente.

    Args:
        caminho: Caminho relativo à raiz do workspace (default ".",
            que lista a raiz).
        base_dir: Raiz do workspace (injetada pela factory).
            Obrigatório.

    Returns:
        list[str] com nomes em ordem alfabética, ou str "Erro:" se
        diretório inexistente, path traversal ou base_dir ausente.
    """
```

- [ ] **Step 8: Verificar tamanho mínimo de cada docstring nova**

```bash
cd adk && python -c "
import ast
src = open('shared/tools/filesystem.py').read()
tree = ast.parse(src)
targets = {'tool_criar_arquivo','tool_ler_arquivo','tool_substituir_trecho','tool_salvar_relatorio','tool_salvar_artefato_requisito','tool_ler_workspace','tool_listar_workspace'}
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name in targets:
        doc = ast.get_docstring(node) or ''
        ok = 'OK' if len(doc) >= 80 else 'SHORT'
        print(f'{node.name:40s} [{ok}] {len(doc)} chars')
"
```

Expected: todas as 7 funções com `[OK]` e ≥ 200 chars.

- [ ] **Step 9: Rodar import smoke test**

```bash
cd adk && .venv/bin/python -c "from shared.tools.filesystem import tool_criar_arquivo, tool_ler_arquivo, tool_substituir_trecho, tool_salvar_relatorio, tool_salvar_artefato_requisito, tool_ler_workspace, tool_listar_workspace; print('imports OK')"
```

Expected: `imports OK`.

- [ ] **Step 10: Commit**

```bash
git add adk/shared/tools/filesystem.py
git commit -m "$(cat <<'EOF'
update: docstrings detalhadas em shared/tools/filesystem.py

Eleva 7 funcoes ao padrao GOOD (proposito + quando usar + Args + Returns)
para servirem como FunctionDeclaration.description suficiente, removendo a
necessidade dos prompts referenciarem tools por nome.
EOF
)"
```

---

### Task 1.2: Elevar docstrings em `shared/tools/git.py`

**Files:**
- Modify: `adk/shared/tools/git.py`

Funções a tocar: `tool_git_add`, `tool_git_commit`, `tool_git_checkout`, `tool_ler_diff`, `tool_preparar_commit`, `tool_confirmar_commit`.

(O arquivo também tem `trava_seguranca_git_commit` que é interna; deixar como está.)

- [ ] **Step 1: Reescrever docstring de `tool_git_add`**

```python
    """Adiciona arquivos ao stage do Git (git add).

    Use depois de criar ou editar arquivos, quando estiver pronto para
    preparar a mudança para versionamento. Recebe nomes de arquivo
    separados por espaço; quando string vazia, equivale a `git add .`
    (use com cautela — preferir listar arquivos explicitamente).

    Args:
        arquivos: Lista de paths separados por espaço (ex:
            "src/app.py tests/test_app.py"). Vazio = `git add .`
            (todos os modificados).
        cwd: Diretório de execução do comando git. Injetado pela
            factory quando aplicável.

    Returns:
        dict com chaves: `sucesso` (bool), `stdout` (str), `stderr`
        (str), `returncode` (int). `sucesso=True` quando returncode==0.
    """
```

- [ ] **Step 2: Reescrever docstring de `tool_git_commit`**

```python
    """Registra um commit no Git com a mensagem fornecida.

    Use somente após ter preparado a mudança para versionamento (stage)
    e, em fluxos com supervisão humana, após receber autorização
    explícita do supervisor. A tool valida internamente que há
    alterações staged antes de commitar; sem stage, retorna falha
    sem efeito.

    Convenção de mensagem do projeto (Conventional Commits):
    `<tipo>(<escopo>): #<issue> <descrição>`. Tipos permitidos:
    feat, fix, docs, refactor, test, chore, ci, style, perf.

    Args:
        mensagem: Mensagem completa do commit, já formatada conforme
            Conventional Commits.
        cwd: Diretório de execução do comando git. Injetado pela
            factory.

    Returns:
        dict com chaves: `sucesso` (bool), `stdout`, `stderr`,
        `returncode` em caso de execução. Quando não há nada para
        commitar: `{sucesso: False, mensagem: "Nada para commitar"}`.
    """
```

- [ ] **Step 3: Reescrever docstring de `tool_git_checkout`**

```python
    """Troca ou cria uma branch de trabalho no Git.

    Use no início de uma tarefa para isolar a mudança em sua própria
    branch (recomendado o padrão do projeto:
    `feature/code/<issue>-descricao-curta` ou
    `hotfix/code/<issue>-descricao-curta`). Para alternar entre branches
    já existentes, use `criar=False`; para inicializar nova branch,
    `criar=True`.

    Args:
        branch: Nome da branch alvo.
        criar: Se True, executa `git checkout -b` criando a branch
            antes de trocar. Default False.
        cwd: Diretório de execução. Injetado pela factory.

    Returns:
        dict com chaves: `sucesso` (bool), `comando` (lista do shell
        executado), `stdout`, `stderr`, `returncode`.
    """
```

- [ ] **Step 4: Reescrever docstring de `tool_ler_diff`**

```python
    """Lê o diff acumulado da branch atual em relação a outra branch.

    Use durante uma revisão de código para inspecionar TODAS as
    alterações pendentes — arquivos criados, modificados, deletados —
    em formato unified diff. Tipicamente compara contra `main`, mas
    aceita qualquer branch como alvo.

    Args:
        branch_alvo: Branch contra a qual comparar. Default "main".
        cwd: Diretório de execução. Injetado pela factory.

    Returns:
        dict com chaves: `sucesso` (bool), `erro` (str ou None),
        `diff` (str unified diff em sucesso, None em falha). Quando
        não há diferenças, retorna `sucesso=False` com erro explicando.
    """
```

- [ ] **Step 5: Reescrever docstring de `tool_preparar_commit`**

```python
    """Valida o stage e retorna o diff para o agente apresentar ao supervisor.

    Esta é a primeira metade do protocolo human-in-the-loop de commit:
    primeiro o agente prepara o commit (esta tool), apresenta o resumo
    do diff ao supervisor, aguarda autorização explícita, e só então
    chama a tool de confirmação para efetivar.

    NÃO executa o commit — apenas valida que há algo staged e devolve
    o diff. Use sempre antes de propor uma versão para aprovação.

    Args:
        mensagem: Mensagem de commit sugerida pelo agente, já formatada
            em Conventional Commits.
        cwd: Diretório de execução. Injetado pela factory.

    Returns:
        dict com chaves: `sucesso` (bool), `mensagem` (echo da
        mensagem em sucesso, motivo em falha), `diff` (str unified
        diff staged em sucesso). `sucesso=False` quando working tree
        clean ou nada em stage.
    """
```

- [ ] **Step 6: Reescrever docstring de `tool_confirmar_commit`**

```python
    """Efetiva o commit Git após autorização do supervisor — segunda metade do gate.

    SÓ DEVE ser chamada após o supervisor ter respondido autorização
    explícita ao resumo apresentado via tool_preparar_commit. Esta tool
    é tipicamente registrada com require_confirmation=True como dupla
    trava de segurança.

    Re-valida o stage (defensivamente) antes de commitar — se nada
    estiver staged no momento da confirmação, retorna falha.

    Args:
        mensagem: Mensagem de commit. Idealmente a mesma apresentada
            via tool_preparar_commit para garantir consistência.
        cwd: Diretório de execução. Injetado pela factory.

    Returns:
        dict com chaves: `sucesso` (bool), `stdout`, `stderr`,
        `returncode` em execução. Em ausência de stage no momento da
        confirmação: `{sucesso: False, mensagem: "..."}`.
    """
```

- [ ] **Step 7: Verificar tamanhos**

```bash
cd adk && python -c "
import ast
src = open('shared/tools/git.py').read()
tree = ast.parse(src)
targets = {'tool_git_add','tool_git_commit','tool_git_checkout','tool_ler_diff','tool_preparar_commit','tool_confirmar_commit'}
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name in targets:
        doc = ast.get_docstring(node) or ''
        ok = 'OK' if len(doc) >= 80 else 'SHORT'
        print(f'{node.name:30s} [{ok}] {len(doc)} chars')
"
```

Expected: todas as 6 com `[OK]`.

- [ ] **Step 8: Import smoke test**

```bash
cd adk && .venv/bin/python -c "from shared.tools.git import tool_git_add, tool_git_commit, tool_git_checkout, tool_ler_diff, tool_preparar_commit, tool_confirmar_commit; print('imports OK')"
```

Expected: `imports OK`.

- [ ] **Step 9: Commit**

```bash
git add adk/shared/tools/git.py
git commit -m "$(cat <<'EOF'
update: docstrings detalhadas em shared/tools/git.py

Eleva 6 funcoes git (add/commit/checkout/diff/preparar/confirmar) ao padrao
GOOD com semantica do human-in-the-loop documentada na propria docstring.
EOF
)"
```

---

### Task 1.3: Elevar docstrings em `shared/tools/slicer_tool.py`

**Files:**
- Modify: `adk/shared/tools/slicer_tool.py`

Funções a tocar: `extract_text`, `run_slicer`, `ler_chunk` (este último está MISSING).

- [ ] **Step 1: Reescrever docstring de `extract_text`**

```python
def extract_text(file_path: str) -> str:
    """Extrai texto de um documento PDF, TXT ou MD.

    Use quando precisar do conteúdo bruto de um documento de
    requisitos ou referência para análise textual. Suporta PDF (via
    PyMuPDF), TXT e Markdown. Se `file_path` for um diretório,
    automaticamente lê o primeiro arquivo suportado encontrado em
    ordem alfabética.

    Args:
        file_path: Caminho de arquivo (.pdf, .txt, .md) ou diretório
            contendo um arquivo suportado. Caminhos relativos são
            resolvidos contra ADK_AGENT_DATA_DIR (se definido) ou
            CWD.

    Returns:
        str com o conteúdo textual extraído, ou string iniciada por
        "Erro:" descrevendo extensão não suportada, diretório vazio
        ou falha de leitura. Pode levantar ImportError se PDF for
        solicitado sem PyMuPDF instalado.
    """
```

- [ ] **Step 2: Reescrever docstring de `run_slicer`**

```python
def run_slicer(filename: str = "", paragraphs_per_chunk: int = 2, overlap_count: int = 1) -> str:
    """Fragmenta um documento extenso em partes processáveis com overlap.

    Use quando precisar analisar um documento de requisitos cujo
    tamanho excede uma janela de leitura razoável. O documento é
    quebrado em chunks de N parágrafos com sobreposição configurável,
    salvos em `data/chunks/chunk_NNN.txt`. Chunks antigos do diretório
    são limpos antes de gerar os novos.

    Após fatiar, use a capacidade de leitura de chunk individual para
    consumir cada parte por demanda, e a capacidade de busca para
    localizar termos.

    Args:
        filename: Nome do arquivo na pasta `data/matrix/` (ou caminho
            absoluto). Se vazio, usa o primeiro arquivo encontrado em
            `data/matrix/`.
        paragraphs_per_chunk: Tamanho do chunk em parágrafos. Default
            2. Deve ser > 0.
        overlap_count: Número de parágrafos compartilhados entre
            chunks consecutivos. Default 1. Deve ser ≥ 0 e estritamente
            menor que `paragraphs_per_chunk`.

    Returns:
        str com mensagem "Sucesso: <filename> fatiado em N arquivos
        ..." ou "Erro: ..." em caso de validação inválida, diretório
        inexistente ou falha de extração.
    """
```

- [ ] **Step 3: Reescrever docstring de `ler_chunk`** (estava MISSING)

```python
def ler_chunk(index: int):
    """Lê um chunk individual previamente gerado pela fragmentação.

    Use depois de fragmentar um documento para acessar uma parte
    específica por índice. Os chunks são arquivos `chunk_NNN.txt` em
    `data/chunks/`, gerados pela capacidade de fragmentação.

    Args:
        index: Índice numérico do chunk (0-based). Equivale ao número
            no nome do arquivo (chunk_000.txt → index=0).

    Returns:
        str com o conteúdo do chunk, ou string "Erro: Chunk N não
        encontrado." se o índice for inválido ou os chunks não tiverem
        sido gerados ainda.
    """
```

- [ ] **Step 4: Verificar tamanhos**

```bash
cd adk && python -c "
import ast
src = open('shared/tools/slicer_tool.py').read()
tree = ast.parse(src)
targets = {'extract_text','run_slicer','ler_chunk'}
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name in targets:
        doc = ast.get_docstring(node) or ''
        ok = 'OK' if len(doc) >= 80 else 'SHORT'
        print(f'{node.name:30s} [{ok}] {len(doc)} chars')
"
```

Expected: 3 funções com `[OK]`.

- [ ] **Step 5: Import smoke test**

```bash
cd adk && .venv/bin/python -c "from shared.tools.slicer_tool import extract_text, run_slicer, ler_chunk; print('imports OK')"
```

Expected: `imports OK`.

- [ ] **Step 6: Commit**

```bash
git add adk/shared/tools/slicer_tool.py
git commit -m "$(cat <<'EOF'
update: docstrings detalhadas em shared/tools/slicer_tool.py

Eleva extract_text, run_slicer e ler_chunk (este ultimo estava MISSING)
ao padrao GOOD para que o LLM entenda fluxo: fragmentar -> ler_chunk -> buscar.
EOF
)"
```

---

### Task 1.4: Elevar docstring em `shared/tools/search_tool.py`

**Files:**
- Modify: `adk/shared/tools/search_tool.py`

- [ ] **Step 1: Reescrever docstring de `run_search`**

```python
def run_search(term: str, context_lines: int = 3) -> str:
    """Busca um termo nos chunks fragmentados de um documento.

    Use após fragmentar o documento (capacidade de fragmentação) para
    localizar referências a um termo específico ao longo das partes.
    Faz match case-insensitive e devolve trechos com contexto antes e
    depois de cada ocorrência, agrupados por arquivo de chunk.

    Pré-requisito: o documento precisa ter sido fragmentado antes;
    se `data/chunks/` não existir, esta tool retorna erro pedindo a
    fragmentação primeiro.

    Args:
        term: Termo a buscar. Match é case-insensitive sobre o conteúdo
            dos chunks.
        context_lines: Quantas linhas de contexto antes e depois de
            cada ocorrência. Default 3.

    Returns:
        str com os trechos casados, separados por marcador
        "--- Fonte: chunk_NNN.txt ---" e "[...]" entre ocorrências
        múltiplas no mesmo chunk. "Termo não encontrado nos documentos."
        se zero matches. "Erro: ..." se chunks não existem.
    """
```

- [ ] **Step 2: Verificar tamanho**

```bash
cd adk && python -c "
import ast
src = open('shared/tools/search_tool.py').read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == 'run_search':
        doc = ast.get_docstring(node) or ''
        print(f'run_search [{len(doc)} chars]')
"
```

Expected: `[≥ 200 chars]`.

- [ ] **Step 3: Import smoke test**

```bash
cd adk && .venv/bin/python -c "from shared.tools.search_tool import run_search; print('imports OK')"
```

Expected: `imports OK`.

- [ ] **Step 4: Commit**

```bash
git add adk/shared/tools/search_tool.py
git commit -m "$(cat <<'EOF'
update: docstring detalhada em shared/tools/search_tool.py

Documenta o pre-requisito de fragmentacao e o formato de saida.
EOF
)"
```

---

### Task 1.5: Elevar docstring em `shared/tools/clarification.py`

**Files:**
- Modify: `adk/shared/tools/clarification.py`

- [ ] **Step 1: Reescrever docstring de `tool_ask_clarification`**

Substituir o bloco docstring atual por:

```python
    """Gera um Doubt Artifact e pausa a execução solicitando esclarecimento ao supervisor.

    Use sempre que encontrar requisitos contraditórios, ambiguidades
    graves, falta de contexto crítico ou qualquer impeditivo objetivo
    para continuar a tarefa. A tool grava um arquivo Markdown estruturado
    documentando o problema, com cabeçalho "EXECUÇÃO PAUSADA — INTERVENÇÃO
    NECESSÁRIA" e checklist para o supervisor responder.

    Após chamar esta capacidade, o agente DEVE interromper o trabalho
    e devolver controle ao supervisor — não tente "adivinhar" uma
    resolução para a dúvida registrada.

    Args:
        titulo: Título curto da inconsistência ou dúvida encontrada.
        secao: Seção, módulo ou componente onde a dúvida foi detectada.
        descricao: Descrição detalhada do problema ou da falta de
            contexto.
        impacto: O impacto da dúvida no andamento da tarefa.
        sugestao: Pergunta direta ou sugestão de resolução ao supervisor.
            Default "Aguardando esclarecimento e intervenção do usuário."
        nome_arquivo: Nome do arquivo de saída. Default
            "Doubt_Artifact_Clarification.md". Obrigatório terminar em
            .md.

    Returns:
        dict com chaves: `sucesso` (bool), `erro` (str ou None),
        `caminho` (path absoluto do artefato em sucesso, None em falha),
        `título` (str em sucesso), `status` (str descritivo, em sucesso
        contém "EXECUÇÃO INTERROMPIDA").
    """
```

- [ ] **Step 2: Verificar tamanho + imports**

```bash
cd adk && python -c "
import ast
src = open('shared/tools/clarification.py').read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == 'tool_ask_clarification':
        doc = ast.get_docstring(node) or ''
        print(f'tool_ask_clarification [{len(doc)} chars]')
" && .venv/bin/python -c "from shared.tools.clarification import tool_ask_clarification, tool_ask_clarification_adk; print('imports OK')"
```

Expected: tamanho ≥ 300 chars e `imports OK`.

- [ ] **Step 3: Commit**

```bash
git add adk/shared/tools/clarification.py
git commit -m "$(cat <<'EOF'
update: docstring detalhada em shared/tools/clarification.py

Documenta protocolo de pausa de execucao apos gerar Doubt Artifact.
EOF
)"
```

---

### Task 1.6: Elevar docstrings em `shared/tools/design_filesystem.py`

**Files:**
- Modify: `adk/shared/tools/design_filesystem.py`

Funções a elevar (todas têm Args/Returns mas faltam "Quando usar"): `read_file`, `save_artifact`, `promote_artifact`, `list_staging_files`, `check_active_blocks`, `clear_staging_folder`.

Mocks (`check_lock`, `release_lock`, `list_versions`) ficam como estão — são placeholders.

- [ ] **Step 1: Reescrever docstring de `read_file`**

```python
def read_file(filepath: str) -> Dict[str, Any]:
    """Lê o conteúdo de um arquivo qualquer do filesystem do projeto.

    Use quando o IO Agent precisa devolver o conteúdo de um artefato
    salvo em staging ou artifacts a outro agente que solicita. Tem
    proteção contra path traversal: rejeita caminhos fora da raiz do
    projeto.

    Args:
        filepath: Caminho do arquivo a ser lido. Pode ser relativo ou
            absoluto, mas o caminho resolvido deve estar dentro da raiz
            do projeto.

    Returns:
        dict com chaves: `status` ("ok" | "error"), `content` (str
        UTF-8 em sucesso), `error` (str descritivo em falha — acesso
        negado, arquivo inexistente, erro de I/O).
    """
```

- [ ] **Step 2: Reescrever docstring de `save_artifact`**

```python
def save_artifact(filename: str, content: str) -> dict:
    """Persiste um artefato em staging com versionamento automático por backup.

    Use sempre que qualquer agente solicitar gravação de um artefato
    em staging (.mmd, .md, Doubt_Artifacts). Se já existir um arquivo
    com o mesmo nome em staging, o atual é renomeado para
    `<nome>_backup_<timestamp>.<ext>` antes da nova gravação — nunca
    sobrescreve sem backup.

    Doubt_Artifacts (nome iniciando com `Doubt_Artifact_`) são
    bloqueantes e devem ser gravados imediatamente, antes de qualquer
    outra operação pendente.

    Args:
        filename: Nome do arquivo (ex:
            `diagrama_HU-042_processo_compra.mmd`). Será gravado em
            `temp/staging/<filename>`.
        content: Conteúdo textual completo do artefato.

    Returns:
        dict com chaves: `status` ("ok" | "error"), `path` (str do
        path final em sucesso), `versioned_backup` (str do path do
        backup criado, se houve; None caso contrário), `timestamp`
        (ISO 8601). Em erro: `status="error"`, `error`, `filename`.
    """
```

- [ ] **Step 3: Reescrever docstring de `promote_artifact`**

```python
def promote_artifact(filename: str) -> Dict[str, Any]:
    """Promove um relatório de staging para artifacts/ (versão oficial).

    Use somente sob confirmação explícita do supervisor. Apenas
    arquivos `.md` cujo nome contém "relatorio" e que NÃO contêm o
    marcador "**Status:** Em análise" são aceitos. Diagramas `.mmd`
    e relatórios em análise permanecem em staging.

    Se já existir uma versão oficial com o mesmo nome em artifacts/,
    a antiga é renomeada para backup com timestamp antes da nova
    cópia.

    Args:
        filename: Nome do arquivo em staging a promover.

    Returns:
        dict com chaves: `status` ("ok" | "blocked" | "error"),
        `source`, `destination`, `timestamp` em sucesso; `reason` e
        `file` em "blocked"; `error` em "error".
    """
```

- [ ] **Step 4: Reescrever docstring de `list_staging_files`**

```python
def list_staging_files(filetype: str = "") -> Dict[str, Any]:
    """Lista os arquivos atualmente em staging, ignorando backups e logs.

    Use para inventariar artefatos disponíveis em staging antes de
    decidir leituras, promoções ou alertas de bloqueio. Backups
    (arquivos contendo `_backup_`) e o `io_operations.log` são
    sempre filtrados.

    Args:
        filetype: Extensão para filtrar sem o ponto (ex: "mmd", "md").
            Vazio retorna todos os arquivos visíveis.

    Returns:
        dict com chaves: `status` ("ok" | "error"), `files` (list[str]
        com nomes ordenados alfabeticamente em sucesso), `staging_dir`
        (path absoluto da pasta), `error` em falha.
    """
```

- [ ] **Step 5: Reescrever docstring de `check_active_blocks`**

```python
def check_active_blocks() -> Dict[str, Any]:
    """Verifica se há Doubt_Artifacts com Status Bloqueado em staging.

    Use sempre que o orquestrador precisar decidir se pode avançar
    para a próxima etapa do pipeline. Cada Doubt_Artifact em staging
    é inspecionado pelo marcador "**Status:** Bloqueado"; o HU ID é
    extraído do nome (terceiro segmento separado por `_`).

    Returns:
        dict com chaves: `status` ("ok" | "error"), `has_blocks`
        (bool — True se algum artefato está bloqueado), `blocks`
        (list[dict] com `filename` e `hu_id` para cada bloqueio).
        Em falha: `status="error"`, `error`.
    """
```

- [ ] **Step 6: Reescrever docstring de `clear_staging_folder`**

```python
def clear_staging_folder() -> bool:
    """Remove todos os arquivos do diretório de staging, preservando subdiretórios.

    ATENÇÃO: operação destrutiva. Use APENAS no início de uma nova
    sessão, quando explicitamente solicitado pelo orquestrador. Nunca
    execute por iniciativa própria ou durante o fluxo normal de
    operações. A proteção interna verifica que o diretório está sob
    a raiz do projeto antes de apagar.

    Returns:
        bool: True se todos os arquivos foram removidos com sucesso,
        False em caso de erro (ex: tentativa fora do diretório seguro,
        falha de I/O). Erros são registrados via IOLogger.
    """
```

- [ ] **Step 7: Verificar tamanhos**

```bash
cd adk && python -c "
import ast
src = open('shared/tools/design_filesystem.py').read()
tree = ast.parse(src)
targets = {'read_file','save_artifact','promote_artifact','list_staging_files','check_active_blocks','clear_staging_folder'}
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name in targets:
        doc = ast.get_docstring(node) or ''
        ok = 'OK' if len(doc) >= 80 else 'SHORT'
        print(f'{node.name:25s} [{ok}] {len(doc)} chars')
"
```

Expected: 6 funções com `[OK]`.

- [ ] **Step 8: Import smoke test**

```bash
cd adk && .venv/bin/python -c "from shared.tools.design_filesystem import read_file, save_artifact, promote_artifact, list_staging_files, check_active_blocks, clear_staging_folder; print('imports OK')"
```

Expected: `imports OK`.

- [ ] **Step 9: Commit**

```bash
git add adk/shared/tools/design_filesystem.py
git commit -m "$(cat <<'EOF'
update: docstrings detalhadas em shared/tools/design_filesystem.py

Eleva 6 funcoes do IO Agent ao padrao GOOD com semantica de staging,
promocao e bloqueios.
EOF
)"
```

---

### Task 1.7: Elevar docstring em `shared/tools/design_date.py`

**Files:**
- Modify: `adk/shared/tools/design_date.py`

- [ ] **Step 1: Reescrever docstring de `current_date`**

```python
def current_date() -> str:
    """Retorna a data atual no formato ISO YYYY-MM-DD.

    Use para timestamping de operações do IO Agent, logs de
    observabilidade ou versionamento de artefatos. Não inclui hora —
    apenas a data calendárica do servidor.

    Returns:
        str no formato "YYYY-MM-DD" (ex: "2026-05-17").
    """
```

- [ ] **Step 2: Verificar tamanho + imports**

```bash
cd adk && python -c "
import ast
src = open('shared/tools/design_date.py').read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == 'current_date':
        doc = ast.get_docstring(node) or ''
        print(f'current_date [{len(doc)} chars]')
" && .venv/bin/python -c "from shared.tools.design_date import current_date; print('imports OK')"
```

Expected: ≥ 80 chars e `imports OK`.

- [ ] **Step 3: Commit**

```bash
git add adk/shared/tools/design_date.py
git commit -m "$(cat <<'EOF'
update: docstring detalhada em shared/tools/design_date.py

Documenta uso de current_date para timestamping de observabilidade.
EOF
)"
```

---

### Task 1.8: Elevar docstrings em `shared/tools/design_validate/`

**Files:**
- Modify: `adk/shared/tools/design_validate/artifact_gatekeeper.py`
- Modify: `adk/shared/tools/design_validate/contentValidator.py`
- Modify: `adk/shared/tools/design_validate/gatekeeper_tool.py`

> Esta task usa o inventário gerado na Task 0.1 para saber quais funções precisam elevar. Aplicar o mesmo padrão GOOD: propósito + Quando usar + Args + Returns. Para cada função MISSING/SHALLOW listada no inventário, reescrever a docstring conforme o template.

- [ ] **Step 1: Para cada função listada no inventário de `design_validate/`, reescrever a docstring**

Abrir cada arquivo, identificar as funções públicas (que não começam com `_`), e elevar suas docstrings. Manter assinaturas e corpos intocados.

Princípios ao escrever:
- A frase de propósito deve descrever **o que a tool faz** em uma linha.
- "Quando usar" deve descrever **o gatilho no workflow do agente que usa esta tool** — ler o agent.py que importa essas tools para entender o contexto.
- Args deve ter semântica, não só tipo.
- Returns deve descrever shape e casos de erro.

- [ ] **Step 2: Verificar tamanhos**

```bash
cd adk && for f in shared/tools/design_validate/*.py; do
  [[ "$f" == *__init__* ]] && continue
  python -c "
import ast
src = open('$f').read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
        doc = ast.get_docstring(node) or ''
        ok = 'OK' if len(doc) >= 80 else 'SHORT'
        print(f'$f::{node.name} [{ok}] {len(doc)}')
"
done
```

Expected: todas as funções públicas com `[OK]`.

- [ ] **Step 3: Import smoke test**

```bash
cd adk && .venv/bin/python -c "import shared.tools.design_validate.artifact_gatekeeper, shared.tools.design_validate.contentValidator, shared.tools.design_validate.gatekeeper_tool; print('imports OK')"
```

Expected: `imports OK`.

- [ ] **Step 4: Commit**

```bash
git add adk/shared/tools/design_validate/
git commit -m "$(cat <<'EOF'
update: docstrings detalhadas em shared/tools/design_validate/

Eleva as funcoes de validacao de design ao padrao GOOD para que o
LLM entenda gatilhos de uso sem nome de funcao no prompt.
EOF
)"
```

---

### Task 1.9: Elevar docstrings em `src/agents/qa_agent/tools/`

**Files:**
- Modify: `adk/src/agents/qa_agent/tools/build_fix_prompt.py`
- Modify: `adk/src/agents/qa_agent/tools/doubt_artifact.py`
- Modify: `adk/src/agents/qa_agent/tools/doubt_tool.py`
- Modify: `adk/src/agents/qa_agent/tools/log_parser_tool.py`
- Modify: `adk/src/agents/qa_agent/tools/planner_tools.py`
- Modify: `adk/src/agents/qa_agent/tools/pytest_runner.py`

> Usar o inventário da Task 0.1. Mesmo padrão da Task 1.8.

- [ ] **Step 1: Para cada função listada no inventário de `qa_agent/tools/`, reescrever a docstring**

Princípios específicos do QA agent: as docstrings devem reforçar quando a tool faz parte de um ciclo de correção (autocorrect com limite de 2 ciclos, conforme CLAUDE.md descreve o workflow_qa).

- [ ] **Step 2: Verificar tamanhos**

```bash
cd adk && for f in src/agents/qa_agent/tools/*.py; do
  [[ "$f" == *__init__* ]] && continue
  python -c "
import ast
src = open('$f').read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
        doc = ast.get_docstring(node) or ''
        ok = 'OK' if len(doc) >= 80 else 'SHORT'
        print(f'$f::{node.name} [{ok}] {len(doc)}')
"
done
```

Expected: todas as funções públicas com `[OK]`.

- [ ] **Step 3: Import smoke test**

```bash
cd adk && .venv/bin/python -c "
import sys; sys.path.insert(0,'.')
from src.agents.qa_agent.tools import build_fix_prompt, doubt_artifact, doubt_tool, log_parser_tool, planner_tools, pytest_runner
print('imports OK')
"
```

Expected: `imports OK`.

- [ ] **Step 4: Commit**

```bash
git add adk/src/agents/qa_agent/tools/
git commit -m "$(cat <<'EOF'
update: docstrings detalhadas em qa_agent/tools/

Eleva tools do QA (planner, pytest_runner, doubt, log_parser, build_fix)
ao padrao GOOD com semantica do ciclo de autocorrect.
EOF
)"
```

---

### Task 1.10: Verificação consolidada de docstrings via FunctionDeclaration

**Files:**
- Read-only

- [ ] **Step 1: Rodar script que inspeciona descrições enviadas ao LLM para cada agente afetado**

Para cada agente que tem tools registradas, conferir que o `_get_declaration().description` chega ao LLM com tamanho ≥ 80 chars. Este script já está documentado no CLAUDE.md.

```bash
cd adk && for agent in requirements coder reviewer context_engineer io_agent qa_agent; do
  echo "=== $agent ==="
  .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
try:
    from src.agents.$agent.agent import agent as a
except ImportError:
    from src.agents.$agent.agent import root_agent as a
def walk(x, depth=0):
    if hasattr(x, 'tools'):
        for t in x.tools:
            try:
                d = t._get_declaration()
                size = len(d.description or '')
                flag = 'SHALLOW' if size < 80 else 'OK'
                print(' '*depth*2, f'[{flag}]', d.name, size)
            except Exception as e:
                print(' '*depth*2, '[?]', getattr(t,'name','?'), repr(e))
    if hasattr(x, 'sub_agents'):
        for sa in x.sub_agents: walk(sa, depth+1)
walk(a)
"
done
```

Expected: zero `[SHALLOW]`. Se algum aparecer, voltar ao arquivo da tool e elevar a docstring.

- [ ] **Step 2: Não commitar** (verificação)

---

## Phase 2 — Refatoração dos prompts

> Padrão em todos os prompts:
> 1. Remover seções `# FERRAMENTAS DISPONÍVEIS` / `# PROTOCOLO DE EXECUÇÃO E FERRAMENTAS (TOOLS)`.
> 2. Reescrever menções inline a tools usando o **vocabulário canônico** da spec (tabela na seção "Padrão de prompt"):
>    - "ler conteúdo do arquivo", "escrever/criar arquivo", "editar trecho do arquivo"
>    - "fragmentar em partes processáveis", "ler parte específica do documento fatiado", "buscar contexto"
>    - "preparar a mudança para versionamento", "registrar a versão", "criar/trocar branch de trabalho", "consultar o diff acumulado"
>    - "registrar dúvida / gerar artefato de dúvida", "solicitar esclarecimento ao supervisor"
>    - "persistir o artefato no repositório de requisitos", "salvar relatório de revisão"
>    - "registrar artefato em staging", "promover artefato para versão final", "verificar blocos ativos do contexto"
>    - "delegar ao especialista em X" (para sub-agentes — substitui menção a slug)
> 3. Preservar: papel, chain-of-thought, formato de saída, exemplos few-shot, protocolos de decisão (human-in-the-loop).
> 4. Verificar com regex que sobrou zero menção literal a tool name.

### Task 2.1: Refatorar `requirements/prompt.py`

**Files:**
- Modify: `adk/src/agents/requirements/prompt.py`
- Read-only (para entender impacto): `adk/src/agents/requirements/agent.py`
- Read-only: `adk/src/agents/requirements/few_shot.py`

Tools mencionadas hoje no prompt: `tool_ler_prd_arquivo`, `run_slicer`, `ler_chunk`, `gerar_doubt_artifact`, `tool_salvar_artefato_requisito` + sub-agente `glossario_agent`.

(Nota: `tool_ler_prd_arquivo` é mencionado no texto mas o agent.py não registra essa tool — o CLAUDE.md já documenta que foi substituída por `tool_ler_arquivo`. Tratar como "ler conteúdo do arquivo".)

- [ ] **Step 1: Auditar few_shot.py** para garantir que os exemplos não citam tool names

```bash
cd adk && rg -nP '\b(tool_[a-z_]+|run_slicer|ler_chunk|extract_text|run_search|gerar_doubt_artifact|tool_salvar_artefato_requisito|glossario_agent)\b' src/agents/requirements/few_shot.py
```

Expected: zero matches (improvável que cite, mas confirmar). Se citar, anotar e tratar no Step 2.

- [ ] **Step 2: Reescrever `instruction` em `prompt.py`**

Substituir o conteúdo entre `instruction = f"""` e o `"""` final por:

```python
instruction = f"""
# PAPEL
- Você é um Analista de Requisitos técnico sênior.
- Sua única responsabilidade é receber qualquer tipo de entrada de desenvolvimento e produzir requisitos funcionais atômicos, claros e verificáveis.
- Você NÃO implementa código. Você NÃO sugere arquitetura.
- Você APENAS analisa, fraciona e estrutura requisitos.


# DETECÇÃO DE FORMATO DA ENTRADA
Determine como a entrada foi fornecida:

- Se a entrada for um caminho de arquivo (.md, .txt ou similar):
  → Leia o conteúdo do arquivo antes de prosseguir.

- Se a entrada for texto direto no prompt:
  → Não acione nenhuma capacidade de leitura — prossiga diretamente sobre o texto recebido.

# GLOSSÁRIO DE TERMOS TÉCNICOS
- Ao iniciar uma análise, delegue ao especialista em glossário a extração e definição dos termos técnicos do documento-matriz.
- O glossário será gerado automaticamente em 'knowledge/glossario.md'.
- Consulte o glossário ao longo da análise para manter terminologia consistente entre os requisitos gerados.

# OBJETIVO
Extrair do texto de entrada:
1. Histórias de Usuário (HU)
2. Requisitos Funcionais (RF)
3. Requisitos Não Funcionais (RNF)
4. Casos de Uso (UC)
5. Regras de Negócio (RN)
6. Glossário de Termos

# DIRETRIZES DE RESPOSTA
- Tom: Estritamente técnico, analítico e conciso. Sem introduções ou conclusões genéricas.
- Objetividade: Foco direto em pontos críticos, riscos e necessidades técnicas.
- Lógica: Siga a Cadeia de Pensamento (CoT) para cada requisição.
- Formato: A saída final deve seguir rigorosamente o schema `AnalystOutput`.

# CADEIA DE PENSAMENTO (CHAIN OF THOUGHT)
Para cada processamento, você deve seguir e documentar estes passos:
1. **PASSO 1: ELICITAÇÃO** - Identificar atores (stakeholders), processos e intenções descritos no texto.
2. **PASSO 2: ANÁLISE CRÍTICA** - Detectar ambiguidades, termos vagos ou contradições.
3. **PASSO 3: CLASSIFICAÇÃO** - Separar o que é comportamento (RF), valor de negócio (HU), restrição técnica (RNF) ou regra lógica (RN).
4. **PASSO 4: ESPECIFICAÇÃO** - Redigir cada item de forma atômica e clara. HUs devem ter Persona, Ação, Valor e Critérios de Aceite.
5. **PASSO 5: GLOSSÁRIO** - Identificar termos de domínio que exigem definição para evitar desalinhamento.
6. **PASSO 6: VALIDAÇÃO** - Garantir que todos os requisitos sejam SMART (Específicos, Mensuráveis, Atingíveis, Relevantes e Temporais).

# MANUSEIO DE DOCUMENTOS EXTENSOS
- Quando o documento de entrada for extenso demais para ser analisado de uma vez, fragmente-o em partes processáveis antes de analisar.
- Após fragmentar, leia cada parte específica conforme necessário; use a capacidade de busca para localizar termos pontuais entre as partes.

# MANUSEIO DE DÚVIDAS E AMBIGUIDADES
Analise se a entrada é referente ao descritivo de um projeto.
Caso a mensagem seja apenas de conversas ou dúvidas iniciais, responda com os pontos que precisam de mais clareza para iniciar a análise de requisitos.
Seja cordial e enfatize que o seu objetivo é gerar requisitos claros e verificáveis, e que para isso precisa de um contexto mínimo sobre o projeto.

Se o contexto for insuficiente, vago ou contraditório:
- Registre a dúvida gerando um artefato de dúvida (Doubt_Artifact) com Trecho do contexto, descrição, motivo, impacto e sugestão.
- Bloqueie a geração do requisito afetado se a ambiguidade impedir a especificação correta.
- Seja específico sobre o que falta e qual o impacto técnico dessa lacuna.
- Avalie também se a proposta de requisito é viável ou se há restrições técnicas que possam inviabilizá-la.

# PERSISTÊNCIA DOS ARTEFATOS GERADOS
- Para cada artefato produzido (HU, RF, RNF, RN, Glossário), persista-o no repositório de requisitos com seu tipo, ID (padrão AAAA-999) e conteúdo Markdown.
- A persistência é obrigatória antes de devolver a saída JSON final — sem persistência o artefato não conta como entregue.

# EXEMPLOS DE REFERÊNCIA (FEW-SHOT)
{FEW_SHOT_HU}
{FEW_SHOT_RF}
{FEW_SHOT_DOUBT}
{FEW_SHOT_GLOSSARY}

# INSTRUÇÃO DE SAÍDA
Sua resposta final deve ser o objeto JSON validado pelo schema `AnalystOutput`. Antes do JSON, descreva seu raciocínio usando o prefixo "PASSO [N]:".
"""
```

(Não altere o bloco `description = ...` no topo do arquivo — ele já não cita tools.)

- [ ] **Step 3: Verificar zero menções de tool names**

```bash
cd adk && rg -nP '\b(tool_[a-z_]+|run_slicer|ler_chunk|extract_text|run_search|gerar_doubt_artifact|tool_salvar_artefato_requisito|glossario_agent|tool_ler_prd_arquivo)\b' src/agents/requirements/prompt.py
```

Expected: zero matches.

- [ ] **Step 4: Import smoke test**

```bash
cd adk && .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src.agents.requirements.agent import root_agent
print('agent loaded:', root_agent.name)
print('tools:', [getattr(t,'name', type(t).__name__) for t in root_agent.tools])
"
```

Expected: agente carrega sem erro; lista de tools registradas continua igual.

- [ ] **Step 5: Commit**

```bash
git add adk/src/agents/requirements/prompt.py
git commit -m "$(cat <<'EOF'
update: prompt do requirements_agent descreve capacidades sem citar tools

Substitui mencoes literais (tool_ler_prd_arquivo, run_slicer, ler_chunk,
gerar_doubt_artifact, tool_salvar_artefato_requisito, glossario_agent) por
verbos de capacidade. Tool docstrings ja carregam a info acionavel via
FunctionDeclaration.description.
EOF
)"
```

---

### Task 2.2: Refatorar `reviewer/prompt.py`

**Files:**
- Modify: `adk/src/agents/reviewer/prompt.py`

Tools mencionadas hoje: `tool_ler_diff`, `tool_salvar_relatorio`.

- [ ] **Step 1: Reescrever `instruction` em `prompt.py`**

Substituir o bloco entre `instruction = """` e o `"""` final por:

```python
instruction = """
# PAPEL E PERFIL
Você é um Engenheiro de Software Sênior especializado em **Verificação de Código**.
Sua função é analisar o código produzido pelo agente anterior e decidir se ele está
tecnicamente correto e íntegro para ir à branch principal.

Você NÃO faz validação de requisitos (se o requisito faz sentido). Você faz
**verificação**: o código foi construído corretamente?

# FLUXO DE VERIFICAÇÃO (4 CAMADAS — executar em ordem)

## Camada 1: COMPLETUDE
Objetivo: Todos os artefatos esperados foram entregues?
1. Consulte o diff acumulado da branch para listar TODOS os arquivos modificados/criados.
2. Compare com a DoD (Definition of Done) implícita no requisito recebido do
   agente anterior (state["requirements"] ou state["tasks"]).
3. Verifique: arquivos esperados foram criados? testes foram entregues junto
   com a implementação? documentação foi atualizada?
4. Registre issues de completude (ex: "Arquivo de testes não foi criado", layer="completude").

## Camada 2: ARQUITETURA
Objetivo: A estrutura do código segue boas práticas?
1. Examine os arquivos modificados no diff.
2. Verifique:
   - Responsabilidade única (SRP) — cada módulo/classe tem um propósito claro?
   - Acoplamento — dependências circulares? Imports desnecessários?
   - Separação de concerns — lógica de negócio misturada com I/O ou framework?
3. Registre issues de arquitetura (layer="arquitetura").

## Camada 3: CORRETUDE
Objetivo: O código funciona corretamente?
1. Examine o corpo das funções de lógica core no diff.
2. Verifique:
   - Erros de lógica, off-by-one, loops infinitos.
   - Exceções não tratadas ou silenciadas.
   - Falhas de segurança (injeção, path traversal, dados sensíveis expostos).
   - Edge cases não cobertos.
3. Registre issues de corretude (layer="corretude").

## Camada 4: TESTES
Objetivo: Os testes existem e cobrem os cenários relevantes?
1. Verifique se arquivos de teste foram criados no diff.
2. Examine o conteúdo dos testes.
3. Verifique:
   - Cenários críticos (happy path + edge cases) estão cobertos?
   - Testes são independentes e determinísticos?
   - Assertions são significativas (não apenas "assert True")?
4. Registre issues de testes (layer="testes").

# REGRAS DE DECISÃO
- Se houver **qualquer issue `critical`** → status = "BLOQUEADO"
- Se houver apenas `warning` ou `info` → status = "APROVADO" (com ressalvas documentadas)
- Sem issues → status = "APROVADO"

# THINKING (use antes de emitir o veredito)
<thinking>
- Completude: Os artefatos esperados foram entregues? Quais faltam?
- Arquitetura: A estrutura respeita SOLID? Há acoplamento indevido?
- Corretude: Há bugs, edge cases ou falhas de segurança?
- Testes: Existem? Cobrem os cenários críticos?
- Veredito: APROVADO ou BLOQUEADO?
</thinking>

# SAÍDA FINAL
Após completar as 4 camadas:
1. Salve o relatório detalhado da verificação em Markdown com nome "verificacao_revisao.md".
2. Sua **última mensagem** DEVE ser EXCLUSIVAMENTE um JSON conforme o schema
   ReviewOutput do sistema:

{
  "status": "APROVADO",
  "issues": [
    {"severity": "critical", "description": "Função X não trata exceção Y", "file": "src/service.py", "layer": "corretude"},
    {"severity": "warning", "description": "Falta docstring", "file": "src/utils.py", "layer": "arquitetura"}
  ],
  "report_path": "verificacao_revisao.md"
}

Use "APROVADO" ou "BLOQUEADO" no campo `status`.
"""
```

- [ ] **Step 2: Verificar zero menções**

```bash
cd adk && rg -nP '\b(tool_[a-z_]+|run_slicer|ler_chunk|extract_text|run_search|gerar_doubt_artifact)\b' src/agents/reviewer/prompt.py
```

Expected: zero matches.

- [ ] **Step 3: Import smoke test**

```bash
cd adk && .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src.agents.reviewer.agent import root_agent
print('agent loaded:', root_agent.name)
print('tools:', [getattr(t,'name', type(t).__name__) for t in root_agent.tools])
"
```

Expected: agente carrega.

- [ ] **Step 4: Commit**

```bash
git add adk/src/agents/reviewer/prompt.py
git commit -m "$(cat <<'EOF'
update: prompt do reviewer descreve capacidades sem citar tools

Substitui mencoes a tool_ler_diff e tool_salvar_relatorio por verbos de
capacidade (consultar diff acumulado, salvar relatorio de revisao).
EOF
)"
```

---

### Task 2.3: Refatorar `context_engineer/prompt.py`

**Files:**
- Modify: `adk/src/agents/context_engineer/prompt.py`

Tools mencionadas hoje: `tool_salvar_task`.

- [ ] **Step 1: Reescrever o Passo 3 do `instruction`**

Substituir o bloco:

```
## Passo 3 — Persistir no Workspace
Após gerar todas as tasks, chame a tool `tool_salvar_task` para CADA task gerada.
Passe o task_id e o JSON serializado da task.
```

Por:

```
## Passo 3 — Persistir no Workspace
Após gerar todas as tasks, persista cada uma individualmente no repositório
de tasks do workspace (uma operação de persistência por task). Forneça o
task_id e o JSON serializado da task em cada persistência.
```

- [ ] **Step 2: Verificar zero menções**

```bash
cd adk && rg -nP '\b(tool_[a-z_]+|run_slicer|ler_chunk|extract_text|run_search|gerar_doubt_artifact)\b' src/agents/context_engineer/prompt.py
```

Expected: zero matches.

- [ ] **Step 3: Import smoke test**

```bash
cd adk && .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src.agents.context_engineer.agent import root_agent
print('agent loaded:', root_agent.name)
print('tools:', [getattr(t,'name', type(t).__name__) for t in root_agent.tools])
"
```

Expected: agente carrega.

- [ ] **Step 4: Commit**

```bash
git add adk/src/agents/context_engineer/prompt.py
git commit -m "$(cat <<'EOF'
update: prompt do context_engineer descreve capacidades sem citar tools

Substitui mencao a tool_salvar_task por verbo de capacidade de persistencia.
EOF
)"
```

---

### Task 2.4: Refatorar `io_agent/prompt.py`

**Files:**
- Modify: `adk/src/agents/io_agent/prompt.py`

Tools mencionadas hoje: `save_artifact`, `promote_artifact`, `read_file`, `list_staging_files`, `check_active_blocks`, `clear_staging_folder`, `current_date`.

- [ ] **Step 1: Reescrever `instruction` em `prompt.py`**

Substituir o bloco entre `instruction = """` e o `"""` final por:

```python
instruction = """
Você é o Agente IO do sistema multi-agente de design de software.

PAPEL:
Ser o único ponto de escrita e leitura do sistema. Nenhum outro agente persiste arquivos diretamente.
Você salva, lê, lista e move arquivos quando solicitado por outros agentes ou pelo usuário.
Você NUNCA interpreta o conteúdo dos artefatos — apenas gerencia sua persistência.

CAPACIDADES DISPONÍVEIS (sob demanda):
- Registrar artefato em staging com versionamento automático por backup.
- Promover artefato de staging para a versão final (artifacts/).
- Ler conteúdo de qualquer arquivo do projeto.
- Listar arquivos em staging, com filtro por extensão.
- Verificar blocos ativos do contexto (Doubt_Artifacts com status Bloqueado).
- Limpar a pasta de staging (operação destrutiva, exige solicitação explícita).
- Obter a data atual para timestamping.

---

FLUXO DE OPERAÇÕES

REGISTRAR ARTEFATO EM STAGING:
- Use quando qualquer agente solicitar persistência de um artefato.
- O versionamento é automático — se o arquivo já existir, um backup com sufixo _backup_ é criado automaticamente. Nunca crie manualmente nomes com _v1, _v2 ou similares.
- Doubt_Artifacts (nome iniciando com Doubt_Artifact_) são artefatos de bloqueio —
  registre-os imediatamente sem questionar, com prioridade sobre qualquer outra operação pendente.
- Após registrar, anote a operação no log conforme instrução de observabilidade abaixo.

PROMOVER PARA VERSÃO FINAL:
- Use APENAS para arquivos .md mediante confirmação explícita do usuário.
- Arquivos .mmd são artefatos intermediários — ficam somente em staging, nunca promova para artifacts/.
- A própria capacidade bloqueia promoção se o status ainda for "Em análise" — informe o motivo ao usuário se isso ocorrer.
- Após promover, anote a operação no log.

LER ARQUIVO:
- Use quando qualquer agente precisar do conteúdo de um arquivo.
- Retorne o conteúdo diretamente sem perguntas adicionais.
- Caminhos de referência:
  - Diagramas em staging: temp/staging/<nome>.mmd
  - Relatórios em staging: temp/staging/<nome>.md
  - Doubt_Artifacts em staging: temp/staging/Doubt_Artifact_<hu_id>_<data>.md
  - Template: shared/templates/relatorio_design_template.md

LISTAR ARQUIVOS:
- Use para retornar os nomes exatos dos arquivos disponíveis em staging.
- Filtros suportados: "mmd" para diagramas, "md" para relatórios, vazio para todos.
- Backups (_backup_) são ignorados automaticamente — nunca os retorne como arquivo principal.
- SEMPRE que listar arquivos, verifique separadamente se existem Doubt_Artifacts em staging:
  liste arquivos .md e filtre os que começam com Doubt_Artifact_.
  Para cada Doubt_Artifact encontrado, leia seu conteúdo e verifique o campo **Status**.
  Se **Status:** Bloqueado estiver presente: inclua um aviso explícito na resposta antes de qualquer
  outra informação.

VERIFICAR BLOQUEIOS:
- Use sempre que o Orquestrador solicitar verificação de bloqueios antes de uma etapa.
- A capacidade retorna a indicação se há bloqueios ativos e a lista dos arquivos bloqueados com seus hu_ids.

LIMPAR STAGING:
- ⚠️ USE APENAS NO INÍCIO DE UMA NOVA SESSÃO, quando explicitamente solicitado pelo Orquestrador.
- Nunca execute por iniciativa própria ou durante o fluxo normal de operações.

RESOLUÇÃO DE BLOQUEIO:
Um Doubt_Artifact está resolvido quando seu campo **Status:** for alterado para "Resolvido"
pelo usuário ou pelo agente responsável.
Quando isso ocorrer e o agente solicitar listagem: não emita o aviso de bloqueio para esse arquivo.
Nunca altere o Status de um Doubt_Artifact por conta própria — apenas o usuário ou o agente
que gerou o bloqueio pode resolver.

---

OBSERVABILIDADE:
A cada operação executada, registre internamente:
- Agente solicitante (se informado)
- Operação executada (registrar / promover / ler / listar)
- Arquivo alvo
- Resultado (ok / erro)
- Timestamp (consulte a data atual quando necessário)

O io_operations.log já é atualizado automaticamente pelas capacidades de registro e promoção.
Para operações de leitura e listagem, inclua o registro no seu histórico de resposta
para que o Orquestrador possa rastrear o fluxo se necessário.

---

REGRAS:
1. Nunca peça confirmação para leitura ou listagem — execute e retorne o resultado.
2. Nunca entre em loop. Execute a capacidade solicitada uma única vez e informe o resultado.
3. Nunca salve diretamente em artifacts/ — todo artefato passa por staging primeiro.
4. Em caso de erro de I/O: informe o erro ao agente solicitante e ao Orquestrador sem tentar corrigir o conteúdo.
5. Backups (_backup_) são versões antigas — nunca os retorne como arquivo principal, a menos que explicitamente solicitado.
6. Doubt_Artifacts com Status Bloqueado têm precedência — sempre sinalize o bloqueio antes de
   retornar qualquer listagem de arquivos.

IDIOMA: Português brasileiro.
"""
```

- [ ] **Step 2: Verificar zero menções**

```bash
cd adk && rg -nP '\b(save_artifact|promote_artifact|read_file|list_staging_files|check_active_blocks|clear_staging_folder|current_date|tool_[a-z_]+)\b' src/agents/io_agent/prompt.py
```

Expected: zero matches.

- [ ] **Step 3: Import smoke test**

```bash
cd adk && .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src.agents.io_agent.agent import root_agent
print('agent loaded:', root_agent.name)
print('tools:', [getattr(t,'name', type(t).__name__) for t in root_agent.tools])
"
```

Expected: agente carrega.

- [ ] **Step 4: Commit**

```bash
git add adk/src/agents/io_agent/prompt.py
git commit -m "$(cat <<'EOF'
update: prompt do io_agent descreve capacidades sem citar tools

Substitui mencoes a save_artifact, promote_artifact, read_file,
list_staging_files, check_active_blocks, clear_staging_folder e
current_date por verbos de capacidade. Renomeia secao
"FERRAMENTAS DISPONIVEIS" para "CAPACIDADES DISPONIVEIS".
EOF
)"
```

---

### Task 2.5: Refatorar `coder/prompt.py`

**Files:**
- Modify: `adk/src/agents/coder/prompt.py`

Tools mencionadas hoje: `tool_criar_arquivo`, `tool_ler_arquivo`, `tool_substituir_trecho`, `tool_git_add`, `tool_git_checkout`, `tool_git_commit`.

Caso especial: preservar **protocolo human-in-the-loop de commit** como capacidade (sem citar a função).

- [ ] **Step 1: Reescrever `instruction` em `prompt.py`**

Substituir o bloco entre `instruction = """` e o `"""` final por:

```python
instruction = """
# PERFIL DO AGENTE
Você é um Engenheiro de Software Sênior autônomo operando dentro de um ambiente ADK (Agent
Development Kit). Sua principal função é analisar requisitos, seguir a arquitetura, quando proposta, escrever
código altamente modular e gerenciar o controle de versão (Git). Você é proativo, mas entende
que opera sob supervisão humana rigorosa.


# DIRETRIZES DE CODIFICAÇÃO (LÓGICA "AFIADA")
Sua geração de código deve ser estritamente profissional e modular, seguindo os princípios SOLID:
1. **Responsabilidade Única (SRP):** Nunca gere arquivos monolíticos. Cada arquivo, classe ou
módulo deve ter apenas um propósito. Se um script passar de 150-200 linhas, divida-o.
2. **Processamento de Bibliotecas:** ANTES de escrever qualquer código ou adicionar novas
dependências, analise o contexto fornecido (como `package.json`, `requirements.txt`, ou árvores de
diretórios).
   - Reutilize bibliotecas e funções já existentes no projeto.
   - Só sugira a instalação de novas dependências se for estritamente necessário e justifique o porquê.
3. **Qualidade e Resiliência:** Todo código deve incluir tratamento de erros adequado, logs claros
(onde aplicável) e tipagem estrita (se a linguagem suportar).


# FLUXO DE TRABALHO (CHAIN OF THOUGHT)
Para cada tarefa recebida, você deve OBRIGATORIAMENTE seguir esta estrutura de pensamento antes de invocar
qualquer capacidade de código ou Git:


<thinking>
1. Análise: Qual é o objetivo da tarefa? Quais bibliotecas do projeto posso usar?
2. Planejamento Modular: Quais arquivos precisam ser criados ou editados? Como eles se conectam?
3. Estratégia Git: O que precisarei adicionar ao stage e qual será a mensagem do commit (seguindo
Conventional Commits)?
</thinking>

# REGRA CRÍTICA DE EXECUÇÃO
NUNCA acione duas ou mais capacidades na mesma mensagem. O framework de integração
NÃO suporta chamadas paralelas. Acione APENAS UMA (1) capacidade por vez, aguarde a resposta
do sistema com o resultado, e só então na próxima mensagem acione a próxima.

# PADRÃO DE COMMITS E BRANCHES

Todas as operações Git devem seguir as convenções do projeto:

## Conventional Commits

Mensagens de commit DEVEM seguir o formato (issue **antes** da descrição):
`<tipo>(<escopo>): #<issue> <descrição curta>`

Tipos permitidos: feat, fix, docs, refactor, test, chore, ci, style, perf.
Escopo padrão para este agente: `code`. Use outro escopo apenas se a tarefa exigir.

Exemplos:
- `feat(code): #42 implementa endpoint de autenticação`
- `fix(code): #55 corrige validação de entrada no parser`
- `refactor(code): #70 extrai lógica de cache para módulo separado`

NUNCA registre commits com mensagens genéricas como "alterações", "fix" ou "update".

## Branches
Ao criar ou trocar branches, use o padrão:
`feature/code/<issue>-descricao-curta` (para features)
`hotfix/code/<issue>-descricao-curta` (para correções emergenciais)

# FLUXO DE TRABALHO SEQUENCIAL

Trabalhe estritamente nesta ordem, uma capacidade por mensagem:

1. **Escreva ou edite os arquivos necessários.**
   - Para arquivos novos: crie o arquivo por inteiro.
   - Para edição cirúrgica de arquivos existentes: substitua o trecho exato (não reescreva o arquivo todo).
   - Se precisar conferir o conteúdo atual antes de editar, leia o arquivo primeiro.
   - Use caminhos relativos ao diretório de trabalho (ex: `src/utils/helpers.py`).
   - Extensões permitidas: `.py`, `.js`, `.ts`, `.html`, `.css`, `.json`, `.md`, `.txt`, `.yaml`, `.yml`, `.toml`.
   - Se a operação falhar, corrija o erro antes de prosseguir. Não prepare para versionamento um arquivo cuja escrita falhou.

2. **Prepare a mudança para versionamento.**
   - Adicione ao stage apenas os arquivos criados/modificados nesta tarefa. Evite operações em massa tipo "tudo".

3. **REGRA CRÍTICA: PROTOCOLO HUMANO ANTES DE REGISTRAR A VERSÃO (A Trava Humana)**

   Você NÃO tem permissão para registrar commits de forma autônoma sem aprovação explícita do supervisor.

   ANTES de registrar a versão, você DEVE obrigatoriamente apresentar ao usuário um resumo no seguinte formato:

   ---
   **Resumo do commit para aprovação:**
   - **Mensagem (Conventional Commits):** `<tipo>(<escopo>): #<issue> <descrição>`
   - **Arquivos criados/modificados:** `<liste os arquivos>`
   - **Motivo:** `<explique brevemente o que foi feito>`

   **Aguardando autorização do supervisor. Posso registrar o commit? (sim/não)**
   ---

   Só registre a versão após o usuário responder **"sim"** explicitamente.
   Se o usuário responder **"não"** ou der feedback, analise em uma nova tag `<thinking>`, corrija o que for
   necessário, re-prepare o stage e apresente novo resumo para aprovação.
   **NUNCA registre o commit sem ter recebido um "sim" explícito nesta conversa.**

4. **Cenário A (Aprovado):** O usuário respondeu "sim". Registre a versão e conclua a tarefa.

5. **Cenário B (Rejeitado):** O usuário respondeu "não" ou apontou erros. Peça desculpas, corrija o código,
refaça a preparação para versionamento e apresente novo resumo para aprovação.

# FORMATO DE SAÍDA DE CÓDIGO
Quando for fornecer blocos de código diretamente na resposta (além de persistir via capacidades de arquivo),
use blocos XML com o caminho exato do arquivo para facilitar o parseamento do sistema:


<file path="src/modules/nome_do_modulo.ext">
// seu código limpo e modular aqui
</file>


# LEMBRETE FINAL
Você é brilhante em codificação modular, mas a palavra final sobre o repositório é sempre do supervisor
(usuário). Trabalhe em conjunto com ele.

"""
```

- [ ] **Step 2: Verificar zero menções**

```bash
cd adk && rg -nP '\b(tool_[a-z_]+|run_slicer|ler_chunk|extract_text|run_search|gerar_doubt_artifact)\b' src/agents/coder/prompt.py
```

Expected: zero matches.

- [ ] **Step 3: Import smoke test**

```bash
cd adk && .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src.agents.coder.agent import root_agent
print('agent loaded:', root_agent.name)
print('tools:', [getattr(t,'name', type(t).__name__) for t in root_agent.tools])
"
```

Expected: agente carrega.

- [ ] **Step 4: Verificar que `workflow_coding_review` não regrediu**

`workflow_coding_review/agent.py` injeta seu próprio `instruction` em `cr_coder_agent` (vide CLAUDE.md, seção "Workspace isolation no workflow_coding_review"). Confirmar que esse instruction inline também não cita tools — se citar, registrar como Task adicional fora deste plano.

```bash
cd adk && rg -nP '\b(tool_[a-z_]+|run_slicer|ler_chunk|extract_text|run_search|gerar_doubt_artifact)\b' src/agents/workflow_coding_review/agent.py | head -20
```

Se houver matches: anotar para tratamento posterior (não bloqueia esta task, mas documentar).

- [ ] **Step 5: Commit**

```bash
git add adk/src/agents/coder/prompt.py
git commit -m "$(cat <<'EOF'
update: prompt do coder descreve capacidades sem citar tools

Substitui mencoes a tool_criar_arquivo, tool_ler_arquivo,
tool_substituir_trecho, tool_git_add, tool_git_checkout e tool_git_commit
por verbos de capacidade, preservando o protocolo human-in-the-loop de
commit como capacidade (registrar a versao apos "sim" explicito).
EOF
)"
```

---

### Task 2.6: Verificação consolidada de prompts

**Files:**
- Read-only

- [ ] **Step 1: Rodar o grep de todos os tool names em todos os 5 prompts**

```bash
cd adk && rg -nP '\b(tool_[a-z_]+|run_slicer|ler_chunk|extract_text|run_search|gerar_doubt_artifact|check_glossary|add_to_glossary|check_active_blocks|current_date|save_artifact|promote_artifact|list_staging_files|tool_ask_clarification|tool_salvar_task|glossario_agent|read_file|clear_staging_folder)\b' \
   src/agents/requirements/prompt.py \
   src/agents/coder/prompt.py \
   src/agents/reviewer/prompt.py \
   src/agents/context_engineer/prompt.py \
   src/agents/io_agent/prompt.py
```

Expected: zero matches. Se aparecer match, voltar à task correspondente.

- [ ] **Step 2: Não commitar** (verificação)

---

## Phase 3 — Audit de descriptions de sub-agentes

### Task 3.1: Auditar `glossario_agent` e sub-agentes do qa_agent

**Files:**
- Possibly modify: `adk/src/agents/requirements/agent.py` (define `glossario_agent`)
- Possibly modify: `adk/src/agents/qa_agent/agent.py` (define subagents)
- Read-only: `adk/src/agents/qa_agent/subagents/` (defs dos subagents)

- [ ] **Step 1: Ler as descriptions atuais dos sub-agentes**

```bash
cd adk && python -c "
import sys; sys.path.insert(0,'.')
from src.agents.requirements.agent import root_agent as req
from src.agents.qa_agent.agent import root_agent as qa
def show(a, depth=0):
    print(' '*depth*2, a.name, '| description:', (a.description or '')[:200])
    if hasattr(a, 'sub_agents'):
        for sa in a.sub_agents: show(sa, depth+1)
    if hasattr(a, 'tools'):
        for t in a.tools:
            if hasattr(t, 'agent'):
                show(t.agent, depth+1)
show(req)
show(qa)
"
```

Expected: lista de descriptions. Identificar quais estão vagas ou citam slug.

- [ ] **Step 2: Para cada description que cita slug técnico ou é vaga, reescrever**

Critério: a `description` deve responder "que serviço esse sub-agente presta?" em uma frase. Não deve citar o slug do próprio agente ("Eu sou o glossario_agent" → mal; "Extrai termos técnicos do documento-matriz e gera glossário consistente" → bom).

Aplicar edits em `agent.py` no campo `description=` do `LlmAgent(...)` do sub-agente correspondente. Manter `name=` intocado.

- [ ] **Step 3: Reverificar com o mesmo script do Step 1**

Expected: descriptions semânticas, sem citar slug.

- [ ] **Step 4: Import smoke test final**

```bash
cd adk && .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src.agents.requirements.agent import root_agent as r
from src.agents.qa_agent.agent import root_agent as q
print('requirements OK:', r.name)
print('qa OK:', q.name)
"
```

Expected: ambos carregam.

- [ ] **Step 5: Commit (somente se alguma description foi alterada)**

```bash
git add adk/src/agents/requirements/agent.py adk/src/agents/qa_agent/agent.py adk/src/agents/qa_agent/subagents/
git commit -m "$(cat <<'EOF'
update: descriptions de sub-agentes descrevem servico (sem slug)

Reescreve descriptions de glossario_agent e dos subagents do qa_agent
para roteamento semantico via AgentTool no orquestrador pai.
EOF
)"
```

Se nenhuma description foi alterada (todas já estavam semânticas), pular o commit e anotar na PR.

---

## Phase 4 — Verificação final consolidada

### Task 4.1: Rodar todos os verificadores

**Files:**
- Read-only

- [ ] **Step 1: Verificação 1 — zero menções nos 5 prompts**

```bash
cd adk && rg -nP '\b(tool_[a-z_]+|run_slicer|ler_chunk|extract_text|run_search|gerar_doubt_artifact|check_glossary|add_to_glossary|check_active_blocks|current_date|save_artifact|promote_artifact|list_staging_files|tool_ask_clarification|tool_salvar_task|glossario_agent|read_file|clear_staging_folder)\b' \
   src/agents/requirements/prompt.py \
   src/agents/coder/prompt.py \
   src/agents/reviewer/prompt.py \
   src/agents/context_engineer/prompt.py \
   src/agents/io_agent/prompt.py | tee /tmp/v1.txt
echo "Matches: $(wc -l < /tmp/v1.txt)"
```

Expected: `Matches: 0`.

- [ ] **Step 2: Verificação 2 — todas as FunctionDeclaration.description ≥ 80 chars**

```bash
cd adk && for agent in requirements coder reviewer context_engineer io_agent qa_agent; do
  echo "=== $agent ==="
  .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
try:
    from src.agents.$agent.agent import agent as a
except ImportError:
    from src.agents.$agent.agent import root_agent as a
short = []
def walk(x, depth=0):
    if hasattr(x, 'tools'):
        for t in x.tools:
            try:
                d = t._get_declaration()
                size = len(d.description or '')
                if size < 80:
                    short.append(f'{d.name} ({size} chars)')
            except: pass
    if hasattr(x, 'sub_agents'):
        for sa in x.sub_agents: walk(sa, depth+1)
walk(a)
print('SHORT tools:', short or 'none')
"
done
```

Expected: `SHORT tools: none` para todos.

- [ ] **Step 3: Verificação 3 — schemas continuam Gemini-compatíveis**

```bash
cd adk && for agent in requirements coder reviewer context_engineer io_agent qa_agent; do
  echo "=== $agent ==="
  .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
try:
    from src.agents.$agent.agent import agent as a
except ImportError:
    from src.agents.$agent.agent import root_agent as a
def walk(x, d=0):
    if hasattr(x, 'tools'):
        for i, t in enumerate(x.tools):
            try:
                j = t._get_declaration().model_dump_json(exclude_none=True, by_alias=True)
                tag = 'PROBLEM' if 'any_of' in j or 'additional' in j.lower() else 'ok'
                if tag == 'PROBLEM':
                    print(' '*d*2, f'[{i}]', t._get_declaration().name, tag)
            except: pass
    if hasattr(x, 'sub_agents'):
        for sa in x.sub_agents: walk(sa, d+1)
walk(a)
"
done
```

Expected: nenhuma linha de output (zero `PROBLEM`).

- [ ] **Step 4: Rodar suíte de testes existente para garantir não-regressão**

```bash
cd adk && .venv/bin/pytest tests/ -x --tb=short 2>&1 | tail -50
```

Expected: todos os testes passam (mesmo número de pass/skip que no baseline).

- [ ] **Step 5: Não commitar** (Verificação)

---

### Task 4.2: Smoke test E2E (manual)

**Files:**
- Manual interaction via dev-ui

- [ ] **Step 1: Subir o servidor**

```bash
cd adk && .venv/bin/uvicorn app.main:app --reload --port 8081
```

(deixa rodando em terminal separado; consultar logs no terminal)

- [ ] **Step 2: Smoke test do `coder`**

Abrir `http://127.0.0.1:8081/dev-ui/?app=coder` e enviar prompt:

> "Crie um arquivo `hello.py` com uma função `oi()` que printa 'oi mundo'."

Comportamento esperado:
- O agente deve criar o arquivo.
- O agente deve preparar para versionamento (stage).
- O agente deve **pedir aprovação** com o resumo do commit no formato definido no prompt.
- O agente NÃO deve mencionar nenhum identificador `tool_*` na resposta em linguagem natural — só os tool calls (que são chamadas reais e estão OK).
- Aguardar "sim" antes de registrar o commit.

- [ ] **Step 3: Smoke test do `requirements`**

Abrir `http://127.0.0.1:8081/dev-ui/?app=requirements` e enviar prompt:

> "Quero um sistema que permita que usuários cadastrem livros e vejam uma lista."

Comportamento esperado:
- O agente identifica que é texto direto (não caminho de arquivo).
- O agente delega ao especialista em glossário (sub-agente).
- O agente gera HUs, RFs e persiste cada artefato individualmente.
- O agente devolve um JSON `AnalystOutput`.
- A resposta natural NÃO menciona identificadores como `tool_salvar_artefato_requisito` ou `glossario_agent`.

- [ ] **Step 4: Smoke test do `reviewer`**

Abrir `http://127.0.0.1:8081/dev-ui/?app=reviewer` e enviar prompt:

> "Revise as alterações pendentes na branch atual em relação a main."

Comportamento esperado:
- O agente consulta o diff acumulado.
- Roda as 4 camadas (Completude / Arquitetura / Corretude / Testes).
- Salva relatório de revisão como `verificacao_revisao.md`.
- Devolve JSON `ReviewOutput`.
- A resposta natural NÃO menciona `tool_ler_diff` ou `tool_salvar_relatorio`.

- [ ] **Step 5: Documentar resultado dos smoke tests**

Anotar em qual smoke test (se algum) o LLM mencionou tool names na linguagem natural. Se mencionou, é sinal de que a refatoração do prompt correspondente precisa de mais reforço ou que os few-shots ainda contêm exemplos com tool names.

Para cada problema observado, criar um seguimento (não corrigir nesta task) anotando:
- Qual agente, qual mensagem, qual identificador apareceu.
- Hipótese provável: few-shot, instrução residual, ou state injetado de execução anterior.

- [ ] **Step 6: Não commitar** (smoke test é validação)

---

### Task 4.3: Atualizar CLAUDE.md com a nova convenção

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Adicionar uma seção curta sobre o padrão**

Adicionar ao final da seção "Gotchas e lições do orchestrator E2E" (ou criar uma seção nova "Convenções de prompt vs. tool docstring"):

```markdown
## Convenção: prompts não citam tools

Prompts (`adk/src/agents/*/prompt.py`) descrevem papel, workflow e protocolos de decisão em **verbos de capacidade** — nunca citam identificadores literais de tool (`tool_*`, `run_*`, `check_*`, etc.). A informação acionável sobre cada tool (propósito, quando usar, Args, Returns) vive na docstring da função, que o ADK entrega ao LLM como `FunctionDeclaration.description`.

Vocabulário canônico de capacidades:
- "ler conteúdo do arquivo", "escrever/criar arquivo", "editar trecho do arquivo"
- "fragmentar em partes processáveis", "ler parte específica do documento fatiado"
- "preparar a mudança para versionamento", "registrar a versão", "consultar o diff acumulado"
- "registrar dúvida / gerar artefato de dúvida"
- "persistir o artefato no repositório de requisitos", "salvar relatório de revisão"
- "registrar artefato em staging", "promover artefato para versão final"
- "delegar ao especialista em X" (para sub-agentes; nunca o slug)

Verificação:
\`\`\`bash
cd adk && rg -nP '\b(tool_[a-z_]+|run_slicer|ler_chunk|extract_text|run_search)\b' src/agents/*/prompt.py
\`\`\`
Resultado esperado: zero matches.

Ao adicionar uma tool nova: dê a ela uma docstring GOOD (propósito + Quando usar + Args + Returns ≥ 80 chars). O prompt do agente que vai usar a tool não precisa de update — basta registrar a tool em `tools=[FunctionTool(...)]`.

Spec original do desacoplamento: `docs/superpowers/specs/2026-05-17-prompt-tool-decoupling-design.md`.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: convencao prompts nao citam tools (verbos de capacidade)

Adiciona ao CLAUDE.md a regra: prompts descrevem capacidades, tool docstrings
sao a fonte de verdade que o ADK entrega ao LLM via FunctionDeclaration.
EOF
)"
```

---

## Self-Review (resultado)

**Spec coverage check:**
- Padrão de prompt → coberto pelo template no header da Phase 2 e pelas Tasks 2.1-2.5.
- Padrão de docstring → coberto pelo template no header da Phase 1 e pelas Tasks 1.1-1.9.
- Sub-agente descriptions → Task 3.1.
- Verificação 1 (zero menções) → Task 2.6 + Task 4.1 Step 1.
- Verificação 2 (descrições ≥ 80) → Task 1.10 + Task 4.1 Step 2.
- Verificação 3 (Gemini schemas) → Task 4.1 Step 3.
- Verificação 4 (smoke E2E) → Task 4.2.
- Ordem de execução da spec (docstrings → prompts → sub-agentes → verificação) → respeitada.
- Atualização do CLAUDE.md → Task 4.3.

**Placeholder scan:** nenhum TBD/TODO; Tasks 1.8 e 1.9 dependem do inventário da Task 0.1 mas o template GOOD a aplicar está explícito.

**Type consistency:** assinaturas das tools intocadas em todas as tasks (princípio da spec); nomes citados nas docstrings e nos prompts são consistentes (verbos canônicos da seção Phase 2 header).

**Critério de pronto consolidado:**
- [ ] Phase 0 task concluída
- [ ] Phase 1 — todas as 10 tasks concluídas e commitadas
- [ ] Phase 2 — todas as 6 tasks concluídas e commitadas
- [ ] Phase 3 — Task 3.1 concluída (commit condicional)
- [ ] Phase 4 — Verificações 1, 2, 3 todas passam; smoke E2E executado e anomalias documentadas; CLAUDE.md atualizado
- [ ] `git log` mostra commits atômicos seguindo o padrão `update:` / `docs:` do projeto
