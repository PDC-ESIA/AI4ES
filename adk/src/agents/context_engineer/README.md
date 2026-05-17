# Agente Context Engineer

**Time:** Codificação (Time 4)
**Modelo:** github_copilot/gpt-4 (padrão) — sobrescreva com `ADK_LLM_MODEL`

---

## O que este agente faz

Recebe requisitos atômicos gerados pelo `requirements_agent` e os transforma em
**tarefas de codificação contextualizadas** (Context Windows), enriquecidas com
contexto arquitetural, regras globais e contratos de dependência.

Persiste cada task como arquivo JSON individual em `$WORKSPACE_OUTPUT_DIR/tasks/`
(default: `./workspace_output/tasks/`).

O agente NÃO implementa código. NÃO define requisitos. Apenas contextualiza e empacota.

## Posição no Pipeline SDLC

```
requirements → context_engineer → architect → test_planner → coder → reviewer → qa → finalizer
```

- **Entrada:** `state["requirements"]` (saída do `requirements`)
- **Saída:** `state["tasks"]` (consumida pelos agentes subsequentes)

## Schema de saída

JSON com `macro_context` (summary, tech_stack, global_rules) e `tasks` (lista de Task com id/type/complexity/description/business_rules/acceptance_criteria/contract).

## Origem

Phase 1.D: criado com `LlmAgent` direto e caminho `artefatos/tasks/`. Phase 2.E: migrado para `create_se_agent(agent_subdir='context_engineer')` com workspace binding — escreve em `$WORKSPACE_OUTPUT_DIR/tasks/`.
