# Plataforma de Negociação de Ativos Financeiros (Corretora de Valores) — Requisitos

---

## Requisitos Funcionais (RF)

### Cadastro e Acesso

| ID   | Descrição |
|------|-----------|
| RF01 | O sistema deve permitir o cadastro de usuários com perfis distintos: investidor pessoa física, investidor pessoa jurídica, assessor de investimentos e administrador da corretora. |
| RF02 | O sistema deve realizar o processo de KYC (Know Your Customer), coletando documentos e dados cadastrais obrigatórios antes da liberação da conta. |
| RF03 | O sistema deve aplicar o questionário de suitability para determinar o perfil de risco do investidor. |
| RF04 | O sistema deve exigir autenticação multifator (MFA) para login e para confirmação de ordens de alto valor. |
| RF05 | O sistema deve bloquear automaticamente novas contas até a validação documental ser concluída pela área de compliance. |
| RF06 | O sistema deve permitir que o investidor vincule uma ou mais contas bancárias para transferência de recursos (depósito e saque). |

### Negociação de Ativos

| ID   | Descrição |
|------|-----------|
| RF07 | O sistema deve exibir cotações de ativos (ações, fundos, renda fixa) em tempo real, integradas à bolsa (B3) e a provedores de dados de mercado. |
| RF08 | O sistema deve permitir o envio de ordens de compra e venda do tipo mercado, limitada e stop. |
| RF09 | O sistema deve validar se o investidor possui saldo ou ativos suficientes antes de aceitar uma ordem. |
| RF10 | O sistema deve restringir operações a produtos compatíveis com o perfil de risco do investidor, alertando ou bloqueando operações incompatíveis conforme configuração de compliance. |
| RF11 | O sistema deve permitir o cancelamento de uma ordem enquanto ela não tiver sido executada. |
| RF12 | O sistema deve registrar a execução (parcial ou total) de cada ordem, com preço, quantidade e horário. |
| RF13 | O sistema deve calcular e aplicar automaticamente taxas de corretagem e emolumentos sobre cada operação executada. |
| RF14 | O sistema deve permitir operações programadas (ordens de longa duração, válidas até data especificada). |

### Carteira e Custódia

| ID   | Descrição |
|------|-----------|
| RF15 | O sistema deve manter a posição consolidada de ativos de cada investidor em tempo real. |
| RF16 | O sistema deve calcular o valor atualizado da carteira do investidor com base nas cotações vigentes. |
| RF17 | O sistema deve registrar eventos de custódia (desdobramentos, bonificações, dividendos, juros sobre capital próprio) e refleti-los automaticamente na carteira. |
| RF18 | O sistema deve permitir a transferência de custódia de ativos de/para outra instituição, seguindo os padrões da B3. |
| RF19 | O sistema deve gerar relatório consolidado de rentabilidade da carteira por período. |

### Renda Fixa e Fundos

| ID   | Descrição |
|------|-----------|
| RF20 | O sistema deve disponibilizar catálogo de produtos de renda fixa (CDB, LCI, LCA, Tesouro Direto) com características de prazo, taxa e liquidez. |
| RF21 | O sistema deve permitir a aplicação e o resgate de produtos de renda fixa, respeitando as regras de liquidez de cada produto. |
| RF22 | O sistema deve permitir a aplicação e o resgate em cotas de fundos de investimento, calculando a cota do dia conforme regra do fundo. |

### Compliance e Prevenção a Fraudes

| ID   | Descrição |
|------|-----------|
| RF23 | O sistema deve monitorar transações em busca de padrões suspeitos de lavagem de dinheiro, conforme normas da CVM e do COAF. |
| RF24 | O sistema deve permitir que a área de compliance bloqueie temporariamente a conta de um investidor para investigação. |
| RF25 | O sistema deve gerar relatórios regulatórios periódicos exigidos pela CVM e pelo Banco Central. |
| RF26 | O sistema deve registrar de forma imutável todas as ordens enviadas, executadas e canceladas, para fins de auditoria regulatória. |
| RF27 | O sistema deve calcular e reter automaticamente o imposto de renda devido sobre operações de renda variável, conforme regras vigentes. |

