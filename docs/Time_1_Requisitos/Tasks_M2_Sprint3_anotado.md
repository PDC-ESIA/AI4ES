# Checklist de Refinamentos - Agente Analista de Requisitos (anotado)

> Copia anotada de `Tasks_M2_Sprint3.md`, atualizada em 2026-05-07 a partir da exploracao do projeto.
>
> Legenda: `[x]` atendido; `[ ]` pendente ou parcial. Itens parciais trazem nota explicando o que falta.

---

# 1. Fatiamento (Chunking) + Glossario

## 1.1 Fatiamento (Chunking)

### Refinamentos imediatos (MVP)

* [ ] Definir criterio simples de chunk:
  > Parcial: existe chunk por paragrafo em `adk/shared/tools/slicer_tool.py`, mas nao ha criterio por tokens.

  * [x] Por paragrafo
    > Implementado em `run_slicer()` com divisao por paragrafos e overlap.
  * [ ] Por tamanho de tokens (limite fixo)
    > Nao implementado. O parametro atual e `paragraphs_per_chunk`, nao limite de tokens.

* [ ] Garantir que cada chunk seja semanticamente minimamente completo
  > Parcial. O overlap reduz perda local de contexto, mas nao ha validacao semantica nem testes que comprovem completude.

* [ ] Padronizar estrutura do chunk:
  > Parcial. O chunk e salvo como arquivo `.txt` simples, sem metadados estruturados.

  * [x] ID do chunk
    > Atendido de forma simples via nome sequencial `chunk_000.txt`, `chunk_001.txt`, etc.
  * [x] Texto
    > O texto do chunk e salvo no conteudo do arquivo.
  * [ ] Documento origem
    > Nao atendido. O chunk nao registra o documento original nem metadados de origem.

* [x] Implementar funcao unica e reutilizavel de slicing (padronizar uso)
  > Implementado em `run_slicer()` e exportado por `shared/tools`.

* [x] Garantir leitura sequencial dos chunks pelo agente
  > Implementado por `ler_chunk(index)` com numeracao sequencial.

### Ajustes importantes identificados

* [ ] Evitar perda de contexto entre chunks
  > Parcial. Ha `overlap_count`, mas a estrategia e simples e nao possui teste de cobertura semantica.

* [ ] Validar se chunking e necessario para documentos pequenos
  > Nao implementado. A decisao fica no prompt/agente; nao ha threshold automatico por tamanho.

* [x] Permitir execucao sem chunking (modo direto)
  > Atendido via `extract_text()` e instrucao no prompt para analisar texto direto ou arquivo diretamente.

### Refinamentos futuros (nao prioritarios)

* [ ] Estrutura para paralelizacao por chunk
  > Nao implementado.
* [ ] Evolucao para RAG mais sofisticado (ex: arvore)
  > Nao implementado.
* [ ] Estrategia de recomposicao de contexto global
  > Nao implementado.

---

## 1.2 Glossario

### Estrutura basica (MVP)

* [ ] Definir estrutura do glossario:
  > Parcial. A tabela existe, mas nao possui versao/timestamp/status vigente.

  * [x] termo
    > Atendido em `knowledge/glossario.md` e nas tools de glossario.
  * [x] definicao
    > Atendido em `add_to_glossary()`.
  * [x] referencias (chunks)
    > Atendido de forma simples pelo campo `sources`; nao ha validacao formal dos chunks citados.
  * [ ] versao/timestamp
    > Nao implementado.

### Operacoes essenciais

* [x] Implementar:
  > Operacoes principais existem em `adk/shared/tools/glossary_tool.py`.

  * [x] buscar_termo_glossario
    > Implementado como `check_glossary(term)`.
  * [x] adicionar_termo_glossario
    > Implementado como `add_to_glossary(term, definition, sources)`.
  * [x] atualizar_termo_glossario
    > Implementado dentro de `add_to_glossary()`, mas por sobrescrita da linha existente.

### Estrategia de atualizacao

* [ ] NAO editar no meio do documento
  > Nao atendido. Quando o termo existe, a linha e substituida no proprio local.

* [ ] Sempre:
  > Nao atendido como estrategia completa de versionamento.

  * [ ] Criar nova versao do termo no final
    > Nao implementado; hoje ha sobrescrita.
  * [ ] Marcar versao mais recente como valida
    > Nao implementado; nao existe coluna de status/versao vigente.

* [ ] (Opcional) manter historico de versoes
  > Nao implementado.

### Comportamento do agente

* [x] Antes de criar termo:
  > O prompt do `glossario_agent` instrui verificar duplicidade antes de salvar.

  * [x] Verificar se ja existe no glossario
    > Implementado com `check_glossary()`.

* [x] Se existir:
  > O comportamento atual permite atualizar o termo existente.

  * [ ] Ignorar OU
    > Ignorar nao e o comportamento implementado como padrao.
  * [x] Atualizar (preferivel)
    > Implementado por sobrescrita em `add_to_glossary()`.

* [x] Se novo documento:
  > A sobrescrita logica e possivel, embora sem historico por documento.

  * [x] Permitir sobrescrita logica do termo
    > Implementado por atualizacao da linha do termo.

