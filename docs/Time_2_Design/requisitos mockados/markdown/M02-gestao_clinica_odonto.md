# Sistema de Gestão de Clínica Odontológica — Requisitos

---

## Requisitos Funcionais (RF)

### Gestão de Usuários e Acesso

| ID   | Descrição |
|------|-----------|
| RF01 | O sistema deve permitir o cadastro de usuários com perfis distintos: administrador, recepcionista, dentista e paciente. |
| RF02 | O sistema deve restringir o acesso às funcionalidades conforme o perfil do usuário autenticado. |

### Agenda

| ID   | Descrição |
|------|-----------|
| RF03 | O sistema deve manter uma agenda individual para cada dentista cadastrado. |
| RF04 | O sistema deve permitir que a recepcionista visualize, em uma tela unificada, a agenda de todos os dentistas. |
| RF05 | O sistema deve permitir que a recepcionista agende, cancele e remarcque consultas para qualquer dentista. |
| RF06 | O sistema deve impedir o agendamento de dois atendimentos sobrepostos na agenda de um mesmo dentista. |
| RF07 | O sistema deve permitir configurar a grade de horários de atendimento de cada dentista individualmente. |
| RF08 | O sistema deve enviar notificação por e-mail ao paciente quando um agendamento for confirmado, cancelado ou remarcado. |

### Prontuário Digital

| ID   | Descrição |
|------|-----------|
| RF09 | O sistema deve manter um prontuário digital por paciente, com histórico completo de procedimentos realizados. |
| RF10 | O sistema deve permitir que o dentista registre procedimentos no prontuário durante ou após o atendimento, incluindo data, descrição e observações clínicas. |
| RF11 | O sistema deve permitir o upload e o armazenamento de radiografias e outros documentos clínicos vinculados ao prontuário do paciente. |
| RF12 | O sistema deve permitir que o dentista consulte e edite os registros do prontuário dos seus próprios pacientes. |
| RF13 | O sistema deve registrar data, hora e dentista responsável em cada entrada do prontuário, garantindo rastreabilidade. |

### Controle de Materiais e Equipamentos

| ID   | Descrição |
|------|-----------|
| RF14 | O sistema deve permitir o cadastro de materiais odontológicos e equipamentos, com nome, quantidade em estoque e quantidade mínima. |
| RF15 | O sistema deve permitir o registro de entradas e saídas de materiais do estoque. |
| RF16 | O sistema deve emitir alerta quando o estoque de um material atingir ou ficar abaixo da quantidade mínima configurada. |
| RF17 | O sistema deve permitir vincular o consumo de materiais a um atendimento específico. |

### Faturamento

| ID   | Descrição |
|------|-----------|
| RF18 | O sistema deve permitir o cadastro de procedimentos odontológicos com código, descrição e valor. |
| RF19 | O sistema deve permitir o registro de convênios com suas tabelas de procedimentos e valores correspondentes. |
| RF20 | O sistema deve gerar uma cobrança por atendimento, discriminando procedimentos realizados, valores e modalidade de pagamento (convênio ou particular). |
| RF21 | O sistema deve permitir o registro do pagamento de uma cobrança e controlar cobranças em aberto. |
| RF22 | O sistema deve gerar relatórios de faturamento por período, por dentista e por modalidade de pagamento. |

### Portal do Paciente

| ID   | Descrição |
|------|-----------|
| RF23 | O sistema deve disponibilizar um portal web para acesso dos pacientes. |
| RF24 | O portal deve permitir que o paciente visualize seus agendamentos futuros e o histórico de consultas. |
| RF25 | O portal deve permitir que o paciente acesse e faça download dos documentos clínicos disponibilizados pelo dentista (laudos, radiografias, receitas). |

---

## Requisitos Não Funcionais (RNF)

| ID    | Categoria        | Descrição |
|-------|------------------|-----------|
| RNF01 | Segurança        | O acesso ao sistema deve exigir autenticação; sessões inativas por mais de 30 minutos devem ser encerradas automaticamente. |
| RNF02 | Segurança        | Os dados clínicos dos pacientes devem ser armazenados em conformidade com a LGPD e as normas do CFO (Conselho Federal de Odontologia). |
| RNF03 | Segurança        | Documentos clínicos (radiografias, laudos) devem ser armazenados com controle de acesso, acessíveis apenas por dentistas vinculados ao paciente e pelo próprio paciente. |
| RNF04 | Segurança        | As senhas dos usuários devem ser armazenadas com hash seguro (ex.: bcrypt). |
| RNF05 | Rastreabilidade  | Toda alteração em prontuário deve gerar um log imutável com usuário, data e hora da modificação. |
| RNF06 | Desempenho       | A visualização da agenda unificada de todos os dentistas deve ser carregada em até 3 segundos. |
| RNF07 | Escalabilidade   | O armazenamento de radiografias e documentos clínicos deve utilizar serviço externo de object storage, desacoplado do servidor da aplicação. |
| RNF08 | Disponibilidade  | O sistema deve estar disponível durante o horário de funcionamento da clínica com no mínimo 99,5% de uptime. |
| RNF09 | Usabilidade      | A interface deve ser responsiva e funcionar adequadamente em dispositivos móveis e desktops. |
| RNF10 | Compatibilidade  | O sistema deve funcionar nos principais navegadores modernos (Chrome, Firefox, Safari, Edge). |
| RNF11 | Backup           | O sistema deve realizar backup automático diário dos dados, com retenção mínima de 30 dias. |

---

## Histórias de Usuário (HU)

### Perfil: Recepcionista

**HU01 — Visualizar agenda unificada dos dentistas**
> Como recepcionista, quero visualizar em uma única tela a agenda de todos os dentistas, para ter visão completa da disponibilidade da clínica e otimizar o agendamento.

