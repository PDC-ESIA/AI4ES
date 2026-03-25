# Sistema de Controle de Estoque — Requisitos

---

## Requisitos Funcionais (RF)

| ID   | Descrição |
|------|-----------|
| RF01 | O sistema deve permitir que o operador cadastre novos produtos, informando nome, quantidade inicial e preço de custo. |
| RF02 | O sistema deve permitir que o operador edite os dados de um produto cadastrado. |
| RF03 | O sistema deve permitir que o operador remova um produto do cadastro. |
| RF04 | O sistema deve permitir que o operador registre uma entrada de mercadoria, informando o produto, a quantidade recebida e a data da entrada. |
| RF05 | O sistema deve permitir que o operador registre uma saída de produtos, informando o produto, a quantidade vendida e a data da saída. |
| RF06 | O sistema deve impedir o registro de saída com quantidade superior ao estoque disponível. |
| RF07 | O sistema deve atualizar o saldo em estoque automaticamente após cada lançamento de entrada ou saída. |
| RF08 | O sistema deve permitir configurar, por produto, um limite mínimo de estoque. |
| RF09 | O sistema deve emitir um alerta visível ao operador quando o estoque de um produto atingir ou ficar abaixo do limite mínimo configurado. |
| RF10 | O sistema deve exibir o saldo atual de estoque de todos os produtos em uma tela de consulta. |
| RF11 | O sistema deve permitir que o operador consulte o histórico de movimentações (entradas e saídas) por produto e por período. |
| RF12 | O sistema deve permitir pesquisar produtos por nome. |

---

## Requisitos Não Funcionais (RNF)

| ID    | Categoria       | Descrição |
|-------|-----------------|-----------|
| RNF01 | Portabilidade   | O sistema deve funcionar como aplicação desktop em sistemas operacionais Windows. |
| RNF02 | Persistência    | Os dados devem ser armazenados localmente em banco de dados embarcado, sem necessidade de servidor externo. |
| RNF03 | Confiabilidade  | O sistema deve garantir que nenhum lançamento de entrada ou saída seja perdido em caso de fechamento inesperado da aplicação. |
| RNF04 | Usabilidade     | As operações de entrada e saída devem ser concluídas em no máximo três interações a partir da tela principal. |
| RNF05 | Desempenho      | A consulta de estoque e o histórico de movimentações devem ser carregados em até 2 segundos, mesmo com grande volume de registros. |
| RNF06 | Segurança       | O acesso ao sistema deve ser protegido por autenticação com usuário e senha. |
| RNF07 | Manutenibilidade| O sistema deve permitir exportar os dados de estoque e movimentações em formato CSV para fins de backup e análise externa. |
| RNF08 | Rastreabilidade | Todo lançamento deve registrar data, hora e usuário responsável pela operação. |

---

## Histórias de Usuário (HU)

### Perfil: Operador

**HU01 — Cadastrar produto**
> Como operador, quero cadastrar um produto com nome, quantidade inicial e preço de custo, para que ele passe a fazer parte do controle de estoque.

*Critérios de aceite:*
- Nome e quantidade inicial são campos obrigatórios.
- O sistema não deve permitir cadastro duplicado para um mesmo nome de produto.
- O produto deve aparecer imediatamente na tela de consulta de estoque após o cadastro.

---

**HU02 — Registrar entrada de mercadoria**
> Como operador, quero registrar a entrada de um lote de mercadoria, para que o estoque reflita as quantidades recebidas.

*Critérios de aceite:*
- Deve ser possível selecionar o produto a partir de uma lista ou busca por nome.
- A quantidade informada deve ser um número inteiro positivo.
- O saldo do produto deve ser atualizado imediatamente após o lançamento.
- O lançamento deve constar no histórico de movimentações com data e hora.

---

**HU03 — Registrar saída de produto**
> Como operador, quero registrar a saída de produtos a cada venda realizada, para manter o estoque atualizado.

*Critérios de aceite:*
- O sistema deve impedir a saída caso a quantidade solicitada seja maior que o saldo disponível, exibindo mensagem de erro clara.
- O saldo deve ser decrementado imediatamente após o lançamento.
- O lançamento deve constar no histórico com data, hora e quantidade.

---

**HU04 — Ser alertado sobre estoque baixo**
> Como operador, quero receber um alerta quando o estoque de um produto atingir o limite mínimo configurado, para providenciar a reposição a tempo.

*Critérios de aceite:*
- O alerta deve ser exibido na interface de forma destacada (ex.: ícone, cor ou notificação) assim que o limite for atingido ou ultrapassado.
- O alerta deve identificar claramente qual produto está com estoque baixo e exibir o saldo atual.
- O alerta deve persistir até que o estoque seja reposto acima do limite mínimo.

---

**HU05 — Configurar limite mínimo de estoque por produto**
> Como operador, quero definir um limite mínimo de estoque para cada produto, para personalizar o gatilho de alerta conforme a realidade de cada item.

*Critérios de aceite:*
- O limite mínimo deve ser configurável individualmente por produto.
- O campo deve aceitar apenas valores inteiros não negativos.
- A alteração do limite deve ser refletida imediatamente no comportamento dos alertas.

---

**HU06 — Consultar saldo atual do estoque**
> Como operador, quero visualizar o saldo atual de todos os produtos em uma única tela, para ter uma visão geral do estoque da loja.

*Critérios de aceite:*
- A tela deve listar todos os produtos com nome, saldo atual e limite mínimo configurado.
- Produtos com estoque abaixo do limite mínimo devem ter destaque visual diferenciado.
- Deve ser possível ordenar a lista por nome ou por quantidade em estoque.

---

**HU07 — Consultar histórico de movimentações**
> Como operador, quero consultar o histórico de entradas e saídas de um produto em um período específico, para acompanhar a movimentação e identificar inconsistências.

*Critérios de aceite:*
- O histórico deve permitir filtro por produto e por intervalo de datas.
- Cada registro deve exibir tipo de movimentação (entrada ou saída), quantidade, data, hora e usuário responsável.
- O histórico deve ser exibido em ordem cronológica decrescente por padrão.

---

**HU08 — Exportar dados de estoque e movimentações**
> Como operador, quero exportar os dados de estoque e o histórico de movimentações em CSV, para realizar backups e análises em planilhas.

*Critérios de aceite:*
- A exportação deve gerar um arquivo CSV com todos os campos relevantes de cada registro.
- O operador deve poder escolher o diretório de destino do arquivo exportado.
- O sistema deve confirmar o sucesso da exportação com uma mensagem ao operador.