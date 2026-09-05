# Relatório Técnico de Arquitetura de Software

## 1. Identificação das HUs

### 1.1 Escopo funcional consolidado
Sistema desktop para controle de estoque de loja física, com autenticação, cadastro de produtos, movimentações (entrada/saída), alertas de estoque mínimo, consultas, histórico e exportação CSV.

### 1.2 Histórias de Usuário identificadas e rastreadas

| HU | Objetivo do usuário | RF relacionados | RNF relacionados |
|---|---|---|---|
| HU01 | Cadastrar produto | RF01, RF10, RF12 | RNF05 |
| HU02 | Registrar entrada de mercadoria | RF04, RF07, RF11 | RNF03, RNF04, RNF08 |
| HU03 | Registrar saída de produto | RF05, RF06, RF07, RF11 | RNF03, RNF04, RNF08 |
| HU04 | Receber alerta de estoque baixo | RF08, RF09, RF10 | RNF04 |
| HU05 | Configurar limite mínimo por produto | RF08, RF09 | RNF04 |
| HU06 | Consultar saldo atual | RF10, RF12 | RNF05 |
| HU07 | Consultar histórico de movimentações | RF11 | RNF05, RNF08 |
| HU08 | Exportar dados em CSV | (derivado de operação de consulta e histórico) | RNF07 |

### 1.3 Atores e responsabilidades
- **Operador**: executa todas as operações de negócio.
- **Sistema**: valida regras, persiste dados localmente, mantém rastreabilidade e disponibiliza consultas/exportações.

---

## 2. Diagramas de Arquitetura (Mermaid)

### 2.1 Visão de componentes lógicos

```mermaid
flowchart LR
    A[Interface Desktop\n(Tela Principal + Telas de Operação)] --> B[Controlador de Aplicação]
    B --> C[Serviço de Autenticação]
    B --> D[Serviço de Produtos]
    B --> E[Serviço de Movimentações]
    B --> F[Serviço de Consulta de Estoque]
    B --> G[Serviço de Histórico]
    B --> H[Serviço de Alertas de Estoque]
    B --> I[Serviço de Exportação CSV]

    D --> RP[Repositório de Produtos]
    E --> RP
    E --> RM[Repositório de Movimentações]
    G --> RM
    F --> RP
    H --> RP
    C --> RU[Repositório de Usuários]
    I --> RP
    I --> RM

    RP --> P[(Persistência Local Embarcada)]
    RM --> P
    RU --> P
```

### 2.2 Sequência — Registrar saída com validação, rastreabilidade e alerta

```mermaid
sequenceDiagram
    autonumber
    participant O as Operador
    participant UI as Tela de Saída
    participant APP as Serviço de Movimentações
    participant SES as Serviço de Sessão/Autenticação
    participant PROD as Repositório de Produtos
    participant MOV as Repositório de Movimentações
    participant TX as Unidade Transacional de Persistência
    participant ALT as Serviço de Alertas

    O->>UI: Informa produto + quantidade + data da saída
    UI->>APP: Solicita registro de saída
    APP->>SES: Obter usuário autenticado
    SES-->>APP: usuárioAtual
    APP->>PROD: Consultar saldo e limite mínimo do produto
    PROD-->>APP: saldoAtual, limiteMinimo

    alt quantidade > saldoAtual
        APP-->>UI: Erro de validação (saldo insuficiente)
        UI-->>O: Mensagem clara de impedimento
    else quantidade <= saldoAtual
        APP->>TX: Iniciar transação atômica
        APP->>MOV: Gravar movimentação (tipo=SAÍDA, qtd, dataHora, usuário)
        APP->>PROD: Atualizar saldo do produto (saldo - qtd)
        APP->>TX: Confirmar transação
        APP->>ALT: Avaliar condição de estoque baixo
        ALT-->>APP: statusAlerta (ativo/inativo)
        APP-->>UI: Sucesso + saldo atualizado + status de alerta
        UI-->>O: Confirmação da operação
    end
```

---

## 3. Decisões de Arquitetura

