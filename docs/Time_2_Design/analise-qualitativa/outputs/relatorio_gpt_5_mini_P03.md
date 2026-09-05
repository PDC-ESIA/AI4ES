# Relatório Técnico de Arquitetura de Software

## 1. Identificação das HUs
Lista das Histórias de Usuário (HU) com breve resumo e referência aos critérios de aceite:

- HU01 — Cadastrar produto  
  - Campos: nome (obrigatório), quantidade inicial (obrigatório), preço de custo.  
  - Critérios: impedir duplicidade por nome; produto aparece imediatamente na tela de consulta.

- HU02 — Registrar entrada de mercadoria  
  - Seleção do produto via lista/busca; quantidade inteira positiva; atualização imediata do saldo; registro no histórico com data/hora.

- HU03 — Registrar saída de produto  
  - Bloquear saída quando quantidade > saldo; atualização imediata; registrar no histórico com data/hora e usuário.

- HU04 — Ser alertado sobre estoque baixo  
  - Alerta visual destacado quando saldo <= limite mínimo; alerta identifica produto e saldo; persiste até reposição.

- HU05 — Configurar limite mínimo de estoque por produto  
  - Limite inteiro não negativo; alteração refletida imediatamente nos alertas.

- HU06 — Consultar saldo atual do estoque  
  - Tela com lista de produtos (nome, saldo, limite); destaque visual para abaixo do limite; ordenar por nome ou quantidade.

- HU07 — Consultar histórico de movimentações  
  - Filtro por produto e intervalo de datas; registro com tipo, quantidade, data, hora e usuário; ordem cronológica decrescente por padrão.

- HU08 — Exportar dados de estoque e movimentações  
  - Exportação CSV com todos os campos relevantes; escolha do diretório destino; confirmação de sucesso.

Relacionamento direto com os RFs: as HUs cobrem os RF01–RF12 (cadastro, edição, remoção, entradas/saídas, controle de limites, alertas, consulta, pesquisa, histórico e exportação).

---

## 2. Diagramas de Arquitetura (Mermaid)

2.1 Diagrama de sequência: "Registrar saída de produto" (fluxo principal com verificação de estoque e persistência, incluindo auditoria e alerta)
```mermaid
sequenceDiagram
    autonumber
    participant Operador as Operador (UI)
    participant App as Aplicação (Application Layer)
    participant Auth as Serviço de Autenticação
    participant Validador as ValidadorDeEstoque (Domain Service)
    participant Repo as RepositórioProduto (Gateway)
    participant Mov as ServiçoMovimentação (Domain/Application)
    participant DB as PersistênciaLocal (Banco embarcado)
    participant Alerta as GeradorDeAlerta (Notificador/UI)
    participant Log as Auditoria (Registro de operações)

    Operador->>App: Solicita registrar saída (produto, quantidade)
    App->>Auth: Validar credenciais do usuário (token/session)
    Auth-->>App: Usuário validado (id usuário)
    App->>Repo: Ler saldo atual do produto
    Repo->>DB: Consulta produto (id)
    DB-->>Repo: Retorna produto com saldo
    Repo-->>App: Saldo atual
    App->>Validador: Verificar disponibilidade (saldo >= quantidade)
    Validador-->>App: OK / Insuficiente
    alt saldo insuficiente
        App->>Operador: Retornar erro claro (quantidade > saldo)
        Note over Operador,App: operação abortada, nenhum registro persistido
    else saldo suficiente
        App->>Mov: Criar registro de saída (tipo=SAÍDA, qtd, data/hora, usuário)
        Mov->>Repo: Atualizar saldo do produto (decremento)
        Repo->>DB: Transação: inserir movimentação; atualizar saldo
        DB-->>Repo: Confirmação de escrita
        Repo-->>Mov: Confirmação
        Mov->>Log: Registrar auditoria (data/hora, usuário, operação)
        Log-->>Mov: OK
        Mov->>Alerta: Verificar se novo saldo <= limite mínimo
        Alerta-->>App: Indica alerta a ser mostrado (produto, saldo)
        App->>Operador: Confirmação de sucesso + exibir alerta (se houver)
    end
```

