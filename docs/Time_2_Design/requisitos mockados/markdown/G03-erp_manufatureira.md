# Sistema Integrado de Gestão Empresarial para Manufatura (ERP) — Requisitos

---

## Requisitos Funcionais (RF)

### Gestão de Usuários e Acesso

| ID   | Descrição |
|------|-----------|
| RF01 | O sistema deve permitir o cadastro de usuários com perfis e permissões granulares por módulo, função e unidade fabril. |
| RF02 | O sistema deve suportar autenticação via SSO (Single Sign-On) integrado ao diretório corporativo (Active Directory / LDAP). |
| RF03 | O sistema deve registrar log de auditoria de todas as operações realizadas por usuário, com data, hora, módulo e ação. |
| RF04 | O sistema deve restringir o acesso a dados de outras unidades fabris conforme a hierarquia organizacional configurada. |

### Planejamento e Controle da Produção (PCP)

| ID   | Descrição |
|------|-----------|
| RF05 | O sistema deve permitir o cadastro e a gestão de ordens de produção (OP), associando produto, quantidade, data prevista e recursos necessários. |
| RF06 | O sistema deve realizar o cálculo de necessidade de materiais (MRP) com base nas ordens de produção abertas e no estoque disponível. |
| RF07 | O sistema deve permitir o sequenciamento e o planejamento de capacidade dos centros de trabalho (máquinas e operadores). |
| RF08 | O sistema deve registrar o apontamento de produção (início, pausa, retomada e encerramento) por operação e por ordem. |
| RF09 | O sistema deve rastrear o consumo de matérias-primas por ordem de produção e atualizar o estoque em tempo real. |
| RF10 | O sistema deve calcular e exibir o índice de OEE (Disponibilidade × Performance × Qualidade) por centro de trabalho e por turno. |
| RF11 | O sistema deve integrar com sistemas de chão de fábrica (SCADA/MES) para receber dados de produção e status de equipamentos em tempo real via API ou protocolo industrial padrão. |
| RF12 | O sistema deve emitir alertas de desvio de produção quando o realizado divergir do planejado acima de threshold configurável. |

### Gestão de Suprimentos

| ID   | Descrição |
|------|-----------|
| RF13 | O sistema deve permitir o cadastro de múltiplos fornecedores por item, com dados de contato, prazo de entrega, moeda e condições de pagamento. |
| RF14 | O sistema deve gerar automaticamente solicitações de compra quando o estoque de um item atingir o ponto de reabastecimento configurado. |
| RF15 | O sistema deve suportar o processo de cotação com múltiplos fornecedores e comparação automática de propostas por critérios configuráveis (preço, prazo, qualidade). |
| RF16 | O sistema deve permitir a emissão de ordens de compra (OC) com aprovação por alçada conforme política configurável. |
| RF17 | O sistema deve registrar o recebimento de mercadorias com conferência de quantidade e vinculação à OC correspondente. |
| RF18 | O sistema deve permitir o registro e o acompanhamento de devoluções a fornecedores com geração de documentos fiscais correspondentes. |
| RF19 | O sistema deve manter histórico de desempenho de fornecedores (prazo, qualidade e preço) por item e por período. |

### Controle de Qualidade por Lote

| ID   | Descrição |
|------|-----------|
| RF20 | O sistema deve permitir a definição de planos de inspeção e critérios de aceitação por produto, lote e etapa do processo produtivo. |
| RF21 | O sistema deve registrar resultados de inspeção por lote, incluindo parâmetros medidos, valores obtidos e status de aprovação ou rejeição. |
| RF22 | O sistema deve bloquear automaticamente o consumo ou a expedição de lotes reprovados na inspeção de qualidade. |
| RF23 | O sistema deve rastrear a rastreabilidade completa de um lote, desde o recebimento da matéria-prima até o produto acabado expedido. |
| RF24 | O sistema deve registrar e acompanhar não conformidades (NC) com abertura, análise de causa-raiz, ação corretiva e encerramento. |
| RF25 | O sistema deve gerar relatórios de qualidade por produto, lote, fornecedor e período, incluindo índice de rejeição e custo da não qualidade. |

### Logística e Distribuição

