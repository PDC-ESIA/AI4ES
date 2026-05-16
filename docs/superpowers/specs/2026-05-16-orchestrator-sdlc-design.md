# Design — Orquestrador SDLC com Doubt Inbox Unificado

> **Status:** Aprovado (escopo MVP — ver Seção 12)
> **Data:** 2026-05-16
> **Branch alvo:** `consolidacao/agentes-times-1-2-3-4`
> **Idioma:** Português brasileiro (artefatos, código, comentários)

---

## 1. Contexto e motivação

O AI4ES consolidou na branch `consolidacao/agentes-times-1-2-3-4` os agentes dos quatro Times SWEBOK (Requisitos, Design, Testes, Codificação). Hoje existem 14 agentes individuais e 5 workflows pré-montados em `adk/src/agents/`:

| Workflow | Time | Composição |
|---|---|---|
| `workflow_requirements` | 1 | LlmAgent → `requirements` |
| `workflow_design_pipeline` | 2 | LlmAgent → 5 especialistas em sequência |
| `workflow_coding_review` | 4 | SequentialAgent: requirements → coder → reviewer |
| `workflow_coding` | 4 | SequentialAgent: SDLC completo (requirements → architect → test_planner → coder → reviewer → qa → finalizer) |
| `workflow_qa` | 3 | LlmAgent → action_planner → receber_requisitos → pytest → code_fix |

**Problemas identificados:**

1. O orquestrador atual (`adk/src/agents/orchestrator/agent.py`) conhece apenas 2 dos 5 workflows (`sdlc_pipeline` e `coding_review_pipeline`). Não chama `workflow_requirements`, `workflow_design_pipeline` nem `workflow_qa` diretamente.
2. Doubt artifacts existem em **quatro formatos diferentes** (Time 1 versionado, `doubt_handler` centralizado, `clarification`, QA `DoubtArtifactGenerator`). Não há agregador — quando um workflow gera uma dúvida, o usuário precisa caçar o arquivo manualmente.
3. O ciclo SDLC só roda fim-a-fim via `workflow_coding`, que é um `SequentialAgent` rígido — não permite pausa entre fases, roteamento de dúvidas, nem paralelismo onde seria possível (ex.: design e preparação de pastas de testes podem ocorrer simultaneamente após requisitos).

**Objetivo deste design:** transformar o `orchestrator` no ponto único de entrada do ciclo SDLC, capaz de (a) acionar qualquer um dos 5 workflows, (b) intercalar fases com paralelismo onde for seguro, (c) coletar e rotear doubt artifacts entre fases — escalando ao usuário apenas quando necessário.

---

## 2. Escopo

### Em escopo

- Reescrever `adk/src/agents/orchestrator/agent.py` e `adk/src/agents/orchestrator/prompt.py` para ancorar o protocolo de fases.
- Criar `adk/shared/tools/doubt_inbox.py` com três funções: `coletar_doubts_pendentes`, `responder_doubt`, `classificar_doubt`.
- Re-exportar as novas tools em `adk/shared/tools/__init__.py`.
- Testes unitários do `doubt_inbox` em `adk/tests/unit/test_doubt_inbox.py`.
- Smoke test do orchestrator descoberto pelo ADK em `adk/tests/unit/test_orchestrator_discovery.py`.

### Fora de escopo

- Qualquer alteração nos 5 workflows existentes (`workflow_*`).
- Qualquer alteração nos 14 agentes individuais.
- Unificação dos 4 formatos de doubt artifact — o `doubt_inbox` é adapter, lê todos.
- Introdução de `ParallelAgent` do ADK no orchestrator — paralelismo vem das chamadas múltiplas de tool no mesmo turno da LLM.
- Paralelização HU-a-HU dentro de um workflow (design entrega HU-001 → coder começa HU-001 enquanto design processa HU-002). Fica como evolução futura — os workflows hoje entregam o lote completo, não streaming.
- Alterações em `adk/app/main.py`. O auto-discovery do ADK já carrega o orchestrator atualizado.
- Testes end-to-end com LLM real (custo + flakiness). Validação manual via `dev-ui`.

