# Relatório Técnico de Arquitetura de Software

## 1. Identificação das HUs
Lista das histórias de usuário (HU) presentes no escopo e referência rápida:

- HU01 — Cadastrar produto com fotos
- HU02 — Gerenciar estoque dos produtos
- HU03 — Acompanhar e atualizar status dos pedidos recebidos
- HU04 — Visualizar painel financeiro
- HU05 — Solicitar saque do saldo disponível
- HU06 — Responder avaliações de compradores
- HU07 — Navegar e pesquisar produtos
- HU08 — Adicionar itens ao carrinho e finalizar compra
- HU09 — Acompanhar status dos pedidos
- HU10 — Avaliar produto após entrega
- HU11 — Gerenciar categorias da plataforma
- HU12 — Configurar percentual de comissão

Observação: os requisitos funcionais (RF01–RF30) e não funcionais (RNF01–RNF13) foram utilizados para validar e traçar cobertura das HUs abaixo.

---

## 2. Diagramas de Arquitetura (Mermaid)

a) Diagrama de sequência — Fluxo de finalização de compra (checkout) com criação de subpedidos, pagamento e decremento de estoque. Este diagrama evidencia a exigência transacional (RNF08) e notificação dos artesãos (RF19, RF18, HU08).

```mermaid
sequenceDiagram
  autonumber
  participant Cliente as Comprador (UI)
  participant Frontend as Frontend Web/Mobile
  participant API as API Gateway
  participant Auth as Auth Service
  participant Cart as Cart Service
  participant Order as Order Service
  participant Payment as Payment Service
  participant Gateway as Payment Gateway
  participant Stock as Stock/Inventory Service
  participant Suborder as Suborder Service
  participant Financial as Financial Service
  participant Audit as Audit Ledger
  participant Notify as Notification Service
  participant Email as Email Service

  Cliente->>Frontend: Finalizar compra (cart + endereço + método de pagamento)
  Frontend->>API: POST /checkout {cart, paymentMethod, address}
  API->>Auth: validar token/credenciais
  Auth-->>API: OK (usuario autenticado)
  API->>Cart: validar conteúdo do carrinho
  Cart-->>API: itens, quantidades, preço vigente
  API->>Order: criar pedido provisório (status: pendente_pagamento)
  Order-->>API: pedido_id
  API->>Payment: iniciar autorização de pagamento (pedido_id, valor)
  Payment->>Gateway: enviar autorização/compra
  Gateway-->>Payment: resposta (autorizado / negado)
  alt pagamento autorizado
    Payment->>Order: confirmar pagamento (pedido_id, transacao_id)
    Order->>Suborder: gerar subpedidos por artesão (atomicidade lógica)
    Suborder-->>Order: subpedidos criados
    Order->>Stock: requisitar decremento de estoque (itens)
    Stock-->>Order: sucesso / falha por item
    alt todos os decrementos bem-sucedidos
      Order->>Financial: registrar venda e calcular comissão
      Financial-->>Audit: registrar transação financeira imutável
      Order->>Audit: registrar evento "pedido confirmado"
      Order->>Notify: notificar comprador (interno)
      Notify->>Email: enviar e-mail confirmação ao comprador
      Notify->>Email: enviar e-mail para cada artesão (subpedido)
      Notify-->>Order: notificações enfileiradas
      Order->>API: confirmação final (pedido confirmado)
      API-->>Frontend: 200 OK / página confirmação
      Frontend-->>Cliente: mostra confirmação e e-mail enviado
    else falha ao decrementar estoque
      Order->>Payment: solicitar cancelamento/estorno (id_transacao)
      Payment->>Gateway: cancelar/autorização reversal
      Payment-->>Order: cancelamento confirmado
      Order->>Audit: registrar falha e rollback
      Order->>API: informar falha por falta de estoque
      API-->>Frontend: 409 Conflict (item sem estoque)
      Frontend-->>Cliente: mensagem de falha; sem cobrança
    end
  else pagamento negado
    Payment->>Order: marcar pagamento como negado
    Order->>Audit: registrar falha de pagamento
    Order->>API: retorno de falha
    API-->>Frontend: 402 Payment Required / erro
    Frontend-->>Cliente: informa falha; sem alteração de estoque
  end
```

