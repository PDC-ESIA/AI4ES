# Plataforma Financeira Digital — Requisitos

---

## Requisitos Funcionais (RF)

### Gestão de Usuários e Autenticação

| ID   | Descrição |
|------|-----------|
| RF01 | O sistema deve permitir o cadastro de usuários com perfis distintos: pessoa física (PF), pessoa jurídica (PJ) e gerente de relacionamento. |
| RF02 | O sistema deve realizar validação de identidade no onboarding de PF (CPF, data de nascimento, documento com foto) e PJ (CNPJ, dados dos sócios, documentos societários). |
| RF03 | O sistema deve exigir autenticação multifator (MFA) em todos os acessos, suportando ao menos dois métodos: OTP por aplicativo autenticador e biometria no mobile. |
| RF04 | O sistema deve encerrar automaticamente sessões inativas após tempo configurável por perfil. |
| RF05 | O sistema deve exibir histórico de acessos recentes (data, hora, dispositivo e localização aproximada) ao usuário. |
| RF06 | O sistema deve permitir que o usuário bloqueie e desbloqueie o acesso à conta remotamente. |
| RF07 | O sistema deve permitir que o gerente de relacionamento acesse, com consentimento do cliente, a visão consolidada de contas sob sua gestão. |

### Conta Corrente e Poupança

| ID   | Descrição |
|------|-----------|
| RF08 | O sistema deve permitir a abertura de conta corrente e conta poupança para PF e PJ. |
| RF09 | O sistema deve exibir o saldo atualizado em tempo real de cada conta do usuário. |
| RF10 | O sistema deve exibir extrato detalhado com filtro por período, tipo de transação e valor. |
| RF11 | O sistema deve calcular e creditar automaticamente os rendimentos da poupança conforme as regras vigentes do Banco Central. |
| RF12 | O sistema deve permitir a transferência de saldo entre contas do mesmo titular. |
| RF13 | O sistema deve gerar comprovante para cada transação realizada, disponível para download em PDF. |

### Cartão de Débito e Crédito

| ID   | Descrição |
|------|-----------|
| RF14 | O sistema deve permitir a emissão de cartão de débito vinculado à conta corrente do usuário. |
| RF15 | O sistema deve permitir a solicitação e emissão de cartão de crédito, sujeita a análise de crédito. |
| RF16 | O sistema deve permitir que o usuário visualize a fatura atual e faturas anteriores do cartão de crédito. |
| RF17 | O sistema deve permitir o pagamento total ou parcial da fatura do cartão de crédito. |
| RF18 | O sistema deve permitir que o usuário defina e altere o limite de gastos do cartão de crédito, respeitando o limite aprovado. |
| RF19 | O sistema deve permitir que o usuário bloqueie e desbloqueie o cartão de débito e crédito de forma independente. |
| RF20 | O sistema deve notificar o usuário em tempo real a cada transação realizada com o cartão. |
| RF21 | O sistema deve permitir a contestação de transações não reconhecidas diretamente pelo aplicativo ou portal web. |

### Transferências

| ID   | Descrição |
|------|-----------|
| RF22 | O sistema deve permitir transferências via Pix, suportando todas as chaves regulamentadas (CPF/CNPJ, e-mail, telefone, chave aleatória e Pix Copia e Cola). |
| RF23 | O sistema deve permitir o gerenciamento de chaves Pix do usuário (cadastro, edição e exclusão). |
| RF24 | O sistema deve processar transferências Pix em até 10 segundos em horário de funcionamento do SPI. |
| RF25 | O sistema deve permitir transferências via TED para contas em outras instituições, respeitando os limites e horários regulamentados pelo Banco Central. |
| RF26 | O sistema deve permitir o agendamento de transferências Pix e TED para datas futuras. |
| RF27 | O sistema deve permitir que o usuário configure limites diários de transferência por canal (Pix, TED) e horário (diurno/noturno), conforme normas do Banco Central. |

### Pagamento de Boletos

| ID   | Descrição |
|------|-----------|
| RF28 | O sistema deve permitir o pagamento de boletos bancários e de concessionárias via leitura de código de barras ou digitação da linha digitável. |
| RF29 | O sistema deve exibir os dados do boleto (beneficiário, valor, vencimento) para confirmação antes do pagamento. |
| RF30 | O sistema deve permitir o agendamento de pagamento de boletos para a data de vencimento ou outra data futura. |
| RF31 | O sistema deve notificar o usuário sobre boletos agendados com vencimento próximo. |

### Investimentos em Renda Fixa