*Critérios de aceite:*
- A agenda unificada deve exibir visões diária e semanal com identificação clara de cada dentista.
- Horários livres e ocupados devem ter distinção visual por dentista.
- Deve ser possível filtrar a visualização por dentista específico.

---

**HU02 — Agendar, cancelar e remarcar consulta**
> Como recepcionista, quero agendar, cancelar e remarcar consultas para qualquer dentista, para gerenciar a agenda da clínica de forma centralizada.

*Critérios de aceite:*
- Somente horários disponíveis dentro da grade configurada do dentista devem ser selecionáveis.
- O sistema deve bloquear tentativas de sobreposição de horários.
- O paciente deve receber e-mail de confirmação, cancelamento ou remarcação automaticamente.

---

**HU03 — Registrar pagamento de cobrança**
> Como recepcionista, quero registrar o pagamento de uma cobrança gerada após um atendimento, para manter o controle financeiro atualizado.

*Critérios de aceite:*
- Deve ser possível registrar pagamento total ou parcial.
- Cobranças em aberto devem ser facilmente identificadas em uma listagem.
- O status da cobrança deve ser atualizado imediatamente após o registro do pagamento.

---

### Perfil: Dentista

**HU04 — Registrar procedimento no prontuário**
> Como dentista, quero registrar os procedimentos realizados no prontuário do paciente durante ou após o atendimento, para manter o histórico clínico completo e rastreável.

*Critérios de aceite:*
- O registro deve incluir data, descrição do procedimento e observações clínicas.
- Cada entrada deve ser automaticamente associada ao dentista responsável com data e hora.
- O prontuário deve exibir o histórico em ordem cronológica decrescente.

---

**HU05 — Anexar radiografias e documentos clínicos ao prontuário**
> Como dentista, quero fazer upload de radiografias e outros documentos clínicos vinculados ao prontuário do paciente, para centralizar toda a documentação no sistema.

*Critérios de aceite:*
- O sistema deve aceitar formatos comuns de imagem (JPEG, PNG) e documentos (PDF).
- Cada arquivo deve ser identificado com nome, tipo, data de upload e dentista responsável.
- O acesso aos documentos deve ser restrito ao dentista vinculado ao paciente e ao próprio paciente via portal.

---

**HU06 — Consultar prontuário completo do paciente**
> Como dentista, quero consultar o prontuário completo de um paciente, incluindo histórico de procedimentos e documentos clínicos, para ter contexto clínico completo antes e durante o atendimento.

*Critérios de aceite:*
- O prontuário deve exibir histórico de procedimentos, radiografias e documentos em abas organizadas.
- Deve ser possível localizar um paciente por nome ou CPF.
- O acesso deve ser restrito aos dentistas da clínica.

---

**HU07 — Gerar cobrança após atendimento**
> Como dentista, quero gerar uma cobrança ao final do atendimento discriminando os procedimentos realizados e a modalidade de pagamento (convênio ou particular), para registrar o faturamento corretamente.

*Critérios de aceite:*
- Os procedimentos devem ser selecionados a partir do cadastro de procedimentos da clínica.
- O sistema deve aplicar automaticamente os valores da tabela do convênio quando a modalidade for convênio.
- A cobrança gerada deve ficar disponível para a recepcionista efetuar o registro do pagamento.

---

### Perfil: Administrador

**HU08 — Gerenciar dentistas e suas grades de horário**
> Como administrador, quero cadastrar dentistas e configurar a grade de horários de cada um, para que a agenda reflita corretamente a disponibilidade individual de cada profissional.

*Critérios de aceite:*
- Deve ser possível definir dias da semana e horários de início e fim de atendimento por dentista.
- Alterações na grade devem afetar apenas os agendamentos futuros, sem impactar os já existentes.

---

**HU09 — Gerenciar materiais e receber alertas de estoque baixo**
> Como administrador, quero cadastrar materiais com quantidade mínima e receber alertas quando o estoque atingir esse limite, para garantir que a clínica nunca fique sem insumos críticos.

*Critérios de aceite:*
- O alerta deve ser exibido no painel do administrador de forma destacada, identificando o material e o saldo atual.
- Deve ser possível registrar entradas de reposição diretamente a partir do alerta.

---

**HU10 — Consultar relatório de faturamento**
> Como administrador, quero consultar relatórios de faturamento por período, por dentista e por modalidade de pagamento, para acompanhar a saúde financeira da clínica.

*Critérios de aceite:*
- O relatório deve permitir filtros por intervalo de datas, dentista e modalidade (convênio ou particular).
- Os resultados devem exibir totais agrupados e discriminados por procedimento.
- Deve ser possível exportar o relatório em formato CSV ou PDF.

---

### Perfil: Paciente

**HU11 — Acessar agendamentos pelo portal**
> Como paciente, quero acessar o portal e visualizar meus agendamentos futuros e meu histórico de consultas, para me organizar e ter controle sobre meus atendimentos.

*Critérios de aceite:*
- O portal deve exigir autenticação do paciente.
- Os agendamentos futuros devem exibir data, horário e nome do dentista responsável.
- O histórico deve listar consultas passadas com data e procedimento realizado.

---

**HU12 — Acessar e baixar documentos clínicos pelo portal**
> Como paciente, quero acessar e fazer download dos meus documentos clínicos disponibilizados pelo dentista, para ter cópias dos meus laudos, radiografias e receitas quando precisar.

*Critérios de aceite:*
- Somente documentos explicitamente disponibilizados pelo dentista devem ser visíveis ao paciente.
- O download deve estar disponível para cada documento individualmente.
- O paciente não deve ter acesso às anotações clínicas internas do prontuário.