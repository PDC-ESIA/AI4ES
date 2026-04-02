# Plataforma de Marketplace para Artesãos — Requisitos

---

## Requisitos Funcionais (RF)

### Gestão de Usuários e Acesso

| ID   | Descrição |
|------|-----------|
| RF01 | O sistema deve permitir o cadastro de usuários com perfis distintos: administrador, artesão (vendedor) e comprador. |
| RF02 | O sistema deve permitir que usuários se autentiquem e encerrem sessão na plataforma. |
| RF03 | O sistema deve permitir que um mesmo usuário possua perfil de comprador e de artesão simultaneamente. |

### Catálogo de Produtos

| ID   | Descrição |
|------|-----------|
| RF04 | O sistema deve permitir que o artesão cadastre produtos com nome, descrição, preço, quantidade em estoque, categoria e fotos. |
| RF05 | O sistema deve permitir que o artesão edite e remova seus próprios produtos. |
| RF06 | O sistema deve permitir que o artesão publique ou despublique um produto, controlando sua visibilidade na plataforma. |
| RF07 | O sistema deve permitir que o artesão gerencie o estoque de cada produto, atualizando a quantidade disponível. |
| RF08 | O sistema deve impedir a compra de um produto com quantidade em estoque igual a zero. |
| RF09 | O sistema deve decrementar automaticamente o estoque de um produto após a confirmação de um pedido. |
| RF10 | O sistema deve permitir que compradores naveguem pelo catálogo de produtos organizados por categorias. |
| RF11 | O sistema deve permitir que compradores pesquisem produtos por nome, categoria ou artesão. |
| RF12 | O sistema deve permitir que o administrador crie, edite e remova as categorias disponíveis na plataforma. |

### Carrinho e Pedidos

| ID   | Descrição |
|------|-----------|
| RF13 | O sistema deve permitir que o comprador adicione e remova produtos do carrinho de compras. |
| RF14 | O sistema deve permitir que o comprador ajuste a quantidade de cada item no carrinho. |
| RF15 | O sistema deve exibir o resumo do pedido com itens, quantidades, valores unitários e total antes da finalização. |
| RF16 | O sistema deve permitir que o comprador finalize o pedido com pagamento integrado. |
| RF17 | O sistema deve suportar ao menos um método de pagamento integrado (ex.: cartão de crédito ou PIX). |
| RF18 | O sistema deve confirmar o pedido ao comprador após a aprovação do pagamento, por e-mail e na plataforma. |
| RF19 | O sistema deve notificar o artesão por e-mail quando um novo pedido for recebido. |
| RF20 | O sistema deve permitir que o artesão atualize o status de cada pedido (recebido, em preparação, enviado, entregue). |
| RF21 | O sistema deve permitir que o comprador acompanhe o status atualizado dos seus pedidos. |
| RF22 | O sistema deve permitir que um pedido contenha produtos de múltiplos artesãos, gerando subpedidos individuais por artesão. |

### Avaliações

| ID   | Descrição |
|------|-----------|
| RF23 | O sistema deve permitir que o comprador avalie um produto após a entrega confirmada, com nota de 1 a 5 e comentário textual. |
| RF24 | O sistema deve exibir a média de avaliações e os comentários de cada produto na sua página pública. |
| RF25 | O sistema deve permitir que o artesão responda publicamente a uma avaliação recebida. |

### Comissão e Painel Financeiro do Vendedor

| ID   | Descrição |
|------|-----------|
| RF26 | O sistema deve calcular e reter automaticamente a comissão da plataforma sobre cada venda confirmada. |
| RF27 | O sistema deve permitir que o administrador configure o percentual de comissão da plataforma. |
| RF28 | O sistema deve disponibilizar ao artesão um painel financeiro com o histórico de vendas, valores brutos, comissões retidas e saldo líquido disponível. |
| RF29 | O sistema deve exibir ao artesão o saldo líquido disponível para saque. |
| RF30 | O sistema deve permitir que o artesão solicite o saque do saldo disponível, informando dados bancários. |

