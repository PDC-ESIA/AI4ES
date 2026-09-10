# Relatório Técnico de Arquitetura de Software
**Sistema:** Sistema de Controle de Estoque para Loja Física (P03)  
**Emissor:** Sistema Multi-Agente de Design de Software (AI4ES - Time 2)  
**Data:** 24/05/2024  

---

## 1. Identificação das HUs

A tabela a seguir consolida a especificação funcional do sistema a partir das Histórias de Usuário (HUs) fornecidas, explicitando atores, objetivos primários e resumos de critérios de aceite.

| ID | Nome da HU | Ator Primário | Objetivo Core | Resumo dos Critérios de Aceite |
| :--- | :--- | :--- | :--- | :--- |
| **HU01** | Cadastrar Produto | Operador | Cadastrar novos itens informando nome, quantidade inicial e preço de custo. | Campos obrigatórios (nome, quantidade inicial); proibição de nomes duplicados; visibilidade imediata na consulta. |
| **HU02** | Registrar Entrada de Mercadoria | Operador | Incrementar a quantidade em estoque a partir do recebimento de lote. | Seleção por lista ou busca; quantidade como inteiro positivo; atualização imediata do saldo; registro histórico com data/hora. |
| **HU03** | Registrar Saída de Produto | Operador | Dar baixa na quantidade em estoque decorrente de venda. | Impede saída se quantidade > saldo disponível; erro claro; decremento imediato; registro histórico com data/hora/quantidade. |
| **HU04** | Ser Alertado sobre Estoque Baixo | Operador | Notificar visualmente a atingimento ou transposição do limite mínimo. | Destaque visual imediato (cor/ícone); exibe produto e saldo; alerta persiste até o restabelecimento do saldo. |
| **HU05** | Configurar Limite Mínimo de Estoque | Operador | Parametrizar o patamar mínimo de segurança por item. | Limite configurável individualmente; aceita inteiros não negativos; reflexo imediato nos alertas. |
| **HU06** | Consultar Saldo Atual do Estoque | Operador | Obter visão consolidada do inventário atual da loja. | Exibe todos os produtos com nome, saldo e limite mínimo; destaque visual de itens críticos; ordenação por nome ou quantidade. |
| **HU07** | Consultar Histórico de Movimentações | Operador | Auditar o fluxo de entradas e saídas por produto e período. | Filtro por produto e intervalo de datas; detalhes de tipo, quantidade, data, hora e usuário; ordenação decrescente padrão. |
| **HU08** | Exportar Dados de Estoque e Movimentações | Operador | Gerar arquivos tabulares locais para backup ou análise em planilhas. | Geração em formato CSV com todos os campos relevantes; seleção de diretório de destino; confirmação de sucesso. |

---

## 2. Diagramas de Arquitetura (Mermaid)

### 2.1 Visão Geral da Arquitetura de Componentes

O diagrama a seguir representa a topologia lógica em camadas da aplicação desktop autônoma.

```mermaid
graph TD
    subgraph Camada_Apresentacao [Camada de Apresentação (GUI)]
        UI_Auth[Tela de Autenticação]
        UI_Stock[Tela de Consulta e Gestão de Estoque]
        UI_Mov[Tela de Lançamento de Entradas/Saídas]
        UI_Hist[Tela de Histórico e Filtros]
        UI_Export[Módulo de Exportação]
        UI_Alert[Componente de Alertas Visuais]
    end

    subgraph Camada_Aplicacao [Camada de Aplicação e Domínio]
        Svc_Auth[Serviço de Autenticação e Sessão]
        Svc_Product[Serviço de Gestão de Produtos]
        Svc_Stock[Serviço de Movimentação de Estoque]
        Svc_Alert[Serviço de Monitoramento de Alertas]
        Svc_Audit[Serviço de Trilha de Auditoria]
        Svc_Export[Serviço de Exportação de Dados]
    end

    subgraph Camada_Persistencia [Camada de Persistência Local]
        DAL[Mapeador / Data Access Layer]
        DB_Embedded[(Banco de Dados Embarcado Local)]
        FS_Local[Sistema de Arquivos Local]
    end

    UI_Auth --> Svc_Auth
    UI_Stock --> Svc_Product
    UI_Stock --> Svc_Alert
    UI_Mov --> Svc_Stock
    UI_Hist --> Svc_Stock
    UI_Hist --> Svc_Audit
    UI_Export --> Svc_Export

    Svc_Product --> Svc_Alert
    Svc_Stock --> Svc_Alert
    Svc_Stock --> Svc_Audit

    Svc_Auth --> DAL
    Svc_Product --> DAL
    Svc_Stock --> DAL
    Svc_Audit --> DAL
    Svc_Export --> DAL
    Svc_Export --> FS_Local

    DAL --> DB_Embedded
```

