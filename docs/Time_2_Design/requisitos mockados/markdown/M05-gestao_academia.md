# Sistema de Gestão de Academia — Requisitos

---

## Requisitos Funcionais (RF)

### Gestão de Usuários e Acesso

| ID   | Descrição |
|------|-----------|
| RF01 | O sistema deve permitir o cadastro de usuários com perfis distintos: administrador, recepcionista, instrutor e aluno. |
| RF02 | O sistema deve permitir que usuários se autentiquem e encerrem sessão na plataforma. |
| RF03 | O sistema deve permitir que a recepcionista cadastre um novo aluno com dados pessoais e plano contratado. |

### Planos e Matrículas

| ID   | Descrição |
|------|-----------|
| RF04 | O sistema deve permitir que o administrador cadastre planos de assinatura com nome, periodicidade e valor. |
| RF05 | O sistema deve permitir que a recepcionista associe um aluno a um plano ativo. |
| RF06 | O sistema deve permitir que a recepcionista renove, altere ou cancele o plano de um aluno. |
| RF07 | O sistema deve bloquear automaticamente o acesso do aluno cuja mensalidade estiver vencida por mais de um período de tolerância configurável. |
| RF08 | O sistema deve cobrar automaticamente a mensalidade do aluno via gateway de pagamento na data de vencimento. |
| RF09 | O sistema deve notificar o aluno por e-mail sobre cobranças próximas do vencimento e cobranças recusadas. |

### Controle de Acesso e Frequência

| ID   | Descrição |
|------|-----------|
| RF10 | O sistema deve permitir que o aluno registre entrada e saída na academia via check-in (cartão, QR Code ou biometria simulada). |
| RF11 | O sistema deve impedir o check-in de alunos com plano vencido ou suspenso. |
| RF12 | O sistema deve exibir à recepção a frequência diária de alunos na academia. |

### Aulas e Treinos

| ID   | Descrição |
|------|-----------|
| RF13 | O sistema deve permitir que o instrutor cadastre aulas coletivas com horário, capacidade máxima e modalidade. |
| RF14 | O sistema deve permitir que o aluno se inscreva em uma aula coletiva, respeitando o limite de vagas. |
| RF15 | O sistema deve permitir que o aluno cancele sua inscrição em uma aula com antecedência mínima configurável. |
| RF16 | O sistema deve permitir que o instrutor monte uma ficha de treino individual para um aluno, com exercícios, séries e repetições. |
| RF17 | O sistema deve permitir que o aluno visualize sua ficha de treino atual pelo aplicativo ou portal. |
| RF18 | O sistema deve permitir que o instrutor atualize periodicamente a ficha de treino de um aluno. |

### Gestão Administrativa

| ID   | Descrição |
|------|-----------|
| RF19 | O sistema deve permitir que o administrador visualize relatórios de faturamento mensal e inadimplência. |
| RF20 | O sistema deve permitir que o administrador cadastre e controle equipamentos da academia, incluindo datas de manutenção. |

---

## Requisitos Não Funcionais (RNF)

| ID    | Categoria         | Descrição |
|-------|-------------------|-----------|
| RNF01 | Segurança         | O acesso a cada módulo do sistema deve respeitar o perfil do usuário autenticado. |
| RNF02 | Segurança         | A comunicação com o gateway de pagamento deve seguir as diretrizes PCI-DSS; dados de cartão não devem ser armazenados no sistema. |
| RNF03 | Desempenho        | O processo de check-in deve ser concluído em até 2 segundos por aluno. |
| RNF04 | Disponibilidade   | O sistema deve ter disponibilidade mínima de 99% ao mês, especialmente no controle de acesso. |
| RNF05 | Confiabilidade    | A cobrança automática de mensalidades deve ser transacional, evitando cobranças duplicadas em caso de falha. |
| RNF06 | Usabilidade       | O aplicativo do aluno deve ser responsivo e de fácil uso para consulta de treino e aulas. |
| RNF07 | Escalabilidade    | O sistema deve suportar múltiplas unidades de academia sob a mesma administração. |
| RNF08 | Conformidade      | O sistema deve estar em conformidade com a LGPD no tratamento de dados pessoais e de pagamento dos alunos. |
| RNF09 | Rastreabilidade   | Toda alteração em plano, cobrança ou bloqueio de acesso deve gerar registro com data, hora e usuário responsável. |
| RNF10 | Compatibilidade   | O sistema deve funcionar nos principais navegadores modernos e em dispositivos móveis Android e iOS. |