### Assessoria e Atendimento

| ID   | Descrição |
|------|-----------|
| RF28 | O sistema deve permitir que o assessor de investimentos visualize a carteira dos clientes sob sua responsabilidade, mediante autorização do investidor. |
| RF29 | O sistema deve permitir que o assessor registre recomendações de investimento para seus clientes. |
| RF30 | O sistema deve disponibilizar canal de mensagens entre investidor e assessor dentro da plataforma. |

### Relatórios e Painel Administrativo

| ID   | Descrição |
|------|-----------|
| RF31 | O sistema deve disponibilizar ao administrador dashboards com volume de operações, receita de corretagem e captação líquida. |
| RF32 | O sistema deve permitir que o administrador configure as tabelas de taxas de corretagem por tipo de ativo e perfil de cliente. |
| RF33 | O sistema deve permitir a emissão do informe de rendimentos anual para fins de declaração de imposto de renda do investidor. |

---

## Requisitos Não Funcionais (RNF)

| ID    | Categoria         | Descrição |
|-------|-------------------|-----------|
| RNF01 | Segurança         | O sistema deve exigir autenticação multifator para login e para confirmação de operações acima de um valor configurável. |
| RNF02 | Segurança         | Toda comunicação com provedores de dados de mercado e com a B3 deve ocorrer por canais criptografados. |
| RNF03 | Desempenho        | O envio e a confirmação de uma ordem devem ser processados em até 300 milissegundos sob condições normais de operação. |
| RNF04 | Disponibilidade   | A plataforma de negociação deve ter disponibilidade mínima de 99,95% durante o horário de pregão. |
| RNF05 | Confiabilidade    | O processamento de ordens deve ser transacional e sequencialmente consistente, evitando execução duplicada ou perda de ordens. |
| RNF06 | Escalabilidade    | O sistema deve suportar picos de volume de ordens em momentos de alta volatilidade do mercado sem degradação perceptível. |
| RNF07 | Conformidade      | O sistema deve estar em conformidade com as normas da CVM, B3, Banco Central e COAF aplicáveis a corretoras de valores. |
| RNF08 | Conformidade      | O sistema deve estar em conformidade com a LGPD no tratamento de dados pessoais e financeiros dos investidores. |
| RNF09 | Rastreabilidade   | Toda ordem, execução, cancelamento e movimentação financeira deve gerar registro imutável e auditável, com timestamp preciso. |
| RNF10 | Auditabilidade    | O sistema deve permitir a reconstituição completa do histórico de operações de um investidor para fins de auditoria ou fiscalização. |
| RNF11 | Resiliência       | Falhas em provedores externos de cotação não devem interromper o funcionamento geral da plataforma, devendo haver contingência de fonte de dados. |
| RNF12 | Monitoramento     | O sistema deve monitorar em tempo real a latência de execução de ordens e alertar a equipe técnica em caso de degradação. |
| RNF13 | Usabilidade       | A plataforma deve ser responsiva e oferecer visualização clara de cotações e posições tanto em desktop quanto em dispositivos móveis. |
| RNF14 | Integridade       | Os cálculos de posição, rentabilidade e impostos devem ser auditáveis e reprodutíveis a qualquer momento. |
| RNF15 | Continuidade      | O sistema deve possuir plano de contingência e recuperação de desastres compatível com a criticidade de uma infraestrutura de mercado financeiro. |

---

## Histórias de Usuário (HU)

### Perfil: Investidor

**HU01 — Completar cadastro e KYC**
> Como investidor, quero completar meu cadastro e enviar os documentos exigidos, para ter minha conta liberada para operar.

*Critérios de aceite:*
- A conta deve permanecer bloqueada para operações até a validação documental ser concluída.
- O investidor deve ser notificado sobre pendências ou reprovações no cadastro.

---

**HU02 — Responder questionário de suitability**
> Como investidor, quero responder ao questionário de perfil de risco, para que a plataforma me oriente sobre produtos compatíveis com meu perfil.