| ID   | Descrição |
|------|-----------|
| RF32 | O sistema deve exibir as opções de investimento em renda fixa disponíveis, com rentabilidade, prazo, valor mínimo e risco. |
| RF33 | O sistema deve permitir que o usuário aplique e resgate investimentos em renda fixa diretamente pela plataforma. |
| RF34 | O sistema deve exibir a posição consolidada de investimentos com rentabilidade acumulada e projeção de rendimento. |
| RF35 | O sistema deve emitir o Informe de Rendimentos dos investimentos para fins de declaração de imposto de renda. |

### Detecção de Fraudes

| ID   | Descrição |
|------|-----------|
| RF36 | O sistema deve monitorar transações em tempo real e sinalizar automaticamente operações com padrão suspeito. |
| RF37 | O sistema deve bloquear preventivamente transações de alto risco e solicitar reautenticação ao usuário antes de prosseguir. |
| RF38 | O sistema deve notificar o usuário imediatamente por push e e-mail quando uma transação suspeita for identificada. |
| RF39 | O sistema deve permitir que o usuário confirme ou conteste a legitimidade de uma transação sinalizada diretamente pelo aplicativo. |
| RF40 | O sistema deve registrar e disponibilizar para auditoria interna o histórico completo de alertas de fraude e suas resoluções. |

### Open Finance

| ID   | Descrição |
|------|-----------|
| RF41 | O sistema deve permitir que o usuário autorize o compartilhamento de seus dados financeiros com outras instituições participantes do open finance, conforme as normas do Banco Central. |
| RF42 | O sistema deve permitir que o usuário visualize, gerencie e revogue os consentimentos de compartilhamento ativos. |
| RF43 | O sistema deve permitir a iniciação de pagamentos por meio de instituições parceiras via open finance. |
| RF44 | O sistema deve disponibilizar APIs padronizadas conforme as especificações do open finance Brasil para integração com outras instituições. |

### Gerente de Relacionamento

| ID   | Descrição |
|------|-----------|
| RF45 | O sistema deve permitir que o gerente visualize a carteira de clientes sob sua responsabilidade com visão consolidada de produtos e saldos. |
| RF46 | O sistema deve permitir que o gerente registre interações e anotações vinculadas ao perfil de cada cliente. |
| RF47 | O sistema deve permitir que o gerente abra solicitações de serviço em nome do cliente (ex.: solicitação de limite, abertura de produto). |

---

## Requisitos Não Funcionais (RNF)

### Segurança

| ID    | Categoria  | Descrição |
|-------|------------|-----------|
| RNF01 | Segurança  | Toda comunicação entre cliente e servidor deve utilizar TLS 1.2 ou superior. |
| RNF02 | Segurança  | Dados sensíveis (número de cartão, dados bancários, documentos) devem ser armazenados criptografados em repouso com AES-256. |
| RNF03 | Segurança  | As senhas dos usuários devem ser armazenadas com hash seguro (bcrypt ou Argon2). |
| RNF04 | Segurança  | O sistema deve implementar rate limiting em endpoints de autenticação e transações para mitigar ataques de força bruta. |
| RNF05 | Segurança  | O sistema deve ser submetido a testes de penetração periódicos e auditorias de segurança. |
| RNF06 | Segurança  | Dados de cartão não devem ser armazenados no sistema; o processamento deve ser delegado a um processador certificado PCI-DSS. |

### Conformidade Regulatória

| ID    | Categoria    | Descrição |
|-------|--------------|-----------|
| RNF07 | Conformidade | O sistema deve estar em conformidade com as normas e circulares do Banco Central do Brasil aplicáveis a instituições financeiras. |
| RNF08 | Conformidade | O sistema deve implementar políticas de KYC (Know Your Customer) e PLD/FT (Prevenção à Lavagem de Dinheiro e ao Financiamento do Terrorismo). |
| RNF09 | Conformidade | O sistema deve gerar e transmitir relatórios regulatórios obrigatórios ao Banco Central (ex.: BACEN 3040, SCR). |
| RNF10 | Conformidade | O sistema deve estar em conformidade com a LGPD no tratamento de dados pessoais e financeiros dos usuários. |
| RNF11 | Conformidade | O sistema deve implementar as especificações técnicas do open finance Brasil, conforme fases e prazos regulamentados pelo Banco Central. |
| RNF12 | Conformidade | O sistema deve manter trilha de auditoria imutável de todas as operações financeiras, acessos e alterações de configuração, com retenção mínima de 5 anos. |

### Disponibilidade e Desempenho

