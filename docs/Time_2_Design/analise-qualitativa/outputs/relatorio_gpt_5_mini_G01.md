# Relatório Técnico de Arquitetura de Software

## 1. Identificação das HUs
Lista das Histórias de Usuário tratadas como entradas primárias para a arquitetura (conforme especificado):

- HU01 — Abrir conta PF com validação de identidade
- HU02 — Autenticar com múltiplos fatores (MFA)
- HU03 — Realizar transferência via Pix
- HU04 — Pagar boleto com agendamento
- HU05 — Gerenciar cartão de crédito
- HU06 — Contestar transação não reconhecida
- HU07 — Investir em renda fixa
- HU08 — Gerenciar consentimentos do open finance
- HU09 — Receber alertas e responder a suspeita de fraude
- HU10 — Abrir conta PJ com documentação societária
- HU11 — Realizar TED para fornecedores (PJ)
- HU12 — Gerente: acompanhar carteira
- HU13 — Gerente: abrir solicitação de serviço em nome do cliente

As HUs acima direcionam os componentes, fluxos e políticas descritas nas seções seguintes.

## 2. Diagramas de Arquitetura (Mermaid)

1) Diagrama de sequência: fluxo “Usuário realiza transferência Pix via mobile” (inclui autenticação MFA, verificação de risco, lançamento contábil e notificação). O diagrama descreve decisões síncronas e assíncronas relevantes para a jornada.

```mermaid
sequenceDiagram
  autonumber
  participant MobileApp as Mobile App (User)
  participant APIGW as API Gateway
  participant Auth as Auth Service
  participant Session as Session Manager
  participant Identity as Identity/KYC Service
  participant Account as Account Service
  participant Limits as Limits & Policy Service
  participant Fraud as Fraud Detection Service
  participant Ledger as Ledger / Transaction Service
  participant Pix as Pix/SPI Adapter
  participant PDF as PDF / Receipt Service
  participant Notify as Notification Service
  participant Audit as Audit & Compliance Store

  MobileApp->>APIGW: Solicita transferência Pix (dados, chave, valor)
  APIGW->>Auth: Verificar token de sessão
  Auth->>Session: Validar sessão ativa
  Session-->>Auth: Sessão válida
  Auth->>MobileApp: Request de MFA (OTP/biometria) [se necessário]
  MobileApp->>Auth: Resposta MFA
  Auth->>APIGW: MFA validado

  APIGW->>Limits: Verificar limites diários e horário (perfil usuário)
  Limits-->>APIGW: Limite permitido / restrição
  APIGW->>Account: Verificar saldo e reservas
  Account-->>APIGW: Saldo disponível / bloqueio possível

  APIGW->>Fraud: Enviar evento de pré-análise (user, device, valor, histórico)
  Fraud-->>APIGW: Resultado de score (OK / SUSPEITO)
  alt score == SUSPEITO
    APIGW->>Auth: Solicitar reautenticação forte
    Auth->>MobileApp: Solicitar confirmação
    MobileApp->>Auth: Confirmação do usuário
    Auth-->>APIGW: Reautenticação OK
  else score == BLOQUEAR
    APIGW->>Ledger: Registrar tentativa e bloquear execução
    Ledger-->>APIGW: Transação bloqueada (status)
    APIGW->>Notify: Notificar usuário (push + email)
    APIGW->>Audit: Registrar alerta de fraude e resolução
    return
  end

  APIGW->>Ledger: Criar transação pendente (idempotente)
  Ledger-->>APIGW: Transação pendente criada (txId)

  APIGW->>Pix: Enviar instrução ao SPI (txId, dados)
  Pix-->>APIGW: Resultado (aceito / rejeitado) dentro do SLA
  opt sucesso
    APIGW->>Ledger: Confirmar/commit transação (status=confirmado)
    Ledger-->>APIGW: Commit OK
    APIGW->>PDF: Gerar comprovante PDF (txId)
    PDF-->>APIGW: PDF gerado (url)
    APIGW->>Notify: Enviar comprovante + push + email
    APIGW->>Audit: Registrar operação completa (imutável)
  else falha
    APIGW->>Ledger: Marcar transação como falhada / revert
    Ledger-->>APIGW: Reversão / ajuste
    APIGW->>Notify: Informar usuário (falha)
    APIGW->>Audit: Registrar falha
  end
```

