# Desacoplar prompts de nomes de tools

**Data:** 2026-05-17
**Branch:** `feature/code/1-initial-project-setup`
**Status:** Aprovado para implementação

## Contexto

No estado atual do ADK em `adk/src/agents/`, cinco prompts de agente (`requirements`, `coder`, `reviewer`, `context_engineer`, `io_agent`) citam identificadores de tools (`tool_criar_arquivo`, `run_slicer`, `gerar_doubt_artifact`, `tool_git_commit`, etc.) verbatim no campo `instruction`. Quatorze identificadores distintos aparecem cruzando os cinco prompts.

Em paralelo, das ~22 funções registradas como `FunctionTool`:

- 3 têm docstring **GOOD** (≥3 frases com Args/Returns e propósito): `check_glossary`, `add_to_glossary`, `gerar_doubt_artifact`.
- 11 têm docstring **SHALLOW** (one-liner ou Args mínimos sem semântica).
- 8 estão **MISSING** (sem docstring).

O ADK usa `__doc__` como `FunctionDeclaration.description` e entrega ao LLM via API. Portanto a fonte de verdade *já é* o docstring; mencionar nomes de tool no prompt é redundância que cria fragilidade:

- Renomear uma tool exige caçar menções em todos os prompts.
- Prompts drift em relação à implementação real (incidente histórico: `cr_requirements_agent` listava no `instruction` tools que não estavam em `tools=[...]`, gerando `ValueError: Tool 'X' not found`).
- O LLM pode interpretar como ordem rígida o que era apenas referência informativa.

## Objetivo

Refatorar prompts dos cinco agentes para descrever **papel, workflow e protocolos de decisão** em vocabulário de capacidade — nunca citando identificadores de função. Em paralelo, elevar todas as docstrings das tools ao padrão GOOD para que o `FunctionDeclaration.description` carregue toda a informação acionável.

Resultado: prompts ficam rename-safe, drift-free, e a tool é a única fonte de verdade sobre si mesma.

## Não-objetivos

- Mudar a assinatura de qualquer tool.
- Renomear funções.
- Alterar a plumbing de `FunctionTool` / `AgentTool` / `agent_factory`.
- Tocar nos 9 prompts que já não citam tools (`architect`, `design_*`, `finalizer`, `test_planner`, `validator`, `markdown_specialist`, `mermaid_specialist`, `qa_agent/qa_prompt.py`).

## Padrão de prompt (regra única)

Prompts devem descrever:

1. **Papel** do agente
2. **Workflow / chain-of-thought** com verbos de capacidade
3. **Protocolos de decisão** (human-in-the-loop, gates, condições)
4. **Formato de saída**
5. **Exemplos few-shot** (quando aplicável)

Prompts **não devem** conter:

- Identificadores literais de função (`tool_*`, `run_*`, `check_*`, `gerar_*`, `extract_*`)
- Seções `# FERRAMENTAS DISPONÍVEIS`, `# PROTOCOLO DE EXECUÇÃO E FERRAMENTAS`, ou listas numeradas de tools
- Nomes de sub-agentes técnicos (`glossario_agent`, `action_planner`); usar serviço/papel

### Verbos de capacidade — vocabulário canônico

| Capacidade técnica | Verbo no prompt |
|---|---|
| Escrita de arquivo novo | "escrever / criar arquivo" |
| Edição parcial de arquivo | "editar trecho do arquivo" |
| Leitura de arquivo | "ler conteúdo do arquivo" |
| Fragmentação de documento extenso | "fragmentar em partes processáveis" |
| Leitura de fragmento | "ler parte específica do documento fatiado" |
| Registro de dúvida bloqueante | "registrar dúvida / gerar artefato de dúvida" |
| Persistência de artefato de requisito | "persistir o artefato no repositório de requisitos" |
| Stage de mudanças no Git | "preparar a mudança para versionamento" |
| Commit no Git | "registrar a versão / registrar o commit" |
| Branch no Git | "criar/trocar branch de trabalho" |
| Diff no Git | "consultar o diff acumulado" |
| Salvar relatório de revisão | "salvar relatório de revisão" |
| Salvar artefato de design (staging) | "registrar artefato em staging" |
| Promover staging → final | "promover artefato para a versão final" |
| Consulta a glossário | "consultar glossário" |
| Adicionar termo ao glossário | "registrar termo no glossário" |
| Consulta ao bloco ativo (io_agent) | "verificar blocos ativos do contexto" |
| Pergunta de clareza ao supervisor | "solicitar esclarecimento ao supervisor" |
| Busca web/contexto | "buscar contexto externo" |