| ID    | Categoria   | Descrição |
|-------|-------------|-----------|
| RNF13 | Disponibilidade | O sistema deve ter disponibilidade mínima de 99,95% ao mês (downtime máximo de ~22 minutos/mês). |
| RNF14 | Desempenho  | Consultas de saldo e extrato devem ser respondidas em até 1 segundo. |
| RNF15 | Desempenho  | Transações Pix devem ser processadas em até 10 segundos no horário de funcionamento do SPI. |
| RNF16 | Escalabilidade | A arquitetura deve suportar escalonamento horizontal automático para absorver picos de demanda sem degradação de desempenho. |
| RNF17 | Resiliência | O sistema deve implementar mecanismos de fallback e recuperação automática em caso de falha de componentes críticos, garantindo que transações em andamento não sejam perdidas. |

### Usabilidade e Compatibilidade

| ID    | Categoria      | Descrição |
|-------|----------------|-----------|
| RNF18 | Usabilidade    | O aplicativo mobile deve estar disponível para iOS e Android com suporte às duas versões mais recentes de cada sistema operacional. |
| RNF19 | Usabilidade    | O portal web deve ser responsivo e funcionar nos principais navegadores modernos (Chrome, Firefox, Safari, Edge). |
| RNF20 | Acessibilidade | A interface deve seguir as diretrizes WCAG 2.1 nível AA para garantir acessibilidade a usuários com deficiência. |
| RNF21 | Usabilidade    | Operações críticas (transferências, pagamentos) devem exigir etapa de confirmação explícita com exibição clara dos dados da operação antes da efetivação. |

### Infraestrutura e Dados

| ID    | Categoria        | Descrição |
|-------|------------------|-----------|
| RNF22 | Backup           | O sistema deve realizar backup contínuo dos dados transacionais com RPO máximo de 1 hora e RTO máximo de 4 horas. |
| RNF23 | Infraestrutura   | O ambiente de produção deve ser implantado em múltiplas zonas de disponibilidade para garantir redundância geográfica. |
| RNF24 | Manutenibilidade | O sistema deve expor métricas operacionais (latência, taxa de erros, disponibilidade) em painel de monitoramento em tempo real. |

---

## Histórias de Usuário (HU)

### Perfil: Pessoa Física (PF)

**HU01 — Abrir conta com validação de identidade**
> Como pessoa física, quero abrir uma conta corrente ou poupança pela plataforma enviando meus documentos de forma digital, para me tornar cliente sem precisar ir a uma agência.

*Critérios de aceite:*
- O onboarding deve validar CPF, data de nascimento e documento com foto.
- O usuário deve ser notificado por e-mail e push sobre o resultado da análise em até 24 horas.
- Após a aprovação, o acesso à conta deve ser habilitado imediatamente.

---

**HU02 — Autenticar com múltiplos fatores**
> Como usuário, quero autenticar meu acesso com múltiplos fatores, para garantir que minha conta esteja protegida mesmo em caso de vazamento de senha.

*Critérios de aceite:*
- O MFA deve ser obrigatório em todo login, suportando OTP por aplicativo autenticador e biometria no mobile.
- O usuário deve poder cadastrar e gerenciar seus métodos de MFA nas configurações de segurança.
- Tentativas de acesso bloqueadas pelo MFA devem gerar alerta imediato ao usuário.

---

**HU03 — Realizar transferência via Pix**
> Como usuário, quero transferir dinheiro via Pix para qualquer chave cadastrada, para enviar valores de forma rápida a qualquer hora do dia.

*Critérios de aceite:*
- O Pix deve suportar chaves CPF/CNPJ, e-mail, telefone, chave aleatória e Pix Copia e Cola.
- O sistema deve exibir os dados do destinatário para confirmação antes de efetivar a transferência.
- O comprovante deve ser gerado e disponibilizado para download em PDF imediatamente após a confirmação.
- Transferências acima do limite noturno configurado devem ser bloqueadas fora do horário permitido.

---

**HU04 — Pagar boleto com agendamento**
> Como usuário, quero pagar ou agendar o pagamento de um boleto diretamente pela plataforma, para quitar minhas contas sem precisar acessar outros canais.

*Critérios de aceite:*
- O sistema deve exibir beneficiário, valor e vencimento para confirmação antes do pagamento.
- Deve ser possível agendar o pagamento para a data de vencimento ou outra data futura.
- O usuário deve receber notificação de lembrete um dia antes do vencimento de boletos agendados.

---

**HU05 — Gerenciar cartão de crédito**
> Como usuário, quero visualizar minha fatura, definir limites e bloquear meu cartão de crédito pela plataforma, para ter controle total sobre meus gastos.

*Critérios de aceite:*
- A fatura deve listar todas as transações com data, estabelecimento e valor, separadas por ciclo.
- O usuário deve poder pagar o valor total, mínimo ou um valor personalizado da fatura.
- O bloqueio do cartão deve ser efetivado em até 60 segundos após a solicitação.
- O usuário deve receber notificação push a cada nova transação no cartão.