---

## 3. Arquitetura

### 3.1 Visão geral

```
adk/src/agents/orchestrator/
├── __init__.py            # expõe root_agent (já existe — não muda)
├── agent.py               # REESCRITO — LlmAgent com 5 workflows + tools de inbox + fs
└── prompt.py              # REESCRITO — description + instruction com protocolo de fases

adk/shared/tools/
├── __init__.py            # ATUALIZADO — re-exporta as 3 novas funções
└── doubt_inbox.py         # NOVO — coleta/resposta/classificação unificada

adk/tests/unit/
├── test_doubt_inbox.py    # NOVO — parser, agregação, resposta nos 4 formatos
└── test_orchestrator_discovery.py  # NOVO — smoke test de descoberta ADK
```

### 3.2 Composição do orchestrator

Tipo: `LlmAgent` (mantém o padrão atual; permite lógica condicional impossível em `SequentialAgent`).

```python
root_agent = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4")),
    name="orchestrator",
    description=prompt.description,
    instruction=prompt.instruction,
    tools=[
        # Workflows dos 4 Times — uma AgentTool por workflow
        AgentTool(agent=workflow_requirements),
        AgentTool(agent=workflow_design_pipeline),
        AgentTool(agent=workflow_coding_review),   # default da Fase 3
        AgentTool(agent=workflow_coding),          # SDLC completo, opt-in
        AgentTool(agent=workflow_qa),

        # Tools de filesystem para Fase 0 e operações avulsas
        FunctionTool(tool_criar_arquivo),
        FunctionTool(tool_ler_arquivo),

        # Doubt Inbox (novo)
        FunctionTool(coletar_doubts_pendentes),
        FunctionTool(responder_doubt),
        FunctionTool(classificar_doubt),
    ],
)
```

**O que é removido vs. o orchestrator atual:** `AgentTool(coder_specialist)` e `AgentTool(reviewer_specialist)`. Eles continuam disponíveis como agentes top-level (descobertos pelo ADK em `src/agents/`), mas o orchestrator SDLC não os chama diretamente — `workflow_coding_review` já encapsula ambos.

### 3.3 Doubt Inbox — peça nova

Arquivo: `adk/shared/tools/doubt_inbox.py`.

#### 3.3.1 `coletar_doubts_pendentes(caminho_projeto: str = ".") -> List[Dict]`

Faz `Path(caminho_projeto).rglob("Doubt_Artifact*.md")`, lê cada arquivo, extrai metadados via regex tolerante, retorna apenas dúvidas com `Status` ∈ {`Aberta`, `Pendente`, `Bloqueado`, `🔴 Aberta`}.

Schema do retorno:
```python
{
    "path": str,           # caminho absoluto do arquivo
    "id": str,             # "D-NNN" ou hash do arquivo se não houver ID
    "status": str,         # status original lido do arquivo
    "categoria": str,      # "Falta de Contexto" | "Ambiguidade" | "Erro Técnico" | "Bloqueio Lógico" | "Desconhecida"
    "severidade": str,     # "Baixa" | "Média" | "Alta" | "Crítica" | "Desconhecida"
    "origem_agente": str,  # nome do agente que gerou (inferido pelo path ou conteúdo)
    "pergunta": str,       # campo "Descrição"/"Dúvida"/"Pergunta"
    "sugestao": str,       # campo "Sugestão" se houver
    "bloqueante": bool,    # True se o doubt indica bloqueio
}
```

Ordenação: `bloqueante=True` primeiro; depois por severidade (Crítica > Alta > Média > Baixa > Desconhecida).

**Tolerância de formatos:** O parser deve aceitar os 4 formatos vigentes:
- Time 1 (`gerar_doubt_artifact`): campos em lista markdown `- **Artefato afetado:** ...`
- `doubt_handler.registrar_duvida`: seções `### [D-NNNNN]` em arquivo único
- `clarification.tool_ask_clarification`: cabeçalho `# Doubt Artifact — <titulo>` com seções `## Descrição`, `## Impacto`, `## Pergunta`
- QA `DoubtArtifactGenerator`: nome `Doubt_Artifact_<id_artefato>_<timestamp>.md`

