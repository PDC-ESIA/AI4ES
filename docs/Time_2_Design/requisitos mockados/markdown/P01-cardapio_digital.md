# Sistema de Cardápio Online — Requisitos

---

## Requisitos Funcionais (RF)

| ID    | Descrição |
|-------|-----------|
| RF01  | O sistema deve permitir que o estabelecimento cadastre itens no cardápio, informando nome, descrição e preço. |
| RF02  | O sistema deve permitir que o estabelecimento edite os dados de um item cadastrado. |
| RF03  | O sistema deve permitir que o estabelecimento remova um item do cardápio. |
| RF04  | O sistema deve permitir que o estabelecimento crie, edite e remova categorias para organizar os itens do cardápio. |
| RF05  | O sistema deve permitir que o estabelecimento associe um item a uma categoria. |
| RF06  | O sistema deve permitir que o estabelecimento marque um item como indisponível, sem removê-lo do cardápio. |
| RF07  | O sistema deve permitir que o estabelecimento reative um item previamente marcado como indisponível. |
| RF08  | O sistema deve exibir o cardápio ao cliente via navegador web, sem exigir cadastro ou autenticação. |
| RF09  | O sistema deve exibir os itens agrupados por categoria na visão do cliente. |
| RF10  | O sistema deve indicar visualmente, na visão do cliente, os itens marcados como indisponíveis. |
| RF11  | O sistema deve exibir nome, descrição e preço de cada item na visão do cliente. |

---

## Requisitos Não Funcionais (RNF)

| ID     | Categoria       | Descrição |
|--------|-----------------|-----------|
| RNF01  | Usabilidade     | A interface do cliente deve ser responsiva e funcionar adequadamente em dispositivos móveis e desktops. |
| RNF02  | Desempenho      | O cardápio deve ser carregado em até 3 segundos em conexões de banda larga padrão. |
| RNF03  | Segurança       | O acesso à área administrativa do estabelecimento deve ser protegido por autenticação (usuário e senha). |
| RNF04  | Disponibilidade | O sistema deve estar disponível ao cliente 99% do tempo em regime 24/7. |
| RNF05  | Manutenibilidade| O sistema deve ser desenvolvido de forma modular, facilitando a adição de novas funcionalidades. |
| RNF06  | Compatibilidade | O cardápio deve ser acessível nos principais navegadores modernos (Chrome, Firefox, Safari, Edge). |
| RNF07  | Acessibilidade  | A interface do cliente deve seguir as diretrizes básicas de acessibilidade web (WCAG 2.1 nível A). |

---

## Histórias de Usuário (HU)

### Perfil: Estabelecimento (Administrador)

**HU01 — Cadastrar item no cardápio**
> Como estabelecimento, quero cadastrar um novo item com nome, descrição e preço, para que ele apareça no cardápio visto pelos clientes.

*Critérios de aceite:*
- Todos os campos obrigatórios (nome e preço) devem ser validados antes de salvar.
- O item deve ser exibido imediatamente no cardápio após o cadastro.

---

**HU02 — Organizar itens por categoria**
> Como estabelecimento, quero criar categorias e associar itens a elas, para que o cardápio fique organizado e mais fácil de navegar.

*Critérios de aceite:*
- Deve ser possível criar e nomear uma categoria livremente.
- Um item pode pertencer a apenas uma categoria.
- A ordem das categorias no cardápio deve ser controlável pelo estabelecimento.

---

**HU03 — Editar item do cardápio**
> Como estabelecimento, quero editar as informações de um item já cadastrado, para corrigir erros ou atualizar preços e descrições.

*Critérios de aceite:*
- As alterações devem ser refletidas imediatamente no cardápio público.
- Todos os campos editáveis do cadastro devem ser modificáveis.

---

**HU04 — Marcar item como indisponível**
> Como estabelecimento, quero marcar um item como indisponível temporariamente, para informar ao cliente sem precisar removê-lo do cardápio.

*Critérios de aceite:*
- O item deve continuar visível no cardápio com indicação clara de indisponibilidade.
- Deve ser possível desfazer a indisponibilidade a qualquer momento.

---

**HU05 — Remover item do cardápio**
> Como estabelecimento, quero remover um item do cardápio, para que ele não apareça mais para os clientes.

*Critérios de aceite:*
- O sistema deve solicitar confirmação antes de excluir o item.
- Após a exclusão, o item não deve mais aparecer no cardápio público.

---

### Perfil: Cliente

**HU06 — Visualizar o cardápio sem cadastro**
> Como cliente, quero acessar o cardápio pelo navegador sem precisar me cadastrar ou fazer login, para ver as opções disponíveis de forma rápida e sem fricção.

*Critérios de aceite:*
- O cardápio deve ser acessível por URL direta, sem qualquer barreira de autenticação.
- A página deve carregar corretamente em dispositivos móveis.

---

**HU07 — Navegar pelo cardápio por categorias**
> Como cliente, quero ver os itens organizados por categoria, para encontrar mais facilmente o que estou procurando.

*Critérios de aceite:*
- As categorias devem estar visíveis e identificadas no cardápio.
- Os itens devem ser listados dentro de suas respectivas categorias.

---

**HU08 — Identificar itens indisponíveis**
> Como cliente, quero saber quais itens estão indisponíveis, para não me frustrar ao tentar pedi-los.

*Critérios de aceite:*
- Itens indisponíveis devem ter indicação visual clara e distinta (ex.: label, opacidade reduzida).
- A informação de indisponibilidade deve ser exibida sem remover o item da lista.