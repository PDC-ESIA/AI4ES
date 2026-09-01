# Sistema de Reservas para Quadras Esportivas — Requisitos

---

## Requisitos Funcionais (RF)

| ID    | Descrição |
|-------|-----------|
| RF01  | O sistema deve permitir que o operador cadastre quadras informando nome, tipo (futebol, tênis, vôlei etc.), horário de funcionamento e valor da hora. |
| RF02  | O sistema deve permitir que o operador edite ou remova uma quadra cadastrada. |
| RF03  | O sistema deve permitir que o operador bloqueie horários específicos de uma quadra para manutenção ou feriados. |
| RF04  | O sistema deve exibir ao cliente, sem exigir cadastro ou login, os horários disponíveis por quadra e por data. |
| RF05  | O sistema deve permitir que o cliente realize uma reserva informando nome, telefone e horário desejado. |
| RF06  | O sistema deve gerar um código de confirmação único para cada reserva realizada. |
| RF07  | O sistema deve impedir a reserva de um horário já ocupado por outro cliente. |
| RF08  | O sistema deve permitir que o cliente cancele sua própria reserva informando o código de confirmação. |
| RF09  | O sistema deve permitir que o operador cancele uma reserva, registrando o motivo do cancelamento. |
| RF10  | O sistema deve enviar ao cliente uma confirmação da reserva por e-mail, contendo quadra, data, horário e código. |
| RF11  | O sistema deve permitir que o operador visualize a agenda diária consolidada de todas as quadras. |
| RF12  | O sistema deve permitir que o operador configure valores diferenciados por faixa de horário (ex.: horário nobre). |

---

## Requisitos Não Funcionais (RNF)

| ID    | Categoria         | Descrição |
|-------|-------------------|-----------|
| RNF01 | Usabilidade       | A interface do cliente deve ser responsiva e funcionar adequadamente em dispositivos móveis e desktops. |
| RNF02 | Desempenho        | O calendário de disponibilidade deve ser carregado em até 2 segundos. |
| RNF03 | Segurança         | A área administrativa do operador deve ser protegida por autenticação. |
| RNF04 | Disponibilidade   | O sistema deve estar disponível 99% do tempo em regime 24/7. |
| RNF05 | Confiabilidade    | A confirmação de reserva deve ser atômica, impedindo duplo agendamento do mesmo horário em caso de requisições simultâneas. |
| RNF06 | Compatibilidade   | O sistema deve ser acessível nos principais navegadores modernos. |
| RNF07 | Manutenibilidade  | O sistema deve ser desenvolvido de forma modular, facilitando a inclusão de novas modalidades esportivas. |

---

## Histórias de Usuário (HU)

### Perfil: Operador

**HU01 — Cadastrar quadra**
> Como operador, quero cadastrar uma quadra com tipo, horário de funcionamento e valor da hora, para disponibilizá-la para reservas.

*Critérios de aceite:*
- Nome, tipo e valor da hora são campos obrigatórios.
- A quadra deve aparecer imediatamente na listagem de disponibilidade do cliente.

---

**HU02 — Bloquear horários para manutenção**
> Como operador, quero bloquear horários específicos de uma quadra, para evitar reservas durante manutenções ou feriados.

*Critérios de aceite:*
- Horários bloqueados não devem aparecer como disponíveis para o cliente.
- O operador pode remover um bloqueio a qualquer momento.

---

**HU03 — Visualizar agenda consolidada**
> Como operador, quero visualizar a agenda diária de todas as quadras em uma única tela, para ter uma visão geral da ocupação do espaço.

*Critérios de aceite:*
- A agenda deve exibir todas as quadras e seus horários reservados ou livres no dia selecionado.
- Deve ser possível navegar entre diferentes datas.

---

**HU04 — Cancelar reserva com justificativa**
> Como operador, quero cancelar uma reserva registrando o motivo, para liberar o horário quando necessário.

*Critérios de aceite:*
- O motivo do cancelamento deve ser obrigatório.
- O cliente deve ser notificado por e-mail sobre o cancelamento.

---

### Perfil: Cliente

**HU05 — Consultar disponibilidade sem cadastro**
> Como cliente, quero consultar os horários disponíveis de uma quadra sem precisar me cadastrar, para verificar rapidamente se posso jogar no horário desejado.

*Critérios de aceite:*
- A consulta deve ser acessível diretamente pelo navegador, sem login.
- Os horários já ocupados devem ser exibidos como indisponíveis.

---

**HU06 — Realizar reserva**
> Como cliente, quero reservar um horário informando meus dados de contato, para garantir o uso da quadra.

*Critérios de aceite:*
- O sistema deve validar que o horário ainda está disponível no momento da confirmação.
- Um código de confirmação deve ser exibido na tela e enviado por e-mail.

---

**HU07 — Cancelar minha reserva**
> Como cliente, quero cancelar minha reserva usando o código de confirmação, para liberar o horário caso eu não possa comparecer.

*Critérios de aceite:*
- O cancelamento só deve ser permitido mediante código válido.
- O horário deve voltar a ficar disponível imediatamente após o cancelamento.