Observações sobre o diagrama:
- Mensagens idempotentes e identificadores de transação (txId) são fundamentais para replays e consistência.
- Branch para score de fraude demonstra decisão inline (reatenticação, bloqueio).
- Interações com SPI/Pix são encapsuladas no componente "Pix Adapter" (responsabilidade: tradução de protocolos, retry, timeout e garantia de SLAs).

(Se necessário, diagramas adicionais de componentes e de contexto podem ser gerados seguindo o mesmo padrão Mermaid.)

## 3. Decisões de Arquitetura
As decisões listadas abaixo são conceituais e mantêm neutralidade tecnológica conforme diretriz.

D01 — Arquitetura baseada em serviços com fronteira bem definida
- Responsabilidade: decompor o domínio em serviços lógicos (Autenticação, Conta, Ledger, Pagamentos, Cartões, Fraude, KYC, Consentimento, Notificação, Auditoria).
- Justificativa: isolamento de responsabilidades, escalabilidade e governança de segurança.

D02 — Separação entre processamento financeiro (ledger) e visões de leitura
- Responsabilidade: Ledger como fonte de verdade transacional (consistência forte); vistas consolidadas e relatórios atendem leituras com eventual consistency.
- Impacto: operações financeiras críticas exigem atomicidade e durabilidade; relatórios podem ser atualizados assincronamente.

D03 — Modelo de integração híbrido: síncrono para autorizações/consulta e assíncrono para eventos e processamento posterior
- Ex.: consulta de saldo e confirmação de transação devem ser rápidas; notificação, geração de relatórios e reconciliações podem ser eventos.

D04 — Garantia forte para operações monetárias
- Requisitos: idempotência, atomicidade de débito/crédito, logs imutáveis para auditoria e recuperabilidade.
- Implementação conceitual: transações com controle de concorrência e reconciliador eventual entre sub-sistemas financeiros.

D05 — Segurança por design
- TLS (>=1.2), criptografia de dados sensíveis em repouso (AES-256 conforme RNF02), hashing de credenciais (bcrypt/Argon2 conforme RNF03), gestão de chaves e rotação regular.
- PCI-DSS: não armazenar dados de cartão (delegação ao processador certificado), conforme RNF06.

D06 — Fluxo de MFA e gerenciamento de sessão
- MFA obrigatório em login (OTP e biometria no mobile), suporte para gerenciamento de métodos e expiração de sessão configurável por perfil.

D07 — Detecção e mitigação de fraudes em tempo real
- Pipeline de pontuação em tempo real com bloqueio preventivo e fluxo de reautenticação.
- Logs imutáveis e retenção (mínimo 5 anos) para auditoria/regulação.

D08 — Open Finance e Consentimento
- Expor APIs padronizadas para open finance; Consent Manager para autorizações do usuário com capacidade de revogação imediata.

D09 — Resiliência e alta disponibilidade
- Multi-zona geográfica, escalonamento horizontal automático e mecanismos de fallback que garantam que transações em andamento não sejam perdidas (ex.: filas persistentes, transações pendentes).

D10 — Observabilidade e governança operacional
- Métricas, tracing distribuído e alertas para latência, erros e volumes; painel em tempo real para operações.

D11 — Backups e recuperação
- Backups contínuos com RPO <=1h e RTO <=4h; testes regulares de DR e runbooks.

D12 — Conformidade e auditoria
- Trails imutáveis e exportáveis, geração de relatórios regulatórios (BACEN) e processos de geração de informe de rendimentos.

Decisões pendentes (ver Seção 5): definições de SLA e formatos de integração com órgãos externos, maturidade de modelos de fraude e cronograma de testes de penetração.

## 4. Tabela de Componentes e Rastreabilidade