2.2 Diagrama de componentes (visão lógica)
```mermaid
graph LR
  UI[Interface Desktop (UI)] 
  Auth[Serviço de Autenticação]
  AppSvc[Serviços de Aplicação]
  Domain[Modelo de Domínio]
  Repo[Repositórios / Gateways]
  Persist[Persistência Local (BD embarcado)]
  CSV[Exportador CSV]
  Alert[Serviço de Alertas / Notificações UI]
  Audit[Serviço de Auditoria / Logs]
  Sync[Gerenciador de Transações / Persistência Confiável]

  UI -->|chama| AppSvc
  UI -->|mostra| Alert
  AppSvc -->|valida| Auth
  AppSvc -->|usa| Domain
  AppSvc -->|persiste| Repo
  Domain -->|opera| Repo
  Repo -->|escreve/ler| Persist
  Repo -->|usa| Sync
  AppSvc -->|exporta| CSV
  AppSvc -->|registra| Audit
  Domain -->|dispara| Alert
```

Legenda: componentes lógicos e suas responsabilidades — todos descrevidos em Seção 4.

---

## 3. Decisões de Arquitetura

1. Separação em Camadas Lógicas (UI / Application / Domain / Infrastructure)  
   - Racional: clareza de responsabilidades, facilita teste e manutenção; apoia RNF07 (manutenibilidade).  
   - Consequência: overhead de coordenação entre camadas; definição clara de interfaces necessária.

2. Repositório + Gateway para Persistência Local (Banco embarcado)  
   - Racional: abstrair acesso ao armazenamento para cumprir RNF02 (persistência local) e permitir troca de mecanismo sem impactar domínio.  
   - Consequência: implementar contratos/contratos de transação para RNF03 (confiabilidade).

3. Garantia de Atomicidade nas Operações de Movimentação (Transação local)  
   - Racional: evitar perda ou inconsistência de lançamentos (RNF03, RNF08). Todas as alterações (inserir movimentação, atualizar saldo, registrar auditoria) devem ser persistidas atomically.  
   - Consequência: implementar mecanismo de transação ou operação idempotente com logs de commit em camada de persistência.

4. Autenticação via Serviço de Autenticação local com sessão/credenciais (sem especificar tecnologia)  
   - Racional: requisito RNF06. Deve ser integrada a logs de auditoria (RNF08).  
   - Consequência: definir políticas de senha, armazenamento seguro e política de sessões (pendência: força mínima de senha não especificada).

5. Notificação/Alerta Reativa em Camada de Aplicação e Persistência de Estado do Alerta  
   - Racional: HU04 pede alerta persistente até reposição. Alerta associado ao estado do produto (saldo <= limite).  
   - Consequência: alerta precisa ser recalculado após cada movimentação e persistido (campo de estado ou verificação dinâmica).

6. Exportação CSV como Operação de Application Layer que lê repositórios e escreve arquivo localmente  
   - Racional: RNF07. Deve permitir escolha de diretório.  
   - Consequência: considerar tratamento de erros I/O e confirmação ao usuário.

7. Performance e Indexação Lógica para Consulta Rápida  
   - Racional: RNF05 exige respostas < 2s mesmo com volume grande. Indexar por nome, por data de movimentação e por produto (conceito, não tecnologia).  
   - Consequência: definir estruturas de dados locais e estratégias de paginação/consulta.

8. Rastreabilidade e Auditoria de Operações  
   - Racional: RNF08 exige data, hora e usuário em todo lançamento. Conservar metadados em cada registro de movimentação e logs de auditoria.  
   - Consequência: impacto no modelo de dados e nos requisitos de sincronização temporal (fuso horário, formato de tempo — pendência).

Alternativas consideradas (breve):
- Arquitetura monolítica vs modular: optar por modular monolito (única aplicação desktop com módulos separados) para simplicidade de implantação local.
- Sincronização / réplica remota: não especificada nos requisitos; opcional futuro.

---