### Preservar ordem prescrita do workflow

Quando o agente precisa executar capacidades em sequência fixa (clássico: coder faz write → stage → resumo → commit), o prompt mantém a sequência mas em verbos. Exemplo de bloco antes/depois:

**Antes (coder):**
```
1. tool_criar_arquivo(caminho, conteudo) — ...
2. tool_ler_arquivo(caminho) — ...
3. tool_substituir_trecho(...) — ...
4. tool_git_add(arquivos) — ...
5. REGRA CRÍTICA PARA tool_git_commit: ...
```

**Depois (coder):**
```
Fluxo de trabalho:
1. Escreva os arquivos necessários (criação completa ou edição parcial).
2. Antes de versionar, leia o arquivo se precisar confirmar conteúdo.
3. Prepare as mudanças para versionamento.
4. Apresente o resumo de commit ao supervisor e aguarde "sim" explícito.
5. Somente após autorização, registre a versão.
```

### Protocolos human-in-the-loop

Permanecem no prompt, descritos em capacidade. Exemplo (coder):

> "Antes de registrar qualquer versão no repositório, apresente um resumo da mudança e aguarde a resposta `sim` do supervisor. Sem `sim` explícito, não registre."

O gate técnico (`require_confirmation=True` no `FunctionTool`) é ortogonal e permanece intocado.

## Padrão de docstring (template canônico)

Toda função registrada como `FunctionTool` deve seguir:

```python
def tool_xyz(param1: str, param2: Optional[int] = None) -> dict:
    """<Frase de propósito, uma linha, verbo no infinitivo>.

    <Parágrafo "Quando usar": gatilhos no workflow do agente,
    o que esta capacidade resolve. 2-4 frases.>

    <Parágrafo "Quando NÃO usar" / caveats — somente se houver risco
    real de uso indevido. Opcional.>

    Args:
        param1: <semântica do parâmetro, não só tipo. Formato esperado,
            valores válidos, relação com workspace.>
        param2: <idem.>

    Returns:
        <Forma do retorno. Para dict, liste as chaves e o que cada uma
        sinaliza, incluindo o shape em caso de erro.>
    """
```

### Critério "GOOD"

Para passar como GOOD a docstring deve ter:

- Frase de propósito ≥ 6 palavras
- Bloco "Quando usar" com pelo menos 2 frases
- Bloco `Args:` com semântica (não só tipos)
- Bloco `Returns:` descrevendo o shape (chaves de dict ou conteúdo de str), incluindo o caso de erro
- Tamanho total da docstring ≥ 80 caracteres (verificável por script)

Caveat só é obrigatório quando há risco de uso indevido demonstrado por bug anterior ou por sobreposição entre tools. Exemplo: `tool_substituir_trecho` deve explicitar "Não use para criar arquivos novos; use a capacidade de criação de arquivo."

## Sub-agentes (`AgentTool` wrapping)

Sub-agentes expostos como `AgentTool` ao orquestrador devem ter `description` que descreve **o serviço prestado** em uma frase, não o nome técnico.

Audit-targets (descrições a revisar; reescrever se a `description` cita o slug ou é vaga):

- `glossario_agent` (em `requirements/agent.py`)
- `action_planner` (em `qa_agent/subagents/`)
- `code_fix_agent` (em `qa_agent/subagents/`)
- `receive_requirements` (em `qa_agent/subagents/`)