b) Diagrama de componentes — visão lógica de alto nível (serviços e interfaces):

```mermaid
graph LR
  subgraph Plataforma
    UI[Frontend (Web/Mobile)]
    API[API Gateway / BFF]
    Auth[Auth Service]
    Product[Product Catalog Service]
    Image[File Storage (object storage)]
    Search[Search & Index Service]
    Cart[Cart Service]
    Order[Order & Suborder Service]
    Stock[Stock/Inventory Service]
    Payment[Payment Service Integration]
    Financial[Financial & Commission Service]
    Notification[Notification Service]
    Email[Email Delivery Service]
    Audit[Audit Ledger / Append-only Store]
    Admin[Admin Service]
    Analytics[Reporting / Dashboard]
  end

  UI --> API
  API --> Auth
  API --> Product
  API --> Search
  API --> Cart
  API --> Order
  API --> Admin
  Product --> Image
  Product --> Search
  Cart --> Order
  Order --> Payment
  Order --> Stock
  Order --> Subgraph{Suborder Service}
  Order --> Notification
  Order --> Financial
  Financial --> Audit
  Order --> Audit
  Notification --> Email
  Admin --> Product
  Admin --> Financial
  Analytics --> Audit
```

Observações do diagrama:
- Cada componente representa uma responsabilidade bem definida e interface clara.
- File Storage é um serviço desacoplado para fotos (RNF04).
- Audit Ledger é um armazenamento imutável (RNF09) para transações financeiras e eventos críticos (RNF13).

---

## 3. Decisões de Arquitetura

Lista das decisões principais, justificativa e impacto:

1. Arquitetura orientada a serviços (modular, por responsabilidades)
   - Justificativa: separação clara entre domínio de produtos, pedidos, estoque, pagamentos, financeiro e notificações melhora escalabilidade (RNF04, RNF05) e manutenibilidade (RNF13).
   - Impacto: define contrato de APIs internas; requer estratégia de versionamento e monitoramento.

2. Garantia de processamento transacional por composição (SAGA/coordenador lógico)
   - Justificativa: RNF08 exige que pagamentos e decremento de estoque sejam transacionais; em ambiente distribuído, implementar uma saga orquestrada permite garantir consistência eventual com compensações (cancelamentos de pagamento ou restock).
   - Impacto: define padrões de idempotência para endpoints, log de correções e mecanismos de retry; aumenta complexidade de tratamento de falhas.

3. Armazenamento de fotos em serviço de object storage desacoplado
   - Justificativa: RNF04 solicita storage externo para fotos; reduz carga do aplicativo e facilita CDN e redimensionamento.
   - Impacto: fluxo de upload com geração de URLs e processamento assíncrono de imagens (thumbnails); integração com Search e Product Service.

4. Search index específico para busca em tempo real
   - Justificativa: HU07 requer pesquisa parcial e em tempo real; indexar produtos e categorias em serviço de busca permite atender RNF05 (carregamento rápido).
   - Impacto: necessidade de sincronização entre Product Service e Search Service (event-driven updates).

5. Registro imutável para transações financeiras e auditoria
   - Justificativa: RNF09 exige registro imutável; adotado um Audit Ledger append-only, com logs legíveis por componentes financeiros e de compliance.
   - Impacto: define políticas de retenção e exportação para auditorias e conformidade LGPD (RNF11).

6. Notificações assíncronas e envio de e-mail por fila
   - Justificativa: evitar bloqueio síncrono em fluxos críticos (checkout) e garantir entrega (RF18, RF19).
   - Impacto: uso de filas e retries; necessidade de garantia de entrega eventual e observabilidade.

7. Painel financeiro com consultas agregadas e cache
   - Justificativa: RNF06 exige painel em até 3s; combinar consultas pré-aggregadas + cache TTL para evitar latência em relatórios.
   - Impacto: desenhar materialized views ou agregações periódicas; definir validade e mecanismos de invalidação ao ocorrerem vendas ou saques.