### Simplificacoes importantes

* [x] NAO implementar:
  > A implementacao se mantem simples, sem rastreabilidade complexa.

  * [x] rastreabilidade complexa
  * [x] encadeamento tipo arvore
  * [x] dependencia entre documentos

### Refatoracao arquitetural

* [ ] Transformar glossario em tool (nao sub-agent)
  > Parcial. Existem tools (`check_glossary`, `add_to_glossary`), mas tambem existe `glossario_agent` como subagente via `AgentTool`.

* [ ] Remover dependencia entre agentes
  > Parcial. O agente de requisitos ainda delega ao `glossario_agent`; a dependencia e controlada, mas ainda existe.

---

# 2. System Prompts + Few-Shots (+ Skills)

## 2.1 Estrutura do System Prompt

### Refinamentos necessarios

* [x] Separar claramente:
  > Atendido em parte pela separacao entre `prompt.py` e `few_shot.py`, e por secoes claras dentro do prompt.

  * [x] instrucoes gerais
  * [x] few-shots
  * [x] comportamento esperado

* [x] Garantir que o prompt:
  > Atendido em `adk/agents/roles/requirements/prompt.py`.

  * [x] define papel do agente
  * [x] define formato de saida
  * [x] define quando gerar duvidas

### Problemas identificados

* [ ] Reduzir tamanho do prompt (controle de contexto)
  > Parcial/pendente. O prompt esta estruturado, mas ainda carrega todos os exemplos no mesmo `instruction`.

* [ ] Evitar multiplos few-shots simultaneos
  > Nao atendido. Todos os few-shots (`HU`, `RF`, `RNF`, `UC`, `RN`, `DOUBT`, `GLOSSARY`) sao interpolados juntos.

---

## 2.2 Estrategia de Few-Shots

### Refinamento central

* [ ] NAO carregar todos os few-shots ao mesmo tempo
  > Nao atendido. O prompt carrega todos os exemplos estaticamente.

* [ ] Selecionar dinamicamente por tipo de artefato:
  > Nao implementado.

  * [ ] historias de usuario
  * [ ] requisitos funcionais
  * [ ] glossario

### Implementacao sugerida

* [ ] Criar parametro:
  > Nao implementado no schema ou nas tools.

  * [ ] tipo_artefato

* [ ] Mapear:
  > Nao implementado.

  * [ ] tipo -> few-shot

### Alternativa simplificada (MVP)

* [x] Usar template unico generico
  > Parcialmente atendido por exemplos fixos usados como referencia geral.

* [ ] Evoluir depois para multiplos
  > Pendente como evolucao.

---

## 2.3 Skills do agente

### Refinamentos

* [x] Definir skills:
  > Atendido no fluxo obrigatorio do prompt e pelas tools registradas.

  * [x] identificar requisitos
  * [x] extrair termos
  * [x] detectar ambiguidades
  * [x] gerar artefatos

* [x] Avaliar:
  > Implementacao hibrida: skills descritas no prompt e funcoes expostas como tools.

  * [x] skills no prompt
  * [x] ou skills como tools

* [ ] (Opcional) modularizar prompt por skill
  > Nao implementado. O prompt ainda e monolitico.

---

## 2.4 Geracao de artefatos

### Refinamentos

* [x] Permitir geracao sob demanda:
  > Atendido pelo prompt e pela tool `tool_salvar_artefato_requisito()`.

  * [x] historias de usuario
  * [x] requisitos funcionais

* [x] Evitar geracao automatica de tudo
  > Atendido no comportamento esperado: o agente classifica e gera conforme entrada/necessidade.

### Padronizacao de saida

* [x] Garantir formato consistente:
  > Atendido pelos schemas Pydantic em `schemas.py` e pelos few-shots.

  * [x] titulo
  * [x] descricao
  * [x] criterios de aceitacao

---

# 3. Artefato de Duvidas (Doubt Artifact)

## 3.1 Estrutura

* [x] Definir formato padrao:
  > Atendido por `gerar_doubt_artifact()` e tambem por `registrar_duvida()`.

  * [x] duvida
  * [x] contexto
  * [x] impacto
  * [x] sugestao (opcional)

---

## 3.2 Classificacao

### Tipos de duvida

* [x] Nao bloqueante:
  > Atendido. `bloqueante` tem default `False`, e o prompt orienta continuar quando possivel.

  * [x] continua execucao
  * [x] registra duvida

* [x] Bloqueante:
  > Atendido no modelo de dados da tool e no prompt quando o contexto inteiro for insuficiente.

  * [x] interrompe execucao
  * [x] solicita resposta

### Criterios de bloqueio

* [ ] Idioma inconsistente
  > Parcial/pendente. Pode ser identificado pelo agente, mas nao ha criterio programatico especifico.
* [x] Ambiguidade critica
  > Atendido no prompt como caso para gerar Doubt Artifact quando impedir especificacao confiavel.
* [ ] Inconsistencia logica grave
  > Parcial/pendente. Pode ser tratada pelo agente, mas nao ha validacao ou regra especifica no codigo.

---

