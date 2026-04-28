# Time 2: Design & Prototipagem (Arquitetura de Agentes)

**Coordenação:** Mariana  
**Líder Operacional:** Jeniffer  
**Autor:** Leonardo Côrtes Filho

## Objetivo

Listar requisitos de sistemas hipotéticos para uso como casos de teste dos agentes de design.

---

## Entrega

Para esta tarefa serão realizados dois tipos de entrega:

1. A lista geral de requisitos consolidada (este arquivo);
    Cada requisito terá seu escopo pré-definido e uma descrição da origem do seu escopo.
2. Arquivos Markdown individuais contendo RFs, RNFs e HUs para cada sistema específico.
    Adicionalmente, todos os sistemas são indexados por: {tamanho: **P**equeno, **M**édio ou **G**rande}{index numérico} - {descrição resumida}

---

## Sistemas

### Escopo pequeno

#### P01 — Cardápio digital para restaurante

**Origem do escopo:** único ator administrativo, sem integrações externas, sem autenticação de usuário final.

Sistema web simples que permite a um restaurante cadastrar e exibir seu cardápio online. O estabelecimento pode organizar os itens por categoria, adicionar descrição e preço, e marcar itens como indisponíveis. O cliente acessa o cardápio pelo navegador, sem necessidade de cadastro ou autenticação.

#### P02 — Agendador de consultas para clínica pequena

**Origem do escopo:** dois atores (recepcionista e paciente), uma integração simples de e-mail, agenda de profissional único.

Sistema que permite a uma clínica de pequeno porte gerenciar a agenda de um único profissional de saúde. A recepcionista cadastra pacientes, registra consultas em horários disponíveis e pode cancelar ou remarcar atendimentos. O sistema envia uma notificação simples por e-mail ao paciente quando o agendamento é confirmado.

#### P03 — Controle de estoque para loja física

**Origem do escopo:** único ator operacional, sem integrações externas, lógica de negócio restrita a entradas e saídas de produtos.

Sistema desktop para controle de entrada e saída de produtos em uma loja física de pequeno porte. O operador registra produtos com nome, quantidade e preço de custo, lança entradas de mercadoria e registra saídas manualmente a cada venda. O sistema alerta quando o estoque de um produto cai abaixo de um limite configurável.

#### P04 — Biblioteca pessoal de livros

**Origem do escopo:** único usuário, sem integrações externas, complexidade restrita a organização e busca de acervo pessoal.

Aplicação web para uso individual que permite ao usuário catalogar seus livros físicos e digitais. O usuário registra títulos, autores, editoras e status de leitura (não lido, lendo, concluído), organiza o acervo por gênero ou coleção e filtra por qualquer atributo. O sistema gera um resumo do acervo com estatísticas simples, como total de livros por status e gêneros mais frequentes.

---

### Escopo médio

#### M01 — Plataforma de cursos online

**Origem do escopo:** dois atores principais (instrutor e estudante), controle de acesso por progresso, geração de certificados e métricas de engajamento.

Sistema web que permite instrutores publicarem cursos em vídeo organizados em módulos e aulas. Estudantes se cadastram, adquirem cursos e acompanham seu progresso. A plataforma controla o acesso ao conteúdo conforme as aulas concluídas, emite certificado ao final do curso e oferece um painel de métricas básicas para o instrutor acompanhar matrículas e engajamento.

#### M02 — Sistema de gestão para clínica odontológica

**Origem do escopo:** múltiplos profissionais, prontuário eletrônico, integração com convênios e portal para pacientes.

Sistema que centraliza a operação de uma clínica odontológica com múltiplos profissionais. Gerencia agenda de cada dentista, prontuário digital dos pacientes com histórico de procedimentos e radiografias, controle de materiais e equipamentos, e faturamento de procedimentos por convênio ou particular. Pacientes podem acessar um portal para visualizar seus agendamentos e documentos.

#### M03 — Marketplace de produtos artesanais

**Origem do escopo:** três atores (artesão, comprador e plataforma), integração com gateway de pagamento, gestão de estoque distribuída por vendedor.

Plataforma que conecta artesãos e compradores. Produtores cadastram seus produtos com fotos, descrições e preços, gerenciam seu próprio estoque e acompanham pedidos recebidos. Compradores navegam por categorias, adicionam itens ao carrinho, realizam pagamento integrado e avaliam as compras. A plataforma retém uma comissão por venda e oferece um painel financeiro para cada vendedor.

#### M04 — Sistema de gestão de condomínio

