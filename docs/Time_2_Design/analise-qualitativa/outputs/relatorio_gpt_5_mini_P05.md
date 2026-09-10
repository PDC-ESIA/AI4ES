# Relatório Técnico de Arquitetura de Software

## 1. Identificação das HUs
Lista das Histórias de Usuário e HUs relacionadas aos requisitos fornecidos:
- HU01 — Cadastrar quadra (RF01, RF02, HU01 critérios)
- HU02 — Bloquear horários para manutenção (RF03)
- HU03 — Visualizar agenda consolidada (RF11)
- HU04 — Cancelar reserva com justificativa (RF09, RF10)
- HU05 — Consultar disponibilidade sem cadastro (RF04)
- HU06 — Realizar reserva (RF05, RF06, RF07, RF10)
- HU07 — Cancelar minha reserva (RF08)

Relacionamento técnico rápido:
- Operador: HU01, HU02, HU03, HU04 — interfaces administrativas autenticadas.
- Cliente (anon/sem-login): HU05, HU06, HU07 — fluxo público para consultar/realizar/cancelar reservas com código.

---

## 2. Diagramas de Arquitetura (Mermaid)

2.1 Diagrama de sequência: fluxo de "Realizar reserva" (inclui verificação de disponibilidade, criação atômica e notificação por e-mail)

```mermaid
sequenceDiagram
autonumber
participant Cliente
participant Frontend
participant API
participant AvailabilityService as "Serviço de Disponibilidade"
participant ReservationService as "Serviço de Reservas"
participant ReservationStore as "Armazenamento de Reservas"
participant NotificationService as "Serviço de Notificações (e-mail)"

Cliente->>Frontend: Seleciona quadra, data e horário; envia dados (nome, e-mail, telefone)
Frontend->>API: POST /reservas/check-and-create {courtId, slot, clientInfo}
API->>AvailabilityService: Verificar disponibilidade (courtId, slot)
AvailabilityService-->>API: Disponível / Indisponível
alt Disponível
    API->>ReservationService: Solicitar criação de reserva (inclui retry-idempotency)
    ReservationService->>ReservationStore: Tentar inserir reserva (operacao transacional / lock)
    ReservationStore-->>ReservationService: Confirmação persistida com reservationCode
    ReservationService->>NotificationService: Enviar confirmação por e-mail (reservation details)
    NotificationService-->>ReservationService: Envio aceito/rejeitado
    ReservationService-->>API: Reserva criada (reservationCode)
    API-->>Frontend: 201 Created + reservationCode
    Frontend-->>Cliente: Exibir código de confirmação e mensagem
else Indisponível
    API-->>Frontend: 409 Conflict (horário já ocupado)
    Frontend-->>Cliente: Exibir erro; solicitar novo horário
end
```

2.2 Diagrama de componentes (visão lógica dos subsistemas)

```mermaid
graph LR
  subgraph UI
    WebClient[Cliente - Web Público]
    AdminUI[Operador - Interface Administrativa (autenticada)]
  end

  subgraph API_Layer
    APIGateway[API / Orquestração]
  end

  subgraph Services
    CourtService[Serviço de Cadastro de Quadras]
    AvailabilityService[Serviço de Disponibilidade]
    PricingService[Serviço de Tarifação por Faixa]
    ReservationService[Serviço de Reservas (coordenação de transações)]
    NotificationService[Serviço de Notificações (e-mail)]
    AuthService[Serviço de Autenticação e Autorização]
    AuditService[Serviço de Auditoria / Logs de Ações do Operador]
  end

  subgraph Persistence
    CourtStore[(Catálogo de Quadras)]
    ReservationStore[(Armazenamento de Reservas)]
    BlockStore[(Bloqueios/Manutenção)]
    PricingStore[(Regras de Preço por Faixa)]
  end

  WebClient -->|REST/HTTP| APIGateway
  AdminUI -->|REST/HTTP + Auth| APIGateway
  APIGateway --> AuthService
  APIGateway --> CourtService
  APIGateway --> AvailabilityService
  APIGateway --> ReservationService
  APIGateway --> NotificationService
  APIGateway --> PricingService
  CourtService --> CourtStore
  AvailabilityService --> ReservationStore
  AvailabilityService --> BlockStore
  PricingService --> PricingStore
  ReservationService --> ReservationStore
  ReservationService --> NotificationService
  ReservationService --> AuditService
  AdminUI --> AuditService
```

