# Plataforma de Gestão de Transporte de Cargas — Requisitos

---

## Requisitos Funcionais (RF)

### Gestão de Usuários e Acesso

| ID   | Descrição |
|------|-----------|
| RF01 | O sistema deve permitir o cadastro de usuários com perfis distintos: embarcador, transportadora, motorista, destinatário e administrador da plataforma. |
| RF02 | O sistema deve restringir o acesso às funcionalidades conforme o perfil autenticado. |
| RF03 | O sistema deve permitir que uma transportadora cadastre e gerencie os motoristas e veículos vinculados a ela. |
| RF04 | O sistema deve registrar log de auditoria de todas as operações críticas com usuário, data, hora e ação realizada. |

### Pedidos de Frete

| ID   | Descrição |
|------|-----------|
| RF05 | O sistema deve permitir que embarcadores registrem pedidos de frete informando origem, destino, tipo de carga, peso, volume, dimensões e prazo desejado. |
| RF06 | O sistema deve permitir que o embarcador declare o valor da mercadoria para fins de seguro e cálculo de ad valorem. |
| RF07 | O sistema deve permitir que o embarcador acompanhe o status de todos os seus pedidos de frete em uma visão consolidada. |
| RF08 | O sistema deve permitir que o embarcador cancele um pedido de frete antes da aceitação pela transportadora, conforme política de cancelamento configurável. |
| RF09 | O sistema deve permitir o upload de documentos vinculados ao pedido (NF-e do embarcador, fichas técnicas de carga perigosa, etc.). |

### Roteamento e Seleção de Transportadoras

| ID   | Descrição |
|------|-----------|
| RF10 | O sistema deve rotear automaticamente o pedido de frete para transportadoras parceiras habilitadas para o tipo de carga, origem e destino informados. |
| RF11 | O sistema deve calcular e comparar fretes de múltiplas transportadoras com base em critérios configuráveis: preço, prazo de entrega, tipo de veículo e histórico de desempenho. |
| RF12 | O sistema deve apresentar ao embarcador as opções de transportadora ranqueadas pelos critérios selecionados para confirmação ou aceitação automática conforme regra configurada. |
| RF13 | O sistema deve notificar as transportadoras selecionadas sobre novos pedidos disponíveis para aceite. |
| RF14 | O sistema deve registrar a aceitação ou recusa do pedido pela transportadora com data, hora e justificativa de recusa. |
| RF15 | O sistema deve acionar automaticamente a próxima transportadora ranqueada em caso de recusa ou ausência de resposta dentro do prazo configurado. |
| RF16 | O sistema deve manter e atualizar continuamente o índice de desempenho de cada transportadora com base em entregas realizadas, prazos cumpridos e ocorrências registradas. |

### Documento de Transporte — CT-e

| ID   | Descrição |
|------|-----------|
| RF17 | O sistema deve integrar com o serviço de emissão de Conhecimento de Transporte Eletrônico (CT-e) para gerar o documento fiscal após a aceitação do frete. |
| RF18 | O sistema deve transmitir o CT-e à SEFAZ e acompanhar o status de autorização em tempo real. |
| RF19 | O sistema deve suportar a emissão de CT-e em contingência (offline) com posterior sincronização com a SEFAZ. |
| RF20 | O sistema deve consultar a SEFAZ para validar NF-es vinculadas ao pedido de frete antes da emissão do CT-e. |
| RF21 | O sistema deve controlar cancelamento e inutilização de CT-e conforme regras e prazos da SEFAZ. |
| RF22 | O sistema deve disponibilizar o DACTE (Documento Auxiliar do CT-e) para download pelo embarcador e transportadora após a autorização. |

### Operação do Motorista

| ID   | Descrição |
|------|-----------|
| RF23 | O aplicativo mobile do motorista deve exibir as ordens de coleta e entrega do dia com endereços, contatos e documentos vinculados. |
| RF24 | O sistema deve permitir que o motorista registre a coleta da carga com confirmação de volumes, fotos e assinatura digital do remetente. |
| RF25 | O sistema deve capturar e transmitir a geolocalização do motorista em intervalos configuráveis durante o transporte ativo. |
| RF26 | O sistema deve permitir que o motorista registre ocorrências durante o transporte (avaria, tentativa de entrega sem sucesso, acidente, roubo). |
| RF27 | O sistema deve permitir que o motorista registre a entrega da carga com foto do comprovante e captura de assinatura digital do destinatário. |
| RF28 | O sistema deve permitir que o motorista opere em modo offline, sincronizando os dados de posição e status quando a conectividade for restabelecida. |
| RF29 | O sistema deve exibir rotas otimizadas ao motorista no aplicativo mobile com suporte a múltiplas paradas. |