Prompt do orquestrador correspondente deve referenciar o serviço, não o slug.

## Escopo concreto

### Prompts a refatorar (5 arquivos)

1. `adk/src/agents/requirements/prompt.py` — 4 tool names + 1 sub-agente
2. `adk/src/agents/coder/prompt.py` — 6 tool names + protocolo de commit (preservar como capacidade)
3. `adk/src/agents/reviewer/prompt.py` — 2 tool names
4. `adk/src/agents/context_engineer/prompt.py` — 1 tool name
5. `adk/src/agents/io_agent/prompt.py` — 1 tool name

### Tools com docstring a elevar (SHALLOW → GOOD)

Arquivo `adk/shared/tools/filesystem.py`:
- `tool_criar_arquivo`
- `tool_ler_arquivo`
- `tool_substituir_trecho`
- `tool_salvar_relatorio`
- `tool_salvar_artefato_requisito`
- `tool_ler_workspace`
- `tool_listar_workspace`

Arquivo `adk/shared/tools/git.py`:
- `tool_git_add`
- `tool_git_commit`
- `tool_git_checkout`
- `tool_ler_diff`

Arquivo `adk/shared/tools/slicer_tool.py`:
- `run_slicer`
- `extract_text`

Arquivo `adk/shared/tools/search_tool.py`:
- `run_search`

Arquivo `adk/shared/tools/clarification.py`:
- `tool_ask_clarification`

### Tools com docstring a criar (MISSING → GOOD)

Arquivo `adk/shared/tools/slicer_tool.py`:
- `ler_chunk`

Arquivo `adk/shared/tools/design_filesystem.py`:
- `save_artifact`
- `promote_artifact`
- `list_staging_files`
- `check_active_blocks`

Arquivo `adk/shared/tools/design_date.py`:
- `current_date`

Arquivo `adk/shared/tools/design_validate/` — listar e elevar tudo que estiver MISSING (a inventariação detalhada acontece na fase de planejamento).

Arquivo `adk/src/agents/qa_agent/tools/` — listar e elevar tudo que estiver MISSING (idem).

### Tools que já estão GOOD (não tocar)

- `check_glossary` (em `glossary_tool.py`)
- `add_to_glossary` (em `glossary_tool.py`)
- `gerar_doubt_artifact` (em `doubt_generator_analista.py`)

Servem de referência de padrão durante implementação.

## Estratégia de verificação

### Verificação 1 — zero menções de tool nos prompts

```bash
cd adk
rg -nP '\b(tool_[a-z_]+|run_slicer|ler_chunk|extract_text|run_search|gerar_doubt_artifact|check_glossary|add_to_glossary|check_active_blocks|current_date|save_artifact|promote_artifact|list_staging_files|tool_ask_clarification)\b' \
   src/agents/requirements/prompt.py \
   src/agents/coder/prompt.py \
   src/agents/reviewer/prompt.py \
   src/agents/context_engineer/prompt.py \
   src/agents/io_agent/prompt.py
```

Resultado esperado: **zero matches**.

### Verificação 2 — docstrings substantivas

Para cada agente refatorado:

```bash
cd adk && .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src.agents.<AGENT>.agent import agent as a
def walk(x, depth=0):
    if hasattr(x, 'tools'):
        for t in x.tools:
            try:
                d = t._get_declaration()
                size = len(d.description or '')
                flag = 'SHALLOW' if size < 80 else 'OK'
                print('  '*depth, f'[{flag}]', d.name, size, 'chars')
            except Exception as e:
                print('  '*depth, '[?]', getattr(t, 'name', '?'), e)
    if hasattr(x, 'sub_agents'):
        for sa in x.sub_agents: walk(sa, depth+1)
walk(a)
"
```

Threshold: descrição < 80 chars = **falha**.

### Verificação 3 — schemas continuam compatíveis com Gemini