## 3.3 Fluxo de execucao

### Refinamento

* [x] NAO interromper fluxo por padrao
  > Atendido pelo prompt: gerar requisitos seguros e registrar pendencias quando so parte do escopo estiver bloqueada.

* [x] Permitir:
  > Atendido.

  * [x] gerar artefatos + registrar duvidas

### Fluxo alternativo

* [x] Executa tudo
  > Atendido como comportamento esperado quando ha partes seguras do escopo.
* [x] Lista duvidas ao final
  > Parcialmente atendido por `summary`, `doubt_generated` e `listar_duvidas_pendentes()`.
* [x] Permite reprocessamento
  > Atendido parcialmente por `registrar_resposta_humana()`, que permite registrar resposta para duvida pendente.

---

## 3.4 Reuso

* [x] Criar tool generica de duvida
  > Atendido em `shared/tools/doubt_generator_analista.py` e `shared/tools/doubt_handler.py`.

* [ ] Reutilizar entre:
  > Parcial. Confirmado para requisitos e glossario; nao esta integrado em todos os outros agentes.

  * [x] requisitos
  * [x] glossario
  * [ ] outros agentes
    > Pendente. Outros roles nao usam a tool de duvida de forma consistente.

---

# 4. Integracao e Orquestracao

## Arquitetura

* [ ] Apenas agentes principais como root_agent
  > Parcial. `app/main.py` usa `runners` como default, mas alguns roles ainda declaram `root_agent` quando `ADK_AGENTS_DIR=agents/roles` for usado em desenvolvimento.

* [ ] Subcomponentes -> tools
  > Parcial. Varias capacidades sao tools, mas o glossario ainda e um subagente (`glossario_agent`) acoplado via `AgentTool`.

---

## Fluxo

* [x] Orquestrador chama agente analista
  > Atendido no workflow sequencial `sdlc_pipeline`, que inicia por `requirements_agent`.

* [x] Agente utiliza:
  > Atendido para o agente de requisitos.

  * [x] glossario
  * [x] slicing
  * [x] duvidas

---

## Testabilidade

* [ ] Teste isolado de:
  > Parcial. Ha testes de tools, mas nao ha teste isolado completo do agente analista.

  * [ ] agente analista
    > Pendente.
  * [x] tools
    > Atendido para filesystem, artifacts/doubt e git; faltam testes para slicer e glossario.

* [ ] Evitar multiplos root_agents
  > Parcial. O default de runtime evita exposicao ampla usando `runners`, mas ainda existem `root_agent` em alguns roles.

---

## Persistencia

* [ ] Corrigir salvamento fora do container (Docker volume)
  > Parcial. Artefatos em `docs/Time_1_Requisitos` persistem via volume `../docs:/app/docs:rw`, mas `ADK_AGENT_DATA_DIR=agents/roles/requirements` aponta para chunks/glossario dentro da arvore do app; no compose principal `.:/app:ro` pode bloquear escrita nesses caminhos.

* [x] Garantir acesso aos artefatos
  > Atendido para Markdown gerado em `docs` e para a aba Artifacts do ADK Web via `tool_context.save_artifact()`.

---

## Entrada de dados

* [ ] Definir padrao:
  > Parcial. Ha leitura local, mas nao foi encontrado endpoint proprio de upload.

  * [ ] upload de arquivo
    > Nao implementado no app FastAPI proprio.
  * [x] leitura local
    > Atendido por `extract_text()` para `.md`, `.txt`, `.pdf` e diretorios.

---

# Prioridade sugerida

## Alta prioridade

* [ ] Glossario como tool
  > Parcial. As funcoes existem como tools, mas ainda ha `glossario_agent` como subagente.
* [ ] Estrategia simples de atualizacao do glossario
  > Parcial. Atualiza por sobrescrita; falta versionamento por append com timestamp/status valido.
* [x] Fluxo de duvidas nao bloqueante
  > Atendido.
* [x] Padronizacao do system prompt
  > Atendido em boa parte.
* [ ] Persistencia de artefatos
  > Parcial. Artefatos de requisitos/doubt estao cobertos; chunks/glossario no container ainda exigem ajuste.

## Media prioridade

* [ ] Selecao dinamica de few-shot
  > Nao implementado.
* [ ] Parametro tipo_artefato
  > Nao implementado.
* [x] Chunking simplificado
  > Atendido por paragrafo com overlap.

## Baixa prioridade

* [ ] RAG avancado
  > Nao implementado.
* [ ] Versionamento complexo
  > Nao implementado; o versionamento simples do glossario tambem ainda falta.
* [ ] Paralelizacao por chunk
  > Nao implementado.

---

# Resumo

* [ ] Simplificar arquitetura (menos agentes, mais tools)
  > Parcial. O projeto ja usa varias tools, mas ainda mantem `glossario_agent` e multiplos `root_agent` em roles.
* [x] Evitar complexidade prematura
  > Atendido em boa parte. A implementacao usa solucoes simples para chunking, glossario e duvidas.
* [x] Focar em MVP funcional
  > Atendido. O fluxo principal de requisitos, duvidas e artefatos esta funcional, com pendencias de refinamento.