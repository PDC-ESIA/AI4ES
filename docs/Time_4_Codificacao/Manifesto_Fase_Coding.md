# Manifesto de Fase — Time 4 (Codificação)

> **Issue de origem:** [#334 — Levantamento da Necessidade do Manifesto](https://github.com/PDC-ESIA/AI4ES/issues/334)
> **Versão:** 1.1 | **Data:** 2026-08-04 | **Autor:** Time 4 — Codificação

---

## 1. Estudo Comparativo

Este estudo analisa os manifestos dos times adjacentes para identificar a estrutura
mínima recomendada e garantir consistência entre fases. A tabela reflete o estado
**verificado em código** após merge com `origin/develop` em 2026-07-23, e
**confirmado em execução real do pipeline SDLC completo** em 2026-08-04
(`workspace_output/coding/manifest.json` gerado com 20 artefatos, `status: partial`).

> **Nota sobre fonte dos dados:** após o merge com `origin/develop`, os arquivos de
> código de Times 1 e 3 foram inspecionados diretamente — os valores abaixo refletem
> implementações reais, não apenas especificações de PR. Time 2 (Design) ainda não
> possui `after_agent_callback` implementado em `workflow_design_pipeline/agent.py`.

### 1.1 Estrutura Comum Identificada

| Dimensão | Time 1 — Requisitos | Time 2 — Design | Time 3 — QA | Time 4 — Codificação |
|---|---|---|---|---|
| Fase (nome canônico) | `requirements` | `design` | `qa` | `coding` |
| Tipos de artefato | HU, RF, RNF, Glossário | analise, diagrama, prototipo, relatorio, validacao | input, teste | codigo, teste, config, revisao |
| Detecção de doubts | `**Bloqueante:** Sim` no arquivo | `**Status:** Bloqueado` no arquivo ¹ | — (sem scan de doubts) | `**Bloqueante:** Sim` no arquivo (mesmo padrão Time 1) |
| Veredicto de validação | — (sem validator separado) | `design/validation/` (validator agent) ¹ | pytest runner (via `executar_pytest_tool`) | `coder/review/` (cr_reviewer) |
| Status canônicos | ok / partial / blocked | ok / partial / blocked | ok / partial | ok / partial / blocked |
| Chave no `session.state` | `requirements_manifest` | `design_manifest` ¹ | `phase_manifests` (lista) ² | `coding_manifest` |
| Arquivo em disco | `requirements/manifest.json` | `design/manifest.json` ¹ | — (somente state) ² | `coding/manifest.json` |
| Consumidor primário | `cr_context_engineer` (Time 4) | `cr_context_engineer` (Time 4) | orquestrador SDLC | `qa_pipeline` (Time 3) |
| Testes unitários | **18 testes** ✅ | 14 testes ¹ | — (sem testes de manifest) | **32 testes** ✅ |
| Padrão de emissão | `after_agent_callback` determinístico, zero LLM ✅ | `after_agent_callback` determinístico, zero LLM ¹ | `after_agent_callback` → `EventActions` ² | `after_agent_callback` determinístico, zero LLM ✅ |
| Estado da implementação | ✅ Implementado e validado (PR #320) | ⚠️ Pendente (especificado em PR #315) | ✅ Implementado (sem testes dedicados) | ✅ Implementado, testado e validado em pipeline real |

> ¹ Time 2 — Design: valores baseados na especificação do PR #315. Inspeção do
> código confirma que `workflow_design_pipeline/agent.py` ainda **não possui**
> `after_agent_callback` wired nem testes de manifesto.
>
> ² Time 3 — QA: implementado via `EventActions(state_delta=...)` em vez de
> escrita direta no state. O manifesto acumula em `phase_manifests` (lista no state)
> mas **não é gravado em disco como `manifest.json`** — diferença relevante para
> consumidores que dependem de leitura do arquivo entre sessões.

### 1.2 Elementos Mínimos Recomendados (extraídos do padrão)

Com base nos três times analisados, um manifesto de fase DEVE conter:

- **`phase`** — nome canônico da fase (string imutável por fase)
- **`status`** — `ok | partial | blocked` (derivado deterministicamente, nunca por LLM)
- **`artifacts`** — lista de `{tipo, id, path}` (path relativo ao workspace root, nunca conteúdo)
- **`doubts`** — lista de `{id, severidade, bloqueante, path}` (vazio se a fase não gera doubts)
- **`summary`** — texto legível derivado dos dados acima, sem inventar informação
- **`session_id`** — opcional, para rastreabilidade entre sessões

**Invariantes obrigatórias** (comuns a todos os times):
- `doubt.bloqueante == true` ⇒ `status == "blocked"`
- `status == "ok"` ⇒ nenhum doubt bloqueante E ao menos um artefato principal produzido
- A emissão do manifesto NUNCA pode derrubar o pipeline (best-effort, fail-and-log)

---

## 2. Recomendação Formal

**Decisão: SIM — o Time de Codificação necessita e deve manter um manifesto de fase.**

**Justificativas:**

1. **Isolamento de sessão.** O ADK usa `InMemorySessionService` — o estado não flui
   entre sessões. O `coding/manifest.json` em disco é o ÚNICO canal confiável de
   handoff entre o pipeline de codificação e o pipeline de QA, que roda em sessão
   isolada.

2. **Consistência com os demais times.** Requisitos (Time 1) e Design (Time 2) já
   adotaram o padrão. QA (Time 3) também possui callback de manifesto em
   desenvolvimento. Sem o manifesto de codificação, o elo central da cadeia quebra.

3. **Eliminação de overflow de contexto.** O output bruto do coder pode ultrapassar
   8 000 tokens quando passado diretamente entre agentes. O manifesto é pequeno,
   estruturado e referencia paths — o consumidor (QA) escolhe quais arquivos ler.

4. **Contrato de saída verificável.** O QA precisa saber exatamente o que foi
   produzido (`codigo`, `teste`, `config`) e se passou pela revisão (`revisao`, com
   status `ok`). Sem manifesto, o QA dependeria de convenções implícitas ou
   varredura total do workspace.

5. **Governança.** O status do manifesto (`ok | partial | blocked`) permite que o
   orquestrador gate a entrada no pipeline de QA, evitando desperdício de tokens em
   código que o próprio reviewer já reprovou.

---

## 3. Manifesto de Fase — Codificação

### 3.1 Papel no Pipeline

O Time 4 ocupa a posição central do SDLC: recebe o contexto estruturado de
Requisitos e Design e entrega código funcional, validado em Docker e revisado,
pronto para ser testado pelo Time 3 (QA).

```
Requisitos → Design → [Codificação] → QA
                            ↑
               coding/manifest.json (consumido pelo QA)
```

Sub-agentes internos:

| Agente | Responsabilidade |
|---|---|
| `cr_context_engineer` | Lê manifestos de Requisitos e Design; fragmenta em tasks contextualizadas |
| `cr_coder` | Implementa código a partir das tasks (tools de filesystem, sem git) |
| `cr_executor` | Builda e executa em Docker; loop de correção automática (máx. 5 iterações) |
| `cr_reviewer` | Revisão em 4 camadas; persiste relatório com `## Status: APROVADO/BLOQUEADO` |
| `emit_coding_manifest` | `after_agent_callback` — emite manifesto determinístico ao final |

### 3.2 Entradas Esperadas

| Fonte | Formato | Lida por |
|---|---|---|
| `workspace_output/requirements/manifest.json` | JSON — schema do manifesto de fase | `cr_context_engineer` via `before_agent_callback` |
| `workspace_output/design/manifest.json` | JSON — schema do manifesto de fase | `cr_context_engineer` via `before_agent_callback` |
| Prompt do usuário | Texto livre (via orchestrator) | `cr_context_engineer` (mensagem de entrada) |

**Schema do manifesto de entrada (requirements e design):**

```json
{
  "phase": "requirements | design",
  "status": "ok | partial | blocked",
  "artifacts": [
    { "tipo": "<tipo>", "id": "<id>", "path": "<path-relativo>" }
  ],
  "doubts": [
    { "id": "<id>", "severidade": "alta | media | baixa", "bloqueante": true, "path": "<path>" }
  ],
  "summary": "<texto>",
  "session_id": "<opcional>"
}
```

**Comportamento quando manifesto de entrada está ausente:**
O `cr_context_engineer` injeta `"(manifesto de X não disponível)"` no prompt.
O pipeline segue com o que o usuário forneceu diretamente.

### 3.3 Saídas Produzidas

#### 3.3.1 Artefatos em disco

| Tipo | Path no workspace | Descrição |
|---|---|---|
| `codigo` | `workspace_output/coder/src/app/**/*.py` | Código-fonte Python da aplicação |
| `teste` | `workspace_output/coder/src/tests/**/*.py` | Testes automatizados |
| `config` | `workspace_output/coder/src/{Dockerfile,requirements.txt,…}` | Infraestrutura Docker e dependências |
| `revisao` | `workspace_output/coder/review/*.md` | Relatório do reviewer (APROVADO/BLOQUEADO) |

Arquivos de config reconhecidos: `requirements.txt`, `Dockerfile`, `docker-compose.yml`,
`docker-compose.yaml`, `conftest.py`, `.dockerignore`, `pyproject.toml`, `setup.py`, `setup.cfg`.

#### 3.3.2 Manifesto de saída (`coding/manifest.json`)

```json
{
  "phase": "coding",
  "status": "ok | partial | blocked",
  "artifacts": [
    { "tipo": "codigo",  "id": "main",      "path": "coder/src/app/main.py" },
    { "tipo": "teste",   "id": "test_main", "path": "coder/src/tests/test_main.py" },
    { "tipo": "config",  "id": "Dockerfile","path": "coder/src/Dockerfile" },
    { "tipo": "revisao", "id": "verificacao_revisao", "path": "coder/review/verificacao_revisao.md" }
  ],
  "doubts": [],
  "summary": "Fase coding concluída com status 'ok'. Artefatos: 3 codigo, 1 config, 1 revisao, 1 teste. Revisão: pass. sem doubts.",
  "session_id": "<session-id-opcional>"
}
```

#### 3.3.3 Derivação de status (determinística)

| Condição (avaliada nesta ordem) | Status |
|---|---|
| Há doubt com `bloqueante == true` | `blocked` |
| Nenhum artefato do tipo `codigo` produzido | `blocked` |
| Reviewer retornou `## Status: APROVADO` | `ok` |
| Qualquer outro caso (reviewer ausente, BLOQUEADO, falha) | `partial` |

> **Nota para consumidores:** `partial` significa que código foi produzido mas a
> revisão não aprovou. O QA deve tratar `status != "ok"` como sinal de atenção
> e decidir se prossegue ou aguarda re-execução.

### 3.4 Limites de Atuação

O Time de Codificação:

- ✅ Implementa código funcional conforme tasks geradas pelo `cr_context_engineer`
- ✅ Valida execução em container Docker (build + runtime + rota principal)
- ✅ Corrige erros de execução automaticamente (máximo 5 iterações)
- ✅ Produz relatório de revisão em 4 camadas via `cr_reviewer`
- ✅ Emite manifesto de fase estruturado ao final

- ❌ Não decide arquitetura (responsabilidade do Time 2 — Design)
- ❌ Não executa testes de QA (responsabilidade do Time 3)
- ❌ Não persiste código em git nem cria branches
- ❌ Não acessa internet (ferramentas limitadas ao filesystem do workspace)
- ❌ Não modifica manifestos de outras fases

### 3.5 Regras de Qualidade e Segurança de Código

#### Regras de integridade do workspace

- Todas as tools do `cr_coder` são bound ao path `workspace_output/coder/src/` — escrita fora desse escopo é bloqueada por `_bind_tool_to_workspace`
- O `WORKSPACE_OUTPUT_DIR` é configurável via variável de ambiente; caminhos relativos são resolvidos a partir do CWD
- O workspace é limpo a cada nova sessão (`init_workspace`) — sem herança de estado entre execuções

#### Regras de código seguro

- Apenas pacotes PyPI válidos no `requirements.txt` (coder recebe instrução explícita com exemplos de erros fatais)
- SQLAlchemy relationships EXIGEM ForeignKey correspondente no model filho
- Todo `import X` deve ter correspondência no `requirements.txt`
- `COPY` no Dockerfile deve referenciar apenas arquivos existentes no workspace

#### Regras de sanitização de saída do manifesto

- O conteúdo dos artefatos NUNCA entra no manifesto — apenas `tipo`, `id` e `path`
- `path` é sempre relativo à raiz do workspace (`workspace_output/`) (nunca absoluto)
- O manifesto é best-effort: qualquer falha na emissão é logada, nunca propaga exceção

---

## 4. Contrato de Integração

### 4.1 Para o Time 2 — Design (produtor de entrada)

O `cr_context_engineer` lê `workspace_output/design/manifest.json` antes de rodar.
O manifesto de design deve estar presente e válido para que o contexto de
arquitetura seja injetado no prompt do context engineer.

**O que o Time 2 deve garantir:**
- `design/manifest.json` presente ao final do pipeline de design
- Artefatos referenciados em `artifacts[].path` acessíveis no workspace
- `status` refletindo fidedignamente o resultado da validação

### 4.2 Para o Time 3 — QA (consumidor de saída)

O pipeline de QA deve ler `workspace_output/coding/manifest.json` antes de rodar.
Os paths em `artifacts` apontam para o código produzido — o QA pode usar esses
paths para gerar testes targetados em vez de varrer o workspace.

**O que o Time 4 garante:**
- `coding/manifest.json` sempre presente ao final do pipeline (mesmo em `blocked`)
- Artefatos do tipo `codigo` têm paths válidos para arquivos `.py` existentes
- `status == "ok"` apenas quando reviewer explicitamente aprovou

**O que o Time 3 deve implementar:**
- Leitura de `coding/manifest.json` no início do pipeline QA
- Gating: se `status == "blocked"`, decidir se aborta ou continua com código parcial
- Usar `artifacts` para determinar quais módulos testar

---

## 5. Versionamento

Este manifesto é versionado em duas formas complementares:

| Forma | Path | Descrição |
|---|---|---|
| Código (runtime) | `adk/src/agents/workflow_coding_review/manifest.py` | Implementação do emissor + schema + invariantes |
| Testes unitários | `adk/tests/unit/test_coding_manifest.py` | 32 testes cobrindo scan de artefatos, doubts, veredicto de revisão e emissão |
| Este documento | `docs/Time_4_Codificacao/Manifesto_Fase_Coding.md` | Especificação formal (critérios, entradas, saídas, limites) |

---

## 6. Melhoria Pendente

### Gating do orquestrador (prioridade: alta)

O orquestrador ainda não lê `coding_manifest` antes de disparar o pipeline de QA.

**Problema:** QA pode rodar sobre código com `status == "blocked"`, desperdiçando
tokens e produzindo testes inválidos.

**Sugestão:** O orchestrator deve verificar `state["coding_manifest"]["status"]`
antes de invocar `qa_pipeline`. Se `blocked`, sinalizar ao usuário e aguardar
re-execução.

---

## Referências

- PR #315 — Time 2: add: manifesto (Design)
- PR #320 — Time 1: feature/req/m3-manifesto-requisitos (Requisitos)
- Issue #334 — Levantamento da Necessidade do Manifesto
- `adk/src/agents/workflow_coding_review/manifest.py` — implementação
- `adk/shared/workspace.py` — AGENT_DIRS e paths do workspace