| Componente | Responsabilidade Principal | Comunica-se com | Origem (HU / Critério de Aceite) |
|---|---|---:|---|
| API Gateway | Entrada unificada, roteamento, autenticação inicial, rate limiting | Mobile/Web Clients, Auth Service, Services internos | HU02, RNF04, RNF13 |
| Auth Service | Autenticação, MFA, gerenciamento de credenciais e sessões | API Gateway, Session Manager, Notify, Audit | HU02, RF03, RF04, RNF03 |
| Session Manager | Controle de sessão, expiração configurável por perfil | Auth Service, API Gateway | RF04, HU02 |
| Identity / KYC Service | Onboarding PF/PJ, validação de documentos, verificação de identidade | API Gateway, External ID Providers, Audit | HU01 (PF), HU10 (PJ), RF02, RNF08 |
| Account Service | Contas correntes/poupança, consultas de saldo, extratos | Ledger, API Gateway, Notification | RF08, RF09, RF10, HU01, HU10 |
| Ledger / Transaction Service | Registro contábil, garantia de atomicidade de transações | Account Service, Pix Adapter, Payment Service, Audit | RF09, RF12, RF24, RNF12, RNF16 |
| Limits & Policy Service | Regras de limite por canal/horário/perfil | API Gateway, Account Service, Auth | RF27, HU03 |
| Pix / SPI Adapter | Tradução e integração com sistema de pagamentos instantâneos | Ledger, External SPI, API Gateway | RF22, RF24, HU03 |
| TED Adapter | Interface para transferências interbancárias tradicionais | Ledger, External Clearing | RF25, HU11 |
| Payment / Boleto Service | Leitura boleto, agendamento, execução de pagamentos | API Gateway, Scheduler, Ledger, PDF Service | RF28, RF30, HU04 |
| Scheduler / Jobs | Execução agendada (transferências, boletos, rendimentos) | Payment Service, Investment Service, Notification | RF26, RF31, RNF22 |
| Card Service (emissor/gestor) | Emissão, bloqueio, limites do cartão; integração com processador | External Card Processor, API Gateway, Notification | RF14–RF21, HU05 |
| Credit Assessment Service | Análise de crédito para cartão | Card Service, External Credit Bureau | RF15, HU05 |
| Investment Service | Oferta, aplicação e resgate de renda fixa; posição consolidada | Account Service, Ledger, PDF Service | RF32–RF35, HU07 |
| Fraud Detection Service | Monitoramento em tempo real, scoring, bloqueios preventivos | API Gateway, Ledger, Notification, Auth | RF36–RF40, HU09 |
| Consent Manager (Open Finance) | Gestão de consentimentos, revogação e APIs padronizadas | API Gateway, Open Finance APIs, Audit | RF41–RF44, HU08 |
| Open Finance API Layer | Exposição de APIs padronizadas (client-facing & third-party) | Consent Manager, API Gateway | RF44, RNF11 |
| Notification Service | Push, e-mail, SMS, alertas; templates de segurança | All Services, Audit | RF20, RF38, HU09 |
| PDF / Receipt Service | Geração e armazenamento de comprovantes em PDF | Ledger, Notification, API Gateway | RF13, HU03, HU04, HU11 |
| Audit & Compliance Store | Trilha imutável de eventos, retenção e exportação regulatória | All Services, Reporting | RNF12, RNF09 |
| Reporting & Regulatory Service | Geração de relatórios (BACEN, informe rendimentos) | Audit Store, Ledger | RNF09, RF35 |
| Metrics & Monitoring | Métricas operacionais, alertas e painel | All Services | RNF24, RNF13, RNF14 |
| Backup & DR Orchestration | Backups contínuos, RTO/RPO e recuperação | Persistent Stores, Admin Tools | RNF22, RNF23 |
| Relationship Manager Portal | Portal para gerentes com visão consolidada (mediante consentimento) | API Gateway, Consent Manager, Account/Investment Services | RF07, RF45–RF47, HU12, HU13 |

Obs.: “External” refere-se a sistemas fora do domínio (ex.: SPI, processador de cartão PCI, bureaus de crédito, provedores de verificação de identidade).

