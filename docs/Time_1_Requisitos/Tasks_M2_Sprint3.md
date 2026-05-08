# ✅ Checklist de Refinamentos – Agente Analista de Requisitos

---

# 🧩 1. Fatiamento (Chunking) + Glossário

## 🔹 1.1 Fatiamento (Chunking)

### ✔️ Refinamentos imediatos (MVP)

* [x] Definir critério simples de chunk:

  * [x] Por parágrafo
  > Cada parágrafo tende a tratar de assunto coeso, fatiar desta forma preserva a organização, embora não garanta que tudo seja reunido no mesmo lugar. O overlap recupera o parágrafo anterior e adiciona ao atual, sendo uma tentativa de não perder o contexto.
  * [ ] Por tamanho de tokens (limite fixo)
* [x] Garantir que cada chunk seja semanticamente minimamente completo
> Não existem mecanismos que verifiquem isso, mas a abordagem por parágrafo tende a garantir, a não ser que o parágrafo do documento esteja incompleto. Existem os casos onde terão pouca informação, como por exemplo no título do documento.
* [ ] Padronizar estrutura do chunk:

  * [x] ID do chunk
  * [x] Texto
  * [ ] Documento origem
  > Para o momento atual, considero que não é ideal salvar o documento de origem, pois não existem chunks de diferentes documentos ao mesmo tempo. Então, em casos onde o documento foi modificado mas possui o mesmo nome, o rastreamento ficaria incoerente.
* [x] Implementar função única e reutilizável de slicing (padronizar uso)
* [x] Garantir leitura sequencial dos chunks pelo agente

### ⚠️ Ajustes importantes identificados

* [x] Evitar perda de contexto entre chunks
> Mecanismo simples, fazendo o uso de overlap de um parágrafo.
* [ ] Validar se chunking é necessário para documentos pequenos
> Não implementado.
* [x] Permitir execução sem chunking (modo direto)

### 🔮 Refinamentos futuros (não prioritários)

* [ ] Estrutura para paralelização por chunk
* [ ] Evolução para RAG mais sofisticado (ex: árvore)
* [ ] Estratégia de recomposição de contexto global

---

## 🔹 1.2 Glossário

### ✔️ Estrutura básica (MVP)

* [x] Definir estrutura do glossário:

  * [x] termo
  * [x] definição
  * [x] referências (chunks)
  * [ ] versão/timestamp
  > A estrutura de glossário possui: termo, definição, referências e status. O status serve para indicar qual definição do termo é a válida, pois podem existir várias definições de um mesmo termo.

### ✔️ Operações essenciais

* [x] Implementar:

  * [x] buscar_termo_glossario
  * [x] adicionar_termo_glossario
  * [x] atualizar_termo_glossario

### ✔️ Estratégia de atualização

* [x] NÃO editar no meio do documento
* [x] Sempre:

  * [x] Criar nova versão do termo no final
  * [x] Marcar versão mais recente como válida
  > Versão anterior é marcada como "Substituído".
* [ ] (Opcional) manter histórico de versões
> As versões do glossário não ficam salvas, apenas mostra os termos antigos com status de substituído.

### ✔️ Comportamento do agente

* [x] Antes de criar termo:

  * [x] Verificar se já existe no glossário
* [x] Se existir:

  * [ ] Ignorar OU
  * [x] Atualizar (preferível)
* [x] Se novo documento:

  * [x] Permitir sobrescrita lógica do termo
  > No momento, não existe distinção entre o glossário de diferentes arquivos, todas as informações ficam no mesmo lugar.

### ⚠️ Simplificações importantes

* [x] NÃO implementar:

  * [x] rastreabilidade complexa
  * [x] encadeamento tipo árvore
  * [x] dependência entre documentos
  > Nenhum dos tópicos foram adicionados.

### 🔧 Refatoração arquitetural

* [x] Transformar glossário em tool (não sub-agent)
> O agente de glossário passou a ser um agentTool para o agente de requirements.
* [ ] Remover dependência entre agentes
> Parcial. O agente de requirements ainda delega ao agente de glossário.

---

# 🧠 2. System Prompts + Few-Shots (+ Skills)

## 🔹 2.1 Estrutura do System Prompt

### ✔️ Refinamentos necessários

* [ ] Separar claramente:

  * [ ] instruções gerais
  * [ ] few-shots
  * [ ] comportamento esperado
* [ ] Garantir que o prompt:

  * [ ] define papel do agente
  * [ ] define formato de saída
  * [ ] define quando gerar dúvidas