### 2.2 Diagrama de Sequência: Registrar Saída de Produto e Monitoramento de Alerta (HU03, HU04, RNF03, RNF06, RNF08)

```mermaid
sequenceDiagram
    autonumber
    actor Operador
    participant UI as InterfaceGrafica
    participant Auth as ServicoAutenticacao
    participant Mov as ServicoMovimentacaoEstoque
    participant Reg as RegrasDeNegocioEstoque
    participant Aud as ServicoAuditoria
    participant Alt as ServicoMonitorAlertas
    participant DB as BancoDadosEmbarcado

    Operador->>UI: Solicita registro de saída (ProdutoID, Quantidade, Data)
    UI->>Auth: Obter Usuário Autenticado da Sessão
    Auth-->>UI: Retorna UsuarioSessao

    UI->>Mov: RegistrarSaida(ProdutoID, Quantidade, Data, UsuarioSessao)
    activate Mov

    Mov->>DB: ConsultarProdutoPorId(ProdutoID)
    DB-->>Mov: Retorna DadosProduto (SaldoAtual, LimiteMinimo)

    Mov->>Reg: ValidarQuantidadeSaida(Quantidade, SaldoAtual)
    alt Quantidade Solicitada > Saldo Atual
        Reg-->>Mov: Erro: Quantidade insuficiente
        Mov-->>UI: Exceção (Estoque Insuficiente)
        UI-->>Operador: Exibe mensagem de erro e bloqueia operação (RF06)
    else Quantidade Válida (<= Saldo Atual)
        Reg-->>Mov: Validação OK
        
        Mov->>DB: Iniciar Transação ACID
        Mov->>DB: Decrementar Saldo (ProdutoID, NovoSaldo)
        Mov->>Aud: RegistrarHistorico(ProdutoID, 'SAIDA', Quantidade, DataHora, UsuarioID)
        Aud->>DB: Inserir RegistroHistórico
        Mov->>DB: Commit Transação (RNF03)

        Mov->>Alt: VerificarStatusEstoque(ProdutoID, NovoSaldo, LimiteMinimo)
        alt NovoSaldo <= LimiteMinimo
            Alt-->>UI: Notificar Alerta Ativo (Produto, NovoSaldo) (RF09/HU04)
        end

        Mov-->>UI: Confirmação de Sucesso
        deactivate Mov
        UI->>UI: Atualizar Visão de Saldo na Tela (RF07/HU06)
        UI-->>Operador: Exibe Confirmação de Lançamento
    end
```

---

## 3. Decisões de Arquitetura

### 3.1 Padrão Arquitetural Desktop Autônomo em Camadas (Layered Monolith Desktop)
* **Justificativa (RNF01, RNF02):** Atendendo à premissa de execução estritamente local em ambiente Windows sem dependência de servidores externos, adotou-se a arquitetura monolítica desktop dividida em três camadas conceituais: Apresentação (UI), Regras de Negócio/Aplicação e Persistência Local.
* **Impacto:** Elimina a complexidade de rede e serviços distribuídos, garantindo baixo tempo de resposta e autonomia operacional total da loja física.

### 3.2 Persistência Embarcada com Garantia ACID
* **Justificativa (RNF02, RNF03):** Para evitar a perda de dados em caso de falha mecânica ou encerramento abrupto da aplicação, o mecanismo de persistência local deve garantir o cumprimento das propriedades ACID (Atomicidade, Consistência, Isolamento e Durabilidade).
* **Impacto:** Lançamentos de estoque e auditoria são executados sob transações explícitas. Se o sistema for fechado durante uma gravação, a transação sofre *rollback* automático, mantendo o estado anterior íntegro.

### 3.3 Mecanismo Centralizado de Sessão e Auditoria
* **Justificativa (RNF06, RNF08):** Todo lançamento de entrada/saída requer rastreabilidade completa (quem, quando, o quê). 
* **Impacto:** O componente de Segurança gerencia a sessão do usuário autenticado e injeta os metadados de auditoria em todos os comandos do `Serviço de Movimentação de Estoque`.