---

## 3. Decisões de Arquitetura

1. Arquitetura em camadas e modular:
   - Separação clara: UI (pública / admin), API/orquestração, serviços de domínio (Quadras, Disponibilidade, Tarifação, Reservas, Notificações), persistência e serviços transversais (Autenticação, Auditoria).
   - Motivo: manutenibilidade (RNF07), facilidade para inclusão de novas modalidades e tarifas.

2. Contratos e interfaces:
   - Serviços comunicam-se por APIs REST internas (interface conceitual), com contratos bem documentados (endpoints: /quadras, /disponibilidade, /reservas, /bloqueios, /precos).
   - Mensagens para notificação são assíncronas (enfileiramento conceitual) quando o envio de e-mail não deve bloquear resposta ao cliente.

3. Consistência e atomicidade (RNF05):
   - Reserva deve ser atômica: o Serviço de Reservas coordena verificação final de disponibilidade e escrita transacional no armazenamento de reservas.
   - Estratégia recomendada (conceitual): garantir unicidade por slot (constraint lógico no modelo de dados) + transação local ou mecanismo de lock por slot. Em cenários de concorrência alta, oferecer tentativa com backoff e resposta idempotente ao cliente (retry-idempotency token).

4. Conflito de concorrência e prevenção de duplo agendamento (RF07, HU06):
   - Implementar verificação final e gravação única por slot com detecção de conflito retornando 409.
   - Uso de token de idempotência para evitar duplicação por reenvio de formulário.

5. Disponibilidade e performance (RNF02, RNF04):
   - Serviços stateless na camada de API/serviços para facilitar escalonamento horizontal.
   - Cache de disponibilidade por quadra/dia com invalidação rápida após criação/cancelamento de reserva/ bloqueio (para atender carregamento do calendário em <=2s). Cache com TTL curto e atualização sob escrita.

6. Notificações (RF10, HU04):
   - Envio assíncrono de e-mail com tentativa/retentativa e fallback. Confirmação ao cliente exibida na UI após persistência; e-mail enviado em segundo plano, com retentativas e registro de falha.

7. Autenticação e autorização administrativa (RNF03):
   - Área administrativa protegida por um Serviço de Autenticação/Autorização. Operações administrativas (cadastrar quadra, bloquear horários, cancelar reserva com justificativa) requerem checagem de privilégios.

8. Auditoria e rastreabilidade:
   - Todas as operações do operador e cancelamentos devem ser auditadas com timestamp, userId e motivo (HU04). Útil para conformidade e troubleshooting.

9. Modelagem de tempo e regras de negócio:
   - Definir claramente slots (granularidade — ex: hora cheia, meia hora), fuso horário do local e regras de duração mínima/múltiplos de hora (não especificado nos requisitos → pendência).
   - Bloqueios temporários aplicam-se sobre slots; remoção de bloqueio deve refletir imediatamente.

10. Esquema de preços por faixa (RF12):
    - Serviço de Tarifação que calcula preço por slot conforme faixas definidas, consultado no momento da visualização e confirmação.

11. Disponibilidade do sistema:
    - Monitoramento e health checks para serviços; estratégia de recuperação e redundância para atingir meta de 99% (RNF04). Planos de backup/restauração para dados críticos.

12. Privacidade e retenção de dados:
    - Minimizar dados coletados do cliente (nome, e-mail, telefone), definir políticas de retenção e segurança de dados (não fornecido nos requisitos → pendência).

13. Interfaces públicas sem cadastro (HU05):
    - Endpoints públicos para consulta de disponibilidade, sem necessidade de autenticação. Rate limiting para evitar scraping e ataques.

14. Internacionalização e compatibilidade de navegadores (RNF06, RNF01):
    - Frontend responsivo; API retornando formatos padronizados (JSON) e suporte a padrões de data/hora.