| ID | Decisão | Motivação | Consequências |
|---|---|---|---|
| DA01 | Arquitetura em camadas (Interface, Aplicação/Serviços, Domínio, Persistência) | Separar regras de negócio da interface e da persistência | Maior manutenibilidade e testabilidade |
| DA02 | Persistência local embarcada com transações atômicas | Atender RNF02 e RNF03 (sem servidor externo e sem perda de lançamento) | Operações críticas (entrada/saída) devem confirmar gravação antes de feedback ao usuário |
| DA03 | Modelo de domínio centrado em **Produto**, **Movimentação**, **Usuário**, **Alerta** | Cobrir RF e HU com objetos de negócio explícitos | Facilita rastreabilidade e auditoria de operações |
| DA04 | Regra de saldo aplicada no serviço de movimentações antes de persistir saída | Atender RF06 e HU03 | Impede inconsistência de estoque negativo |
| DA05 | Atualização de saldo por operação de movimentação dentro da mesma unidade transacional | Atender RF07 e RNF03 | Evita divergência entre histórico e saldo atual |
| DA06 | Alerta de estoque baixo calculado e refletido imediatamente após alterações de saldo/limite | Atender RF09, HU04 e HU05 | Feedback imediato e persistência do alerta até reposição |
| DA07 | Consultas de estoque/histórico com filtros e ordenação no serviço de consulta | Atender RF10, RF11, HU06, HU07 e RNF05 | Necessidade de estratégia de paginação/índices lógicos para grande volume |
| DA08 | Exportação CSV como serviço próprio desacoplado de consulta | Atender RNF07 e HU08 | Permite evolução de formatos de exportação sem alterar regra de estoque |
| DA09 | Autenticação por usuário e senha com sessão ativa | Atender RNF06 e RNF08 | Todas as movimentações devem capturar usuário autenticado |
| DA10 | Operações de entrada/saída desenhadas em fluxo curto na UI (máx. 3 interações) | Atender RNF04 | Tela principal deve oferecer atalhos diretos para operações críticas |

---

## 4. Tabela de Componentes e Rastreabilidade

| Componente | Responsabilidade Principal | Comunica-se com | Origem (HU / Critério de Aceite) |
|---|---|---|---|
| Interface Desktop (Tela Principal e Telas de Operação) | Capturar dados, exibir consultas, alertas, erros e confirmações | Controlador de Aplicação | HU02/CA seleção por lista/busca; HU03/CA mensagem clara; HU04/CA alerta destacado; HU06/CA destaque visual e ordenação; HU08/CA confirmação |
| Controlador de Aplicação | Orquestrar fluxos de caso de uso | Serviços de Domínio/Aplicação | Todas as HUs (orquestração central) |
| Serviço de Autenticação/Sessão | Validar acesso por usuário/senha e prover usuário corrente | Repositório de Usuários, Controlador | RNF06, RNF08; HU07/CA exibir usuário responsável |
| Serviço de Produtos | Cadastrar, editar, remover, configurar limite mínimo, validar duplicidade de nome | Repositório de Produtos | HU01/CA obrigatórios e não duplicidade; HU05/CA limite não negativo; RF01, RF02, RF03, RF08 |
| Serviço de Movimentações | Registrar entradas/saídas com validação de quantidade e saldo | Repositório de Produtos, Repositório de Movimentações, Unidade Transacional, Serviço de Sessão | HU02/CA inteiro positivo; HU03/CA impedir saldo insuficiente; RF04, RF05, RF06, RF07, RNF03, RNF08 |
| Serviço de Alertas | Avaliar e sinalizar estoque <= limite mínimo; manter estado até reposição | Repositório de Produtos, Interface | HU04/CA persistência do alerta; RF09 |
| Serviço de Consulta de Estoque | Listar produtos com saldo/limite, busca por nome e ordenação | Repositório de Produtos | HU06/CA listagem e ordenação; RF10, RF12, RNF05 |
| Serviço de Histórico | Consultar movimentações por produto e período, ordem cronológica desc | Repositório de Movimentações | HU07/CA filtros e campos; RF11, RNF05, RNF08 |
| Serviço de Exportação CSV | Exportar dados de estoque e movimentações para arquivo | Serviço de Consulta, Serviço de Histórico, Interface | HU08/CA diretório e confirmação; RNF07 |
| Repositório de Produtos | Persistir produtos, saldo e limite mínimo | Persistência Local, Serviços | RF01, RF02, RF03, RF07, RF08, RF10, RF12 |
| Repositório de Movimentações | Persistir lançamentos com data/hora/usuário | Persistência Local, Serviços | RF04, RF05, RF11, RNF08 |
| Repositório de Usuários | Persistir credenciais e dados mínimos de usuário | Persistência Local, Serviço de Autenticação | RNF06 |
| Unidade Transacional de Persistência | Garantir atomicidade e durabilidade das operações críticas | Repositórios, Serviço de Movimentações | RNF03 |

---

## 5. Bloqueios e Pendências

| ID | Pendência | Impacto arquitetural | Recomendação |
|---|---|---|---|
| BP01 | Regra de remoção de produto com histórico existente não definida (exclusão física vs lógica) | Pode quebrar rastreabilidade e integridade do histórico | Definir política: exclusão lógica recomendada |
| BP02 | Unicidade de nome de produto não detalha normalização (maiúsculas/minúsculas, acentos, espaços) | Risco de duplicidade semântica | Definir critério canônico de comparação de nomes |
| BP03 | “Grande volume” não quantificado para RNF05 | Difícil validar desempenho objetivamente | Definir metas de volume (ex.: número de produtos e movimentações) |
| BP04 | Política de senha não especificada (complexidade, expiração, bloqueio) | Segurança pode ficar insuficiente | Definir política mínima de autenticação |
| BP05 | Requisitos de backup/restauração além de exportação CSV não definidos | Continuidade operacional limitada | Especificar processo de restauração/importação |
| BP06 | Regras de data/hora (fuso horário, edição manual da data do lançamento) não detalhadas | Inconsistência de auditoria/histórico | Definir fonte de tempo oficial e permissões de edição |
| BP07 | Concorrência de acesso local (um ou múltiplos operadores simultâneos) não descrita | Pode impactar bloqueios de gravação e UX | Definir modelo de uso e estratégia de controle de concorrência |

