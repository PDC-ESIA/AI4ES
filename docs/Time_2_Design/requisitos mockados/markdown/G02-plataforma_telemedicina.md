# Plataforma Integrada de Saúde Digital — Requisitos

---

## Requisitos Funcionais (RF)

### Gestão de Usuários e Acesso

| ID   | Descrição |
|------|-----------|
| RF01 | O sistema deve permitir o cadastro de usuários com perfis distintos: paciente, médico, administrador de clínica/hospital, operador de plano de saúde e administrador da plataforma. |
| RF02 | O sistema deve validar o CRM do médico junto ao CFM durante o cadastro, bloqueando o acesso clínico em caso de registro inativo ou suspenso. |
| RF03 | O sistema deve exigir autenticação multifator (MFA) para todos os perfis, com suporte a OTP por aplicativo autenticador e biometria no mobile. |
| RF04 | O sistema deve restringir o acesso às funcionalidades estritamente conforme o perfil e as permissões do usuário autenticado. |
| RF05 | O sistema deve encerrar sessões inativas automaticamente após tempo configurável por perfil. |
| RF06 | O sistema deve registrar log de todos os acessos ao prontuário eletrônico, com identificação do usuário, data, hora e ação realizada. |

### Agendamento de Consultas

| ID   | Descrição |
|------|-----------|
| RF07 | O sistema deve permitir que pacientes agendem consultas presenciais e por videochamada com médicos credenciados. |
| RF08 | O sistema deve exibir a disponibilidade de agenda de cada médico em tempo real. |
| RF09 | O sistema deve verificar automaticamente a cobertura do plano de saúde do paciente para o procedimento e especialidade selecionados antes de confirmar o agendamento. |
| RF10 | O sistema deve permitir que o paciente cancele ou remarcque uma consulta dentro do prazo configurado. |
| RF11 | O sistema deve enviar notificações de confirmação, lembrete e cancelamento por e-mail e push ao paciente e ao médico. |
| RF12 | O sistema deve permitir que médicos e administradores de clínica configurem a grade de horários e os tipos de atendimento disponíveis. |
| RF13 | O sistema deve suportar encaixe de consulta urgente, com notificação ao médico responsável. |

### Videochamada Médico-Paciente

| ID   | Descrição |
|------|-----------|
| RF14 | O sistema deve prover infraestrutura de videochamada integrada para consultas remotas, sem necessidade de aplicativo de terceiros. |
| RF15 | O sistema deve permitir que médico e paciente ingressem na videochamada diretamente pelo aplicativo ou portal web, mediante autenticação. |
| RF16 | O sistema deve registrar a duração da chamada para fins de faturamento e auditoria. |
| RF17 | O sistema deve permitir o compartilhamento de documentos e imagens durante a videochamada entre médico e paciente. |
| RF18 | O sistema deve alertar médico e paciente quando faltarem 5 minutos para o horário agendado da consulta. |

### Prontuário Eletrônico

| ID   | Descrição |
|------|-----------|
| RF19 | O sistema deve manter um prontuário eletrônico único por paciente, compartilhado entre especialidades e unidades de saúde parceiras autorizadas. |
| RF20 | O sistema deve permitir que o médico registre evoluções clínicas, diagnósticos (CID), anamnese, hipóteses diagnósticas e plano terapêutico em cada consulta. |
| RF21 | O sistema deve permitir o armazenamento e a consulta de documentos clínicos no prontuário (laudos, imagens diagnósticas, relatórios de exames). |
| RF22 | O sistema deve exibir o histórico completo de consultas, procedimentos, medicamentos e resultados de exames no prontuário. |
| RF23 | O sistema deve exigir consentimento explícito do paciente para que médicos de outras especialidades ou unidades acessem seu prontuário. |
| RF24 | O sistema deve permitir que o paciente visualize seu próprio prontuário pelo aplicativo, com acesso controlado às informações conforme política de privacidade. |
| RF25 | O sistema deve tornar imutável cada entrada do prontuário após assinatura digital do médico responsável, permitindo apenas adendos identificados. |