*Critérios de aceite:*
- O sistema deve calcular automaticamente o perfil (conservador, moderado, arrojado) com base nas respostas.
- Operações incompatíveis com o perfil devem gerar alerta antes da confirmação.

---

**HU03 — Enviar ordem de compra ou venda**
> Como investidor, quero enviar uma ordem de compra ou venda de um ativo, para executar minha estratégia de investimento.

*Critérios de aceite:*
- O sistema deve validar saldo ou posição suficiente antes de aceitar a ordem.
- O investidor deve poder acompanhar o status da ordem (pendente, executada, cancelada) em tempo real.

---

**HU04 — Acompanhar carteira consolidada**
> Como investidor, quero visualizar minha carteira consolidada com valor atualizado, para acompanhar meus investimentos.

*Critérios de aceite:*
- Os valores devem refletir as cotações mais recentes disponíveis.
- Eventos como dividendos e desdobramentos devem ser refletidos automaticamente na posição.

---

**HU05 — Aplicar em renda fixa**
> Como investidor, quero aplicar em um produto de renda fixa disponível na plataforma, para diversificar meus investimentos.

*Critérios de aceite:*
- O sistema deve exibir claramente prazo, taxa e condições de liquidez antes da confirmação.
- O resgate antecipado, quando permitido, deve seguir as regras específicas do produto.

---

**HU06 — Emitir informe de rendimentos**
> Como investidor, quero gerar meu informe de rendimentos anual, para utilizá-lo na minha declaração de imposto de renda.

*Critérios de aceite:*
- O informe deve consolidar todas as operações e rendimentos do ano-calendário selecionado.
- O documento deve estar disponível para download em formato PDF.

---

### Perfil: Assessor de Investimentos

**HU07 — Visualizar carteiras de clientes**
> Como assessor, quero visualizar a carteira dos clientes sob minha responsabilidade, para acompanhar seus investimentos e sugerir ajustes.

*Critérios de aceite:*
- O acesso à carteira do cliente deve depender de autorização prévia concedida pelo investidor.
- O assessor não deve poder enviar ordens em nome do cliente sem procuração eletrônica registrada.

---

**HU08 — Registrar recomendação de investimento**
> Como assessor, quero registrar uma recomendação de investimento para um cliente, para documentar minha orientação profissional.

*Critérios de aceite:*
- A recomendação deve ficar visível para o cliente na plataforma.
- O histórico de recomendações deve ficar disponível para consulta futura.

---

### Perfil: Compliance / Administrador

**HU09 — Investigar transação suspeita**
> Como analista de compliance, quero visualizar transações sinalizadas por padrões suspeitos, para investigá-las conforme normas de prevenção à lavagem de dinheiro.

*Critérios de aceite:*
- O sistema deve permitir bloquear temporariamente a conta durante a investigação.
- Toda ação de bloqueio ou liberação deve gerar registro de auditoria com justificativa.

---

**HU10 — Configurar tabela de taxas**
> Como administrador, quero configurar as taxas de corretagem por tipo de ativo e perfil de cliente, para ajustar o modelo comercial da corretora.

*Critérios de aceite:*
- A alteração de taxas deve afetar apenas operações futuras.
- O sistema deve registrar log com data, usuário e valores anterior e novo de cada alteração.

---

**HU11 — Gerar relatório regulatório**
> Como administrador, quero gerar os relatórios periódicos exigidos pela CVM e pelo Banco Central, para manter a corretora em conformidade regulatória.

*Critérios de aceite:*
- O relatório deve ser gerado no formato e periodicidade exigidos pelo órgão regulador.
- O sistema deve manter histórico dos relatórios já gerados e enviados.

---

**HU12 — Monitorar volume de operações**
> Como administrador, quero acompanhar dashboards com volume de operações e receita de corretagem, para avaliar o desempenho comercial da corretora.

*Critérios de aceite:*
- O painel deve permitir filtro por período, tipo de ativo e perfil de cliente.
- Os dados devem refletir informações atualizadas do dia de operação.