## 4. Tabela de Componentes e Rastreabilidade

| Componente | Responsabilidade Principal | Comunica-se com | Origem (HU / Critério de Aceite) |
|------------|---------------------------|------------------|----------------------------------|
| Interface Desktop (UI) | Fornecer telas de cadastro, consulta, movimentação, alertas e exportação; UX em <= 3 interações para lançamentos | Serviços de Aplicação; Serviço de Alertas; Serviço de Autenticação | HU01, HU02, HU03, HU04, HU06, RNF04 |
| Serviço de Autenticação | Autenticar usuários (usuário/senha), manter sessão local | UI; Serviços de Aplicação; Auditoria | RNF06, RNF08 |
| Serviços de Aplicação (Application Layer) | Coordenar fluxos (cadastro, entrada/saída, busca, exportação), validações de nível de aplicação | UI; Domain; Repositórios; Auth; CSV; Alert | HU01–HU08, RF01–RF12 |
| Modelo de Domínio (Produto, Movimentação, Limite) | Regras de negócio: validação de quantidade, cálculo de saldo, regras de alerta, unicidade por nome | Serviços de Aplicação; Repositórios; ValidadorDeEstoque | HU01–HU07, RF06, RF07, RF08 |
| ValidadorDeEstoque (Domain Service) | Verificar disponibilidade, regras de limites, regras de bloqueio de saída | Serviços de Aplicação; Repositórios | RF06, HU02, HU03 |
| RepositórioProduto / RepositórioMovimentação | CRUD de produtos e movimentações; consultas por nome/período; exposições para export | Persistência Local; Services | RF01–RF05, RF07, RF10, RF11, HU01–HU08 |
| Persistência Local (Banco embarcado) | Armazenamento local durável; garantir escrita segura e recuperação após falha | Repositórios; Gerenciador de Transações | RNF02, RNF03, RNF05, RNF08 |
| Gerenciador de Transações / Persistência Confiável | Garantir atomicidade e durabilidade de operações compostas; mecanismo de flush/commit | Repositórios; Persistência Local | RNF03, RNF08 |
| ServiçoMovimentação (Application/Domain) | Criar/validar registros de entrada/saída e acionar atualizações de saldo e auditoria | RepositórioMovimentação; Audit; Alert | HU02, HU03, RF04, RF05, RNF08 |
| Serviço de Alertas / Notificador | Determinar e apresentar alertas persistentes quando saldo <= limite; persistir estado de alerta | UI; Repositórios; ServiçoMovimentação | HU04, HU05, RF08, RF09 |
| Exportador CSV | Gerar arquivos CSV para estoque e movimentações; permitir escolha de diretório | Serviços de Aplicação; Repositórios; UI | HU08, RNF07 |
| Serviço de Auditoria/Log | Registrar data/hora/usuário de cada lançamento e eventos importantes | Serviços de Aplicação; Persistência Local | RNF08, HU02, HU03 |
| Índices / Cache de Consulta (opcional) | Suportar consultas rápidas para UI (ordenar, pesquisar) | Repositórios; Persistência Local | RNF05, HU06, HU12 (pesquisa) |

Observação: "Origem" referencia HU ou Critério de Aceite específicos que motivam o componente.

---

## 5. Bloqueios e Pendências

1. Política de autenticação não especificada (força de senha, bloqueio por tentativas, recuperação). Impacto: implementação do Serviço de Autenticação e requisitos de segurança. Ação recomendada: definir política mínima de credenciais e requisitos de armazenamento seguro.

2. Especificação de volume e "grande volume" indefinida (RNF05). Impacto: dimensionamento de estruturas de dados, índices e estratégias de paginação. Ação: obter estimativas (nº de produtos, movimentações/ano) para otimização e testes de desempenho.

3. Requisitos de sincronia/backup remoto ausentes. RNF02 exige armazenamento local, mas RNF07 pede export CSV. Impacto: estratégia de recuperação de desastre não totalmente definida (apenas export). Ação: definir política de backup automático/local e/ou opção de exportação agendada.

