# Sistema de Administração de Condomínio Residencial — Requisitos

---

## Requisitos Funcionais (RF)

### Gestão de Usuários e Acesso

| ID   | Descrição |
|------|-----------|
| RF01 | O sistema deve permitir o cadastro de usuários com perfis distintos: síndico, condômino, funcionário e administrador. |
| RF02 | O sistema deve restringir o acesso às funcionalidades conforme o perfil do usuário autenticado. |
| RF03 | O sistema deve permitir que todos os usuários se autentiquem e encerrem sessão na plataforma. |

### Gestão de Unidades e Moradores

| ID   | Descrição |
|------|-----------|
| RF04 | O sistema deve permitir que o síndico cadastre, edite e remova unidades (apartamentos/casas), informando bloco, número e tipo. |
| RF05 | O sistema deve permitir que o síndico cadastre moradores e os vincule a uma unidade, informando nome, CPF, e-mail e telefone. |
| RF06 | O sistema deve permitir que o síndico registre se o morador é proprietário ou inquilino. |
| RF07 | O sistema deve permitir que o síndico desative um morador sem excluir seu histórico no sistema. |
| RF08 | O sistema deve permitir que o síndico registre veículos vinculados a uma unidade, informando placa, modelo e cor. |

### Financeiro — Boletos

| ID   | Descrição |
|------|-----------|
| RF09 | O sistema deve permitir que o síndico configure o valor da taxa condominial por unidade ou por tipo de unidade. |
| RF10 | O sistema deve permitir a emissão de boletos de condomínio individuais por unidade, com vencimento configurável. |
| RF11 | O sistema deve integrar com gateway de pagamento para processar e confirmar o pagamento dos boletos. |
| RF12 | O sistema deve atualizar automaticamente o status do boleto para pago após a confirmação do gateway. |
| RF13 | O sistema deve permitir a emissão em lote de boletos para todas as unidades em um único mês de referência. |
| RF14 | O sistema deve permitir que o síndico registre pagamentos realizados fora da plataforma (ex.: depósito bancário). |
| RF15 | O sistema deve exibir ao síndico um painel com inadimplências por unidade e período. |

### Comunicados e Assembleias

| ID   | Descrição |
|------|-----------|
| RF16 | O sistema deve permitir que o síndico publique comunicados visíveis a todos os condôminos no portal. |
| RF17 | O sistema deve notificar os condôminos por e-mail quando um novo comunicado for publicado. |
| RF18 | O sistema deve permitir que o síndico crie assembleias com data, horário, local e pauta. |
| RF19 | O sistema deve permitir o registro da ata de uma assembleia concluída, vinculada ao evento correspondente. |
| RF20 | O sistema deve permitir que condôminos acompanhem assembleias agendadas e acessem atas de assembleias passadas pelo portal. |

### Ocorrências

| ID   | Descrição |
|------|-----------|
| RF21 | O sistema deve permitir que condôminos registrem ocorrências (reclamações, solicitações ou sugestões) pelo portal. |
| RF22 | O sistema deve permitir que funcionários registrem ocorrências internas do condomínio. |
| RF23 | O sistema deve permitir que o síndico visualize, categorize e atualize o status das ocorrências (aberta, em andamento, encerrada). |
| RF24 | O sistema deve notificar o autor da ocorrência por e-mail quando o seu status for atualizado. |

### Reserva de Áreas Comuns

| ID   | Descrição |
|------|-----------|
| RF25 | O sistema deve permitir que o síndico cadastre as áreas comuns disponíveis para reserva, com nome, capacidade e regras de uso. |
| RF26 | O sistema deve permitir que condôminos realizem reservas de áreas comuns pelo portal, selecionando data e horário. |
| RF27 | O sistema deve impedir reservas sobrepostas para uma mesma área comum no mesmo horário. |
| RF28 | O sistema deve permitir que o condômino cancele uma reserva dentro do prazo configurado pelo síndico. |
| RF29 | O sistema deve exibir ao síndico o calendário de reservas de todas as áreas comuns. |

### Controle de Acesso e Visitantes

| ID   | Descrição |
|------|-----------|
| RF30 | O sistema deve permitir que funcionários registrem a entrada e saída de visitantes, informando nome, documento, unidade visitada e horário. |
| RF31 | O sistema deve permitir que condôminos pré-autorizem a entrada de visitantes pelo portal, informando nome e data prevista. |
| RF32 | O sistema deve exibir ao funcionário as pré-autorizações registradas para facilitar a liberação de acesso. |
| RF33 | O sistema deve manter um histórico de acessos de visitantes por unidade, consultável pelo síndico. |