### Rastreamento em Tempo Real

| ID   | Descrição |
|------|-----------|
| RF30 | O sistema deve disponibilizar ao destinatário uma interface de rastreamento em tempo real da sua carga, acessível por link sem necessidade de cadastro. |
| RF31 | O sistema deve exibir no rastreamento o histórico de eventos da carga (coleta, em trânsito, saiu para entrega, entregue, ocorrência) com data, hora e localização. |
| RF32 | O sistema deve exibir a posição atual do veículo no mapa e a previsão de entrega atualizada dinamicamente. |

### Notificações

| ID   | Descrição |
|------|-----------|
| RF33 | O sistema deve notificar o destinatário por e-mail e SMS a cada mudança de status relevante da carga (coleta realizada, em trânsito, saiu para entrega, entrega realizada, ocorrência). |
| RF34 | O sistema deve notificar o embarcador sobre aceitação do frete, ocorrências durante o transporte e conclusão da entrega. |
| RF35 | O sistema deve notificar a transportadora sobre novos pedidos, prazos críticos e ocorrências que exijam ação. |
| RF36 | O sistema deve alertar o administrador da plataforma sobre pedidos sem transportadora aceita após o prazo configurado e sobre fretes com SLA em risco. |

### Comprovante de Entrega Digital (POD)

| ID   | Descrição |
|------|-----------|
| RF37 | O sistema deve gerar o Comprovante de Entrega Digital (POD) consolidando assinatura do destinatário, foto da entrega, data, hora e geolocalização. |
| RF38 | O sistema deve aplicar carimbo de tempo (timestamp) com validade jurídica ao POD no momento da assinatura. |
| RF39 | O sistema deve disponibilizar o POD para download pelo embarcador, transportadora e destinatário imediatamente após a conclusão da entrega. |
| RF40 | O sistema deve registrar a recusa de recebimento pelo destinatário com motivo e captura de evidências fotográficas. |

### Seguros e Sinistros

| ID   | Descrição |
|------|-----------|
| RF41 | O sistema deve integrar com seguradoras parceiras para cotação e contratação de cobertura de seguro por viagem com base no valor declarado da mercadoria. |
| RF42 | O sistema deve permitir a abertura de sinistro diretamente pela plataforma, vinculando o pedido de frete, as ocorrências registradas e os documentos comprobatórios. |
| RF43 | O sistema deve acompanhar o status do sinistro aberto junto à seguradora e notificar o embarcador sobre atualizações. |
| RF44 | O sistema deve armazenar toda a documentação do sinistro (boletim de ocorrência, laudos, fotos de avaria, POD) de forma estruturada e acessível. |

### Financeiro e Faturamento da Plataforma

| ID   | Descrição |
|------|-----------|
| RF45 | O sistema deve calcular o valor do frete por viagem com base na tabela de preços da transportadora e nas características do pedido. |
| RF46 | O sistema deve calcular e reter automaticamente a comissão da plataforma sobre cada frete concluído. |
| RF47 | O sistema deve gerar fatura consolidada para o embarcador com os fretes do período, discriminando viagens, valores e impostos. |
| RF48 | O sistema deve gerar demonstrativo de repasse para a transportadora com os fretes concluídos, comissão retida e valor líquido a receber. |
| RF49 | O sistema deve manter painel financeiro para o administrador com receita de comissões, volume de fretes e inadimplências por período. |

---

## Requisitos Não Funcionais (RNF)

### Segurança

| ID    | Categoria | Descrição |
|-------|-----------|-----------|
| RNF01 | Segurança | Toda comunicação entre cliente e servidor deve utilizar TLS 1.2 ou superior. |
| RNF02 | Segurança | Dados financeiros, fiscais e de localização devem ser armazenados criptografados em repouso com AES-256. |
| RNF03 | Segurança | O acesso ao sistema deve exigir autenticação com MFA para perfis administrativos e de embarcador. |
| RNF04 | Segurança | O aplicativo mobile do motorista deve autenticar via token de sessão renovável, com bloqueio após inatividade configurável. |
| RNF05 | Segurança | O link de rastreamento do destinatário deve ser protegido por token único e com prazo de validade, sem expor dados de outros fretes. |
| RNF06 | Segurança | Os dados de geolocalização do motorista devem ser transmitidos exclusivamente para usuários com permissão sobre o frete correspondente. |

