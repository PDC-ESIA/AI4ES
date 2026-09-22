# Documento de Histórias de Usuário e Requisitos — Sistema de Gestão de Ensaios Fotográficos

```markdown
# 1. Histórias de Usuário (HU)

## HU-001: Organização de Sessões Fotográficas (Ensaio)

### Metadados

| Campo   | Valor               |
|---------|---------------------|
| ID      | HU-001              |
| Tipo    | História de Usuário |
| Persona | Fotógrafo Profissional |

### História

> Como **fotógrafo profissional**,
> quero **cadastrar ensaios fotográficos com nome, data e cliente**,
> para que **eu organize o fluxo de trabalho e os materiais de cada sessão**.

### Critérios de Aceitação
- [ ] CA-1: O sistema deve permitir criar um novo ensaio, exigindo nome, data e cliente.
- [ ] CA-2: O sistema deve exibir uma lista de ensaios cadastrados.

---

## HU-002: Upload em Lote de Fotos

### Metadados

| Campo   | Valor               |
|---------|---------------------|
| ID      | HU-002              |
| Tipo    | História de Usuário |
| Persona | Fotógrafo Profissional |

### História

> Como **fotógrafo profissional**,
> quero **fazer upload de múltiplas fotos brutas de uma sessão**,
> para que **eu possa centralizar todas as imagens do ensaio e selecionar após a importação**.

### Critérios de Aceitação
- [ ] CA-1: O sistema deve aceitar upload em lote de arquivos JPEG e PNG.
- [ ] CA-2: O sistema deve permitir upload de 50 ou mais fotos por vez de forma estável.
- [ ] CA-3: Após o upload, as fotos devem aparecer associadas ao ensaio correspondente.

---

## HU-003: Seleção e Montagem de Álbum

### Metadados

| Campo   | Valor               |
|---------|---------------------|
| ID      | HU-003              |
| Tipo    | História de Usuário |
| Persona | Fotógrafo Profissional |

### História

> Como **fotógrafo profissional**,
> quero **marcar fotos selecionadas e montar álbuns organizando sua ordem e título**,
> para que **eu entregue ao cliente um álbum visualmente atrativo, já curado, de cada ensaio**.

### Critérios de Aceitação
- [ ] CA-1: O sistema deve permitir marcar/desmarcar fotos para seleção do álbum.
- [ ] CA-2: O sistema deve permitir reorganizar a ordem das fotos selecionadas.
- [ ] CA-3: É possível definir um título para o álbum.
- [ ] CA-4: O sistema gera uma página final do álbum montado (capa e grid das fotos).

---

# 2. Requisitos Funcionais (RF)

## RF — HU-001 (Organização de Sessões Fotográficas)
- RF-01: Cadastrar ensaio com campos obrigatórios: nome, data e cliente.
- RF-02: Validar preenchimento dos campos obrigatórios antes de salvar.
- RF-03: Listar ensaios cadastrados, exibindo nome, data e cliente.

## RF — HU-002 (Upload em Lote de Fotos)
- RF-04: Permitir seleção e envio simultâneo de múltiplos arquivos (JPEG/PNG).
- RF-05: Vincular automaticamente cada foto enviada ao ensaio de origem.
- RF-06: Exibir progresso/status do upload ao usuário.
- RF-07: Rejeitar arquivos em formatos não suportados, informando o motivo.

## RF — HU-003 (Seleção e Montagem de Álbum)
- RF-08: Permitir marcar/desmarcar fotos individualmente como selecionadas para o álbum.
- RF-09: Permitir reordenar as fotos selecionadas (ex.: arrastar e soltar).
- RF-10: Permitir definir/editar o título do álbum.
- RF-11: Gerar página final do álbum com capa e grid de fotos, refletindo a ordem definida.

## RF — Escopo e Execução (transversal)
- RF-12: Persistir metadados (ensaios, fotos, álbuns) em banco SQLite.
- RF-13: Armazenar os arquivos de imagem em disco local, sem dependência de serviços externos (ex.: S3).
- RF-14: A aplicação deve ser iniciável com um único comando via `uvicorn`, sem etapas manuais adicionais.

---

# 3. Requisitos Não Funcionais (RNF)

## RNF — HU-001 (Organização de Sessões Fotográficas)
- RNF-01: O cadastro de um ensaio deve ser concluído em até 2 segundos.
- RNF-02: Os dados do ensaio devem ser persistidos de forma íntegra e recuperável.

## RNF — HU-002 (Upload em Lote de Fotos)
- RNF-03: O sistema deve suportar upload de lotes de 50+ fotos sem falhas ou perda de arquivos.
- RNF-04: O upload deve continuar em caso de instabilidade momentânea de rede (retry).
- RNF-05: Tempo de resposta da interface durante o upload não deve travar a navegação.

## RNF — HU-003 (Seleção e Montagem de Álbum)
- RNF-06: A reordenação das fotos deve refletir na interface em tempo real.
- RNF-07: A geração da página final do álbum deve preservar a qualidade das imagens.
- RNF-08: O layout gerado deve ser responsivo/legível em diferentes tamanhos de tela.

## RNF — Escopo e Execução (transversal)
- RNF-09: A aplicação é de uso local (single-user), sem autenticação/login nesta versão.
- RNF-10: Fora de escopo nesta versão: compartilhamento por link público, edição de imagem (corte/filtro) e marca d'água.
```