Se o parser não conseguir extrair um campo, preenche com string vazia ou `"Desconhecida"` — nunca lança exceção. O `coletar_doubts_pendentes` é best-effort e robusto a formatos novos.

**Diretórios ignorados na varredura:** `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `dist`, `build`, `.tox`. Reaproveita a constante `DIRETORIOS_PROIBIDOS` de `adk/shared/tools/filesystem.py` e estende com os adicionais.

#### 3.3.2 `responder_doubt(caminho_arquivo: str, resposta: str, autor: str = "humano") -> bool`

Lê o arquivo, substitui o valor do campo `Status:` para `Resolvido` (preservando emoji se houver — `✅ Resolvido`), substitui o valor do campo `Resposta:` (variantes: `Resposta Humana:`, `Resposta:`, `Pergunta / Sugestão de Resolução` etc.) pelo conteúdo de `resposta`, e anexa uma linha de metadado no final do bloco:

```
- **Resolvido por:** {autor}
- **Data resolução:** {timestamp ISO 8601}
```

Retorna `True` se conseguiu escrever; `False` se o arquivo não foi encontrado ou o status não era pendente.

#### 3.3.3 `classificar_doubt(doubt: Dict) -> Literal["usuario", "requirements", "design", "coding", "qa"]`

Heurística por palavras-chave em `categoria` + `pergunta` + `origem_agente`:

| Sinal | Destino |
|---|---|
| `origem_agente` ∈ {requirements, glossario_agent} | `requirements` |
| `origem_agente` ∈ {design_architect, mermaid_specialist, markdown_specialist, validator, io_agent} | `design` |
| `origem_agente` ∈ {coder, reviewer, architect, test_planner, finalizer} | `coding` |
| `origem_agente` ∈ {qa_agent, action_planner, code_fix_agent, receive_requirements} | `qa` |
| `categoria == "Falta de Contexto"` E menciona HU/RF/RNF/UC/RN | `requirements` |
| `categoria == "Erro Técnico"` E menciona pytest/teste | `qa` |
| `categoria == "Bloqueio Lógico"` ou texto contém "decisão de negócio", "regra de negócio", "stakeholder" | `usuario` |
| Default (sem sinal claro) | `usuario` |

O LLM do orchestrator pode sobrescrever via instrução do prompt — `classificar_doubt` é só uma sugestão.

---

## 4. Protocolo de fases (instrução do orchestrator)

O `prompt.py` documenta este protocolo como instrução em PT-BR para o LlmAgent seguir como máquina de estados implícita.

### Fase 0 — Scaffolding (paralelo, imediato)

Antes de qualquer workflow, o orchestrator chama em **um único turno** múltiplas invocações de `tool_criar_arquivo` para garantir que os diretórios que os workflows precisam existam:

```
tool_criar_arquivo(
    caminho="temp/staging/README.md",
    conteudo="# Staging (Time 2)\n\nDiretório de artefatos intermediários do pipeline de Design (.mmd, .md, Doubt_Artifacts).\nGerenciado pelo io_agent."
)
tool_criar_arquivo(
    caminho="artefactsTests/README.md",
    conteudo="# Testes Gerados (Time 3)\n\nDiretório onde o qa_agent salva os arquivos pytest gerados a partir de artefatos de requisito."
)
tool_criar_arquivo(
    caminho="docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/README.md",
    conteudo="# Agente Analista (Time 1)\n\nDiretório default para Doubt_Artifacts gerados pelo workflow_requirements."
)
```

**Por que `README.md` e não `.gitkeep`:** a tool `tool_criar_arquivo` (`adk/shared/tools/filesystem.py:8`) só aceita extensões da whitelist `EXTENSOES_PERMITIDAS` — `.gitkeep` não está na lista. Usar `README.md` evita modificar a shared tool e ainda documenta o propósito da pasta.

Esses caminhos foram extraídos do código existente:
- `temp/staging/` — usado pelo `io_agent` (Time 2) e referenciado em prompts de `design_orchestrator`, `validator`, `mermaid_specialist`, `markdown_specialist`.
- `artefactsTests/` — usado pelo `qa_agent` (`adk/src/agents/qa_agent/subagents/receive_requirements.py:19`).
- `docs/Time_1_Requisitos/setup-ADK/AgenteAnalista/` — default do `caminho_base` em `gerar_doubt_artifact` (`adk/shared/tools/doubt_generator_analista.py`).

`tool_criar_arquivo` sobrescreve se o arquivo já existir — operação é idempotente por natureza. Conteúdo consistente entre rodadas garante que não há ruído de diff.

### Fase 1 — Requisitos (bloqueante)

Chama `workflow_requirements(request=<pedido_original>)`. Aguarda retorno.

Ao terminar, chama `coletar_doubts_pendentes(".")`:
- Se vazio → Fase 2.
- Se ≥1 dúvida → entra no **loop de resolução de doubts** (seção 5) antes de seguir.

### Fase 2 — Design (paralelo com QA scaffolding)

Em **um turno**, chama em paralelo:
- `workflow_design_pipeline(request=<contexto+artefatos_da_Fase_1>)`
- `tool_criar_arquivo(caminho="artefactsTests/<projeto>/.gitkeep", conteudo="")` para criar subpasta específica do projeto

Ao terminar design → `coletar_doubts_pendentes` → loop ou Fase 3.

### Fase 3 — Codificação

**Default:** `workflow_coding_review(request=<requirements+design>)`. Pipeline enxuto: requirements → coder → reviewer (o `requirements` interno do `coding_review_pipeline` reaproveita os artefatos da Fase 1, não duplica trabalho).

**Opt-in:** se o usuário pedir explicitamente "ciclo completo" ou "SDLC completo", usa `workflow_coding` em vez de `workflow_coding_review`. Caveat: `workflow_coding` é `SequentialAgent` rígido que embute requirements/architect/test_planner/coder/reviewer/qa/finalizer — usar isso significa "deixe o pipeline rígido fazer tudo, ignore as Fases 4 do orchestrator". Documentar essa exclusividade no prompt.

Ao terminar → `coletar_doubts_pendentes` → loop ou Fase 4.

### Fase 4 — QA

Chama `workflow_qa(request=<artefatos_requisito + codigo_implementado>)`.

Ao terminar → `coletar_doubts_pendentes` → loop ou entrega final.

### Entrega final

Resumo executivo em PT-BR:
- Lista de artefatos produzidos por fase com caminhos.
- Doubt artifacts criados durante o ciclo e como foram resolvidos.
- Doubt artifacts ainda abertos (se houver — só em caso de erro inesperado).

---

## 5. Loop de resolução de doubts

Sempre que `coletar_doubts_pendentes` retorna ≥1 dúvida, o orchestrator entra em loop. **Não avança para a próxima fase enquanto houver dúvida bloqueante pendente.**

```
para cada doubt em duvidas_pendentes (ordenadas por bloqueante+severidade):

    tentativas = 0
    destino = classificar_doubt(doubt)

    enquanto tentativas < 2 e destino != "usuario":
        # Snapshot dos doubts antes da tentativa
        snapshot_antes = set(d["path"] for d in coletar_doubts_pendentes("."))

        resposta = workflow_<destino>(
            request=f"Esclarecer doubt {doubt.id} gerado por {doubt.origem_agente}: "
                     f"{doubt.pergunta}. Contexto: {doubt.path}. "
                     f"Sugestão do agente: {doubt.sugestao}"
        )

        # Critério de sucesso (todas as condições):
        # 1. workflow retornou texto não-vazio
        # 2. resposta não contém marcadores de erro/bloqueio
        #    ("bloqueado", "não foi possível", "preciso de mais contexto")
        # 3. workflow não emitiu novo Doubt_Artifact durante a execução
        snapshot_depois = set(d["path"] for d in coletar_doubts_pendentes("."))
        novos_doubts = snapshot_depois - snapshot_antes

        marcadores_falha = ["bloqueado", "não foi possível", "preciso de mais contexto"]
        resposta_tem_falha = any(m in resposta.lower() for m in marcadores_falha)

        if resposta and not resposta_tem_falha and not novos_doubts:
            responder_doubt(doubt.path, resposta, autor=f"workflow_{destino}")
            break  # próximo doubt

        else:
            tentativas += 1
            destino = "usuario"  # escala se workflow não conseguiu

    se chegou aqui e doubt ainda não foi respondido:
        # Escala para o usuário
        apresenta_ao_usuario(
            f"🚧 [{doubt.origem_agente}] precisa de esclarecimento sobre {doubt.id}:\n"
            f"Pergunta: {doubt.pergunta}\n"
            f"Sugestão do agente: {doubt.sugestao}\n"
            f"Tentativa de roteamento automático: {'falhou' if tentativas > 0 else 'pulada (classificada como usuário)'}\n"
            f"Como deseja proceder?"
        )
        aguarda resposta do usuário
        responder_doubt(doubt.path, resposta_usuario, autor="humano")