## 5. Bloqueios e Pendências
Lista de itens que impedem decisões técnicas finais ou exigem esclarecimento externo:

B1 — Integrações externas obrigatórias
- Integração com SPI/Pix e requisitos operacionais (certificados, endpoints, SLAs). Dependência de contratos e certificações.
- Integração com processador de cartões (obrigatório para cumprir RNF06).

B2 — Especificações regulatórias detalhadas
- Formato e periodicidade exata dos relatórios regulatórios (por ex., BACEN 3040/SCR) e requisitos de homologação.
- Fases/versões do Open Finance a suportar (detalhamento do escopo da API padronizada e modelos de autorização).

B3 — Modelos e limiares de fraude
- Definição de regras iniciais, fontes de dados para scoring e política de bloqueio/atenuação; necessidade de dados históricos para treinar modelos.

B4 — SLAs de tempo/volume e dimensionamento
- Valores esperados de TPS, picos diários, número médio de clientes ativos são necessários para dimensionamento e políticas de escalonamento.

B5 — Roteiro de testes de segurança e conformidade
- Frequência e escopo de testes de penetração; aceitação de auditorias; políticas de resposta a incidentes.

B6 — Políticas de retenção e anonimização além do mínimo
- RNF12 exige 5 anos; precisam ser definidas políticas de retenção para dados de sessão, métricas e backups.

B7 — Consentimento e UX legal
- Texto legal e formatos de consentimento para open finance; requisitos sobre logs de consentimento auditáveis.

B8 — Procedimentos de contestação e estorno
- Prazos e fluxos regulatórios para estorno e comunicação entre instituição e adquirentes/estabelecimentos.

Ações recomendadas:
- Priorizar contratação/engajamento com provedores SPI e processador de cartão e obter documentação de integração.
- Tomar decisões de capacidade após levantamento de tráfego e SLOs de negócio.
- Definir políticas de fraude iniciais e planos de evolução com equipe de Machine Learning/CI.

## 6. Cobertura de Requisitos
Mapeamento direto dos Requisitos Funcionais (RF) e Não-Funcionais (RNF) para componentes e elementos de arquitetura — status: Coberto (C).

Funcionais (seleção resumida com referência de componentes):

- RF01 (cadastro PF/PJ/gerente): Identity/KYC Service, Account Service, Relationship Manager Portal — C
- RF02 (validação identidade PF/PJ): Identity/KYC Service, External ID Providers — C (HU01, HU10)
- RF03 (MFA): Auth Service, Session Manager, Mobile App — C (HU02)
- RF04 (encerramento sessões inativas): Session Manager, Auth Service — C
- RF05 (histórico de acessos): Audit & Compliance Store, API Gateway, Account Service — C
- RF06 (bloquear/desbloquear conta remotamente): Account Service, Auth Service, Notify — C
- RF07 (gerente com consentimento): Relationship Manager Portal, Consent Manager, Account/Investment Service — C (HU12)
- RF08 (abrir conta corrente/poupança): Account Service, Identity/KYC Service, Ledger — C (HU01, HU10)
- RF09 (saldo em tempo real): Account Service + Ledger (consistência forte) — C (RNF14)
- RF10 (extrato detalhado com filtros): Account Service, Reporting, Audit Store — C
- RF11 (rendimento poupança): Scheduler, Account Service, Investment/Interest Engine — C
- RF12 (transferência entre contas do titular): Ledger, Account Service — C
- RF13 (comprovante PDF por transação): PDF Service, Notification Service — C
- RF14 (cartão débito emissão): Card Service (integração com processador) — C
- RF15 (solicitação cartão crédito com análise): Card Service, Credit Assessment Service — C
- RF16 (visualizar faturas): Card Service, Account Service — C
- RF17 (pagamento fatura): Card Service, Account/Ledger, Payment Service — C
- RF18 (definir/alterar limite do cartão): Card Service, Credit Assessment Service, Audit Store — C
- RF19 (bloquear/desbloquear cartão): Card Service, Notification Service — C
- RF20 (notificação em tempo real por transação): Notification Service, Fraud Service, Card/Account Services — C
- RF21 (contestar transação): Account Service, Card Service, Case Management (parte do Audit/Service) — C (HU06)
- RF22 (Pix com chaves regulamentadas): Pix Adapter, Account Service, Identity Service — C (HU03)
- RF23 (gerenciar chaves Pix): Account Service, Identity/KYC Service — C
- RF24 (processar Pix em até 10s): Pix Adapter, Ledger, API Gateway, RNF15 — C (implementação depende de SLA externo)
- RF25 (TED para outras instituições): TED Adapter, Ledger, Account Service — C (HU11)
- RF26 (agendamento transferências Pix/TED): Scheduler, Payment Service, Ledger — C
- RF27 (limites diários por canal e horário): Limits & Policy Service, Account Service — C
- RF28 (pagar boleto leitura/digitação): Payment/Boleto Service, PDF Service, Scheduler — C
- RF29 (exibir dados do boleto antes do pagamento): Payment Service, UI — C
- RF30 (agendamento pagamento boletos): Scheduler, Payment Service — C
- RF31 (notificar boletos agendados): Scheduler, Notification Service — C
- RF32–RF35 (investimentos renda fixa): Investment Service, Account Service, Ledger, Reporting — C (HU07)
- RF36–RF40 (detecção de fraudes): Fraud Detection Service, Notification, Ledger, Auth Service — C (HU09)
- RF41–RF44 (open finance): Consent Manager, Open Finance API Layer, API Gateway — C (HU08)
- RF45–RF47 (gerente de relacionamento): Relationship Manager Portal, Consent Manager, Audit Store, Service Request Workflow — C (HU12, HU13)