4. Comportamento de unicidade por nome: caso-sensível? espaços/normalização? Impacto: regras de negócio e UI (prevent duplicates). Ação: definir norma de comparação (ex.: normalizar caixa e espaços).

5. Definição de fuso horário e formato de data/hora (RNF08). Impacto: consistência nos registros de auditoria e exibição no histórico. Ação: definir política (usar timezone local do sistema) e padrão de formatação.

6. Comportamento de remoção de produto (RF03): remover fisicamente ou marca como inativo? Impacto: histórico e integridade referencial de movimentações. Ação: preferir marcação como inativo para manter histórico; confirmar decisão.

7. Critérios visuais e acessibilidade para alertas (HU04 / RNF04) precisam de design UX. Impacto: definição de UI/UX. Ação: criar especificações de design interativas.

8. Garantia de que "nenhum lançamento seja perdido em caso de fechamento inesperado" (RNF03) requer detalhes do mecanismo de flush/commit e teste de falha. Ação: definir política de flushing síncrono ou log de transação e testar com cenários de crash.

9. Perfis de usuário: apenas "Operador" foi descrito; falta distinção de papéis (admin, gerente). Impacto: autorização e gestão de usuários. Ação: clarificar papéis e permissões.

---

## 6. Cobertura de Requisitos

6.1 Mapeamento principal RF / RNF → Componentes / HUs

| Requisito | Coberto por (Componentes / HU) | Observações |
|-----------|-------------------------------|-------------|
| RF01 (Cadastrar produto) | UI; Serviços de Aplicação; RepositórioProduto; Modelo de Domínio (HU01) | Valida obrigatoriedade, unicidade por nome |
| RF02 (Editar produto) | UI; Serviços de Aplicação; RepositórioProduto; Modelo de Domínio | Mesmas validações de unicidade e atualização imediata |
| RF03 (Remover produto) | UI; Serviços de Aplicação; RepositórioProduto | Recomenda marcar inativo (pendência) |
| RF04 (Registrar entrada) | UI; ServiçoMovimentação; Repositório; Persistência; Auditoria (HU02) | Atualização imediata do saldo e registro no histórico |
| RF05 (Registrar saída) | UI; ServiçoMovimentação; ValidadorDeEstoque; Repositório; Persistência; Auditoria (HU03) | Bloqueio quando qtd > saldo |
| RF06 (Impedir saída > saldo) | ValidadorDeEstoque; Serviços de Aplicação; UI | Mensagem de erro clara |
| RF07 (Atualizar saldo automaticamente) | RepositórioProduto; ServiçoMovimentação; Persistência | Operação atômica com transação |
| RF08 (Configurar limite mínimo) | UI; RepositórioProduto; Modelo de Domínio (HU05) | Campo inteiro não negativo |
| RF09 (Emitir alerta quando saldo <= limite) | Serviço de Alertas; UI; ServiçoMovimentação (HU04) | Alerta persistente até reposição |
| RF10 (Exibir saldo atual de todos os produtos) | UI; RepositórioProduto; Índices/Cache (HU06) | Ordenação por nome/quantidade |
| RF11 (Consultar histórico por produto/periodo) | UI; RepositórioMovimentação; ServiçoMovimentação (HU07) | Filtros e ordenação decrescente |
| RF12 (Pesquisar por nome) | UI; RepositórioProduto; Índices/Cache (HU01, HU06) | Busca por nome com normalização |

| RNF01 (Portabilidade Windows) | UI (desktop) | UI deve ser implementada como aplicação desktop compatível com Windows |
| RNF02 (Persistência local) | Persistência Local; Repositórios | Banco embarcado local (abstraído) |
| RNF03 (Confiabilidade — não perder lançamentos) | Gerenciador de Transações; Persistência; Auditoria | Implementar flush/commit e logs de transação |
| RNF04 (Usabilidade — 3 interações) | UI; Serviços de Aplicação | Fluxos otimizados para entrada/saída |
| RNF05 (Desempenho <2s) | Repositórios; Índices/Cache; Persistência | Requer dimensionamento e testes |
| RNF06 (Segurança — autenticação) | Serviço de Autenticação; Auditoria | Login por usuário/senha |
| RNF07 (Exportar CSV) | Exportador CSV; UI; Repositórios (HU08) | Escolha de diretório e confirmação |
| RNF08 (Rastreabilidade) | Auditoria; Movimentação; Serviços de Aplicação | Data/hora/usuário em cada registro |