### Prescrição Digital

| ID   | Descrição |
|------|-----------|
| RF26 | O sistema deve permitir que o médico emita prescrições digitais de medicamentos, exames e procedimentos diretamente pela plataforma. |
| RF27 | O sistema deve aplicar assinatura digital com certificado ICP-Brasil às prescrições, conferindo-lhes validade jurídica conforme regulamentação do CFM. |
| RF28 | O sistema deve validar interações medicamentosas e alertar o médico antes da confirmação da prescrição. |
| RF29 | O sistema deve permitir que o paciente acesse e compartilhe a prescrição digital pelo aplicativo com farmácias e outros serviços. |
| RF30 | O sistema deve controlar prescrições de medicamentos sujeitos a controle especial, exigindo registro da via de receituário correspondente. |

### Integração com Laboratórios

| ID   | Descrição |
|------|-----------|
| RF31 | O sistema deve integrar com laboratórios parceiros para receber resultados de exames eletronicamente e vinculá-los automaticamente ao prontuário do paciente. |
| RF32 | O sistema deve notificar o médico solicitante e o paciente quando os resultados de um exame forem disponibilizados. |
| RF33 | O sistema deve permitir que o paciente visualize e faça download dos seus resultados de exames pelo aplicativo. |
| RF34 | O sistema deve permitir que o médico solicite exames diretamente pela plataforma, com encaminhamento eletrônico para o laboratório parceiro. |
| RF35 | O sistema deve exibir alertas ao médico quando resultados de exames contiverem valores críticos fora dos parâmetros de referência. |

### Cobertura por Planos de Saúde

| ID   | Descrição |
|------|-----------|
| RF36 | O sistema deve permitir o cadastro e a gestão de planos de saúde parceiros com suas tabelas de cobertura e procedimentos (TUSS). |
| RF37 | O sistema deve verificar a elegibilidade do beneficiário em tempo real junto à operadora do plano de saúde antes de cada atendimento. |
| RF38 | O sistema deve gerar guias de atendimento e de solicitação de exames nos padrões TISS (Troca de Informações em Saúde Suplementar) da ANS. |
| RF39 | O sistema deve processar a autorização prévia de procedimentos junto à operadora do plano diretamente pela plataforma. |
| RF40 | O sistema deve gerar e transmitir faturamento eletrônico às operadoras conforme o padrão TISS. |
| RF41 | O sistema deve registrar o valor a ser cobrado do paciente (coparticipação ou particular) por atendimento. |

### Módulo Administrativo

| ID   | Descrição |
|------|-----------|
| RF42 | O sistema deve permitir o cadastro e a gestão de hospitais e clínicas parceiras, com seus médicos, especialidades e unidades. |
| RF43 | O sistema deve permitir que administradores de clínica gerenciem médicos vinculados, configurem agendas e acompanhem indicadores operacionais. |
| RF44 | O sistema deve gerar relatórios gerenciais de atendimentos, ocupação de agenda, faturamento por convênio e produtividade por médico. |
| RF45 | O sistema deve permitir o gerenciamento de equipamentos e salas por unidade de saúde. |
| RF46 | O sistema deve disponibilizar painel de indicadores de saúde operacional da plataforma para o administrador da plataforma. |

---

## Requisitos Não Funcionais (RNF)

### Segurança

| ID    | Categoria | Descrição |
|-------|-----------|-----------|
| RNF01 | Segurança | Toda comunicação entre cliente e servidor deve utilizar TLS 1.2 ou superior. |
| RNF02 | Segurança | Dados de prontuário e documentos clínicos devem ser armazenados criptografados em repouso com AES-256. |
| RNF03 | Segurança | As senhas dos usuários devem ser armazenadas com hash seguro (bcrypt ou Argon2). |
| RNF04 | Segurança | A videochamada deve ser transmitida com criptografia ponta a ponta (end-to-end encryption), sem gravação de conteúdo. |
| RNF05 | Segurança | O sistema deve implementar rate limiting e detecção de acessos anômalos ao prontuário eletrônico. |
| RNF06 | Segurança | A assinatura digital das prescrições deve utilizar certificado digital padrão ICP-Brasil (e-CPF médico ou certificado em nuvem homologado pelo CFM). |

