# Sistema de Catalogação de Livros — Requisitos

---

## Requisitos Funcionais (RF)

| ID   | Descrição |
|------|-----------|
| RF01 | O sistema deve permitir que o usuário cadastre um livro, informando título, autor, editora e status de leitura. |
| RF02 | O sistema deve permitir que o usuário edite os dados de um livro cadastrado. |
| RF03 | O sistema deve permitir que o usuário remova um livro do acervo. |
| RF04 | O sistema deve oferecer três opções de status de leitura: não lido, lendo e concluído. |
| RF05 | O sistema deve permitir que o usuário atualize o status de leitura de um livro a qualquer momento. |
| RF06 | O sistema deve permitir que o usuário crie, edite e remova gêneros literários. |
| RF07 | O sistema deve permitir que o usuário crie, edite e remova coleções personalizadas. |
| RF08 | O sistema deve permitir que o usuário associe um livro a um ou mais gêneros e a uma coleção. |
| RF09 | O sistema deve permitir filtrar o acervo por qualquer atributo cadastrado (título, autor, editora, status, gênero ou coleção). |
| RF10 | O sistema deve exibir um resumo do acervo com o total de livros por status de leitura. |
| RF11 | O sistema deve exibir os gêneros mais frequentes no acervo do usuário. |
| RF12 | O sistema deve permitir que o usuário pesquise livros por título ou autor via campo de busca. |
| RF13 | O sistema deve diferenciar livros físicos de livros digitais no cadastro. |

---

## Requisitos Não Funcionais (RNF)

| ID    | Categoria       | Descrição |
|-------|-----------------|-----------|
| RNF01 | Segurança       | O acesso à aplicação deve ser protegido por autenticação, garantindo que o acervo seja estritamente pessoal e isolado por usuário. |
| RNF02 | Usabilidade     | A interface deve ser responsiva e funcionar adequadamente em dispositivos móveis e desktops. |
| RNF03 | Desempenho      | A listagem e filtragem do acervo devem ser executadas em até 2 segundos, independentemente do volume de registros. |
| RNF04 | Persistência    | Os dados do acervo devem ser persistidos em banco de dados, sem risco de perda ao fechar ou recarregar a aplicação. |
| RNF05 | Usabilidade     | O resumo estatístico do acervo deve ser atualizado em tempo real conforme o usuário adiciona, edita ou remove livros. |
| RNF06 | Compatibilidade | A aplicação deve funcionar nos principais navegadores modernos (Chrome, Firefox, Safari, Edge). |
| RNF07 | Manutenibilidade| O sistema deve permitir exportar o acervo completo em formato CSV ou JSON para fins de backup pessoal. |

---

## Histórias de Usuário (HU)

### Perfil: Usuário

**HU01 — Cadastrar livro**
> Como usuário, quero cadastrar um livro com título, autor, editora, tipo (físico ou digital) e status de leitura, para registrá-lo no meu acervo pessoal.

*Critérios de aceite:*
- Título e autor são campos obrigatórios.
- O status de leitura deve ser selecionado dentre as opções: não lido, lendo e concluído.
- O livro deve aparecer no acervo imediatamente após o cadastro.

---

**HU02 — Atualizar status de leitura**
> Como usuário, quero atualizar o status de leitura de um livro, para registrar meu progresso ao longo do tempo.

*Critérios de aceite:*
- O status deve poder ser alterado entre não lido, lendo e concluído a qualquer momento.
- A alteração deve ser refletida imediatamente nas estatísticas do resumo do acervo.

---

**HU03 — Organizar livros por gênero**
> Como usuário, quero criar gêneros literários e associar livros a eles, para categorizar meu acervo de forma organizada.

*Critérios de aceite:*
- O usuário deve poder criar, renomear e remover gêneros livremente.
- Um livro pode ser associado a mais de um gênero.
- Ao remover um gênero, os livros associados não devem ser excluídos, apenas desvinculados.

---

**HU04 — Organizar livros por coleção**
> Como usuário, quero criar coleções e agrupar livros dentro delas, para organizar séries, sagas ou agrupamentos temáticos pessoais.

*Critérios de aceite:*
- O usuário deve poder criar, renomear e remover coleções livremente.
- Um livro pode pertencer a apenas uma coleção por vez.
- Ao remover uma coleção, os livros associados não devem ser excluídos, apenas desvinculados.

---

**HU05 — Filtrar o acervo**
> Como usuário, quero filtrar meu acervo por qualquer atributo (título, autor, editora, status, gênero, coleção ou tipo), para localizar livros específicos com facilidade.

*Critérios de aceite:*
- Deve ser possível combinar múltiplos filtros simultaneamente.
- Os resultados devem ser atualizados dinamicamente conforme os filtros são aplicados.
- Deve haver uma opção para limpar todos os filtros ativos com um único clique.

---

**HU06 — Pesquisar livros por título ou autor**
> Como usuário, quero pesquisar livros digitando parte do título ou do nome do autor, para encontrar rapidamente um registro específico no acervo.

*Critérios de aceite:*
- A busca deve retornar resultados parciais (ex.: parte do título ou sobrenome do autor).
- Os resultados devem aparecer de forma dinâmica enquanto o usuário digita.

---

**HU07 — Visualizar resumo do acervo**
> Como usuário, quero visualizar um resumo com estatísticas do meu acervo, para entender meu comportamento de leitura e a composição da minha biblioteca.

*Critérios de aceite:*
- O resumo deve exibir o total geral de livros e o total separado por status (não lido, lendo, concluído).
- O resumo deve listar os gêneros mais frequentes no acervo.
- As estatísticas devem ser atualizadas automaticamente a cada alteração no acervo.

---

**HU08 — Exportar o acervo**
> Como usuário, quero exportar todos os dados do meu acervo em CSV ou JSON, para fazer backup pessoal ou usar as informações em outras ferramentas.

*Critérios de aceite:*
- A exportação deve incluir todos os campos cadastrados para cada livro.
- O usuário deve poder escolher o formato de exportação (CSV ou JSON).
- O arquivo deve ser gerado e disponibilizado para download diretamente pelo navegador.