Não-funcionais (resumo por componente/decisão):

- RNF01 (TLS >=1.2): Coberto pela camada de transporte (API Gateway / infra) — C
- RNF02 (AES-256 repouso): Coberto via serviços de armazenamento e Key Management — C (requer política de chaves)
- RNF03 (hash de senhas - bcrypt/Argon2): Coberto por Auth Service — C
- RNF04 (rate limiting): API Gateway + Auth Service — C
- RNF05 (pen-tests periódicos): Processo operacional / segurança — C (pendência de cronograma)
- RNF06 (não armazenar dados de cartão): Card Service delega a processador PCI — C
- RNF07–RNF11 (conformidade Bacen, KYC, PLD/FT, LGPD, Open Finance): Audit & Compliance, Identity/KYC, Consent Manager, Reporting — C (pendências de integração)
- RNF12 (trilha imutável por 5 anos): Audit & Compliance Store — C
- RNF13 (99,95% disponibilidade): Arquitetura Multi-Zone, escalonamento horizontal, HA — C (requer negociação de infra/SLO)
- RNF14 (consulta saldo <1s): Account Service + Ledger otimizado para leitura — C (depende de dimensionamento)
- RNF15 (Pix <=10s): Pix Adapter + Ledger com timeouts & retries — C (dependência SPI)
- RNF16 (escalabilidade horizontal automática): Serviços stateless e orquestração de escalonamento — C
- RNF17 (fallback e recuperação automática): Filas persistentes, transações pendentes, reconciliador — C
- RNF18–RNF21 (usabilidade, compatibilidade, acessibilidade): Produto (mobile/web) — C (especificação de UX não detalhada)
- RNF22 (backup RPO=1h RTO=4h): Backup & DR Orchestration — C
- RNF23 (multi-ZA): Infraestrutura — C
- RNF24 (expor métricas): Metrics & Monitoring — C

Resumo: todos os RFs e RNFs têm um mapeamento arquitetural (coberto conceitualmente). Implementação detalhada depende de resolução das pendências da Seção 5.

## 7. Gap Analysis
Identificação de lacunas na especificação, impactos arquiteturais e recomendações de ação.

GAP 1 — Especificação técnica de integração com SPI/Pix e SLAs operacionais
- Impacto: sem os contratos/formatos e SLAs definidos, não é possível dimensionar corretamente o Pix Adapter (timeouts, retries) nem garantir RNF15.
- Risco: falhas de integração que causem tempos de resposta fora do requerido.
- Recomendação: obter documentação técnica do SPI, acordos de SLA e realizar integração piloto/homologação antes de cutover.