---

## Requisitos Não Funcionais (RNF)

| ID    | Categoria        | Descrição |
|-------|------------------|-----------|
| RNF01 | Segurança        | O acesso às áreas administrativas e de vendedor deve ser restrito por autenticação com perfil correspondente. |
| RNF02 | Segurança        | As senhas dos usuários devem ser armazenadas com hash seguro (ex.: bcrypt). |
| RNF03 | Segurança        | A comunicação com o gateway de pagamento deve ocorrer via HTTPS e seguir as diretrizes PCI-DSS; dados de cartão não devem ser armazenados no sistema. |
| RNF04 | Escalabilidade   | As fotos de produtos devem ser armazenadas em serviço externo de object storage, desacoplado do servidor da aplicação. |
| RNF05 | Desempenho       | A listagem de produtos por categoria deve ser carregada em até 2 segundos, mesmo com grande volume de itens. |
| RNF06 | Desempenho       | O painel financeiro do artesão deve ser carregado em até 3 segundos. |
| RNF07 | Usabilidade      | A interface deve ser responsiva e funcionar adequadamente em dispositivos móveis e desktops. |
| RNF08 | Confiabilidade   | O processamento de pagamento deve ser transacional: em caso de falha, nenhuma cobrança deve ser efetivada e nenhum estoque deve ser decrementado. |
| RNF09 | Rastreabilidade  | Toda transação financeira (venda, comissão, saque) deve gerar registro imutável com data, hora, valor e partes envolvidas. |
| RNF10 | Compatibilidade  | A plataforma deve funcionar nos principais navegadores modernos (Chrome, Firefox, Safari, Edge). |
| RNF11 | Conformidade     | O sistema deve estar em conformidade com a LGPD no tratamento de dados pessoais e financeiros dos usuários. |
| RNF12 | Disponibilidade  | A plataforma deve ter disponibilidade mínima de 99,5% ao mês. |
| RNF13 | Manutenibilidade | O sistema deve registrar logs de eventos críticos: confirmação de pedido, falha de pagamento, solicitação de saque e alterações de comissão. |

---

## Histórias de Usuário (HU)

### Perfil: Artesão (Vendedor)

**HU01 — Cadastrar produto com fotos**
> Como artesão, quero cadastrar meus produtos com nome, descrição, preço, quantidade em estoque, categoria e fotos, para apresentá-los de forma atrativa aos compradores.

*Critérios de aceite:*
- Nome, preço e quantidade são campos obrigatórios.
- Deve ser possível fazer upload de múltiplas fotos por produto.
- O produto deve aparecer no catálogo imediatamente após a publicação.

---

**HU02 — Gerenciar estoque dos produtos**
> Como artesão, quero gerenciar a quantidade em estoque dos meus produtos, para evitar vendas de itens que não possuo disponíveis.

*Critérios de aceite:*
- O artesão deve poder atualizar manualmente a quantidade de qualquer produto.
- O sistema deve decrementar o estoque automaticamente após cada venda confirmada.
- Produtos com estoque zerado devem ser sinalizados visualmente e bloqueados para compra.

---

**HU03 — Acompanhar e atualizar status dos pedidos recebidos**
> Como artesão, quero visualizar os pedidos recebidos e atualizar o status de cada um, para manter o comprador informado sobre o andamento da sua compra.

*Critérios de aceite:*
- Os pedidos devem ser listados com data, itens, quantidade, valor e status atual.
- O artesão deve poder avançar o status do pedido entre: recebido, em preparação, enviado e entregue.
- O comprador deve ser notificado na plataforma a cada atualização de status.

---

**HU04 — Visualizar painel financeiro**
> Como artesão, quero visualizar meu painel financeiro com o histórico de vendas, comissões retidas e saldo líquido disponível, para acompanhar meus ganhos na plataforma.