```

**Critério concreto de "workflow resolveu o doubt":**
1. Workflow retornou texto não-vazio
2. Texto não contém marcadores de falha (`"bloqueado"`, `"não foi possível"`, `"preciso de mais contexto"`, case-insensitive)
3. Workflow não emitiu Doubt_Artifact novo durante sua execução (diff entre snapshots de `coletar_doubts_pendentes` antes/depois)

Se qualquer condição falhar, conta como tentativa malsucedida e escala.

**Regras:**
- Máximo 2 tentativas de roteamento automático por doubt antes de obrigatoriamente escalar.
- Toda dúvida sempre termina com `Status: Resolvido` — seja pela máquina, seja pelo humano.
- O orchestrator nunca pula uma dúvida silenciosamente. Se não conseguiu resolver, pergunta.
- Doubts novos surgidos durante a tentativa de resolução **não são** processados no mesmo loop — entram na próxima chamada de `coletar_doubts_pendentes` no fim da fase atual, evitando recursão.

---

## 6. Diagrama de fluxo

```
┌─────────────────────────────────────────────────────────────┐
│ USUÁRIO: "construa feature X"                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 0: Scaffolding (paralelo)                              │
│   tool_criar_arquivo × 3  ──┐                               │
│                              │ (mesmo turno LLM)             │
│                              ▼                               │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 1: workflow_requirements (bloqueante)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ coletar_doubts       │
              │ pendentes()          │
              └──┬───────────────┬───┘
       vazio     │               │  ≥1 doubt
                 │               ▼
                 │   ┌─────────────────────────┐
                 │   │ Loop resolução (sec 5)  │
                 │   └──────────┬──────────────┘
                 │              │
                 ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 2: design + qa scaffold (paralelo, mesmo turno)        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼  (loop doubts)
┌─────────────────────────────────────────────────────────────┐
│ FASE 3: workflow_coding_review (default)                    │
│         OU workflow_coding (opt-in, exclui Fase 4)          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼  (loop doubts)
┌─────────────────────────────────────────────────────────────┐
│ FASE 4: workflow_qa                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼  (loop doubts)
┌─────────────────────────────────────────────────────────────┐
│ ENTREGA: resumo + lista de artefatos + doubts resolvidos    │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Testes

### 7.1 Unit — `adk/tests/unit/test_doubt_inbox.py`

Casos:
- `test_coleta_formato_time1_versionado`: cria arquivo no formato `gerar_doubt_artifact`, verifica que `coletar_doubts_pendentes` retorna 1 entrada com campos corretos.
- `test_coleta_formato_doubt_handler_centralizado`: cria `Doubt_Artifact.md` com múltiplas seções `### [D-NNN]`, verifica que retorna N entradas.
- `test_coleta_formato_clarification`: cria arquivo `Doubt_Artifact_Clarification.md` no formato de `tool_ask_clarification`, verifica parsing.
- `test_coleta_formato_qa`: cria `Doubt_Artifact_<id>_<ts>.md` no formato `DoubtArtifactGenerator`, verifica parsing.
- `test_coleta_ignora_resolvidos`: arquivo com `Status: Resolvido` não aparece no retorno.
- `test_coleta_ordenacao_bloqueante_severidade`: mistura de dúvidas, verifica ordem.
- `test_responder_doubt_atualiza_status_e_resposta`: chama `responder_doubt`, lê arquivo, valida que status virou `Resolvido` e resposta foi escrita.
- `test_responder_doubt_arquivo_inexistente_retorna_false`.
- `test_classificar_doubt_por_origem_agente`: ≥1 caso por destino possível.
- `test_classificar_doubt_default_para_usuario`: doubt sem sinal claro → `usuario`.
- `test_parser_robusto_campos_faltantes`: arquivo malformado não causa exceção; campos faltantes viram string vazia.