GAP 2 — Dados de capacidade e tráfego esperados
- Impacto: dimensionamento, autoscaling rules, custos e cumprimento de RNF13 e RNF14 ficam imprecisos.
- Risco: sub/dimensionamento resultando em degradação ou custos excessivos.
- Recomendação: coletar estimativas de usuários ativos, TPS esperado, picos (campanhas) e definir SLOs claros.

GAP 3 — Políticas de fraude e modelos quantitativos
- Impacto: regras de bloqueio e thresholds não especificados afetam UX e risco operacional.
- Risco: falsos positivos/negativos, escalonamento de atendimento e impacto na receita.
- Recomendação: definir regras iniciais, histórico de dados para treino e roadmap de evolução com equipe de análise de risco.

GAP 4 — Fluxos detalhados para contestação e estorno
- Impacto: não definido o tempo de resposta, passos de investigação e integração com adquirentes/estabelecimentos.
- Risco: não conformidade com regulamentação e má experiência do cliente.
- Recomendação: detalhar SLA de contestação, campos necessários e integração com Case Management/Backoffice.

GAP 5 — Requisitos de usabilidade e acessibilidade granular
- Impacto: RNF18–RNF21 dão diretrizes gerais, mas falta detalhamento de funcionalidades (ex.: fluxo de recuperação, mensagens de erro acessíveis).
- Risco: não atingir WCAG 2.1 AA; rejeição por usuários com necessidades especiais.
- Recomendação: produzir especificação de UX acessível e validar com testes de usabilidade.

GAP 6 — Política de retenção e anonimização além do mínimo
- Impacto: falta definição para logs de sessão, métricas, backups e dados sensíveis, além dos 5 anos mínimos.
- Risco: exposição a multas ou consumo excessivo de armazenamento.
- Recomendação: estabelecer políticas de retenção, arquivamento e anonimização (tempos por tipo de dado).

GAP 7 — Processos operacionais e runbooks
- Impacto: RNF22/17 exigem recuperação e fallback — sem runbooks testados, risco operacional aumenta.
- Recomendação: criar e testar planos de desastre, playbooks de recuperação e exercícios de DR.

GAP 8 — Formato e provas exigidas para KYC e validações automáticas
- Impacto: qualidade da automação de onboarding e tempos (HU01/HU10) dependem do que é aceitável como prova documental.
- Recomendação: alinhar com compliance quais documentos/formatos aceitos e requisitos para revisão humana.

GAP 9 — Escopo e maturidade do Open Finance a suportar
- Impacto: implementar APIs incompletas ou incompatíveis com fases regulamentares.
- Recomendação: alinhar cronograma/regulamentação e planejar compatibilidade retroativa.

GAP 10 — Testes de penetração e plano de conformidade contínua
- Impacto: RNF05 exige testes periódicos; sem cronograma não há garantia de remediação.
- Recomendação: estabelecer ciclo (anual/semianual), critérios de aceitação e orçamento.

Conclusão e próximos passos recomendados (prioritários):
1. Formalizar contratos e documentação técnica com SPI/Pix e processador de cartões (B1, GAP1).
2. Levantamento de capacidade/SLAs de negócio para dimensionamento e SLOs (B4, GAP2).
3. Definir política de fraude inicial e indicadores; planejar coleta de dados e iteração (B3, GAP3).
4. Documentar fluxos de contestação/estorno e requisitos legais (B2, GAP4).
5. Produzir runbooks DR e executar testes de recuperação (B5, GAP7).
6. Aprofundar especificação de UX acessível e testes com personas (GAP5).

---

Relatório finalizado. Se desejar, eu gero:
- diagramas adicionais (componentes/contexto) em Mermaid;
- matriz completa de rastreabilidade RF/HU -> componentes em formato CSV/planilha;
- propostas de APIs REST/MSG (contratos) para os componentes críticos (Auth, Ledger, Pix Adapter, Consent Manager).