O CLAUDE.md já documenta o risco de `str | None` e `Union` quebrarem o Gemini API. A refatoração não toca assinaturas, mas o script de validação de schemas (já existente no CLAUDE.md) deve ser rodado para cada agente refatorado para garantir que não houve regressão acidental:

```bash
cd adk && .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src.agents.<AGENT>.agent import agent
def walk(a, d=0):
    if hasattr(a, 'tools'):
        for i, t in enumerate(a.tools):
            j = t._get_declaration().model_dump_json(exclude_none=True, by_alias=True)
            tag = 'PROBLEM' if 'any_of' in j or 'additional' in j.lower() else 'ok'
            print('  '*d, f'[{i}]', t._get_declaration().name, tag)
    if hasattr(a, 'sub_agents'):
        for sa in a.sub_agents: walk(sa, d+1)
walk(agent)
"
```

Resultado esperado: nenhum `PROBLEM`.

### Verificação 4 — smoke test E2E

Rodar `uvicorn app.main:app --port 8081` e exercitar via dev-ui pelo menos:

- **coder**: pedir criação de arquivo simples + observação de que o agente pede `sim` antes de commitar.
- **requirements**: passar um texto curto de PRD e confirmar que ele fatia + persiste artefatos (mesmo que workspace_output siga vazio pelo bug separado de `tool_salvar_artefato_requisito` ignorar `base_dir`).
- **reviewer**: dar um diff fictício e confirmar saída de relatório.

Tipo de regressão a vigiar: o LLM citar nome de função numa resposta dele (ex.: "vou chamar tool_criar_arquivo"). Se citar, é sinal de que o `instruction` precisa de mais reforço de capacidade ou as few-shots estão treinando o LLM a copiar nomes.

## Ordem de execução

1. **Inventário detalhado** das tools MISSING em `design_validate/` e `qa_agent/tools/` (não inspecionados na exploração inicial).
2. **Upgrade de docstrings** em todas as tools listadas, sem mexer em prompt. Commit:
   `update: docstrings de tools elevadas para padrão GOOD (Args/Returns/quando usar)`
3. **Refatoração de prompts**, um por commit, na ordem: `requirements` → `reviewer` → `context_engineer` → `io_agent` → `coder`. Cada commit:
   `update: prompt do <agente> descreve capacidades sem citar tools`
4. **Audit de descriptions de sub-agentes** (`glossario_agent` e qa subagents). Commit:
   `update: descriptions de sub-agentes descrevem servico (sem slug)`
5. **Verificações 1–3** rodam em cada commit como sanity check.
6. **Smoke test E2E** (Verificação 4) ao final, antes de declarar pronto.

## Riscos e mitigação

| Risco | Mitigação |
|---|---|
| LLM perde sequência prescrita do workflow | Manter no prompt a sequência explícita em verbos numerados; few-shots reforçam |
| Docstring fica longa demais e estoura context | Threshold sugerido: 80–500 chars por docstring; suficiente para semântica |
| Refator do coder quebra o gate de aprovação | Preservar a frase "aguarde `sim` antes de registrar a versão" e o `require_confirmation=True` no `FunctionTool` |
| Workflow chamador (ex.: `workflow_coding_review`) recria o agente sem o `instruction` atualizado | Esse workflow já injeta `instruction` próprio; revisar `agent.py` do workflow ao mexer em `coder/prompt.py` |
| Few-shots em `requirements/few_shot.py` citam nomes de tool | Auditar few-shots no momento da refatoração de `requirements/prompt.py` |

## Critério de pronto

- Verificação 1 passa (zero menções).
- Verificação 2 passa (todas as tools listadas com descrição ≥ 80 chars).
- Verificação 3 passa (zero `PROBLEM` em schemas Gemini).
- Smoke test E2E (Verificação 4) executa sem o LLM citar identificadores de tool nas respostas.
- Commits seguem o padrão de mensagens do projeto (`update:`).
