# Agente de Requisitos

## 1. Visão Geral
- **Identificação:** Role de Requisitos.
- **Propósito:** Interpretar PRDs e elucidar ambiguidades via geração de artefatos de dúvida logo no início do processo de ES.
- **Tecnologias:** Google ADK, Pydantic, LiteLLM.

## 2. Funcionalidades
Lê arquivos PRD e extrai regras estruturadas. Levanta dúvidas críticas formatando-as como artefatos para intervenção do usuário.

## 3. Como executar ou testar
- **Pré-requisitos:** `.env` configurado e PRD preenchido.
- **Instalação:** `uv sync`.
- **Execução:** Como sub-agente acionado pelo workflow SDLC.
- **Testes:** `pytest adk/tests/`.

## 4. Entradas e Saídas
- **Entrada:** Escopo textual recebido do orquestrador e leitura do arquivo PRD.
- **Saída:** JSON validado pelo esquema `RequirementsOutput`.

## 5. Cenário de Teste Específico
Submeter um PRD sem especificação de banco de dados. O agente deve usar a tool para gerar o Doubt Artifact perguntando sobre qual banco de dados utilizar.

## 6. Lista de Erros Identificados
- *Pydantic ValidationError:* Ocorre se o LLM fugir do esquema esperado de saída. Solução: Instruções estritas no `prompt.py`.