| ID   | Descrição |
|------|-----------|
| RF26 | O sistema deve gerenciar o estoque de produtos acabados por local de armazenagem (endereçamento de armazém). |
| RF27 | O sistema deve permitir o planejamento e a execução de expedições, associando pedidos de venda, volumes, transportadoras e rotas. |
| RF28 | O sistema deve gerar romaneios de carga e documentos de expedição vinculados à NF-e correspondente. |
| RF29 | O sistema deve permitir o rastreamento do status de entregas com atualização de ocorrências logísticas. |
| RF30 | O sistema deve controlar devoluções de clientes (RMA), vinculando-as ao pedido original e gerando o processo de inspeção e reposição ou crédito. |

### Faturamento Fiscal e Emissão de NF-e

| ID   | Descrição |
|------|-----------|
| RF31 | O sistema deve emitir Notas Fiscais Eletrônicas (NF-e) modelo 55 com transmissão à SEFAZ em tempo real. |
| RF32 | O sistema deve calcular automaticamente os impostos incidentes (ICMS, IPI, PIS, COFINS, ISS) conforme a operação fiscal, NCM e UF de destino. |
| RF33 | O sistema deve controlar o cancelamento e a inutilização de NF-e conforme os prazos e as regras da SEFAZ. |
| RF34 | O sistema deve suportar emissão de NF-e em contingência (offline) com posterior sincronização com a SEFAZ. |
| RF35 | O sistema deve emitir Conhecimento de Transporte Eletrônico (CT-e) para operações de transporte próprio ou terceirizado. |
| RF36 | O sistema deve manter o SPED Fiscal e Contribuições atualizados a partir das movimentações registradas no sistema. |

### Gestão de RH e Folha de Pagamento

| ID   | Descrição |
|------|-----------|
| RF37 | O sistema deve manter o cadastro completo de colaboradores com dados pessoais, contratuais, cargos, centros de custo e histórico funcional. |
| RF38 | O sistema deve registrar e controlar ponto eletrônico com integração a relógios de ponto, apurando horas normais, extras e faltas. |
| RF39 | O sistema deve processar a folha de pagamento mensal com cálculo de salários, encargos (INSS, FGTS, IRRF), benefícios e descontos. |
| RF40 | O sistema deve gerar os arquivos e obrigações acessórias de RH: eSocial, CAGED, RAIS e DIRF. |
| RF41 | O sistema deve controlar férias, 13º salário, rescisões e demais verbas trabalhistas conforme a CLT. |
| RF42 | O sistema deve permitir a gestão de benefícios (VT, VR, plano de saúde, PLR) por categoria de colaborador. |

### Contabilidade e DRE em Tempo Real

| ID   | Descrição |
|------|-----------|
| RF43 | O sistema deve gerar lançamentos contábeis automaticamente a partir das movimentações de outros módulos (compras, vendas, produção, folha). |
| RF44 | O sistema deve manter o plano de contas configurável conforme a estrutura contábil da empresa. |
| RF45 | O sistema deve gerar a Demonstração do Resultado do Exercício (DRE) em tempo real, consolidada e por centro de custo. |
| RF46 | O sistema deve gerar o Balanço Patrimonial e o Fluxo de Caixa com atualização automática a partir dos lançamentos. |
| RF47 | O sistema deve controlar contas a pagar e a receber com gestão de vencimentos, baixas e projeção de fluxo de caixa. |
| RF48 | O sistema deve suportar a escrituração contábil digital e gerar os arquivos do SPED Contábil (ECD) e SPED Fiscal (EFD). |
| RF49 | O sistema deve suportar múltiplas moedas com atualização de taxas de câmbio e conversão automática para a moeda funcional. |

### Dashboards Executivos e KPIs

| ID   | Descrição |
|------|-----------|
| RF50 | O sistema deve disponibilizar dashboards executivos configuráveis com indicadores operacionais, financeiros e de qualidade em tempo real. |
| RF51 | O sistema deve permitir a definição de metas por KPI e exibir alertas visuais quando o desempenho se desviar do target configurado. |
| RF52 | O sistema deve suportar drill-down nos painéis, permitindo navegar do indicador consolidado até o registro transacional de origem. |
| RF53 | O sistema deve permitir a exportação de relatórios e painéis em PDF e Excel. |

