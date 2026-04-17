# Fluxo de Trabalho: Agente de Requisitos & Validação de Domínio (Atualizado)

Este diagrama descreve a interação entre o Usuário, o Agente Orquestrador (SDLC Pipeline) e o Agente Analista de Requisitos, detalhando o uso de ferramentas específicas e o fluxo de tratamento de dúvidas.

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuário (Cliente)
    participant O as Orquestrador (SDLC Pipeline)
    participant A as Agente Analista (Requirements)
    participant T as Tools (Ferramentas)
    participant FS as Sistema de Arquivos

    U->>O: Inicia processo (Contexto do Projeto)
    O->>A: Delega análise de requisitos
    
    Note over A: Processamento via System Prompt & CoT
    
    loop Elicitação e Análise
        A->>T: run_slicer() / ler_chunk()
        T-->>A: Retorna trechos do contexto
    end

    alt Inconsistência ou Falta de Informação
        A->>T: gerar_doubt_artifact(id, motivo)
        T->>FS: Salva Doubt_Artifact_<ID>_<TS>.md
        T-->>A: Retorna caminho do arquivo
        A-->>O: Notifica Bloqueio de Domínio
        O-->>U: Solicita Intervenção Humana
        U->>O: Fornece Clarificação / Resolução
        O->>A: Retoma Processamento com novo contexto
    else Fluxo Nominal (Requisitos Claros)
        A->>A: Valida consistência e aplica templates (HU, RF, RNF, Glossary)
        A->>T: tool_salvar_artefato_requisito(conteudo)
        T->>FS: Salva artefatos Markdown
    end

    A-->>O: Finaliza tarefa (analysis_result)
    
    Note over O, A: [Artefatos Gerados]
    Note over O, A: • User Stories (HU) <br/> • Requisitos Funcionais (RF) <br/> • Requisitos Não-Funcionais (RNF) <br/> • Glossário / Regras de Negócio

    O->>O: Segue para próxima etapa (Arquitetura)
```

## Papéis e Artefatos (Atualizado)

*   **Usuário (Cliente):** Fornece o contexto inicial e resolve impedimentos documentados.
*   **Orquestrador (SDLC Pipeline):** Gerencia a sequência de agentes (Requirements -> Architect -> ...).
*   **Agente Analista (requirements_analyst):** Especialista que utiliza CoT (Chain of Thought) para elicitar e classificar requisitos.
*   **Tools (shared/tools):** 
    *   `run_slicer` / `ler_chunk`: Para navegação granular no contexto.
    *   `gerar_doubt_artifact`: Criação formal de pedidos de esclarecimento.
    *   `tool_salvar_artefato_requisito`: Persistência dos requisitos validados.
*   **Doubt_Artifact_<ID>.md:** Documento de bloqueio que exige revisão humana para prosseguir.
*   **Output Final:** Artefatos técnicos estruturados salvos no sistema de arquivos.