### Conformidade Regulatória

| ID    | Categoria    | Descrição |
|-------|--------------|-----------|
| RNF07 | Conformidade | O CT-e deve ser emitido em conformidade com o schema XSD vigente publicado pela SEFAZ, incluindo suporte à versão mais recente do leiaute. |
| RNF08 | Conformidade | O sistema deve suportar as modalidades de CT-e previstas na legislação: normal, complementar, de anulação e substituto. |
| RNF09 | Conformidade | O sistema deve estar em conformidade com a LGPD no tratamento de dados pessoais de motoristas, destinatários e embarcadores. |
| RNF10 | Conformidade | O comprovante de entrega digital (POD) com assinatura e timestamp deve atender aos requisitos de validade jurídica conforme a Lei nº 14.063/2020 (assinaturas eletrônicas). |
| RNF11 | Conformidade | O sistema deve manter trilha de auditoria imutável de todas as movimentações financeiras e fiscais com retenção mínima de 5 anos conforme o CTN. |

### Disponibilidade e Desempenho

| ID    | Categoria       | Descrição |
|-------|-----------------|-----------|
| RNF12 | Disponibilidade | O sistema deve ter disponibilidade mínima de 99,5% ao mês, incluindo o serviço de rastreamento em tempo real. |
| RNF13 | Desempenho      | O roteamento automático e o ranqueamento de transportadoras devem ser concluídos em até 10 segundos após o registro do pedido. |
| RNF14 | Desempenho      | A transmissão de CT-e à SEFAZ deve ser concluída em até 30 segundos em condições normais de rede. |
| RNF15 | Desempenho      | A atualização de posição do veículo no mapa de rastreamento deve ocorrer em até 30 segundos após a transmissão pelo aplicativo do motorista. |
| RNF16 | Escalabilidade  | A arquitetura deve suportar processamento simultâneo de alto volume de atualizações de geolocalização sem degradação do rastreamento em tempo real. |
| RNF17 | Resiliência     | O aplicativo mobile do motorista deve operar em modo offline completo, garantindo que nenhum evento de coleta, entrega ou ocorrência seja perdido por falta de conectividade. |

### Usabilidade e Compatibilidade

| ID    | Categoria      | Descrição |
|-------|----------------|-----------|
| RNF18 | Usabilidade    | O aplicativo mobile do motorista deve ser otimizado para uso com luvas e em condições de baixa luminosidade, com elementos de interface de toque ampliado. |
| RNF19 | Compatibilidade | O aplicativo mobile deve estar disponível para Android (versões mais recentes) com prioridade, dado o perfil do público de motoristas, e iOS. |
| RNF20 | Compatibilidade | O portal web deve ser responsivo e funcionar nos principais navegadores modernos (Chrome, Firefox, Safari, Edge). |
| RNF21 | Usabilidade    | O fluxo de confirmação de entrega no aplicativo do motorista (foto + assinatura + envio) não deve exigir mais de quatro interações. |

### Infraestrutura e Dados

| ID    | Categoria        | Descrição |
|-------|------------------|-----------|
| RNF22 | Backup           | O sistema deve realizar backup automático diário com retenção mínima de 90 dias e RPO máximo de 1 hora para dados transacionais e de rastreamento. |
| RNF23 | Infraestrutura   | Os dados de geolocalização devem ser armazenados em banco de dados otimizado para séries temporais e consultas geoespaciais. |
| RNF24 | Interoperabilidade | As integrações com SEFAZ, seguradoras e sistemas de emissão de CT-e devem ser implementadas via APIs com contrato versionado, permitindo atualização independente de cada integração. |
| RNF25 | Manutenibilidade | O sistema deve expor métricas operacionais (latência de roteamento, taxa de aceitação de fretes, disponibilidade de integrações externas) em painel de monitoramento em tempo real. |

---

## Histórias de Usuário (HU)

### Perfil: Embarcador