---

## Requisitos Não Funcionais (RNF)

### Segurança

| ID    | Categoria | Descrição |
|-------|-----------|-----------|
| RNF01 | Segurança | Toda comunicação entre cliente e servidor deve utilizar TLS 1.2 ou superior. |
| RNF02 | Segurança | Dados financeiros, fiscais e de RH devem ser armazenados criptografados em repouso com AES-256. |
| RNF03 | Segurança | O sistema deve implementar controle de acesso baseado em papéis (RBAC) com segregação de funções (SoD) para operações financeiras e fiscais críticas. |
| RNF04 | Segurança | O sistema deve implementar rate limiting e bloqueio automático de contas após tentativas de acesso malsucedidas configuráveis. |
| RNF05 | Segurança | O sistema deve ser submetido a auditorias de segurança e testes de penetração periódicos. |

### Conformidade Regulatória

| ID    | Categoria    | Descrição |
|-------|--------------|-----------|
| RNF06 | Conformidade | O sistema deve estar em conformidade com a legislação fiscal brasileira vigente, incluindo atualizações de alíquotas, tabelas NCM e regras de tributação por UF. |
| RNF07 | Conformidade | O sistema deve garantir a integridade e a validade jurídica dos documentos fiscais eletrônicos (NF-e, CT-e) conforme os schemas XSD publicados pela SEFAZ. |
| RNF08 | Conformidade | O sistema deve estar em conformidade com o leiaute vigente do eSocial, SPED Contábil (ECD), SPED Fiscal (EFD) e SPED Contribuições. |
| RNF09 | Conformidade | O sistema deve estar em conformidade com a LGPD no tratamento de dados pessoais de colaboradores e clientes. |
| RNF10 | Conformidade | O sistema deve manter trilha de auditoria imutável de todas as operações financeiras, fiscais e de RH, com retenção mínima de 10 anos conforme o Código Tributário Nacional. |
| RNF11 | Conformidade | O módulo de folha de pagamento deve refletir as obrigações trabalhistas vigentes da CLT e das convenções coletivas aplicáveis. |

### Disponibilidade e Desempenho

| ID    | Categoria       | Descrição |
|-------|-----------------|-----------|
| RNF12 | Disponibilidade | O sistema deve ter disponibilidade mínima de 99,5% em horário de operação fabril, com janelas de manutenção programadas fora do turno produtivo. |
| RNF13 | Desempenho      | O cálculo de MRP deve ser concluído em até 10 minutos para bases com até 50.000 itens ativos. |
| RNF14 | Desempenho      | Os dashboards executivos devem ser carregados em até 5 segundos com dados do dia corrente. |
| RNF15 | Desempenho      | A transmissão de NF-e à SEFAZ deve ser concluída em até 30 segundos em condições normais de rede. |
| RNF16 | Escalabilidade  | A arquitetura deve suportar múltiplas unidades fabris e filiais com isolamento de dados e consolidação centralizada. |
| RNF17 | Resiliência     | A emissão de NF-e em contingência deve ser ativada automaticamente em caso de indisponibilidade da SEFAZ, com posterior sincronização. |

### Integração e Interoperabilidade

| ID    | Categoria          | Descrição |
|-------|--------------------|-----------|
| RNF18 | Interoperabilidade | A integração com sistemas SCADA/MES deve suportar protocolos industriais padrão (OPC-UA, MQTT ou REST/JSON), com configuração por unidade fabril. |
| RNF19 | Interoperabilidade | O sistema deve expor APIs RESTful documentadas para integração com sistemas legados, portais de clientes e parceiros. |
| RNF20 | Interoperabilidade | O sistema deve suportar importação e exportação de dados em formatos padrão (XML, CSV, JSON, XLSX) para integração com sistemas externos. |

### Infraestrutura e Dados