15. Observabilidade:
    - Logs estruturados, métricas de latência e taxa de erros, rastreamento distribuído conceitual para investigação de falhas.

---

## 4. Tabela de Componentes e Rastreabilidade

| Componente | Responsabilidade Principal | Comunica-se com | Origem (HU / Critério de Aceite) |
|------------|---------------------------|-----------------|----------------------------------|
| Web Client (Público) | UI pública responsiva para consultar disponibilidade e realizar/cancelar reservas | API Gateway | HU05, HU06, HU07; RNF01 |
| Admin UI (Operador) | UI autenticada para cadastrar/editar/ bloquear quadras, visualizar agenda e cancelar reservas | API Gateway, AuthService | HU01, HU02, HU03, HU04; RNF03 |
| API Gateway / Orquestrador | Endpoint unificado, roteamento, validações de entrada e aplicação de rate-limits | Todos os serviços | Todos os RFs/HUs |
| AuthService | Autenticação e autorização da área administrativa, gestão de sessões/credenciais | API Gateway, Admin UI | RNF03; Operador HUs |
| CourtService (Cadastro de Quadras) | CRUD de quadras: nome, tipo, horário de funcionamento, valor base | CourtStore, PricingService, APIGateway | RF01, RF02; HU01 |
| CourtStore (persistência de quadras) | Armazenamento do catálogo de quadras e horários padrões | CourtService | RF01, RF02 |
| AvailabilityService | Computar disponibilidade por quadra/data, aplicar bloqueios e reservas | ReservationStore, BlockStore, CourtStore, PricingService | RF03, RF04, HU02, HU05 |
| ReservationService | Orquestra criação/cancelamento de reservas, garantia de atomicidade e geração de código | ReservationStore, NotificationService, AuditService, AvailabilityService | RF05, RF06, RF07, RF08, HU06, HU07 |
| ReservationStore | Persistência de reservas com constraints por slot e índices | ReservationService, AvailabilityService | RF05, RF06, RF07 |
| BlockStore | Persistência de bloqueios/feriados/manutenção | AvailabilityService, Admin UI | RF03, HU02 |
| PricingService | Regras de tarifação por faixa horária; calcula preço por slot | CourtService, AvailabilityService | RF12 |
| NotificationService (E-mail) | Enviar confirmação/cancelamento por e-mail; retries e logs de entrega | ReservationService, Admin UI | RF10, HU04, HU06 |
| AuditService | Registrar ações administrativas e motivos de cancelamentos | ReservationService, Admin UI | HU03, HU04 |
| Cache Layer (conceitual) | Cache de disponibilidade/agenda para performance | AvailabilityService, Web Client | RNF02 |
| Monitoring & Health | Métricas, alertas, health checks para SLAs | Todos os serviços | RNF04 |

Observação: os nomes acima são conceituais — representam responsabilidades e interfaces, não tecnologias específicas (conforme Diretriz de Neutralidade Tecnológica).

---

## 5. Bloqueios e Pendências

1. Autenticação administrativa: método, provedor e políticas (complexidade de senha, MFA) não especificados — pendência crítica (RNF03).
2. Granularidade dos slots e regras de reserva (ex.: duração mínima, múltiplos de 1h, reserva parcial) não especificadas — impacto direto em AvailabilityService e modelagem de dados.
3. Políticas de cancelamento (prazos, penalidades, reembolso) não definidas — afeta UX e lógica de negócios.
4. Fornecedor/estratégia de envio de e-mail (requisitos de entrega, SPAM, reputação) não definidos — pendência operacional para NotificationService.
5. Retenção e proteção de dados pessoais (períodos, consentimento, requisitos legais) não descritos — pendência de conformidade.
6. Métricas/SLIs detalhadas para 99% de disponibilidade (janela de medição, RTO/RPO) não fornecidas — necessário para detalhar estratégia de alta disponibilidade.
7. Requisitos de carga/concurrency esperada (número de reservas por minuto) não fornecidos — influência nas decisões de dimensionamento e caching.
8. Comportamento nos casos de e-mail com falha de entrega (deve impedir confirmação?) não definido — política de notificação necessária.
9. Integração com calendário externo ou exportação (não mencionada) — confirmar se necessária.