*Critérios de aceite:*
- O painel deve exibir, por venda: valor bruto, percentual e valor da comissão retida e valor líquido repassado.
- Deve haver um resumo com totais por período (diário, mensal e acumulado).
- O saldo líquido disponível para saque deve estar em destaque no painel.

---

**HU05 — Solicitar saque do saldo disponível**
> Como artesão, quero solicitar o saque do meu saldo líquido disponível, para receber os valores das minhas vendas na minha conta bancária.

*Critérios de aceite:*
- O artesão deve informar os dados bancários para transferência no momento da solicitação.
- A solicitação deve ser registrada com data, valor e status (pendente, processado).
- O saldo disponível deve ser atualizado imediatamente após a solicitação, refletindo o valor em processamento.

---

**HU06 — Responder avaliações de compradores**
> Como artesão, quero responder publicamente às avaliações que recebi nos meus produtos, para interagir com os compradores e demonstrar cuidado com o atendimento.

*Critérios de aceite:*
- Cada avaliação deve ter espaço para uma única resposta do artesão.
- A resposta deve ser exibida publicamente abaixo da avaliação correspondente.
- Não deve ser possível editar ou excluir uma resposta após a publicação.

---

### Perfil: Comprador

**HU07 — Navegar e pesquisar produtos**
> Como comprador, quero navegar pelo catálogo por categorias e pesquisar produtos por nome ou artesão, para encontrar facilmente o que estou procurando.

*Critérios de aceite:*
- A navegação por categorias deve exibir os produtos disponíveis com foto, nome, preço e média de avaliações.
- A pesquisa deve retornar resultados parciais e em tempo real enquanto o usuário digita.
- Produtos sem estoque não devem ser exibidos nos resultados de busca por padrão.

---

**HU08 — Adicionar itens ao carrinho e finalizar compra**
> Como comprador, quero adicionar produtos de diferentes artesãos ao carrinho e finalizar a compra com pagamento integrado, para adquirir tudo em uma única transação.

*Critérios de aceite:*
- O carrinho deve exibir itens, quantidades, valores unitários e total consolidado.
- Deve ser possível ajustar quantidades ou remover itens antes da finalização.
- O sistema deve confirmar a compra por e-mail após a aprovação do pagamento.
- Em caso de falha no pagamento, nenhum estoque deve ser decrementado.

---

**HU09 — Acompanhar status dos pedidos**
> Como comprador, quero acompanhar o status atualizado dos meus pedidos, para saber quando meu produto está sendo preparado, enviado ou entregue.

*Critérios de aceite:*
- A área de pedidos deve listar todas as compras com data, itens e status atual.
- O status deve ser atualizado em tempo real conforme o artesão o avança.
- Pedidos com múltiplos artesãos devem exibir o status individual de cada subpedido.

---

**HU10 — Avaliar produto após entrega**
> Como comprador, quero avaliar um produto com nota de 1 a 5 e um comentário, para compartilhar minha experiência com outros compradores.

*Critérios de aceite:*
- A avaliação só deve ser habilitada após o pedido ter o status de entregue.
- Cada produto de um pedido deve poder ser avaliado individualmente.
- Não deve ser possível avaliar o mesmo item mais de uma vez.

---

### Perfil: Administrador

**HU11 — Gerenciar categorias da plataforma**
> Como administrador, quero criar, editar e remover as categorias de produtos disponíveis, para manter o catálogo organizado e relevante.

*Critérios de aceite:*
- Ao remover uma categoria, os produtos associados devem ser notificados ao artesão para reclassificação.
- Uma categoria com produtos ativos não deve ser removida sem confirmação explícita.

---

**HU12 — Configurar percentual de comissão**
> Como administrador, quero configurar o percentual de comissão retido pela plataforma sobre cada venda, para ajustar o modelo de negócio conforme necessário.

*Critérios de aceite:*
- A alteração do percentual deve afetar apenas as vendas futuras, sem alterar registros já processados.
- O sistema deve registrar log com data, usuário e valores anterior e novo a cada alteração de comissão.
- O percentual vigente deve ser visível para os artesãos no painel financeiro.