### 7.2 Smoke — `adk/tests/unit/test_orchestrator_discovery.py`

Verifica que `from src.agents.orchestrator import root_agent` carrega sem erro e que `root_agent.name == "orchestrator"`. Não testa LLM real.

### 7.3 Manual

Após implementação, validar via `uvicorn app.main:app --reload --port 8081` e `dev-ui` em `http://127.0.0.1:8081/dev-ui/?app=orchestrator` com pedido típico ("construa um endpoint /healthcheck").

---

## 8. Tradeoffs assumidos

| Decisão | Tradeoff |
|---|---|
| Parser tolerante (best-effort) em vez de schema rígido | Aceita 4 formatos atuais sem mexer nos workflows; pode falhar silenciosamente em formato 5 — mitigado por testes por formato. |
| `LlmAgent` com `AgentTool` em vez de `ParallelAgent`/`SequentialAgent` | Paralelismo depende do LLM emitir tool calls paralelas no mesmo turno (suportado pelo ADK mas não determinístico). Em troca, ganhamos lógica condicional e doubt routing. |
| Default Fase 3 = `workflow_coding_review` (não `workflow_coding`) | Evita duplicar Fases 1/4 (que `workflow_coding` embute como SequentialAgent rígido). Usuário ainda pode pedir SDLC completo via opt-in. |
| Cap de 2 tentativas de roteamento automático antes de escalar | Equilibra autonomia (resolver dúvidas técnicas entre workflows) com risco de loop infinito. Escala rápido em casos ambíguos. |
| `coder_specialist` e `reviewer_specialist` removidos das tools do orchestrator | Mantém o orchestrator focado em fluxo SDLC. Para ops avulsas, usuário acessa esses agentes diretamente via dev-ui. |
| Sem paralelização HU-a-HU | Workflows são caixa-preta — entregam tudo no final. Implementar streaming exigiria refatorar 4 workflows recém-consolidados. ROI baixo agora. |

---

## 9. Riscos

- **Determinismo do paralelismo**: o LLM pode optar por chamar tools sequencialmente mesmo quando o prompt sugere paralelo. Mitigação: prompt enfatiza paralelismo explicitamente e dá exemplos.
- **Formatos novos de doubt artifact**: se um Time introduzir um 5º formato, o parser ignora silenciosamente. Mitigação: smoke test diário no CI que conta `Doubt_Artifact*.md` no projeto vs. doubts retornados pelo `coletar_doubts_pendentes` — alerta se houver divergência.
- **`workflow_coding` vs Fases**: se o usuário pedir SDLC completo, o `workflow_coding` interno dispara `qa_agent` que pode gerar doubts — o orchestrator não estará "ouvindo" no meio dessa execução. Mitigação: ao terminar `workflow_coding`, ainda chama `coletar_doubts_pendentes` uma vez para capturar pendências.
- **Caminhos relativos**: as tools de filesystem assumem CWD = `adk/` (pythonpath do `pyproject.toml`). Documentar no prompt para o LLM não usar caminhos absolutos.