### 3.4 Processamento síncrono para Alertas e Assíncrono para Exportação
* **Justificativa (RNF04, RNF05, RNF07):** A avaliação do limite mínimo de estoque ocorre em tempo real de forma síncrona a cada movimento. A exportação de dados em massa (CSV) é tratada em fluxo secundário/paralelo na interface para evitar o congelamento da tela principal.
* **Impacto:** Garante carregamento das consultas e movimentações dentro do limite prescrito de 2 segundos (RNF05).

---

## 4. Tabela de Componentes e Rastreabilidade

| Componente | Responsabilidade Principal | Comunica-se com | Origem (HU / Critério de Aceite / RNF) |
| :--- | :--- | :--- | :--- |
| **Módulo de Autenticação** | Gerenciar autenticação por usuário/senha e manter o contexto da sessão ativa. | Apresentação (UI), Repositório Local | RNF06 |
| **Gestor de Produtos** | Processar cadastro, alteração, remoção e validação de nomes duplicados. | Interface de Gestão, Repositório Local, Monitor de Alertas | RF01, RF02, RF03, HU01, HU05 |
| **Motor de Movimentação** | Processar entradas e saídas, validar saldos e executar regras de atualização. | Interface de Movimentação, Monitor de Alertas, Trilha de Auditoria, Repositório | RF04, RF05, RF06, RF07, HU02, HU03 |
| **Monitor de Alertas** | Avaliar saldos em relação aos limites mínimos e emitir/manter alertas visuais. | Motor de Movimentação, Gestor de Produtos, Interface Gráfica | RF08, RF09, HU04, HU05 |
| **Motor de Consulta e Histórico** | Recuperar saldos atuais e movimentações históricas com suporte a filtros e ordenação. | Interface de Consulta, Repositório Local | RF10, RF11, RF12, HU06, HU07, RNF05 |
| **Trilha de Auditoria** | Registrar carimbo de data, hora e usuário responsável para cada operação executada. | Motor de Movimentação, Repositório Local | RNF08, HU02, HU03, HU07 |
| **Gerador de Exportação (CSV)** | Formatar e gravar dados de produtos e movimentações no sistema de arquivos local. | Interface de Exportação, Repositório Local, Sistema de Arquivos | RNF07, HU08 |
| **Repositório Local (DAL)** | Abstrair comandos de leitura e escrita transacionais no mecanismo embarcado. | Banco de Dados Embarcado | RNF02, RNF03 |

---

## 5. Bloqueios e Pendências

1. **Gestão de Perfis e Cadastro de Usuários (RNF06 / RNF08):**
   * *Pendência:* Os requisitos especificam a necessidade de autenticação e auditoria por usuário, porém não detalham como os usuários são cadastrados nem se há múltiplos perfis (ex: Administrador vs. Operador).
   * *Impacto:* Impede a implementação de permissões diferenciadas (ex: proibir que operadores editem limites ou apaguem produtos).

2. **Política para Exclusão de Produtos com Histórico (RF03 / RF11):**
   * *Pendência:* O RF03 prevê a remoção de produtos, mas não especifica a regra para produtos que já possuem histórico de movimentação associado.
   * *Impacto:* A remoção física pode quebrar a integridade referencial dos relatórios e do histórico de movimentações (HU07/RNF08).

3. **Concorrência e Múltiplas Instâncias no Mesmo Computador (RNF01 / RNF02):**
   * *Pendência:* Não há definição se duas instâncias da aplicação podem rodar concorrentemente no mesmo sistema operacional compartilhando o mesmo arquivo de banco de dados local.
   * *Impacto:* Risco de travamento do arquivo (*file locking*) na camada de persistência local.

4. **Tratamento de Fuso Horário e Horário de Verão (RNF08 / HU07):**
   * *Pendência:* A especificação menciona registrar "data e hora", mas não padroniza a zona temporal (UTC vs. Hora Local).
   * *Impacto:* Risco de inconsistência na ordenação do histórico em caso de mudanças de horário local.

---

## 6. Cobertura de Requisitos

A matriz abaixo confirma a rastreabilidade integral entre Requisitos Funcionais (RF), Requisitos Não Funcionais (RNF), Histórias de Usuário (HU) e os elementos da arquitetura.