**Origem do escopo:** múltiplos atores (síndico, condôminos e funcionários), integração com gateway de pagamento para boletos, gestão de áreas comuns e comunicados.

Sistema web que centraliza a administração de um condomínio residencial. O síndico cadastra unidades e moradores, emite boletos de condomínio com integração a gateway de pagamento, registra ocorrências e publica comunicados. Condôminos acessam um portal para visualizar boletos, reservar áreas comuns, registrar ocorrências e acompanhar assembleias. Funcionários registram visitantes e controle de acesso.

---

### Escopo grande

#### G01 — Sistema bancário digital

**Origem do escopo:** múltiplos perfis de usuário, diversas integrações regulatórias (Banco Central, open finance, Pix, TED), requisitos de segurança e conformidade em toda a plataforma.

Plataforma financeira completa que oferece conta corrente, poupança, cartão de débito e crédito, transferências via Pix e TED, pagamento de boletos e investimentos em renda fixa. Conta com autenticação multifator, detecção de fraudes em tempo real, conformidade com regulamentações do Banco Central e integração com o open finance. Disponível em aplicativo mobile e web, com suporte a múltiplos perfis de usuário — pessoa física, pessoa jurídica e gerente de relacionamento.

#### G02 — Plataforma de telemedicina

**Origem do escopo:** alta complexidade regulatória (LGPD, CFM), múltiplas integrações externas (laboratórios, planos de saúde, prescrição digital), atores variados em contextos clínicos distintos.

Sistema de saúde que integra agendamento de consultas, videochamada médico-paciente, prontuário eletrônico compartilhado entre especialidades, prescrição digital com validade jurídica, integração com laboratórios para resultados de exames e cobertura por planos de saúde. Conta com módulo administrativo para gestão de hospitais e clínicas parceiras, conformidade com a LGPD e o CFM, e aplicativo para médicos e pacientes.

#### G03 — ERP para indústria manufatureira

**Origem do escopo:** cobertura de toda a cadeia operacional da empresa, integração com sistemas de chão de fábrica (SCADA/MES) e obrigações fiscais, alto volume de dados transacionais e múltiplos departamentos como atores.

Sistema integrado de gestão empresarial voltado para indústrias de manufatura. Cobre planejamento e controle da produção, gestão de suprimentos com múltiplos fornecedores, controle de qualidade por lote, logística e distribuição, faturamento fiscal com emissão de NF-e, gestão de RH e folha de pagamento, contabilidade e DRE em tempo real. Integra-se com sistemas de chão de fábrica (SCADA/MES) e oferece dashboards executivos com indicadores de desempenho operacional.

#### G04 — Plataforma de logística e rastreamento de cargas

**Origem do escopo:** ecossistema com múltiplos parceiros externos (transportadoras, clientes embarcadores e destinatários), integração com APIs de rastreamento, geolocalização e fiscalização de notas fiscais, alto volume de eventos em tempo real.

Plataforma que gerencia o ciclo completo de transporte de cargas, desde a coleta até a entrega. Embarcadores registram pedidos de frete, a plataforma roteia automaticamente para transportadoras parceiras com base em preço, prazo e tipo de carga. Motoristas atualizam o status da entrega via aplicativo mobile com geolocalização. Destinatários acompanham a carga em tempo real, recebem notificações de cada etapa e assinam o comprovante de entrega digitalmente. A plataforma integra com sistemas de emissão de CT-e, consulta de SEFAZ e seguradoras para cobertura de sinistros.

---

## Visão geral

| Sistema | Qtd. RFs | Qtd. RNFs | Qtd. HUs |
| ------- | -------- | --------- | -------- |
| P01 — Cardápio digital para restaurante                  | 11 | 07 | 08 |
| P02 — Agendador de consultas para clínica pequena        | 12 | 08 | 09 |
| P03 — Controle de estoque para loja física               | 12 | 08 | 08 |
| P04 — Biblioteca pessoal de livros                       | 13 | 07 | 08 |
| M01 — Plataforma de cursos online                        | 16 | 10 | 09 |
| M02 — Sistema de gestão para clínica odontológica        | 25 | 11 | 12 |
| M03 — Marketplace de produtos artesanais                 | 30 | 13 | 12 |
| M04 — Sistema de gestão de condomínio                    | 33 | 13 | 14 |
| G01 — Sistema bancário digital                           | 47 | 24 | 13 |
| G02 — Plataforma de telemedicina                         | 46 | 26 | 14 |
| G03 — ERP para indústria manufatureira                   | 53 | 24 | 12 |
| G04 — Plataforma de logística e rastreamento de cargas   | 49 | 25 | 14 |