---

## Histórias de Usuário (HU)

### Perfil: Recepcionista

**HU01 — Matricular novo aluno**
> Como recepcionista, quero cadastrar um novo aluno e associá-lo a um plano, para iniciar sua matrícula na academia.

*Critérios de aceite:*
- Dados pessoais e plano são obrigatórios para concluir a matrícula.
- O aluno deve poder realizar check-in imediatamente após a matrícula ativa.

---

**HU02 — Gerenciar plano do aluno**
> Como recepcionista, quero renovar, alterar ou cancelar o plano de um aluno, para manter a base de assinaturas atualizada.

*Critérios de aceite:*
- Alterações de plano devem recalcular automaticamente o valor da próxima cobrança.
- O cancelamento deve registrar a data efetiva de encerramento do acesso.

---

### Perfil: Instrutor

**HU03 — Criar aula coletiva**
> Como instrutor, quero cadastrar uma aula coletiva com horário e capacidade, para que os alunos possam se inscrever.

*Critérios de aceite:*
- A aula não deve aceitar inscrições além da capacidade máxima definida.
- Alunos inscritos devem ser notificados em caso de cancelamento da aula pelo instrutor.

---

**HU04 — Montar ficha de treino**
> Como instrutor, quero montar uma ficha de treino individual para um aluno, para orientar seus exercícios na academia.

*Critérios de aceite:*
- A ficha deve conter exercícios, séries, repetições e observações.
- O aluno deve conseguir visualizar a ficha atualizada imediatamente após a publicação.

---

### Perfil: Aluno

**HU05 — Fazer check-in na academia**
> Como aluno, quero registrar minha entrada na academia, para ter minha frequência contabilizada.

*Critérios de aceite:*
- O check-in deve ser recusado se o plano do aluno estiver vencido.
- O horário de entrada deve ficar registrado no histórico de frequência do aluno.

---

**HU06 — Inscrever-se em aula coletiva**
> Como aluno, quero me inscrever em uma aula coletiva disponível, para participar de atividades em grupo.

*Critérios de aceite:*
- A inscrição só deve ser permitida se houver vagas disponíveis.
- O aluno deve poder cancelar a inscrição respeitando o prazo mínimo de antecedência.

---

**HU07 — Consultar ficha de treino**
> Como aluno, quero consultar minha ficha de treino atual, para saber quais exercícios realizar durante meu treino.

*Critérios de aceite:*
- A ficha exibida deve ser sempre a versão mais recente cadastrada pelo instrutor.
- O aluno deve conseguir visualizar o histórico de fichas anteriores.

---

### Perfil: Administrador

**HU08 — Acompanhar inadimplência**
> Como administrador, quero visualizar um relatório de inadimplência dos alunos, para tomar ações de cobrança ou renegociação.

*Critérios de aceite:*
- O relatório deve listar alunos com pagamento em atraso e o número de dias de atraso.
- O relatório deve poder ser filtrado por período e por plano.

---

**HU09 — Gerenciar equipamentos**
> Como administrador, quero cadastrar os equipamentos da academia e suas datas de manutenção, para planejar a manutenção preventiva.

*Critérios de aceite:*
- O sistema deve alertar quando um equipamento estiver próximo da data de manutenção programada.
- O histórico de manutenções realizadas deve ficar registrado por equipamento.