| ID    | Categoria        | Descrição |
|-------|------------------|-----------|
| RNF21 | Backup           | O sistema deve realizar backup automático diário com retenção mínima de 90 dias e backup contínuo (WAL) dos dados transacionais com RPO máximo de 1 hora. |
| RNF22 | Infraestrutura   | O ambiente de produção deve suportar implantação on-premises, em nuvem privada ou híbrida, conforme política de TI da empresa. |
| RNF23 | Manutenibilidade | O sistema deve expor métricas operacionais de todos os módulos em painel de monitoramento em tempo real para a equipe de TI. |
| RNF24 | Usabilidade      | A interface deve ser responsiva e funcionar nos principais navegadores modernos, sem necessidade de instalação de plugins. |

---

## Histórias de Usuário (HU)

### Perfil: Planejador de Produção (PCP)

**HU01 — Gerar ordens de produção e calcular necessidade de materiais**
> Como planejador de produção, quero criar ordens de produção e executar o cálculo de MRP automaticamente, para garantir que os materiais necessários estejam disponíveis antes do início da produção.

*Critérios de aceite:*
- A OP deve ser associada a produto, quantidade, data de entrega e roteiro de produção.
- O MRP deve calcular as necessidades líquidas considerando estoque disponível, OPs abertas e pedidos de compra em andamento.
- O resultado do MRP deve gerar automaticamente solicitações de compra para itens com necessidade não coberta.

---

**HU02 — Monitorar OEE e desvios de produção em tempo real**
> Como planejador de produção, quero acompanhar o OEE de cada centro de trabalho e receber alertas de desvio em tempo real, para agir rapidamente sobre perdas de eficiência.

*Critérios de aceite:*
- O OEE deve ser calculado automaticamente a partir dos dados de apontamento e integração com o chão de fábrica.
- Desvios acima do threshold configurado devem gerar alerta visual no painel e notificação por e-mail ao responsável.
- Deve ser possível fazer drill-down do OEE consolidado até os apontamentos individuais que originaram a perda.

---

### Perfil: Comprador / Gestor de Suprimentos

**HU03 — Gerenciar cotações com múltiplos fornecedores**
> Como comprador, quero enviar solicitações de cotação para múltiplos fornecedores e comparar as propostas automaticamente, para selecionar a melhor opção de compra com base em critérios objetivos.

*Critérios de aceite:*
- A cotação deve poder ser enviada para múltiplos fornecedores cadastrados para o mesmo item.
- O sistema deve comparar propostas por preço, prazo de entrega e histórico de desempenho do fornecedor.
- A aprovação da OC deve seguir o fluxo de alçada configurado, com notificação ao aprovador responsável.

---

**HU04 — Acompanhar desempenho de fornecedores**
> Como gestor de suprimentos, quero visualizar o histórico de desempenho de cada fornecedor em prazo, qualidade e preço, para embasar decisões de homologação e descredenciamento.

*Critérios de aceite:*
- O painel de desempenho deve exibir índices de pontualidade, taxa de rejeição e variação de preço por fornecedor e por item.
- Deve ser possível filtrar por período, item e categoria de material.
- O relatório deve ser exportável em Excel e PDF.

---

### Perfil: Analista de Qualidade

**HU05 — Registrar inspeção de lote e bloquear reprovados**
> Como analista de qualidade, quero registrar os resultados de inspeção de um lote e bloquear automaticamente lotes reprovados para consumo ou expedição, para garantir que apenas materiais conformes avancem no processo produtivo.

*Critérios de aceite:*
- O registro deve incluir parâmetros medidos, valores obtidos, limites de referência e status de aprovação ou rejeição.
- Lotes reprovados devem ser bloqueados automaticamente no estoque, impedindo movimentação até liberação formal.
- O sistema deve notificar o responsável pela produção e pelo suprimentos quando um lote for reprovado.

---

**HU06 — Rastrear lote do insumo ao produto acabado**
> Como analista de qualidade, quero rastrear um lote de matéria-prima do seu recebimento até o produto acabado expedido ao cliente, para suportar investigações de qualidade e ações de recall se necessário.

*Critérios de aceite:*
- A rastreabilidade deve cobrir: nota fiscal de entrada, inspeção de recebimento, consumo na OP, inspeção do produto acabado e NF-e de saída.
- A consulta deve retornar todas as OPs que consumiram o lote pesquisado e todos os clientes que receberam produtos dele derivados.
- O resultado deve ser exportável em PDF para fins de auditoria e certificação.