---

## 6. Cobertura de Requisitos

Apresenta-se o mapeamento dos Requisitos Funcionais e Não-Funcionais para os componentes e notas de cobertura.

Tabela resumida (ID | Cobertura | Componentes envolvidos | Observações):

- RF01 — Cadastrar quadras
  - Cobertura: Completa
  - Componentes: Admin UI, CourtService, CourtStore, API Gateway
  - Observação: Critérios de aceite (nome, tipo, valor obrigatórios) tratados na validação da API e UI.

- RF02 — Editar/remover quadra
  - Cobertura: Completa
  - Componentes: Admin UI, CourtService, CourtStore, AvailabilityService (invalidação cache)
  - Observação: Remoção deve checar reservas existentes (regra a definir: impedir remoção com reservas? — pendência).

- RF03 — Bloquear horários específicos
  - Cobertura: Completa (funcional)
  - Componentes: Admin UI, BlockStore, AvailabilityService
  - Observação: Bloqueios refletem imediatamente na disponibilidade e na cache.

- RF04 — Exibir disponibilidade sem login
  - Cobertura: Completa
  - Componentes: Web Client, API Gateway, AvailabilityService, Cache Layer
  - Observação: Sistema público; aplicar rate-limits. RNF02 atende via cache.

- RF05 — Realizar reserva (dados de cliente)
  - Cobertura: Completa
  - Componentes: Web Client, API Gateway, ReservationService, ReservationStore, AvailabilityService, PricingService
  - Observação: Validação final de disponibilidade antes de persistir (RNF05).

- RF06 — Gerar código de confirmação único
  - Cobertura: Completa
  - Componentes: ReservationService, ReservationStore, NotificationService
  - Observação: Código retornado ao usuário e enviado por e-mail.

- RF07 — Impedir reserva duplicada
  - Cobertura: Completa (arquitetural)
  - Componentes: ReservationService, ReservationStore
  - Observação: Garantir unicidade no armazenamento + transação/lock.

- RF08 — Cliente cancelar reserva por código
  - Cobertura: Completa
  - Componentes: Web Client, API Gateway, ReservationService, ReservationStore, NotificationService
  - Observação: Validação de código obrigatório; imediata disponibilidade do slot após cancelamento.

- RF09 — Operador cancelar reserva com motivo
  - Cobertura: Completa
  - Componentes: Admin UI, ReservationService, ReservationStore, AuditService, NotificationService
  - Observação: Motivo obrigatório (critério de aceite).

- RF10 — Enviar confirmação por e-mail
  - Cobertura: Parcialmente completa (arquitetural prevista)
  - Componentes: NotificationService, ReservationService
  - Observação: Estratégia de envio assíncrona e retries definida; escolha de provedor de e-mail pendente.

- RF11 — Visualizar agenda diária consolidada
  - Cobertura: Completa
  - Componentes: Admin UI, AvailabilityService, ReservationStore, Cache Layer
  - Observação: Navegação por datas e exibição de status por quadra.

- RF12 — Configurar valores diferenciados por faixa horária
  - Cobertura: Completa
  - Componentes: Admin UI, PricingService, PricingStore, CourtService
  - Observação: Precisa de UI de configuração de faixas e de aplicação na confirmação do preço.

Não-funcionais (selecionados):

- RNF01 (Usabilidade/responsividade)
  - Cobertura: Planejado
  - Componentes: Web Client, Admin UI
  - Observação: Frontend deve ser responsivo; design e testes necessários.

- RNF02 (Desempenho: calendário <= 2s)
  - Cobertura: Planejado
  - Componentes: AvailabilityService, Cache Layer, API Gateway
  - Observação: Cache e pré-computação por dia recomendadas; requisitos de carga pendentes.

- RNF03 (Segurança: autenticação admin)
  - Cobertura: Planejado/Parcial
  - Componentes: AuthService, Admin UI
  - Observação: Mecanismo de autenticação a definir (pendência).