### ⚠️ Problemas identificados

* [ ] Reduzir tamanho do prompt (controle de contexto)
* [ ] Evitar múltiplos few-shots simultâneos

---

## 🔹 2.2 Estratégia de Few-Shots

### ✔️ Refinamento central

* [ ] NÃO carregar todos os few-shots ao mesmo tempo
* [ ] Selecionar dinamicamente por tipo de artefato:

  * [ ] histórias de usuário
  * [ ] requisitos funcionais
  * [ ] glossário

### ✔️ Implementação sugerida

* [ ] Criar parâmetro:

  * [ ] tipo_artefato
* [ ] Mapear:

  * [ ] tipo → few-shot

### ✔️ Alternativa simplificada (MVP)

* [ ] Usar template único genérico
* [ ] Evoluir depois para múltiplos

---

## 🔹 2.3 Skills do agente

### ✔️ Refinamentos

* [ ] Definir skills:

  * [ ] identificar requisitos
  * [ ] extrair termos
  * [ ] detectar ambiguidades
  * [ ] gerar artefatos
* [ ] Avaliar:

  * [ ] skills no prompt
  * [ ] ou skills como tools
* [ ] (Opcional) modularizar prompt por skill

---

## 🔹 2.4 Geração de artefatos

### ✔️ Refinamentos

* [ ] Permitir geração sob demanda:

  * [ ] histórias de usuário
  * [ ] requisitos funcionais
* [ ] Evitar geração automática de tudo

### ✔️ Padronização de saída

* [ ] Garantir formato consistente:

  * [ ] título
  * [ ] descrição
  * [ ] critérios de aceitação

---

# ❓ 3. Artefato de Dúvidas (Doubt Artifact)

## 🔹 3.1 Estrutura

* [ ] Definir formato padrão:

  * [ ] dúvida
  * [ ] contexto
  * [ ] impacto
  * [ ] sugestão (opcional)

---

## 🔹 3.2 Classificação

### ✔️ Tipos de dúvida

* [ ] Não bloqueante:

  * [ ] continua execução
  * [ ] registra dúvida
* [ ] Bloqueante:

  * [ ] interrompe execução
  * [ ] solicita resposta

### ✔️ Critérios de bloqueio

* [ ] Idioma inconsistente
* [ ] Ambiguidade crítica
* [ ] Inconsistência lógica grave

---

## 🔹 3.3 Fluxo de execução

### ✔️ Refinamento

* [ ] NÃO interromper fluxo por padrão
* [ ] Permitir:

  * [ ] gerar artefatos + registrar dúvidas

### ✔️ Fluxo alternativo

* [ ] Executa tudo
* [ ] Lista dúvidas ao final
* [ ] Permite reprocessamento

---

## 🔹 3.4 Reuso

* [ ] Criar tool genérica de dúvida
* [ ] Reutilizar entre:

  * [ ] requisitos
  * [ ] glossário
  * [ ] outros agentes

---

# 🔗 4. Integração e Orquestração

## ✔️ Arquitetura

* [ ] Apenas agentes principais como root_agent
* [ ] Subcomponentes → tools

---

## ✔️ Fluxo

* [ ] Orquestrador chama agente analista
* [ ] Agente utiliza:

  * [ ] glossário
  * [ ] slicing
  * [ ] dúvidas

---

## ✔️ Testabilidade

* [ ] Teste isolado de:

  * [ ] agente analista
  * [ ] tools

* [ ] Evitar múltiplos root_agents

---

## ✔️ Persistência

* [ ] Corrigir salvamento fora do container (Docker volume)
* [ ] Garantir acesso aos artefatos

---

## ✔️ Entrada de dados

* [ ] Definir padrão:

  * [ ] upload de arquivo
  * [ ] leitura local

---

# 🚀 Prioridade sugerida

## 🔥 Alta prioridade

* [ ] Glossário como tool
* [ ] Estratégia simples de atualização do glossário
* [ ] Fluxo de dúvidas não bloqueante
* [ ] Padronização do system prompt
* [ ] Persistência de artefatos

## ⚖️ Média prioridade

* [ ] Seleção dinâmica de few-shot
* [ ] Parâmetro tipo_artefato
* [ ] Chunking simplificado

## 💤 Baixa prioridade

* [ ] RAG avançado
* [ ] Versionamento complexo
* [ ] Paralelização por chunk

---

# ✅ Resumo

* [ ] Simplificar arquitetura (menos agentes, mais tools)
* [ ] Evitar complexidade prematura
* [ ] Focar em MVP funcional
