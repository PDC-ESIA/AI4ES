# Fluxo de Trabalho: Agente de Requisitos & Validação de Domínio

Este diagrama descreve a interação entre o Usuário, o Agente Supervisor e o Agente Analista, destacando a geração de artefatos de domínio e o tratamento de dúvidas.

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuário (Cliente)
    participant S as Agente Supervisor (Orquestrador)
    participant A as Agente Analista (Requisitos)

    Note over S: [Artefato] Documento Matriz
    
    U->>S: Descreve o contexto do projeto 
    S->>S: Estrutura Documento Matriz
    S->>A: Envia Input Fatiado (Segmentos)
    
    A->>A: Processa via System Prompt & Tools
    
    alt Inconsistência ou Bloqueio Detectado
        Note right of A: [Artefato] Doubt_Artifact.md (Pendente)
        A-->>S: Notifica Bloqueio de Domínio
        Note over S, U: Interação Humana (Natalie/Karlla/Cliente)
        U->>S: Fornece Clarificação/Regras Ocultas
        S->>A: Retoma Processamento com novo contexto
        Note right of A: [Artefato] Doubt_Artifact.md (Resolvido)
    else Fluxo Nominal
        A->>A: Valida consistência interna e lógica de domínio
    end

    A->>S: Entrega Estrutura de Requisitos
    
    Note over S, A: [Artefatos Finais Gerados]
    Note over S, A: • User Stories (HU) <br/> • Requisitos Funcionais (RF) <br/> • Requisitos Não-Funcionais (RNF) <br/> • Casos de Uso (UC)

    S->>U: Apresenta Backlog Refinado (Markdown)
```

## Papéis e Artefatos

*   **Usuário (Cliente):** Fonte primária de conhecimento e validador final.
*   **Agente Supervisor:** Orquestra o fatiamento e consolida o backlog final.
*   **Agente Analista (MVP):** Transforma contexto bruto em requisitos técnicos estruturados.
*   **Doubt_Artifact.md:** Canal de comunicação síncrona/assíncrona para resolução de ambiguidades de domínio (Responsabilidade: Natalie).
*   **Output Final:** Conjunto de documentos Markdown padronizados contendo HU, RF, RNF e UC.
