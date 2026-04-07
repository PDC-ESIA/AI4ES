# Plataforma de Cursos em Vídeo — Requisitos

---

## Requisitos Funcionais (RF)

| ID   | Descrição |
|------|-----------|
| RF01 | O sistema deve permitir que o instrutor crie um curso, informando título, descrição, capa e preço. |
| RF02 | O sistema deve permitir que o instrutor organize o curso em módulos e adicione aulas a cada módulo. |
| RF03 | O sistema deve permitir que o instrutor faça upload de vídeo para cada aula. |
| RF04 | O sistema deve permitir que o instrutor edite e remova cursos, módulos e aulas. |
| RF05 | O sistema deve permitir que o instrutor publique ou despublique um curso, controlando sua visibilidade na plataforma. |
| RF06 | O sistema deve permitir que estudantes se cadastrem na plataforma informando nome, e-mail e senha. |
| RF07 | O sistema deve permitir que estudantes adquiram cursos disponíveis. |
| RF08 | O sistema deve liberar o acesso ao conteúdo de um curso somente após a aquisição pelo estudante. |
| RF09 | O sistema deve registrar a conclusão de uma aula quando o estudante a marca como concluída. |
| RF10 | O sistema deve controlar o progresso do estudante no curso com base no número de aulas concluídas. |
| RF11 | O sistema deve emitir um certificado de conclusão ao estudante quando todas as aulas do curso forem concluídas. |
| RF12 | O sistema deve exibir ao estudante seu percentual de progresso em cada curso adquirido. |
| RF13 | O sistema deve oferecer ao instrutor um painel com o número total de matrículas por curso. |
| RF14 | O sistema deve oferecer ao instrutor métricas de engajamento por aula, como número de visualizações e taxa de conclusão. |
| RF15 | O sistema deve permitir que o estudante acesse o certificado emitido para download. |
| RF16 | O sistema deve permitir que estudantes e instrutores façam login e logout na plataforma. |

---

## Requisitos Não Funcionais (RNF)

| ID    | Categoria       | Descrição |
|-------|-----------------|-----------|
| RNF01 | Segurança       | O acesso ao conteúdo de um curso deve ser restrito exclusivamente a estudantes que o adquiriram. |
| RNF02 | Segurança       | As senhas dos usuários devem ser armazenadas com hash seguro (ex.: bcrypt). |
| RNF03 | Desempenho      | Os vídeos devem ser entregues via streaming, evitando download integral antes da reprodução. |
| RNF04 | Escalabilidade  | O armazenamento de vídeos deve utilizar serviço externo de object storage (ex.: S3 ou equivalente), desacoplado do servidor da aplicação. |
| RNF05 | Usabilidade     | A interface deve ser responsiva e funcionar adequadamente em dispositivos móveis e desktops. |
| RNF06 | Desempenho      | O painel de métricas do instrutor deve ser carregado em até 3 segundos. |
| RNF07 | Confiabilidade  | O progresso do estudante deve ser salvo automaticamente a cada aula marcada como concluída, sem risco de perda. |
| RNF08 | Compatibilidade | A plataforma deve funcionar nos principais navegadores modernos (Chrome, Firefox, Safari, Edge). |
| RNF09 | Manutenibilidade| O sistema deve registrar logs de eventos críticos: aquisição de curso, emissão de certificado e erros de upload de vídeo. |
| RNF10 | Acessibilidade  | O player de vídeo deve oferecer controles básicos de acessibilidade (play/pause, volume, velocidade de reprodução). |

---

## Histórias de Usuário (HU)

### Perfil: Instrutor

**HU01 — Criar e estruturar um curso**
> Como instrutor, quero criar um curso com título, descrição e capa, organizá-lo em módulos e adicionar aulas com vídeos a cada módulo, para disponibilizar meu conteúdo de forma estruturada na plataforma.

*Critérios de aceite:*
- Título e descrição são campos obrigatórios para criação do curso.
- Deve ser possível adicionar, reordenar e remover módulos e aulas livremente antes da publicação.
- Cada aula deve aceitar o upload de um arquivo de vídeo.

---

**HU02 — Publicar e despublicar curso**
> Como instrutor, quero controlar quando meu curso fica visível na plataforma, para publicá-lo apenas quando estiver pronto e despublicá-lo se necessário.

*Critérios de aceite:*
- Um curso despublicado não deve aparecer para estudantes na plataforma.
- Estudantes que já adquiriram o curso devem manter acesso mesmo após uma despublicação.
- O instrutor deve visualizar claramente o status (publicado / rascunho) de cada curso no seu painel.

---

**HU03 — Acompanhar matrículas do curso**
> Como instrutor, quero visualizar o número total de matrículas em cada um dos meus cursos, para entender o alcance do meu conteúdo.

*Critérios de aceite:*
- O painel deve exibir o total de estudantes matriculados por curso.
- Os dados devem ser atualizados em tempo real ou com defasagem máxima de 1 hora.

---

**HU04 — Acompanhar engajamento por aula**
> Como instrutor, quero visualizar métricas de engajamento por aula (visualizações e taxa de conclusão), para identificar quais partes do curso geram mais ou menos engajamento.

*Critérios de aceite:*
- O painel deve exibir, por aula, o número de visualizações e o percentual de estudantes que a concluíram.
- As métricas devem ser acessíveis a partir do painel do curso correspondente.

---

### Perfil: Estudante

**HU05 — Cadastrar-se na plataforma**
> Como estudante, quero me cadastrar na plataforma informando meu nome, e-mail e senha, para ter acesso à compra e ao consumo de cursos.

*Critérios de aceite:*
- E-mail e senha são obrigatórios; o e-mail deve ter formato válido e ser único na plataforma.
- A senha deve ter no mínimo 8 caracteres.
- Após o cadastro, o estudante deve ser redirecionado para a página inicial da plataforma.

---

**HU06 — Adquirir um curso**
> Como estudante, quero adquirir um curso disponível na plataforma, para ter acesso ao seu conteúdo completo.

*Critérios de aceite:*
- O acesso ao conteúdo do curso deve ser liberado imediatamente após a aquisição.
- O curso adquirido deve aparecer na área de cursos do estudante.
- Não deve ser possível adquirir o mesmo curso duas vezes.

---

**HU07 — Assistir aulas e acompanhar progresso**
> Como estudante, quero assistir às aulas do curso e marcar cada uma como concluída, para acompanhar meu progresso até a conclusão.

*Critérios de aceite:*
- O vídeo deve ser reproduzido via streaming diretamente na plataforma.
- O estudante deve poder marcar uma aula como concluída manualmente.
- O percentual de progresso no curso deve ser atualizado imediatamente após cada conclusão de aula.

---

**HU08 — Receber e baixar o certificado de conclusão**
> Como estudante, quero receber e fazer o download do meu certificado ao concluir todas as aulas de um curso, para ter comprovação do aprendizado.

*Critérios de aceite:*
- O certificado deve ser emitido automaticamente quando a última aula do curso for marcada como concluída.
- O certificado deve conter nome do estudante, título do curso, nome do instrutor e data de conclusão.
- O estudante deve poder baixar o certificado em formato PDF a qualquer momento após a emissão.

---

**HU09 — Acessar meus cursos adquiridos**
> Como estudante, quero visualizar todos os cursos que adquiri em uma área centralizada, para retomar facilmente de onde parei.

*Critérios de aceite:*
- A área do estudante deve listar todos os cursos adquiridos com título, capa e percentual de progresso.
- Deve ser possível acessar qualquer aula diretamente a partir da listagem.
- Cursos concluídos devem ser identificados visualmente com destaque distinto.