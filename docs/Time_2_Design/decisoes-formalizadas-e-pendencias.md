# Decisões Formalizadas e Pendências — Time 2 (Design)

**Última atualização:** 24/07/2026

Este documento registra, no próprio projeto, decisões que já foram tomadas
(seja por auditoria de código, seja em reunião) e que até agora só existiam em
material de discussão fora do repositório. Não descreve trabalho de código —
cada item aqui é uma decisão fechada ou uma pendência que depende de
alinhamento humano, não de implementação.

Para o estado técnico detalhado (o que está implementado, testado, e as
lacunas de código que ainda restam), ver `README.md` desta mesma pasta e o
código-fonte referenciado em cada seção.

---

## 1. Decisões formalizadas

### 1.1 `design_orchestrator` confirmado como entry point para HITL isolado

**Decisão:** chamar um especialista de design isoladamente via
`AgentTool` (fora do `design_pipeline` completo) é um modo de uso suportado,
inclusive para fluxos que dependem de pausa real (HITL). O mecanismo de
pausa/retomada do `orchestrator` genérico reage a qualquer `function_call`
long-running em qualquer profundidade de aninhamento — não há nada hardcoded
para o pipeline completo.

**Ressalva que permanece válida (não é bug):** o Manifesto de Fase só é
emitido quando o `design_pipeline` completo roda, porque `emit_design_manifest`
está plugado como `after_agent_callback` do `SequentialAgent` raiz do
pipeline — não em cada especialista individualmente. Uma chamada isolada a um
especialista via `design_orchestrator` tem HITL funcional, mas não gera
manifesto. Isso é coerente com o princípio de produto reafirmado na reunião
de 17/07 (agentes independentes não devem depender obrigatoriamente do
manifesto para toda execução).

**Onde isso está refletido no código:** `src/agents/design_orchestrator/agent.py`
(docstring do módulo).

### 1.2 Workspace por sessão / refatoração do orquestrador — adiado deliberadamente

**Decisão (reunião de 17/07):** a criação de um workspace segmentado por
sessão/ID e a refatoração completa do `orchestrator` genérico foram
conscientemente adiadas, para não travar o desenvolvimento simultâneo de
todos os Times. A ordem combinada é a inversa da inicialmente cogitada:
primeiro cada Time avança de forma independente no seu subagente; só depois,
com feedback prático de todos, faz sentido normalizar um padrão comum no
orquestrador.

**Implicação prática:** nenhuma ação é esperada do Time 2 nessa frente agora.
Continuar usando a pasta de workspace atual (não segmentada por sessão) está
oficialmente sancionado. `shared/workspace.py` permanece, por decisão, como
uma variável de estado apontando para uma única pasta — não uma falha a
corrigir.

---

## 2. Pronto para levar à discussão entre Times

### 2.1 Estrutura do campo de dúvidas do Manifesto de Fase

Ação combinada da reunião de 17/07: o Time 2 se antecipou e já implementou —
não apenas propôs — uma estrutura para o campo de dúvidas do Manifesto de
Fase, hoje em produção em `src/agents/workflow_design_pipeline/manifest.py`:

```python
ManifestDoubt = {
    id: string,
    severidade: "alta" | "media" | "baixa",
    bloqueante: boolean,
    path: string,
}
```

O campo `bloqueante` (booleano explícito e estruturado) resolve, no nível do
contrato entre fases, o problema de fragmentação de convenções de status hoje
existente no sistema — sem exigir que nenhum Time reescreva sua própria
convenção de arquivo internamente:

| Origem | Convenção de status usada internamente |
| --- | --- |
| Design (canônica, `Doubt_Artifact`) | `**Status:** Bloqueado` / `**Status:** Resolvido` |
| `clarification.py` (genérico, injetado em todo agente) | `Status: Pendente` |
| `doubt_handler.py` | `🔴 Aberta` / `✅ Resolvida` |
| `doubt_generator_analista.py` (Time 1) | `Status: Aberta` |

Cada Time mantém seu tradutor interno e produz o schema estruturado acima na
saída do manifesto — a padronização acontece na interface entre fases, não
dentro de cada Time.

**Próximo passo (não é trabalho de código do Time 2):** levar esta
implementação — já testada em `tests/unit/test_design_manifest.py` — para a
próxima reunião entre Times, e validar especificamente com o QA se o schema
de 4 campos escalares (sem conteúdo textual embutido) é compacto o suficiente
para a restrição deles de não processar manifestos longos ou redundantes.

---

## 3. Pendências sem resposta interna (dependem de confirmação externa)

### 3.1 Estrutura de issues para esforços comuns com o orquestrador

Dúvida original levantada por Danillo no Slack: existe um grupo de mudanças
que não se encaixa em nenhum flow de agente específico (ex.: workspace com
ID de sessão, refinamentos do próprio orquestrador) — já há esforço formal
para isso, gerenciado em issues ou alguma estrutura equivalente?

A ata da reunião de 17/07 não registra uma resposta explícita. O que ficou
definido foi apenas um modelo organizacional: cada Time destaca uma ou mais
pessoas para atuar como ponte com o orquestrador, trabalhando em paralelo com
Hugo nas demandas comuns, sem que isso vire pré-requisito bloqueante para o
resto do Time.

**Status:** não é uma pendência de código — nenhuma auditoria de código
resolve isso. Continua dependendo de confirmação direta com Danillo ou
KarolSR sobre se existe (ou deveria existir) um board/estrutura formal de
issues para rastrear esses esforços comuns.

### 3.2 Contrato de manifesto de fase entre Times (leitura, lado de Requisitos)

Registrado aqui apenas para rastreabilidade: o Design já **emite** seu
próprio Manifesto de Fase (seção 2.1 acima), mas ainda não **lê** um
manifesto da fase `requirements`, porque esse manifesto — do lado de
Requisitos — ainda não existe. Isso não é decidível unilateralmente pelo
Time 2; depende do Time 1 emitir o seu manifesto primeiro. Sem mudança de
código prevista para o Time 2 enquanto essa dependência não for resolvida do
outro lado.

---

## Referências

- `docs/Time_2_Design/README.md` — visão geral técnica do sistema de design.
- `src/agents/workflow_design_pipeline/manifest.py` — implementação do
  Manifesto de Fase.
- `src/agents/design_orchestrator/agent.py` — exposição de especialistas
  isolados via `AgentTool`.
- `shared/workspace.py` — mapeamento de pastas por agente.