6.2 Observações de cobertura
- Todas as HUs/RFs listados possuem componentes designados.  
- RNF03 e RNF05 exigem validações adicionais (testes de falha e de carga) para garantir requisitos — listados como pendências.

---

## 7. Gap Analysis

7.1 Gaps identificados (especificação ausente ou ambígua)
- G1: Detalhes de Autorização/Roles (apenas "Operador" descrito).  
  - Impacto: definição de quem pode cadastrar/editar/remover/exportar e como auditar.  
  - Recomendação: definir perfis mínimos (Operador, Administrador) e permissões.

- G2: Política de unicidade de nome (normalização, sensibilidade a maiúsculas, espaços, caracteres especiais não definida).  
  - Impacto: risco de duplicidade ou rejeição inconsistente.  
  - Recomendação: especificar regras de normalização e validação (ex.: trimming, lowercasing, caracteres permitidos).

- G3: Comportamento de remoção de produto (delete físico vs inativar).  
  - Impacto: perda de histórico e integridade referencial.  
  - Recomendação: optar por inativação com flag "ativo/inativo" e permitir reativação, mantendo movimentações.

- G4: Definição de fuso horário e formato de data/hora nos registros (RNF08).  
  - Impacto: inconsistências em auditoria e filtros por período.  
  - Recomendação: padronizar em timezone local do sistema e armazenamento em timestamp unificado; especificar formato de exibição.

- G5: Critério de "grande volume" para RNF05 não quantificado.  
  - Impacto: difícil dimensionar índices, cache e limites de memória.  
  - Recomendação: obter estimativas (nº produtos, movimentações/ano) e realizar testes de carga.

- G6: Mecanismo exato para garantir que "nenhum lançamento seja perdido" em crash (RNF03).  
  - Impacto: escolhas técnicas/arquiteturais (flush síncrono, log de transação).  
  - Recomendação: definir estratégia (ex.: transação ACID local, write-ahead log) e incluir testes de falha.

- G7: Requisitos de backup/recuperação além do CSV export (automático, agendado, manual).  
  - Impacto: recuperação e continuidade do serviço.  
  - Recomendação: especificar política de backup local e procedimentos de restauração.

- G8: Requisitos de usabilidade/UX detalhados (ex.: ícone de alerta, cor, persistência visual).  
  - Impacto: implementação inconsistente da HU04.  
  - Recomendação: criar telas e protótipos de interação e validar com usuários.

7.2 Impactos arquiteturais e priorização
- Prioridade alta: G1 (perfis/autorizações), G6 (garantia contra perda), G2 (unicidade). Sem essas decisões, segurança e integridade ficam incompletas.  
- Prioridade média: G3 (remoção/inativação), G4 (timezone), G7 (backup).  
- Prioridade baixa: G5 (estimativas de volume) – necessário para otimização, porém funcionalidade básica pode ser implementada antes com testes.

7.3 Ações recomendadas para desenvolvimento
1. Sessão de esclarecimento com stakeholders para definir perfis de usuário, política de unicidade, política de remoção e formato de data/hora. (Curto prazo)  
2. Definir e implementar mecanismo de persistência confiável: transação local ou log de alterações; criar testes de crash e recovery. (Curto → Médio prazo)  
3. Coletar métricas de volume esperado e criar planos de testes de carga; otimizar índices/consultas conforme resultado. (Médio prazo)  
4. Produzir protótipos de UI focados em fluxo de entrada/saída (garantir RNF04) e em visualização de alertas (HU04). (Curto prazo)  
5. Definir política de backup (manual e/ou agendado) e integrar com Exportador CSV como opção de emergência. (Médio prazo)

---

Fim do Relatório.