**HU01 — Registrar pedido de frete**
> Como embarcador, quero registrar um pedido de frete informando origem, destino, características da carga e prazo desejado, para acionar automaticamente a seleção de transportadoras sem negociação manual.

*Critérios de aceite:*
- Origem, destino, tipo de carga, peso e volume são campos obrigatórios.
- Deve ser possível declarar o valor da mercadoria para fins de seguro.
- O pedido deve permitir upload de documentos vinculados (NF-e, fichas de carga especial).
- Após o registro, o sistema deve iniciar o roteamento automático e notificar o embarcador sobre as opções disponíveis.

---

**HU02 — Selecionar transportadora e contratar seguro**
> Como embarcador, quero visualizar as transportadoras ranqueadas para o meu pedido e contratar o seguro da carga em um único fluxo, para tomar a melhor decisão de frete com cobertura garantida.

*Critérios de aceite:*
- As opções de transportadora devem ser exibidas com preço, prazo estimado, tipo de veículo e índice de desempenho.
- Deve ser possível contratar o seguro da carga diretamente pela plataforma antes de confirmar o frete.
- A confirmação do frete deve disparar a emissão do CT-e e a notificação à transportadora selecionada.

---

**HU03 — Acompanhar pedidos e receber comprovante de entrega**
> Como embarcador, quero visualizar o status de todos os meus fretes em uma tela consolidada e receber o comprovante de entrega assim que a carga for entregue, para manter controle sobre minhas operações logísticas.

*Critérios de aceite:*
- A visão consolidada deve exibir pedido, transportadora, status atual, previsão de entrega e alertas de ocorrência.
- O POD deve ser disponibilizado para download imediatamente após a confirmação da entrega pelo motorista.
- Ocorrências durante o transporte devem ser destacadas visualmente e notificadas por e-mail.

---

**HU04 — Abrir sinistro por avaria ou extravio**
> Como embarcador, quero registrar um sinistro diretamente pela plataforma em caso de avaria ou extravio da carga, para acionar a cobertura do seguro sem precisar contatar a seguradora por outros canais.

*Critérios de aceite:*
- O formulário de sinistro deve estar vinculado automaticamente ao pedido de frete e às ocorrências registradas pelo motorista.
- Deve ser possível anexar documentos comprobatórios (BO, fotos, laudo de avaria).
- O sistema deve notificar o embarcador sobre cada atualização de status do sinistro pela seguradora.

---

### Perfil: Transportadora

**HU05 — Aceitar pedidos de frete e gerenciar frota**
> Como transportadora, quero receber notificações de novos pedidos compatíveis com minha operação e aceitá-los ou recusá-los pela plataforma, para gerenciar minha capacidade de forma eficiente.

*Critérios de aceite:*
- A notificação deve exibir origem, destino, tipo de carga, prazo e valor do frete antes do aceite.
- O aceite deve ser confirmado em até o prazo configurado, sob pena de o pedido ser oferecido à próxima transportadora.
- Em caso de recusa, deve ser informada a justificativa a partir de lista predefinida.

---

**HU06 — Acompanhar operação dos motoristas em tempo real**
> Como transportadora, quero visualizar a posição em tempo real de todos os meus motoristas em campo e o status das entregas sob minha responsabilidade, para monitorar a operação e agir rapidamente em caso de ocorrências.

*Critérios de aceite:*
- O painel deve exibir um mapa com a posição atualizada de cada motorista e o status do frete correspondente.
- Ocorrências registradas pelo motorista devem gerar alerta imediato no painel da transportadora.
- Deve ser possível contatar o motorista diretamente pela plataforma em caso de necessidade.

---

**HU07 — Consultar demonstrativo financeiro de repasse**
> Como transportadora, quero visualizar o demonstrativo de fretes concluídos com os valores brutos, comissão retida e saldo líquido a receber, para conciliar meu faturamento com a plataforma.

*Critérios de aceite:*
- O demonstrativo deve listar cada frete com data, origem, destino, valor bruto, percentual e valor da comissão e valor líquido.
- Deve ser possível filtrar por período e exportar em CSV e PDF.
- O saldo líquido total disponível deve estar em destaque no painel financeiro.

---

### Perfil: Motorista