---

## Requisitos Não Funcionais (RNF)

| ID    | Categoria        | Descrição |
|-------|------------------|-----------|
| RNF01 | Segurança        | O acesso ao sistema deve exigir autenticação; sessões inativas por mais de 30 minutos devem ser encerradas automaticamente. |
| RNF02 | Segurança        | As senhas dos usuários devem ser armazenadas com hash seguro (ex.: bcrypt). |
| RNF03 | Segurança        | A integração com o gateway de pagamento deve seguir as diretrizes PCI-DSS; dados de cartão não devem ser armazenados no sistema. |
| RNF04 | Conformidade     | O sistema deve estar em conformidade com a LGPD no tratamento de dados pessoais de moradores, funcionários e visitantes. |
| RNF05 | Rastreabilidade  | Toda operação financeira (emissão, pagamento, registro manual) deve gerar registro imutável com usuário, data e hora. |
| RNF06 | Rastreabilidade  | Todo acesso de visitante deve ser registrado com data, hora, funcionário responsável e unidade visitada. |
| RNF07 | Disponibilidade  | O sistema deve estar disponível 24/7 com uptime mínimo de 99,5% ao mês, dado que condôminos acessam o portal a qualquer hora. |
| RNF08 | Desempenho       | O painel de inadimplências e o calendário de reservas devem ser carregados em até 3 segundos. |
| RNF09 | Usabilidade      | A interface deve ser responsiva e funcionar adequadamente em dispositivos móveis e desktops. |
| RNF10 | Compatibilidade  | O sistema deve funcionar nos principais navegadores modernos (Chrome, Firefox, Safari, Edge). |
| RNF11 | Confiabilidade   | A emissão de boletos em lote deve ser transacional: em caso de falha parcial, o sistema deve registrar quais unidades foram afetadas sem corromper as demais. |
| RNF12 | Backup           | O sistema deve realizar backup automático diário dos dados, com retenção mínima de 90 dias. |
| RNF13 | Manutenibilidade | O sistema deve registrar logs de eventos críticos: emissão e pagamento de boletos, publicação de comunicados, atualizações de ocorrências e registros de acesso. |

---

## Histórias de Usuário (HU)

### Perfil: Síndico

**HU01 — Cadastrar unidades e moradores**
> Como síndico, quero cadastrar as unidades do condomínio e vincular moradores a cada uma delas, para manter o cadastro do condomínio atualizado e organizado.

*Critérios de aceite:*
- Bloco e número são campos obrigatórios para o cadastro de unidade.
- Nome, CPF e e-mail são obrigatórios para o cadastro de morador; o CPF deve ser único no sistema.
- Deve ser possível vincular mais de um morador à mesma unidade (ex.: proprietário e inquilino).

---

**HU02 — Emitir boletos em lote**
> Como síndico, quero emitir boletos de condomínio para todas as unidades de uma vez referentes a um mês, para agilizar o processo de cobrança mensal.

*Critérios de aceite:*
- O síndico deve informar o mês de referência e a data de vencimento antes de confirmar a emissão.
- O sistema deve gerar um boleto individual para cada unidade ativa.
- Após a emissão, cada condômino deve receber o boleto por e-mail.
- O sistema deve indicar quais unidades falharam na emissão, se houver.

---

**HU03 — Acompanhar inadimplências**
> Como síndico, quero visualizar um painel com as unidades inadimplentes por período, para tomar as providências cabíveis de cobrança.

*Critérios de aceite:*
- O painel deve listar unidades com boletos em aberto após o vencimento, exibindo unidade, morador, valor e dias em atraso.
- Deve ser possível filtrar por bloco, período e faixa de atraso.
- O síndico deve poder exportar a lista de inadimplentes em CSV.

---

**HU04 — Publicar comunicados**
> Como síndico, quero publicar comunicados no portal do condomínio, para informar os moradores sobre decisões, eventos e avisos importantes.

*Critérios de aceite:*
- O comunicado deve ter título, corpo de texto e data de publicação.
- Todos os condôminos devem receber notificação por e-mail imediatamente após a publicação.
- O síndico deve poder fixar comunicados importantes no topo do portal.

---

**HU05 — Gerenciar ocorrências**
> Como síndico, quero visualizar todas as ocorrências registradas, categorizá-las e atualizar seus status, para garantir que solicitações e reclamações dos moradores sejam tratadas.