8. Controle de acesso por perfis e roles
   - Justificativa: RNF01 e RF01 — validar perfis (administrador, artesão, comprador); um usuário pode ter múltiplos perfis (RF03).
   - Impacto: Auth Service deve suportar atribuição múltipla de roles e autorização por endpoint (RBAC).

9. Não armazenar dados de cartão no sistema
   - Justificativa: RNF03; todas as integrações de cartão via tokenização fornecida pelo gateway.
   - Impacto: Payment Service atua apenas como orquestrador dos tokens; reduzir surface de compliance.

10. Logs estruturados e eventos críticos registrados centralmente
    - Justificativa: RNF13 requer logs de eventos críticos.
    - Impacto: definição de formato de log, rastreabilidade por correlação (request-id).

---

## 4. Tabela de Componentes e Rastreabilidade

| Componente | Responsabilidade Principal | Comunica-se com | Origem (HU / Critério de Aceite) |
|---|---:|---|---|
| Frontend (Web/Mobile) | Interface responsiva para usuários (vendedores, compradores, admins) | API Gateway | RNF07, HU01, HU07, HU08 |
| API Gateway / BFF | Roteamento, autenticação inicial, rate limiting, orquestração de chamadas | Frontend, Auth, Product, Order, Cart, Admin | RNF01, RNF10, HU08 |
| Auth Service | Autenticação, emissão de tokens, gestão de perfis e roles (suporte a múltiplos perfis) | API, User DB | RF01, RF02, RF03, RNF01 |
| Product Catalog Service | CRUD de produtos, publicação/despublicação, metadados e links para imagens | Image Storage, Search, DB | RF04, RF05, RF06, HU01 |
| File Storage (object storage) | Armazenamento de fotos e versões (thumbnails) | Product Catalog, Image Processor | RNF04, HU01 |
| Image Processor (assíncrono) | Processamento de imagens (resize, thumbnails), geração de metadados | File Storage, Product Catalog | HU01, RNF04 |
| Search & Index Service | Indexação para pesquisa por nome, categoria, artesão; busca parcial em tempo real | Product Catalog, API | RF11, HU07, RNF05 |
| Cart Service | Manter carrinho do usuário, cálculos de resumo | API, Product, Order, Stock | RF13, RF14, HU08 |
| Order Service | Criar pedidos/provisórios, transições de status, orquestrar subpedidos | Cart, Payment, Stock, Suborder, Financial, Audit, Notification | RF16, RF18, RF20, RF21, RF22, HU03, HU08, HU09 |
| Suborder Service | Criar e gerenciar subpedidos por artesão | Order, Stock, Notification | RF22, HU09 |
| Stock/Inventory Service | Gerenciar quantidades, bloqueio/commit em checkout, sinalização de estoque zero | Product Catalog, Order | RF07, RF08, RF09, HU02 |
| Payment Service (integração) | Orquestrar autorizações, confirmar/cancelar transações com gateway | Payment Gateway, Order, Financial | RF16, RF17, RNF03, RNF08 |
| Payment Gateway (externo) | Processamento real de pagamentos (fornecedor externo) | Payment Service | RF16, RF17, RNF03 |
| Financial & Commission Service | Calcular comissões, reter valores, registrar histórico e saldo para vendedores | Order, Audit, Admin | RF26, RF27, RF28, HU04, HU05 |
| Payout/Saque Service | Registrar solicitações de saque, expor status e dados bancários para processamento | Financial, Audit | RF30, HU05 |
| Notification Service | Enfileirar e orquestrar notificações internas e e-mails | Order, Suborder, Email | RF18, RF19, RF21, HU03 |
| Email Delivery Service | Entrega de e-mails transacionais | Notification | RF18, RF19 |
| Admin Service | Gerenciar categorias, configurações (ex.: comissão vigente) | Product Catalog, Financial, Audit | RF12, HU11, HU12 |
| Audit Ledger (append-only) | Registro imutável de transações financeiras e eventos críticos | Financial, Order, Admin, Analytics | RNF09, RNF13 |
| Reporting / Analytics | Geração de relatórios, dashboards (painel financeiro do artesão) | Financial, Audit, Order | RNF06, HU04 |
| Reviews & Responses Service | Gerenciar avaliações, média de notas, respostas do artesão | Order, Product, Notification | RF23, RF24, RF25, HU06, HU10 |
| Background Worker / Scheduler | Processos assíncronos: limpeza, agregações, processamento de imagens, reconciliação de pagamentos | Vários | RNF05, RNF06 |