---

## 6. Cobertura de Requisitos

### 6.1 Cobertura dos Requisitos Funcionais (RF)

| RF | Cobertura arquitetural | Componentes-chave | Status |
|---|---|---|---|
| RF01 | Cadastro de produto com validações | Serviço de Produtos, Repositório de Produtos, UI | Coberto |
| RF02 | Edição de produto | Serviço de Produtos, Repositório de Produtos, UI | Coberto |
| RF03 | Remoção de produto | Serviço de Produtos, Repositório de Produtos, UI | Coberto (com pendência BP01) |
| RF04 | Registro de entrada | Serviço de Movimentações, Repositórios, UI | Coberto |
| RF05 | Registro de saída | Serviço de Movimentações, Repositórios, UI | Coberto |
| RF06 | Bloqueio de saída acima do saldo | Serviço de Movimentações (regra de validação) | Coberto |
| RF07 | Atualização automática de saldo | Serviço de Movimentações + transação atômica | Coberto |
| RF08 | Configuração de limite mínimo por produto | Serviço de Produtos, Repositório de Produtos, UI | Coberto |
| RF09 | Alerta visível de estoque baixo | Serviço de Alertas + UI | Coberto |
| RF10 | Consulta de saldo de todos os produtos | Serviço de Consulta de Estoque, UI | Coberto |
| RF11 | Histórico por produto e período | Serviço de Histórico, Repositório de Movimentações, UI | Coberto |
| RF12 | Pesquisa de produtos por nome | Serviço de Consulta de Estoque, UI | Coberto |

### 6.2 Cobertura dos Requisitos Não Funcionais (RNF)

| RNF | Estratégia arquitetural | Componentes-chave | Status |
|---|---|---|---|
| RNF01 (Desktop Windows) | Interface desktop e empacotamento local | Interface Desktop | Coberto |
| RNF02 (Persistência local embarcada) | Repositórios sobre persistência local | Repositórios + Persistência Local | Coberto |
| RNF03 (Confiabilidade) | Transações atômicas e confirmação de escrita antes do retorno | Unidade Transacional + Serviço de Movimentações | Coberto |
| RNF04 (Usabilidade 3 interações) | Fluxos diretos a partir da tela principal | UI + Controlador | Coberto |
| RNF05 (Desempenho até 2s) | Consulta otimizada com filtros/ordenação/paginação | Serviços de Consulta/Histórico + Repositórios | Parcial (depende de BP03) |
| RNF06 (Autenticação) | Usuário/senha com sessão | Serviço de Autenticação | Coberto (política pendente BP04) |
| RNF07 (Exportação CSV) | Serviço dedicado de exportação + seleção de diretório | Serviço de Exportação CSV + UI | Coberto |
| RNF08 (Rastreabilidade) | Registro obrigatório de data/hora/usuário em movimentações | Serviço de Movimentações + Sessão + Repositório de Movimentações | Coberto (detalhe de tempo pendente BP06) |

---

## 7. Gap Analysis

| Lacuna de especificação | Impacto | Risco | Ação recomendada |
|---|---|---|---|
| Falta de política para exclusão de produto com histórico | Integridade de dados e auditoria | Alto | Formalizar exclusão lógica e impedir remoção física com movimentações |
| Unicidade de nome sem regra de normalização | Duplicidade e erros operacionais | Médio | Definir normalização e validação única na camada de serviço e persistência |
| RNF05 sem volume-alvo | Critério de aceite técnico indefinido | Alto | Estabelecer cenários de carga e metas objetivas para testes |
| Segurança de autenticação subespecificada | Vulnerabilidades de acesso | Médio/Alto | Definir política de senha, tentativas, bloqueio e trilha de login |
| Ausência de requisito de restauração | Recuperação operacional incompleta | Médio | Incluir HU/RF de importação/restauração e procedimento operacional |
| Sem regra explícita para concorrência de operadores | Possível conflito de atualização de saldo | Médio | Definir se uso é mono ou multiusuário e adotar controle de concorrência adequado |
| Regra temporal incompleta (fuso, ajustes manuais) | Rastreabilidade inconsistente | Médio | Definir padrão de data/hora e permissões de edição de lançamento |

### Conclusão do Gap Analysis
A arquitetura proposta cobre integralmente o fluxo principal de negócio e quase todos os requisitos. As principais lacunas são **de especificação** (não de desenho) e devem ser resolvidas antes da fase de implementação final para reduzir retrabalho, risco de inconsistência de dados e ambiguidades de aceite.