---

## 10. Plano de implementação (alto nível, será detalhado pelo writing-plans)

1. Criar `adk/shared/tools/doubt_inbox.py` com as 3 funções e parser tolerante.
2. Re-exportar em `adk/shared/tools/__init__.py`.
3. Escrever `adk/tests/unit/test_doubt_inbox.py` (TDD — testes antes da implementação parser completa).
4. Reescrever `adk/src/agents/orchestrator/prompt.py` com o protocolo de fases e regras de doubt routing.
5. Reescrever `adk/src/agents/orchestrator/agent.py` com os 5 workflows + tools de inbox + fs.
6. Escrever `adk/tests/unit/test_orchestrator_discovery.py`.
7. Validação manual via `dev-ui`.
8. Commits atômicos seguindo convenção PT-BR (`add:`, `update:`, `refactor:`).

---

## 12. Escopo MVP (v1)

Para validar a hipótese central — *"agregar doubt artifacts em um inbox unificado + escalá-los ao usuário em um ponto central reduz fricção do ciclo SDLC?"* — a v1 entrega um subconjunto deste design:

### v1 — INCLUI

- `doubt_inbox` com **2 das 3** funções: `coletar_doubts_pendentes` e `responder_doubt`. Parser dos 4 formatos completo.
- Orchestrator reescrito com os 5 workflows como tools.
- Protocolo de fases completo (Fase 0 → Fase 4).
- **Doubts sempre escalam para o usuário.** O orchestrator não tenta rotear automaticamente entre workflows.

### v1 — EXCLUI (fica para v2)

- `classificar_doubt` (Seção 3.3.3) — heurística de roteamento por origem_agente/categoria.
- Loop de roteamento automático com cap de 2 tentativas (Seção 5, `enquanto tentativas < 2`).
- Snapshot comparison (`coletar_doubts_pendentes` antes/depois para detectar novos doubts).
- Marcadores de falha (`"bloqueado"`, `"não foi possível"`, etc).

### Loop de resolução simplificado (v1)

A Seção 5 vira:

```
para cada doubt em duvidas_pendentes (ordenadas por bloqueante+severidade):
    apresenta_ao_usuario(
        f"🚧 [{doubt.origem_agente}] precisa de esclarecimento sobre {doubt.id}:\n"
        f"Pergunta: {doubt.pergunta}\n"
        f"Sugestão do agente: {doubt.sugestao}\n"
        f"Como deseja proceder?"
    )
    aguarda resposta do usuário
    responder_doubt(doubt.path, resposta_usuario, autor="humano")
```

### Por que essa fatia

1. Valida a peça nova (inbox + parser + escalation) sem acoplar a outro experimento (auto-routing).
2. Comportamento determinístico — usuário consegue prever o que o orchestrator vai fazer.
3. Plano de implementação menor → ciclo de feedback mais rápido.
4. Se v1 não funcionar, sabemos que o problema é no inbox/escalation. Se v2 não funcionar com auto-routing, sabemos que o problema é no roteamento.

A v2 (auto-routing) será adicionada após v1 ser validada no `dev-ui` com um caso real do AI4ES.

---

## 11. Referências cruzadas

- `adk/src/agents/orchestrator/agent.py` — orchestrator atual (será reescrito)
- `adk/src/agents/workflow_*` — 5 workflows compostos (não serão alterados)
- `adk/shared/tools/doubt_generator_analista.py` — formato Time 1
- `adk/shared/tools/doubt_handler.py` — formato centralizado
- `adk/shared/tools/clarification.py` — formato clarification
- `adk/src/agents/qa_agent/tools/doubt_tool.py` — formato QA
- `CLAUDE.md` — convenções do repo (idioma, branches, ADK auto-discovery)
- `CONTRIBUTING.md` — convenções de commit e PR