### Conformidade Regulatória

| ID    | Categoria    | Descrição |
|-------|--------------|-----------|
| RNF07 | Conformidade | O sistema deve estar em conformidade com a LGPD, com base legal explícita para cada finalidade de tratamento de dados de saúde (dado sensível, art. 11). |
| RNF08 | Conformidade | O sistema deve observar as resoluções do CFM aplicáveis à telemedicina, ao prontuário eletrônico e à prescrição digital (em especial CFM nº 2.314/2022 e correlatas). |
| RNF09 | Conformidade | O sistema deve observar as normas da ANS relativas ao padrão TISS para troca de informações em saúde suplementar. |
| RNF10 | Conformidade | O prontuário eletrônico deve estar em conformidade com a resolução CFM nº 1.821/2007 e normas SBIS para certificação de sistemas de registro eletrônico em saúde. |
| RNF11 | Conformidade | O sistema deve manter trilha de auditoria imutável de todos os acessos e alterações em prontuários, com retenção mínima de 20 anos conforme resolução CFM. |
| RNF12 | Conformidade | O sistema deve permitir a portabilidade e o acesso dos dados pelo titular conforme os direitos previstos na LGPD. |

### Disponibilidade e Desempenho

| ID    | Categoria       | Descrição |
|-------|-----------------|-----------|
| RNF13 | Disponibilidade | O sistema deve ter disponibilidade mínima de 99,9% ao mês, com plano de contingência documentado para indisponibilidades. |
| RNF14 | Desempenho      | A verificação de elegibilidade do plano de saúde deve ser concluída em até 5 segundos. |
| RNF15 | Desempenho      | O carregamento do prontuário eletrônico completo deve ocorrer em até 3 segundos. |
| RNF16 | Desempenho      | A videochamada deve suportar resolução mínima de 720p com latência máxima de 150ms em condições de rede adequadas. |
| RNF17 | Escalabilidade  | A arquitetura deve suportar escalonamento horizontal para absorver picos de demanda sem degradação de desempenho. |
| RNF18 | Resiliência     | Documentos clínicos e imagens diagnósticas devem ser armazenados em serviço externo de object storage com redundância geográfica. |

### Usabilidade e Compatibilidade

| ID    | Categoria      | Descrição |
|-------|----------------|-----------|
| RNF19 | Compatibilidade | O aplicativo mobile deve estar disponível para iOS e Android, com suporte às duas versões mais recentes de cada sistema operacional. |
| RNF20 | Compatibilidade | O portal web deve ser responsivo e funcionar nos principais navegadores modernos (Chrome, Firefox, Safari, Edge). |
| RNF21 | Acessibilidade  | A interface deve seguir as diretrizes WCAG 2.1 nível AA para garantir acessibilidade a usuários com deficiência. |
| RNF22 | Usabilidade     | O fluxo de ingresso na videochamada não deve exigir mais de dois cliques a partir da tela inicial do aplicativo. |

### Infraestrutura e Dados

| ID    | Categoria        | Descrição |
|-------|------------------|-----------|
| RNF23 | Backup           | O sistema deve realizar backup contínuo dos dados clínicos com RPO máximo de 1 hora e RTO máximo de 4 horas. |
| RNF24 | Infraestrutura   | O ambiente de produção deve ser implantado em múltiplas zonas de disponibilidade para garantir redundância geográfica. |
| RNF25 | Manutenibilidade | O sistema deve expor métricas operacionais (latência, taxa de erros, disponibilidade por módulo) em painel de monitoramento em tempo real. |
| RNF26 | Interoperabilidade | As integrações com laboratórios e operadoras de planos de saúde devem seguir padrões abertos (HL7 FHIR e TISS) para facilitar a incorporação de novos parceiros. |

---

## Histórias de Usuário (HU)

