# Agente Context Engineer

**Time:** Codificação (Time 4)
**Modelo:** github_copilot/gpt-4 (padrão) — sobrescreva com `ADK_LLM_MODEL`

---

## O que este agente faz

Recebe requisitos atômicos gerados pelo `requirements_agent` e os transforma em
**tarefas de codificação contextualizadas** (Context Windows), enriquecidas com
contexto arquitetural, regras globais e contratos de dependência.

Persiste cada task como arquivo JSON individual em `artefatos/tasks/`.

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

Portado de `feat/me2/coding_squad` (Time 4). Adaptado para usar `LlmAgent` direto e caminho `artefatos/tasks/` hardcoded (sem dependência da factory que será adicionada na Phase 2).
