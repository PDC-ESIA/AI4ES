# Agente de Codificação (Coder)

## 1. Visão Geral
- **Identificação:** Role de Implementação.
- **Propósito:** Materializar requisitos e arquitetura escrevendo arquivos e versionando código localmente no repositório.
- **Tecnologias:** Google ADK, Git CLI, Python.

## 2. Funcionalidades
Operações de I/O locais em arquivos e versionamento autônomo através das ferramentas do Git (Add, Commit, Checkout).

## 3. Como executar ou testar
- **Pré-requisitos:** Repositório Git inicializado e `.env` com provedor de LLM.
- **Instalação:** `uv sync`.
- **Execução:** Suporta execução isolada (pois expõe `root_agent`).
- **Testes:** `pytest adk/tests/`.

## 4. Entradas e Saídas
- **Entrada:** Requisitos e documentação técnica definida pelos agentes anteriores.
- **Saída:** Arquivos modificados e commits gerados (`output_key="implementation"`).

## 5. Cenário de Teste Específico
Solicitar a implementação de uma função matemática em um arquivo específico. Validar se a tool de criação de arquivo e os commits git (padrão conventional) foram acionados com sucesso.

## 6. Lista de Erros Identificados
- *Conflitos de Git / Lock:* Bloqueio ao tentar realizar um commit em branch restrita. Solução: Garantir o checkout dinâmico da branch pelo orquestrador antes do run.