- RNF04 (Disponibilidade 99%)
  - Cobertura: Planejado
  - Componentes: Todos (monitoring, redundância)
  - Observação: Definir SLIs, estratégias de failover e backups.

- RNF05 (Confiabilidade/Atomicidade)
  - Cobertura: Completa (conceitual)
  - Componentes: ReservationService, ReservationStore
  - Observação: Transações locais/locks e constraints de unicidade recomendados.

- RNF06 (Compatibilidade navegadores)
  - Cobertura: Planejado
  - Componentes: Web Client
  - Observação: Testes cross-browser necessários.

- RNF07 (Manutenibilidade/modularidade)
  - Cobertura: Completa (arquitetural)
  - Componentes: Serviços separados por domínio (Court, Availability, Reservation, Pricing)
  - Observação: Facilita inclusão de novas modalidades.

---

## 7. Gap Analysis

Identificamos lacunas na especificação que afetam design e implementação. Para cada lacuna: descrição, impacto arquitetural e ação recomendada.

1. Granularidade de slots e regras de reserva
   - Impacto: Modelagem de dados (chave de unicidade), UX (seleção de horários), lógica de tarifação.
   - Recomendação: Definir se slots são em unidades de 60/30/15 minutos, políticas de duração mínima e ocupação parcial. Priorizar definição antes de implementar ReservationStore e AvailabilityService.

2. Políticas de cancelamento e prazos
   - Impacto: Fluxos de negócio, reabertura de slots, possíveis regras de reembolso (se houver cobrança futura).
   - Recomendação: Documentar regras (cancelamento gratuito até X horas, reembolso ou não). Implementar flags e workflow de cancelamento.

3. Autenticação administrativa (MFA, roles)
   - Impacto: Segurança e conformidade; determina integração do AuthService.
   - Recomendação: Definir requisitos de autenticação (senha+MFA, provisionamento de usuários) e autorizações (roles: admin, gerente, operador).

4. Estratégia de envio de e-mail e garantia de entrega
   - Impacto: Notificações confiáveis (RF10, HU04); políticas de retry e fila.
   - Recomendação: Selecionar e integrar provedor de entrega e definir SLAs de entrega. Implementar logs de entrega e fallback manual.

5. Requisitos de carga (quantidade esperada de usuários/reservas)
   - Impacto: Dimensionamento, estratégia de cache, escalabilidade.
   - Recomendação: Obter estimativas de pico para dimensionamento e testes de performance (incl. requisito do calendário 2s).

6. Requisitos legais e retenção de dados pessoais
   - Impacto: Segurança, backup, políticas de purge e consentimento.
   - Recomendação: Definir política de retenção de dados de clientes, requisitos de conformidade local e mecanismos de descarte seguro.

7. Backup/recuperação e definição de RTO/RPO
   - Impacto: Estratégia para atingir 99% de disponibilidade e recuperação após falhas.
   - Recomendação: Definir RTO/RPO aceitáveis e planejar backups periódicos e testes de restauração.

8. Comportamento em falha de envio de e-mail
   - Impacto: Se confirmação por e-mail for mandatória antes de considerar reserva como confirmada, fluxo muda.
   - Recomendação: Especificar se confirmação exibida no UI é suficiente; e-mail é notificativo (preferível).

9. Integrações futuras (pagamentos, calendários externos)
   - Impacto: Propiciar extensibilidade e definirá contratos de serviço.
   - Recomendação: Antecipar pontos de extensão na API e modularizar NotificationService/ReservationService para permitir plugins.

10. Definição de métricas e alertas para 99% uptime
    - Impacto: Implementação de observabilidade.
    - Recomendação: Definir SLIs (latência, erro 5xx, disponibilidade da API) e configurar alertas.

Ações recomendadas imediatas:
- Sprint de alinhamento com stakeholders para fechar pendências críticas: slots, autenticação, política de cancelamento, volume esperado.
- Definição de contrato de e-mail e política de retenção de dados.
- Prova de conceito (PoC) para lógica de concorrência (testes de criação simultânea de reservas) e validação de estratégia de cache para garantir RNF02.

---

Fim do Relatório.