### Perfil: Paciente

**HU01 — Cadastrar-se e consentir com o tratamento de dados de saúde**
> Como paciente, quero me cadastrar na plataforma e consentir explicitamente com o tratamento dos meus dados de saúde, para utilizar os serviços de forma segura e em conformidade com meus direitos.

*Critérios de aceite:*
- O cadastro deve coletar dados pessoais e informações do plano de saúde do paciente.
- O consentimento para tratamento de dados sensíveis de saúde deve ser explícito, registrado com data e hora.
- O paciente deve poder rever e revogar consentimentos a qualquer momento pelas configurações do aplicativo.

---

**HU02 — Agendar consulta presencial ou por videochamada**
> Como paciente, quero agendar uma consulta presencial ou por videochamada com um médico, para ser atendido sem precisar ligar para a clínica.

*Critérios de aceite:*
- A disponibilidade do médico deve ser exibida em tempo real no calendário de agendamento.
- O sistema deve verificar automaticamente a cobertura do meu plano de saúde para a especialidade selecionada antes de confirmar.
- Após o agendamento, devo receber confirmação por e-mail e push com data, horário, tipo de consulta e link de acesso (para videochamada).

---

**HU03 — Participar de consulta por videochamada**
> Como paciente, quero ingressar na videochamada com meu médico diretamente pelo aplicativo, para ser atendido remotamente com segurança e sem instalar outros programas.

*Critérios de aceite:*
- O botão de ingresso deve ser habilitado 5 minutos antes do horário agendado.
- A chamada deve ser criptografada ponta a ponta, sem gravação de conteúdo.
- Devo receber alerta push 5 minutos antes do início da consulta.
- Deve ser possível compartilhar documentos e imagens com o médico durante a chamada.

---

**HU04 — Visualizar prontuário e resultados de exames**
> Como paciente, quero acessar meu prontuário e os resultados dos meus exames pelo aplicativo, para acompanhar meu histórico de saúde e compartilhar informações com outros profissionais.

*Critérios de aceite:*
- O prontuário deve exibir histórico de consultas, medicamentos prescritos, procedimentos realizados e resultados de exames.
- Deve ser possível fazer download dos resultados de exames e documentos clínicos em PDF.
- O acesso ao prontuário por médicos de outras especialidades deve exigir meu consentimento explícito.

---

**HU05 — Acessar e compartilhar prescrição digital**
> Como paciente, quero acessar minhas prescrições digitais pelo aplicativo e compartilhá-las com farmácias, para retirar medicamentos sem depender de papel.

*Critérios de aceite:*
- A prescrição deve ser exibida com assinatura digital do médico e QR Code de validação.
- Deve ser possível compartilhar a prescrição por link ou exportá-la em PDF.
- Prescrições de medicamentos de controle especial devem exibir o tipo de receituário correspondente.

---

**HU06 — Receber notificação de resultado de exame disponível**
> Como paciente, quero ser notificado quando o resultado de um exame solicitado pelo meu médico estiver disponível, para acessá-lo sem precisar verificar periodicamente.

*Critérios de aceite:*
- A notificação deve ser enviada por push e e-mail imediatamente após o recebimento do resultado pelo sistema.
- A notificação deve identificar o tipo de exame e o laboratório responsável.
- O resultado deve estar acessível no prontuário do paciente imediatamente após a notificação.

---

### Perfil: Médico

**HU07 — Validar cadastro com CRM ativo**
> Como médico, quero me cadastrar na plataforma com validação automática do meu CRM junto ao CFM, para iniciar minha atuação clínica de forma legalmente respaldada.

*Critérios de aceite:*
- O sistema deve consultar o status do CRM no CFM durante o cadastro e bloquear o acesso clínico para registros inativos ou suspensos.
- O médico deve ser notificado sobre o resultado da validação em até 24 horas.
- Revalidações periódicas do CRM devem ser realizadas automaticamente pelo sistema.

---