Observação: "Origem" indica HU ou critério de aceite que motivou o componente.

---

## 5. Bloqueios e Pendências

1. Escolha do provedor de gateway de pagamento e definição do fluxo de cobranças (autorização vs captura)
   - Impacto: define latência, garantias de reversão, tokenização e requisitos PCI-DSS.
   - Ação recomendada: selecionar e validar contrato com gateway; definir fluxo de autorização/captura e políticas de retry.

2. Definição da política de periodicidade de liquidação/pagamento aos artesãos (quando a plataforma efetua repasse)
   - Impacto: afeta Financial Service, cálculo de comissões, e o processo de saque (HU05).
   - Ação: decidir periodicidade (diária/seminal/mensal) e regras de retenção.

3. Especificação de regras de comissão por categoria ou excepcionais (além do percentual global)
   - Impacto: complexidade no Financial Service e relatórios.
   - Ação: especificar regimes (por produto, por categoria, promos).

4. Detalhes do processo de saque bancário (integração com instituições financeiras)
   - Impacto: segurança dos dados bancários (LGPD) e requisitos de verificação.
   - Ação: definir fluxo operacional para processar saques e validação KYC.

5. Regras de frete e integração com provedores de envio/confirmacao de entrega
   - Impacto: HU09 e atualização de status "entregue" — atualmente não há especificação de logística.
   - Ação: definir se haverá integração com terceiros para rastreamento e confirmação de entrega.

6. Política de retenção de dados e consentimento LGPD detalhada
   - Impacto: armazenamento de dados pessoais, logs, imagens e dados bancários.
   - Ação: definir prazos de retenção, base legal e mecanismo de anonimização/exclusão.

7. Estimativas de carga e dimensionamento (tráfego, quantidades de produtos, QPS)
   - Impacto: arquitetura de escalabilidade e SLAs (RNF12).
   - Ação: coletar estimativas de negócio para definir escalonamento e capacidades.

8. Regras de disputa, reembolso e chargebacks
   - Impacto: fluxo financeiro (RNF08) e auditoria.
   - Ação: especificar regras operacionais para reembolsos e responsabilidades.

9. Definir mecanismo de confirmação de entrega (quem valida "entregue")
   - Impacto: habilitar RF23 e HU10 (avaliar somente após "entregue").
   - Ação: escolher fontes de verdade (scanner, confirmação manual, webhook do transportador).

10. SLA e garantias para o serviço de Email/Notification
    - Impacto: entrega de confirmações e notificações críticas.
    - Ação: definir SLA e estratégia de retry/backup.

---

## 6. Cobertura de Requisitos

Resumo conciso de como os requisitos foram atendidos pelo design:

- RF01 (Cadastro de usuários perfis): Auth Service com RBAC e suporte a múltiplos perfis (RF03) — mapeado na Tabela de Componentes.
- RF02 (Autenticação/sessão): Auth Service + API Gateway tratam login/logout e tokens.
- RF03 (Usuário com perfis múltiplos): Auth Service permite roles múltiplas; UI exibe switch de contextos.
- RF04–RF06 (Catálogo CRUD, publicar/despublicar, fotos): Product Catalog + File Storage + Image Processor; publicação controla visibilidade.
- RF07–RF09 (Estoque, bloqueio compra, decremento após confirmação): Stock/Inventory Service com bloqueio/commit durante saga; decremento somente após pagamento confirmado; bloqueio de itens com estoque zero.
- RF10–RF11 (Navegação e pesquisa): Product Catalog + Search Service com indexação e busca parcial em tempo real; produtos sem estoque filtrados por padrão (HU07).
- RF12 (Admin categorias): Admin Service expõe CRUD de categorias; remocao com verificação e notificacao a artesãos (HU11).
- RF13–RF15 (Carrinho e resumo): Cart Service + Frontend exibem resumo; API compõe dados.
- RF16–RF19 (Pagamento, integração, confirmações, notificação artesão): Payment Service integra com Payment Gateway (RNF03); Order Service coordena confirmação e Notification Service/Email envia notificações (RF18, RF19).
- RF20–RF21 (Atualizar e acompanhar status): Order & Suborder Services mantêm estados; Notification Service propaga updates ao comprador (HU03, HU09).
- RF22 (Pedidos com múltiplos artesãos): Order Service gera subpedidos e trata status individual por subpedido.
- RF23–RF25 (Avaliações e respostas): Reviews Service guarda avaliações acionadas após status entregue (controle por Order Service); artesão pode responder; resposta única e imutável implementada por regra de negócio (HU06).
- RF26–RF30 (Comissão, painel, saque): Financial Service calcula e retém comissões; Admin pode configurar percentual (HU12); painel financeiro e histórico via Reporting/Analytics; Payout Service registra solicitações de saque (HU04, HU05).
- RNF01–RNF02 (Segurança, hash senhas): Auth Service aplica hashing seguro (design exige algoritmo por implementação) e RBAC.
- RNF03 (Pagamento seguro e PCI-DSS): Design evita armazenar dados de cartão; Payment Service usa tokenização e comunicação HTTPS com gateway.
- RNF04 (Fotos em object storage): File Storage dedicado e desacoplado.
- RNF05–RNF06 (Desempenho das listagens e painel): Search Service e agregações pré-computadas + cache para atender latências solicitadas.
- RNF07 (Usabilidade responsiva): Frontend responsável por UI responsiva (diretriz de projeto).
- RNF08 (Transacionalidade no pagamento): Saga orquestrada com compensações e checagens idempotentes.
- RNF09 (Registro imutável): Audit Ledger registra transações financeiras com metadata (data/hora/valor/partes).
- RNF10 (Compatibilidade navegadores): Frontend deve ser testado nos navegadores mencionados.
- RNF11 (Conformidade LGPD): Mecanismos de consentimento e anonimização previstos; requer políticas detalhadas (pendência).
- RNF12 (Disponibilidade 99,5%): Arquitetura de serviços, redundância e monitoramento previstos; requer dimensionamento e SLAs de infra (pendência).
- RNF13 (Logs de eventos críticos): Audit e logs centralizados cobrem confirmação de pedido, falhas de pagamento, saques e alterações de comissão.

Rastreabilidade (exemplos):
- HU01 -> Product Catalog, File Storage, Image Processor
- HU02 -> Stock/Inventory, Order Service
- HU04 -> Financial, Audit, Reporting
- HU08 -> Cart, Order, Payment, Stock, Notification
- HU12 -> Admin Service, Audit

---

## 7. Gap Analysis

Identificamos lacunas na especificação que impactam a arquitetura, com riscos e recomendações concretas.

1. Fluxo de liquidação e cronograma de repasse aos artesãos
   - Lacuna: Não definido quando e como a plataforma repassa valores (imediato ou periódico).
   - Impacto: afeta cálculo de comissões, disponibilidade de saldo para saque (HU05), responsabilidades financeiras.
   - Recomendação: definir política de liquidação (ex.: repasse semanal com reconciliação) e regras de bloqueio por disputa.

2. Regras de reembolso, chargeback e disputas
   - Lacuna: Não há procedimentos para retornar valores ao comprador.
   - Impacto: complexidade do Financial Service e necessidade de integração com gateway para estornos; impacto legal.
   - Recomendação: especificar cenários de reembolso, responsabilidade sobre devoluções de frete e prazo para disputas.