---

**HU06 — Contestar transação não reconhecida**
> Como usuário, quero contestar diretamente pela plataforma uma transação que não reconheço, para iniciar o processo de estorno sem precisar ligar para a central de atendimento.

*Critérios de aceite:*
- A contestação deve estar disponível para qualquer transação listada no extrato ou na fatura.
- O usuário deve poder descrever o motivo da contestação e, opcionalmente, anexar evidências.
- O sistema deve confirmar o recebimento da contestação e informar o prazo de análise.

---

**HU07 — Investir em renda fixa**
> Como usuário, quero visualizar as opções de investimento em renda fixa disponíveis e aplicar ou resgatar valores diretamente pela plataforma, para rentabilizar meu dinheiro de forma simples.

*Critérios de aceite:*
- Cada produto deve exibir rentabilidade, prazo, valor mínimo, liquidez e classificação de risco.
- A aplicação deve exigir confirmação com exibição do valor, produto e rentabilidade estimada.
- A posição consolidada deve ser atualizada imediatamente após cada aplicação ou resgate.

---

**HU08 — Gerenciar consentimentos do open finance**
> Como usuário, quero autorizar, visualizar e revogar os consentimentos de compartilhamento dos meus dados financeiros com outras instituições, para controlar quem tem acesso às minhas informações.

*Critérios de aceite:*
- O painel de consentimentos deve listar instituição, dados compartilhados, data de autorização e prazo de validade.
- A revogação deve ser efetivada imediatamente, interrompendo o acesso da instituição aos dados.
- O usuário deve ser notificado por e-mail ao conceder ou revogar qualquer consentimento.

---

**HU09 — Receber alertas e responder a suspeita de fraude**
> Como usuário, quero ser notificado imediatamente quando uma transação suspeita for identificada e poder confirmar ou contestar sua legitimidade pelo app, para proteger minha conta em tempo real.

*Critérios de aceite:*
- O alerta deve ser enviado simultaneamente por push e e-mail com detalhes da transação suspeita.
- O usuário deve poder confirmar a legitimidade ou contestar a transação em até dois cliques.
- Em caso de contestação, a transação deve ser bloqueada preventivamente e a conta sinalizada para análise.

---

### Perfil: Pessoa Jurídica (PJ)

**HU10 — Abrir conta PJ com documentação societária**
> Como representante legal de uma empresa, quero abrir uma conta PJ enviando os documentos societários digitalmente, para habilitar minha empresa a operar na plataforma.

*Critérios de aceite:*
- O onboarding deve validar CNPJ, dados dos sócios e documentos societários (contrato social ou equivalente).
- O sistema deve realizar validação de KYC dos sócios administradores.
- O representante legal deve ser notificado sobre o resultado da análise em até 48 horas.

---

**HU11 — Realizar TED para fornecedores**
> Como usuário PJ, quero realizar transferências via TED para contas em outras instituições, para efetuar pagamentos a fornecedores e parceiros.

*Critérios de aceite:*
- O sistema deve validar os dados bancários do destinatário antes de permitir a transferência.
- A TED deve respeitar os limites diários configurados e os horários regulamentados pelo Banco Central.
- O comprovante deve ser gerado e disponibilizado para download em PDF após a confirmação.

---

### Perfil: Gerente de Relacionamento

**HU12 — Acompanhar carteira de clientes**
> Como gerente de relacionamento, quero visualizar a carteira de clientes sob minha responsabilidade com visão consolidada de produtos, saldos e investimentos, para oferecer um atendimento personalizado e proativo.

*Critérios de aceite:*
- O acesso à carteira deve exigir consentimento prévio do cliente cadastrado no sistema.
- A visão consolidada deve exibir produtos ativos, saldos, investimentos e últimas movimentações.
- O gerente deve poder registrar anotações e interações vinculadas ao perfil de cada cliente.

---

**HU13 — Abrir solicitação de serviço em nome do cliente**
> Como gerente de relacionamento, quero abrir solicitações de serviço em nome do cliente, como pedido de aumento de limite ou abertura de novo produto, para agilizar o atendimento sem exigir que o cliente acesse o app.

*Critérios de aceite:*
- Toda solicitação aberta pelo gerente deve registrar o identificador do gerente responsável para fins de auditoria.
- O cliente deve ser notificado sobre a abertura e o resultado da solicitação.
- O gerente não deve ter permissão para realizar transações financeiras em nome do cliente sem autorização explícita do mesmo registrada no sistema.