**HU08 — Executar coleta com registro de evidências**
> Como motorista, quero registrar a coleta da carga pelo aplicativo com confirmação de volumes, fotos e assinatura do remetente, para documentar o início do transporte com evidências formais.

*Critérios de aceite:*
- O registro de coleta deve incluir foto da carga, confirmação da quantidade de volumes e assinatura digital do remetente.
- O evento de coleta deve ser transmitido imediatamente ao sistema, atualizando o status do frete para "em trânsito".
- Em caso de divergência de volumes ou avaria na coleta, deve ser possível registrar uma ocorrência antes de confirmar a coleta.

---

**HU09 — Registrar entrega com assinatura digital do destinatário**
> Como motorista, quero registrar a entrega da carga com foto e assinatura digital do destinatário pelo aplicativo, para gerar o comprovante de entrega com validade jurídica sem uso de papel.

*Critérios de aceite:*
- O fluxo de entrega deve capturar foto da entrega, assinatura do destinatário e geolocalização automaticamente.
- O POD deve ser gerado e transmitido ao sistema em até 60 segundos após a confirmação.
- Em caso de recusa de recebimento, deve ser possível registrar o motivo e capturar evidências fotográficas.
- O aplicativo deve suportar o fluxo completo de entrega em modo offline, sincronizando quando a conexão for restabelecida.

---

**HU10 — Registrar ocorrência durante o transporte**
> Como motorista, quero registrar ocorrências durante o transporte (avaria, tentativa sem sucesso, acidente, roubo) pelo aplicativo, para formalizar o evento e acionar os responsáveis sem perda de tempo.

*Critérios de aceite:*
- A ocorrência deve ser categorizada a partir de lista predefinida com campo de descrição livre.
- Deve ser possível anexar fotos à ocorrência diretamente pelo aplicativo.
- O registro deve disparar notificação imediata à transportadora e ao embarcador.

---

### Perfil: Destinatário

**HU11 — Rastrear carga em tempo real sem cadastro**
> Como destinatário, quero acompanhar minha carga em tempo real pelo link recebido, sem precisar me cadastrar na plataforma, para saber exatamente onde está minha encomenda e quando será entregue.

*Critérios de aceite:*
- O link de rastreamento deve ser acessível sem autenticação e exibir mapa com posição atual do veículo.
- O histórico de eventos deve ser exibido em ordem cronológica com data, hora e descrição de cada etapa.
- A previsão de entrega deve ser recalculada e exibida dinamicamente com base na posição atual do veículo.
- O link deve ser protegido por token único e expirar após a conclusão da entrega.

---

**HU12 — Receber notificações de cada etapa da entrega**
> Como destinatário, quero ser notificado por e-mail e SMS a cada mudança de status relevante da minha carga, para me preparar para o recebimento sem precisar verificar o rastreamento continuamente.

*Critérios de aceite:*
- Notificações devem ser enviadas nos eventos: coleta realizada, em trânsito, saiu para entrega, entrega realizada e ocorrência.
- A notificação de "saiu para entrega" deve incluir a previsão de horário de chegada.
- O destinatário deve poder gerenciar suas preferências de notificação (e-mail, SMS ou ambos) pelo link de rastreamento.

---

### Perfil: Administrador da Plataforma

**HU13 — Monitorar SLA de fretes e acionar contingência**
> Como administrador, quero visualizar em tempo real os fretes com SLA em risco e os pedidos sem transportadora aceita, para intervir manualmente ou acionar regras de contingência antes que o prazo seja comprometido.

*Critérios de aceite:*
- O painel de monitoramento deve destacar fretes com risco de atraso com base no prazo acordado e na posição atual do veículo.
- Pedidos sem aceite após o prazo configurado devem gerar alerta com ação rápida para reassignação manual.
- Deve ser possível comunicar embarcador e transportadora diretamente pelo painel em situações críticas.

---

**HU14 — Acompanhar painel financeiro da plataforma**
> Como administrador, quero visualizar o painel financeiro consolidado com receita de comissões, volume de fretes e inadimplências por período, para monitorar a saúde financeira da operação da plataforma.

*Critérios de aceite:*
- O painel deve exibir receita bruta de comissões, volume de fretes realizados, ticket médio e taxa de inadimplência no período selecionado.
- Deve ser possível filtrar por transportadora, embarcador, rota e período.
- Os dados devem ser exportáveis em CSV e PDF para análise externa.