*Critérios de aceite:*
- As ocorrências devem ser listadas com data, unidade de origem, categoria, descrição e status atual.
- Deve ser possível filtrar por status, categoria e período.
- O autor da ocorrência deve ser notificado por e-mail a cada mudança de status.

---

**HU06 — Criar e registrar assembleias**
> Como síndico, quero criar assembleias com data, horário, local e pauta, e registrar a ata após a realização, para manter o histórico de decisões do condomínio.

*Critérios de aceite:*
- A criação da assembleia deve notificar todos os condôminos por e-mail.
- A ata deve ser associada à assembleia correspondente e disponibilizada no portal após o registro.
- Deve ser possível anexar documentos à ata (ex.: listas de presença em PDF).

---

**HU07 — Gerenciar áreas comuns e reservas**
> Como síndico, quero cadastrar as áreas comuns, configurar regras de reserva e acompanhar o calendário de reservas, para controlar o uso dos espaços compartilhados.

*Critérios de aceite:*
- Deve ser possível configurar horários permitidos para reserva e antecedência mínima e máxima por área.
- O calendário deve exibir todas as reservas confirmadas por área e período.
- O síndico deve poder cancelar qualquer reserva, com notificação ao condômino.

---

### Perfil: Condômino

**HU08 — Visualizar e pagar boleto pelo portal**
> Como condômino, quero acessar meus boletos em aberto e pagos pelo portal, para acompanhar minha situação financeira com o condomínio.

*Critérios de aceite:*
- O portal deve listar boletos com mês de referência, vencimento, valor e status (em aberto, pago, vencido).
- Deve ser possível visualizar e baixar o boleto em aberto para pagamento.
- O status do boleto deve ser atualizado automaticamente após a confirmação do pagamento.

---

**HU09 — Reservar área comum**
> Como condômino, quero reservar uma área comum pelo portal para uma data e horário específicos, para planejar meu uso dos espaços do condomínio.

*Critérios de aceite:*
- O portal deve exibir a disponibilidade da área para o período selecionado em tempo real.
- A reserva deve ser confirmada imediatamente se o horário estiver disponível.
- O condômino deve receber confirmação por e-mail com os detalhes da reserva.

---

**HU10 — Registrar e acompanhar ocorrência**
> Como condômino, quero registrar uma ocorrência pelo portal e acompanhar sua evolução, para reportar problemas e saber quando foram resolvidos.

*Critérios de aceite:*
- O condômino deve informar categoria, descrição e, opcionalmente, anexar fotos.
- O sistema deve exibir o status atual e o histórico de atualizações da ocorrência.
- O condômino deve ser notificado por e-mail a cada atualização de status.

---

**HU11 — Pré-autorizar entrada de visitante**
> Como condômino, quero registrar antecipadamente a visita de alguém, para agilizar a liberação de acesso pelo funcionário na portaria.

*Critérios de aceite:*
- O condômino deve informar nome do visitante e data prevista da visita.
- A pré-autorização deve ficar visível para o funcionário na portaria no dia indicado.
- O condômino deve poder cancelar a pré-autorização enquanto a visita não tiver sido registrada.

---

**HU12 — Acompanhar assembleias e consultar atas**
> Como condômino, quero visualizar as assembleias agendadas e consultar as atas das assembleias passadas, para me manter informado sobre as decisões do condomínio.

*Critérios de aceite:*
- As assembleias futuras devem exibir data, horário, local e pauta.
- As atas disponíveis devem poder ser visualizadas e baixadas em PDF diretamente pelo portal.

---

### Perfil: Funcionário

**HU13 — Registrar entrada e saída de visitantes**
> Como funcionário, quero registrar a entrada e saída de visitantes na portaria, para manter o controle de acesso ao condomínio.

*Critérios de aceite:*
- O registro de entrada deve exigir nome, documento, unidade visitada e horário.
- O sistema deve destacar se o visitante possui pré-autorização registrada pelo condômino.
- A saída deve ser registrada com horário, encerrando o registro de visita em aberto.

---

**HU14 — Consultar pré-autorizações de acesso**
> Como funcionário, quero consultar as pré-autorizações registradas pelos condôminos para o dia, para agilizar a liberação de visitantes esperados.

*Critérios de aceite:*
- A listagem deve exibir nome do visitante, unidade destino e condômino autorizador.
- Deve ser possível filtrar por unidade ou por nome do visitante.
- Após confirmar a entrada do visitante pré-autorizado, o registro deve ser vinculado à pré-autorização correspondente.