---

### Perfil: Analista Fiscal / Faturamento

**HU07 — Emitir NF-e com cálculo automático de impostos**
> Como analista fiscal, quero emitir NF-e com cálculo automático dos impostos incidentes e transmissão imediata à SEFAZ, para garantir a conformidade fiscal das operações de venda sem retrabalho manual.

*Critérios de aceite:*
- O sistema deve calcular ICMS, IPI, PIS e COFINS automaticamente com base no NCM, operação fiscal e UF de destino.
- A NF-e deve ser transmitida à SEFAZ e ter seu status de autorização atualizado em até 30 segundos.
- Em caso de rejeição pela SEFAZ, o sistema deve exibir o código e a descrição do erro com orientação de correção.
- Em caso de indisponibilidade da SEFAZ, a emissão em contingência deve ser ativada automaticamente.

---

**HU08 — Manter SPED Fiscal atualizado**
> Como analista fiscal, quero que o SPED Fiscal seja alimentado automaticamente pelas movimentações do sistema, para gerar os arquivos de entrega sem consolidação manual de dados.

*Critérios de aceite:*
- Todas as entradas e saídas fiscais devem gerar registros no SPED Fiscal automaticamente.
- O sistema deve validar a consistência do arquivo gerado antes da transmissão.
- Deve ser possível gerar o arquivo para qualquer período passado dentro do histórico retido.

---

### Perfil: Analista de RH / Departamento Pessoal

**HU09 — Processar folha de pagamento mensal**
> Como analista de RH, quero processar a folha de pagamento mensal com cálculo automático de salários, encargos e benefícios, para garantir o pagamento correto e o cumprimento das obrigações trabalhistas.

*Critérios de aceite:*
- O cálculo deve considerar horas normais, extras e faltas apuradas pelo ponto eletrônico integrado.
- INSS, FGTS e IRRF devem ser calculados conforme as tabelas vigentes.
- O sistema deve gerar o arquivo de remessa bancária para crédito dos salários e os arquivos do eSocial correspondentes.

---

**HU10 — Gerar obrigações acessórias de RH**
> Como analista de RH, quero gerar os arquivos do eSocial, CAGED, RAIS e DIRF diretamente pelo sistema, para cumprir as obrigações acessórias dentro dos prazos legais sem reprocessamento manual.

*Critérios de aceite:*
- Os arquivos devem ser gerados no leiaute vigente de cada obrigação.
- O sistema deve alertar sobre prazos de entrega próximos com antecedência mínima de 5 dias úteis.
- Deve ser possível validar o arquivo antes do envio ao respectivo órgão receptor.

---

### Perfil: Controller / Diretor Financeiro

**HU11 — Visualizar DRE e Fluxo de Caixa em tempo real**
> Como controller, quero visualizar a DRE e o fluxo de caixa atualizados em tempo real a partir das movimentações de todos os módulos, para tomar decisões financeiras com dados precisos e sem aguardar fechamentos manuais.

*Critérios de aceite:*
- A DRE deve ser exibida consolidada e com abertura por centro de custo.
- O fluxo de caixa deve distinguir realizado e projetado, com base nos vencimentos de contas a pagar e a receber.
- Deve ser possível fazer drill-down de qualquer linha da DRE até o lançamento contábil de origem.

---

### Perfil: Diretor / CEO (Executivo)

**HU12 — Acompanhar indicadores operacionais e financeiros pelo dashboard executivo**
> Como diretor, quero visualizar um dashboard executivo com os principais KPIs operacionais e financeiros da empresa em tempo real, para identificar desvios e oportunidades de melhoria com agilidade.

*Critérios de aceite:*
- O dashboard deve exibir, no mínimo: OEE médio, volume de produção versus planejado, receita versus meta, margem bruta, índice de qualidade e nível de serviço logístico.
- KPIs abaixo da meta devem ser destacados visualmente com indicação de variação percentual.
- O dashboard deve permitir navegação por período (dia, semana, mês, acumulado do ano) e por unidade fabril.
- Qualquer KPI deve permitir drill-down até o dado transacional de origem com no máximo três cliques.