3. Processos de confirmação de entrega e integração logística
   - Lacuna: Não especificado como o status "entregue" é estabelecido.
   - Impacto: habilitação de avaliações (RF23/RN10) e resolução de disputas.
   - Recomendação: decidir integração com transportadoras ou confirmar via confirmação do comprador; definir eventos fonte de verdade.

4. Detalhamento de dados bancários e compliance LGPD
   - Lacuna: Ainda sem definição de quais dados bancários serão armazenados e por quanto tempo.
   - Impacto: requer controles de acesso, criptografia e política de retenção; obriga revisão legal.
   - Recomendação: especificar dados mínimos, criptografia em repouso e consulta legal para LGPD; definir consentimento claro.

5. Política de taxas e possíveis exceções (promoções, isenções)
   - Lacuna: Comissão global ajustável descrita (HU12), mas sem regras para promoções ou exceções.
   - Impacto: necessidade de flexibilidade no Financial Service para aplicar regras por produto/categoria.
   - Recomendação: definir catálogo de regras de comissão (prioridade: global > categoria > produto).

6. Métricas, SLAs e capacidade esperada
   - Lacuna: ausência de estimativas de carga (número de usuários, pedidos concorrentes).
   - Impacto: impede dimensionamento correto para atender disponibilidade 99,5% (RNF12) e latências RNF05/RNF06.
   - Recomendação: obter estimativas de negocio e planejar teste de carga; definir RTO/RPO.

7. Política de retenção de logs e eventos do Audit Ledger
   - Lacuna: sem definição de períodos de retenção ou requisitos de exportação para auditoria.
   - Impacto: conformidade legal e custo de armazenamento.
   - Recomendação: especificar retenção mínima e processo de exportação seguro para auditorias.

8. Especificação de notificação em tempo real (polling vs websockets vs push)
   - Lacuna: HU03/HU09 pede atualização em tempo real, mas não especifica tecnologia.
   - Impacto: afeta escalabilidade do Notification Service e escolhas tecnológicas.
   - Recomendação: decidir mecanismo (WebSocket/Server-Sent/Push) e dimensionar acordo com simultaneidade.

9. Concurrency control para estoque (concorrência alta em vendas de unidades limitadas)
   - Lacuna: não explícito se usar lock pessimista, otimista ou reservas temporárias.
   - Impacto: risco de oversell; performance trade-offs.
   - Recomendação: definir estratégia (p.ex. reserva no checkout com timeout + confirmação final no pagamento).

10. Detalhes de segurança operacional e testes de penetração
    - Lacuna: política de segurança e testes regulares não definidas.
    - Impacto: compliance e risco de vazamento de dados.
    - Recomendação: agendar avaliação de segurança, definir plano de resposta a incidentes.

11. Tratamento de fotos e direitos autorais
    - Lacuna: regras sobre persistência de imagens após exclusão de produto ou solicitação do artesão.
    - Impacto: requisitos legais e espaço de armazenamento.
    - Recomendação: definir políticas de retenção de mídia e processos de remoção conforme LGPD.

12. Internacionalização / multi-moeda / impostos
    - Lacuna: não há definição sobre suporte a múltiplas moedas ou cálculo de impostos.
    - Impacto: afeta Financial Service e checkout.
    - Recomendação: especificar escopo (local apenas ou multi-país) e regras fiscais necessárias.

Cada lacuna listada acima deve ser tratada como requisito adicional antes da implementação detalhada das partes afetadas (Financial, Payment, Order, Admin). Priorizar por risco e impacto ao negócio.

---

Fim do Relatório.

Observações finais rápidas:
- O design permanece neutro quanto a tecnologias específicas: as decisões descritas são conceituais, e cada componente pode ser implementado com alternativas tecnológicas adequadas ao time.
- Próximos passos operacionais recomendados: workshop de definição de políticas financeiras (liquidação/saque/comissão), seleção do gateway de pagamento, definição de SLAs e estimativas de carga para dimensionamento.