| Requisito / HU | Módulo / Componente Arquitetural | Mecanismo / Estratégia Adotada | Coberta? |
| :--- | :--- | :--- | :---: |
| **RF01 / HU01** | Gestor de Produtos | Validação de obrigatoriedade e restrição de unicidade no repositório local. | **Sim** |
| **RF02** | Gestor de Produtos | Atualização cadastral via camada de persistência. | **Sim** |
| **RF03** | Gestor de Produtos | Exclusão de registro (requer definição de *soft delete*). | **Sim** |
| **RF04 / HU02** | Motor de Movimentação | Soma ao saldo atual e gravação de histórico com carimbo temporal. | **Sim** |
| **RF05 / HU03** | Motor de Movimentação | Subtração de saldo validada por regra de negócio. | **Sim** |
| **RF06 / HU03** | Motor de Movimentação | Trava lógica de validação pré-transacional. | **Sim** |
| **RF07 / HU02 / HU03**| Motor de Movimentação | Atualização síncrona de saldo em bloco transacional. | **Sim** |
| **RF08 / HU05** | Gestor de Produtos | Parametrização do campo `limite_minimo` por item. | **Sim** |
| **RF09 / HU04** | Monitor de Alertas | Avaliação de regra `saldo <= limite_minimo` acionando alerta visual persistentemente. | **Sim** |
| **RF10 / HU06** | Motor de Consulta | Leitura otimizada de saldos com ordenação customizada. | **Sim** |
| **RF11 / HU07** | Motor de Consulta / Auditoria | Filtros combinados de produto e intervalo de datas com ordenação decrescente. | **Sim** |
| **RF12** | Motor de Consulta | Busca por substring no cadastro local. | **Sim** |
| **RNF01** | Aplicação Desktop Windows | Empacotamento para SO target sem dependências de servidores Web. | **Sim** |
| **RNF02** | Repositório Local (DAL) | Uso de mecanismo de banco de dados embarcado local. | **Sim** |
| **RNF03** | Repositório Local (DAL) | Transações ACID (Commit/Rollback) explicitadas em cada movimento. | **Sim** |
| **RNF04** | Interface Gráfica (UI) | Atalhos e fluxos diretos a partir do painel principal (<= 3 cliques). | **Sim** |
| **RNF05** | Motor de Consulta / DAL | Índices em `produto_id`, `data_movimentacao` e `nome` para garantir tempo de resposta < 2s. | **Sim** |
| **RNF06** | Módulo de Autenticação | Tela de login obrigatória na inicialização mantendo sessão ativa. | **Sim** |
| **RNF07 / HU08** | Gerador de Exportação | Formatação tabular e escrita contínua em arquivo `.csv` no diretório escolhido. | **Sim** |
| **RNF08** | Trilha de Auditoria | Injeção de metadados (`usuario_id`, `timestamp`) em todas as movimentações. | **Sim** |

---

## 7. Gap Analysis

### 7.1 Identificação de Lacunas e Impactos Arquiteturais

1. **Lacuna: Remoção Física vs. Exclusão Lógica (*Soft Delete*)**
   * *Impacto:* Se o operador executar a remoção de um produto (RF03) que já possui registros no histórico de movimentações (RF11/HU07), a exclusão física quebrará a integridade referencial da base embarcada ou apagará o histórico das vendas passadas, violando a rastreabilidade (RNF08).
   * *Ação Recomendada:* Implementar o padrão *Soft Delete* (campo `ativo = false`), onde a exclusão apenas oculta o produto para novos lançamentos, mantendo os registros históricos preservados para auditoria e consultas passadas.

2. **Lacuna: Inexistência de Mecanismo Local de Backup e Restauração**
   * *Impacto:* Embora o RNF07 permita exportar arquivos CSV, a exportação CSV não substitui uma cópia de segurança estruturada do banco de dados local. Em caso de falha de hardware no computador da loja, os dados serão perdidos.
   * *Ação Recomendada:* Adicionar um serviço de backup automatizado que copie periodicamente o arquivo de banco de dados embarcado para um diretório seguro configurado pelo operador.

3. **Lacuna: Ajuste/Inventário de Estoque (Correção de Inconsistências)**
   * *Impacto:* Os requisitos contemplam apenas entradas por lote (RF04) e saídas por venda (RF05). Não há previsão funcional para lançamentos de ajuste (ex: perda, avaria, roubo ou recontagem de inventário).
   * *Ação Recomendada:* Estender o tipo de movimentação no `Motor de Movimentação` para aceitar categorias de "Ajuste de Estoque" (Entrada/Saída extraordinária), mantendo a devida justificativa e auditoria.

4. **Lacuna: Bootstrapping e Primeiro Acesso do Sistema**
   * *Impacto:* O RNF06 exige login e senha, mas não define a existência de um usuário padrão inicial (*admin/seed*) para o primeiro uso da aplicação recém-instalada.
   * *Ação Recomendada:* Definir uma rotina de inicialização da base de dados local que cria uma conta administrativa padrão exigindo a troca de senha obrigatoriamente no primeiro acesso.