**HU08 — Registrar evolução clínica no prontuário**
> Como médico, quero registrar a evolução clínica do paciente no prontuário eletrônico durante ou após a consulta, para documentar o atendimento com validade legal e continuidade de cuidado.

*Critérios de aceite:*
- O registro deve incluir anamnese, diagnóstico (CID), plano terapêutico e observações clínicas.
- Após a assinatura digital, o registro deve se tornar imutável; apenas adendos identificados devem ser permitidos.
- O prontuário deve registrar automaticamente data, hora e identificação do médico responsável em cada entrada.

---

**HU09 — Emitir prescrição digital com validade jurídica**
> Como médico, quero emitir prescrições digitais assinadas com meu certificado ICP-Brasil diretamente pela plataforma, para garantir validade jurídica e eliminar o uso de papel.

*Critérios de aceite:*
- A prescrição deve ser assinada digitalmente com o certificado e-CPF ou certificado em nuvem homologado pelo CFM.
- O sistema deve alertar sobre interações medicamentosas identificadas antes da confirmação.
- Medicamentos de controle especial devem exigir seleção do tipo de receituário conforme legislação vigente.
- A prescrição assinada deve ser vinculada automaticamente ao prontuário do paciente.

---

**HU10 — Solicitar exame e receber resultado com alerta de valor crítico**
> Como médico, quero solicitar exames para o paciente pela plataforma e receber os resultados com alerta quando houver valores críticos, para agilizar a conduta clínica.

*Critérios de aceite:*
- A solicitação deve ser encaminhada eletronicamente ao laboratório parceiro, com identificação do paciente e do médico solicitante.
- O médico deve ser notificado por push e e-mail quando o resultado estiver disponível.
- Valores fora dos parâmetros críticos de referência devem gerar alerta destacado na interface, com indicação do parâmetro alterado.

---

**HU11 — Acessar prontuário compartilhado entre especialidades**
> Como médico de uma especialidade, quero acessar o prontuário de um paciente que foi atendido por outro especialista na plataforma, para ter contexto clínico completo sem repetir exames ou anamnese.

*Critérios de aceite:*
- O acesso deve ser condicionado ao consentimento explícito do paciente registrado no sistema.
- O prontuário compartilhado deve exibir todos os registros de consultas, prescrições e exames realizados por outros profissionais autorizados.
- Todo acesso ao prontuário por médico externo deve ser registrado em log com data, hora e justificativa clínica.

---

### Perfil: Administrador de Clínica / Hospital

**HU12 — Gerenciar médicos e agendas da unidade**
> Como administrador de clínica, quero cadastrar médicos vinculados à minha unidade, configurar suas grades de horários e acompanhar a ocupação das agendas, para garantir a eficiência operacional do estabelecimento.

*Critérios de aceite:*
- Deve ser possível configurar dias, horários e tipos de atendimento por médico.
- O painel de ocupação deve exibir a taxa de utilização de cada agenda por período.
- Alterações na grade devem notificar os médicos afetados e respeitar agendamentos já confirmados.

---

**HU13 — Acompanhar faturamento por convênio**
> Como administrador de clínica, quero visualizar relatórios de faturamento por convênio e período, para monitorar a receita e identificar pendências de autorização ou glosa.

*Critérios de aceite:*
- O relatório deve exibir atendimentos faturados, valores enviados, valores autorizados e glosas por operadora.
- Deve ser possível filtrar por médico, especialidade, convênio e período.
- O relatório deve ser exportável em CSV e PDF.

---

### Perfil: Operador de Plano de Saúde

**HU14 — Processar autorização prévia de procedimentos**
> Como operador de plano de saúde, quero receber e processar solicitações de autorização prévia enviadas pela plataforma no padrão TISS, para agilizar a liberação de procedimentos e reduzir processos manuais.

*Critérios de aceite:*
- As guias recebidas devem seguir o padrão TISS vigente definido pela ANS.
- A resposta de autorização ou negativa deve ser transmitida eletronicamente à plataforma em até 30 minutos para procedimentos eletivos.
- Negativas devem incluir o código e a justificativa conforme tabela TISS.