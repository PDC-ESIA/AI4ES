# Protocolo de Comunicação: Agente Supervisor ↔ Agente QA

---

## 1. Contexto do Projeto

| Campo | Valor |
|---|---|
| Nome do projeto | PDC-AI4SE |
| Framework de agentes | Google ADK |
| Localização dos agentes | `adk/src/agents/` |
| Localização do sub-agente QA | `adk/src/agents/tests/ ` |
| Branch de desenvolvimento Principal | `feature/time3-testes` e as branchs das subs-task: `task-[issue]/[descrição]` |

---

## 2. Protocolo de Comunicação

O protocolo de comunicação entre os agentes é o **Google ADK**. O Supervisor chamará o QA Agent como um `AgentTool` — não há necessidade de protocolo de transporte customizado para que o supervisor seja o pai que consiga direcionar os requesitos retirados e direcionar para o agente de QA.

```
Supervisor Agent
      │
      │  AgentTool(agent=qa_agent)
      │  passa: { artefato de requisito }
      ▼
  QA Agent
      │
      │  processa e gera testes pytest
      ▼
  retorna relatório ao Supervisor
```

---

## 3. Estrutura da Mensagem

### 3.1 Formatos de Artefato Suportados

Os requisitos podem chegar em diferentes formatos. Preencha quais o seu time suportará:

| Tipo | Sigla | Descrição | 
|---|---|---|
| Requisito Funcional | RF | "O sistema deve fazer X" | 
| Requisito Não-Funcional | RNF | Performance, segurança, disponibilidade |
| User Story | HU | "Como [usuário], quero [ação], para [benefício]" | 
| Caso de Uso | UC | Fluxo principal + fluxos alternativos | 
| Regra de Negócio | RN | "Se condição X, então ação Y" |

### 3.2 O que o Supervisor envia ao QA

```python
# Estrutura da mensagem recebida pelo QA Agent
mensagem_do_supervisor = {
    "id_artefato": "[ ex: RF-001 ]",   # Identificador único
    "tipo": "[ RF | HU | UC | RNF | RN ]",
    "conteudo": "[ texto do requisito ]",
    "modulo": "[ módulo do sistema ]",
    "criticidade": "[ alta | media | baixa ]",
    "metadados": {
        "enviado_por": "supervisor_agent",
        "timestamp": "ISO-8601",
        "versao_protocolo": "1.0",
    }
}
```

### 3.3 O que o QA retorna ao Supervisor

```python
resposta_do_qa = {
    "id_artefato": "[ eco do ID recebido ]",
    "status": "[ sucesso | falha | parcial ]",
    "tipo_teste": "pytest",
    "testes_gerados": [
        {
            "nome": "[ ex: test_rf001_login_valido ]",
            "arquivo": "[ /caminho do arquivo gerado ]",
            "resultado": "[ passou | falhou | pendente ]",
        }
    ],
    "cobertura": {
        "percentual": 0.0,       # preenchido em tempo de execução
        "linhas_cobertas": 0,
        "linhas_totais": 0,
    },
    "erros": [],
}
```

---

## 4. Implementação no ADK

### 4.1 Definição inicial do QA Agent 
```python
# arquivo: adk/src/agents/tests/qa_agent.py PARCIAL 
#[... def e imports do agente para o fluxo]

qa_agent = Agent(
    name="qa_agent",
    model="[ ex: gemini-2.0-flash ]",
    description="[  descrição do agente QA ]",
    instruction="""
        [ instruções do agente, necessitando ainda de configuração de prompt]

        Para cada artefato recebido:
        1. Analise o artefato e identifique o que precisa ser testado
        2. Gere cenários: caminho feliz, erros esperados e casos de borda
        3. Escreva código pytest completo e funcional de acordo com padrão do pytest.ini
        4. Execute os testes e colete os resultados
        5. Retorne relatório com status, arquivos gerados e cobertura
    """,
    tools=[], # Tools configurads e anexadas
)
```

### 4.2 Registro do QA Agent no Supervisor (quando disponível)

```python
# arquivo: [ caminho do supervisor  obs: aguardando MVPs]

from google.adk.agents import Agent
from google.adk.tools import AgentTool
from [ PREENCHER ].qa_agent import qa_agent # Caminho do arquivo do agent

supervisor_agent = Agent(
    name="supervisor_agent",
    # ...
    tools=[
        # [ PREENCHER: ferramentas existentes do Supervisor ],
        AgentTool(agent=qa_agent),
    ],
)
```

---

## 5. Testando o QA Agent Sem o Supervisor

Enquanto o Supervisor não estiver pronto, use o ADK diretamente:

```bash
# [ PREENCHER: ajuste o caminho conforme a estrutura do projeto ]
cd [ PREENCHER: raiz do ADK ]

# Interface web (simula conversas com o agente)
adk web

# Ou via terminal
adk run [ PREENCHER: caminho do qa_agent.py ]
```

