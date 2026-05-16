# Sistema de Agenda de Clínica — Requisitos

---

## Requisitos Funcionais (RF)

| ID   | Descrição |
|------|-----------|
| RF01 | O sistema deve permitir que a recepcionista cadastre novos pacientes, informando nome, data de nascimento, telefone e e-mail. |
| RF02 | O sistema deve permitir que a recepcionista edite os dados cadastrais de um paciente. |
| RF03 | O sistema deve permitir que a recepcionista pesquise pacientes pelo nome ou por outros dados cadastrais. |
| RF04 | O sistema deve exibir a agenda do profissional com os horários disponíveis e ocupados. |
| RF05 | O sistema deve permitir que a recepcionista registre uma consulta associando um paciente a um horário disponível. |
| RF06 | O sistema deve impedir o agendamento de duas consultas no mesmo horário. |
| RF07 | O sistema deve permitir que a recepcionista cancele uma consulta agendada. |
| RF08 | O sistema deve permitir que a recepcionista remarcque uma consulta para outro horário disponível. |
| RF09 | O sistema deve enviar um e-mail de confirmação ao paciente quando um agendamento for registrado. |
| RF10 | O sistema deve enviar um e-mail de notificação ao paciente quando uma consulta for cancelada ou remarcada. |
| RF11 | O sistema deve permitir configurar os horários de atendimento disponíveis do profissional (grade de horários). |
| RF12 | O sistema deve exibir um histórico de consultas realizadas e canceladas por paciente. |

---

## Requisitos Não Funcionais (RNF)

| ID    | Categoria      | Descrição |
|-------|----------------|-----------|
| RNF01 | Segurança      | O acesso ao sistema deve ser restrito a usuários autenticados (recepcionista e administrador). |
| RNF02 | Segurança      | Os dados dos pacientes devem ser armazenados em conformidade com a LGPD. |
| RNF03 | Usabilidade    | A interface deve permitir visualizar a agenda em formato de calendário (diário e semanal). |
| RNF04 | Desempenho     | O carregamento da agenda do profissional deve ocorrer em até 2 segundos. |
| RNF05 | Confiabilidade | O envio do e-mail de confirmação deve ocorrer em até 5 minutos após o registro do agendamento. |
| RNF06 | Disponibilidade| O sistema deve estar disponível durante o horário de funcionamento da clínica com no mínimo 99% de uptime. |
| RNF07 | Compatibilidade| O sistema deve funcionar nos principais navegadores modernos (Chrome, Firefox, Safari, Edge). |
| RNF08 | Manutenibilidade| O sistema deve registrar logs de operações críticas (criação, cancelamento e remarcação de consultas). |

---

## Histórias de Usuário (HU)

### Perfil: Recepcionista

**HU01 — Cadastrar paciente**
> Como recepcionista, quero cadastrar um novo paciente com seus dados pessoais e de contato, para que ele possa ser vinculado a agendamentos futuros.

*Critérios de aceite:*
- Os campos nome, telefone e e-mail são obrigatórios.
- O sistema deve validar o formato do e-mail antes de salvar.
- O sistema não deve permitir cadastro duplicado para um mesmo CPF ou e-mail.

---

**HU02 — Pesquisar paciente**
> Como recepcionista, quero pesquisar um paciente pelo nome ou telefone, para localizar rapidamente seu cadastro ao registrar uma consulta.

*Critérios de aceite:*
- A busca deve retornar resultados parciais (ex.: parte do nome).
- Os resultados devem ser exibidos em lista com nome e telefone.

---

**HU03 — Visualizar agenda do profissional**
> Como recepcionista, quero visualizar a agenda do profissional em formato de calendário, para identificar horários livres e ocupados com facilidade.

*Critérios de aceite:*
- A agenda deve exibir visões diária e semanal.
- Horários ocupados e disponíveis devem ter distinção visual clara.
- Deve ser possível navegar entre dias e semanas.

---

**HU04 — Registrar agendamento**
> Como recepcionista, quero agendar uma consulta para um paciente em um horário disponível, para reservar o atendimento na agenda do profissional.

*Critérios de aceite:*
- Apenas horários disponíveis devem poder ser selecionados.
- O sistema deve exibir confirmação após o registro bem-sucedido.
- O paciente deve receber um e-mail de confirmação automaticamente.

---

**HU05 — Cancelar agendamento**
> Como recepcionista, quero cancelar uma consulta agendada, para liberar o horário na agenda e informar o paciente.

*Critérios de aceite:*
- O sistema deve solicitar confirmação antes de efetivar o cancelamento.
- O horário cancelado deve voltar a ficar disponível na agenda imediatamente.
- O paciente deve receber um e-mail informando o cancelamento.

---

**HU06 — Remarcar agendamento**
> Como recepcionista, quero remarcar uma consulta para outro horário disponível, para atender mudanças na disponibilidade do paciente ou do profissional.

*Critérios de aceite:*
- O novo horário deve ser selecionado dentre os horários disponíveis na grade.
- O horário anterior deve ser liberado automaticamente.
- O paciente deve receber um e-mail com o novo horário confirmado.

---

**HU07 — Consultar histórico do paciente**
> Como recepcionista, quero visualizar o histórico de consultas de um paciente, para ter contexto sobre seus atendimentos anteriores.

*Critérios de aceite:*
- O histórico deve listar consultas realizadas e canceladas com data, horário e status.
- Deve ser possível acessar o histórico a partir do cadastro do paciente.

---

### Perfil: Paciente

**HU08 — Receber confirmação de agendamento por e-mail**
> Como paciente, quero receber um e-mail quando minha consulta for agendada, para ter a confirmação do dia e horário do meu atendimento.

*Critérios de aceite:*
- O e-mail deve conter nome do profissional, data, horário e endereço da clínica.
- O e-mail deve ser enviado em até 5 minutos após o registro do agendamento.

---

**HU09 — Receber notificação de cancelamento ou remarcação por e-mail**
> Como paciente, quero ser notificado por e-mail caso minha consulta seja cancelada ou remarcada, para me organizar com antecedência.

*Critérios de aceite:*
- Em caso de cancelamento, o e-mail deve informar claramente que a consulta foi cancelada.
- Em caso de remarcação, o e-mail deve conter o novo dia e horário confirmados.