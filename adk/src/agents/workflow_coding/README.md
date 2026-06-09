# Agente Workflow de Pipeline SDLC

## 1. Visão Geral
- **Identificação:** Workflow Orquestrador (SDLC).
- **Propósito:** Automatiza o ciclo de vida de desenvolvimento de software orquestrando a sequência: requisitos, arquitetura, testes, codificação, revisão e finalização.
- **Tecnologias:** Google ADK, LiteLLM, Python, `SequentialAgent`.

## 2. Funcionalidades
Execução encadeada e passagem de contexto entre os sub-agentes especialistas do ciclo SDLC.

## 3. Como executar ou testar
- **Pré-requisitos:** Chave `ADK_LLM_MODEL` no `.env`.
- **Instalação:** `uv sync`.
- **Execução:** Invocado via orquestrador principal (`adk run`).
- **Suíte de Testes:** *Não implementada.* Atualmente não há testes de integração ou unitários para este workflow na pasta `adk/tests/`.

## 4. Entradas e Saídas
- **Entrada:** Demanda natural do usuário.
- **Saída:** Arquivos alterados, relatórios (PRD, Diff) e feedback encadeado.

## 5. Cenário de Teste Específico
Solicitação de nova feature genérica. Valida-se se os 6 agentes são instanciados sequencialmente sem interrupção de contexto. *(Status: Cenário E2E Não Implementado)*

## 6. Lista de Erros Identificados
- *Falha de Sub-agente:* Interrompe o workflow caso um agente intermediário gere erro fatal. Requer fallback ativado ou ajuste de prompt local.