Exemplo de mensagem para simular o Supervisor:

```
Gere testes para o seguinte requisito:
{
  "id_artefato": "[ PREENCHER ]",
  "tipo": "[ PREENCHER ]",
  "conteudo": "[ PREENCHER ]",
  "modulo": "[ PREENCHER ]",
  "criticidade": "[ PREENCHER ]"
}
```

---

## 6. Os Dois Tipos de Pytest no Projeto

| Tipo | Finalidade | Quem escreve | Localização |
|---|---|---|---|
| **Pytest de produto** | Testa o código da aplicação | Agente QA gera automaticamente | `[ AINDA À DEFINIR ex: adk/src/agents/test/ ]` |
| **Pytest de eval** | Testa o próprio Agente QA | Desenvolvedor do time escreve | `[ AINDA À DEFINIR ex: adk/src/agents/tests/evals/ ]` |

---
 
## 7. Doubt Artifacts — Intervenção Humana
 
> **Regra de arquitetura do projeto:** Obrigatoriamente, todos os agentes devem gerar um arquivo `Doubt_Artifact.md` caso encontrem inconsistências ou bloqueios, **pausando a execução do nó** para intervenção humana.
 
### 7.1 Quando o QA Agent deve gerar um `Doubt_Artifact.md`
 
O QA Agent deve parar e gerar o arquivo sempre que não conseguir prosseguir de forma autônoma e segura:
 
| Situação | Exemplo concreto |
|---|---|
| Artefato ambíguo ou incompleto | Requisito sem critério de aceite claro |
| Conflito entre requisitos | RF-001 contradiz RF-005 no mesmo módulo |
| Módulo ou código-fonte não encontrado | Caminho do módulo informado não existe |
| Requisito fora do escopo do time | Artefato pertence a outro time/agente |
| Dúvida sobre criticidade ou prioridade | Não está claro se o bloqueio é crítico |
| `[ PREENCHER: outras situações que pode aparecer ]` | `[ PREENCHER ]` |
 
### 7.2 Estrutura do arquivo `Doubt_Artifact.md`
 
```markdown
# Doubt Artifact — QA Agent
 
**ID do Artefato:** [ id do artefato/ferramenta que gerou a dúvida/erro ]
**Data/Hora:** [ ISO-8601 ]
**Agente:** qa_agent
**Status:** BLOQUEADO — aguardando intervenção humana
 
---
 
## Descrição da Inconsistência ou Bloqueio
 
[ Descreva claramente o que o agente encontrou e não conseguiu resolver ]
 
## Contexto
 
- Artefato recebido: [ id e tipo ]
- Módulo: [ módulo envolvido ]
- Etapa onde o bloqueio ocorreu: [ ex: geração de testes | leitura do PDF | execução ]
 
## O que foi tentado
 
[ Liste as abordagens que o agente tentou antes de pausar ]
 
## O que é necessário para continuar
 
[ Descreva exatamente o que um humano precisa fornecer ou decidir ]
 
## Artefatos relacionados
 
[ Links ou referências para outros arquivos relevantes ]
```
 
### 7.3 Localização do arquivo
 
```
adk/src/agents/tests/
└── doubt_artifacts/
    └── Doubt_Artifact_[ id_artefato ]_[ timestamp ].md
```
 
> Use timestamp no nome para não sobrescrever dúvidas anteriores quando múltiplos artefatos gerarem bloqueios em paralelo.
 
### 7.4 Comportamento após gerar o arquivo
 
1. O agente **para de processar** o artefato problemático
2. Os demais artefatos da fila **continuam sendo processados** normalmente
3. O agente **reporta ao Supervisor** (ou ao chamador) que há um `Doubt_Artifact.md` pendente
4. A execução do nó **só é retomada** após intervenção humana e resolução documentada
 
```python
# Exemplo de como sinalizar o bloqueio no retorno do agente
return {
    "id_artefato": id_artefato,
    "status": "bloqueado",
    "motivo": "doubt_artifact_gerado",
    "arquivo_duvida": "doubt_artifacts/Doubt_Artifact_RF001_20260317T140000.md",
    "mensagem": "Inconsistência encontrada. Aguardando intervenção humana.",
}
```

---

## 8. Tratamento de Erros

| Código | Situação | O QA deve... |
|---|---|---|
| `ERR_ARTEFATO_INCOMPLETO` | Campos obrigatórios ausentes | Solicitar mais detalhes e dados obritórios |
| `ERR_MODULO_NAO_ENCONTRADO` | Módulo informado não existe | Informar o caminho esperado e o caminho recebido |
| `ERR_TESTE_FALHOU` | Teste gerado e executado com falha | Reportar qual teste e por quê com logs explícitos |
| `ERR_TIMEOUT` | Execução ultrapassou o tempo limite | Reportar quais testes não concluíram |
| `ERR_LOOP` | Loop infinito ao executar a tool| Finalizar a execução, gerar o Doubt_Artifact e informar no log |

---

