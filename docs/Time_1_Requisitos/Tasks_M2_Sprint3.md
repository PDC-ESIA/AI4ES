# ✅ Checklist de Refinamentos – Agente Analista de Requisitos

---

# 🧩 1. Fatiamento (Chunking) + Glossário

## 🔹 1.1 Fatiamento (Chunking)

### ✔️ Refinamentos imediatos (MVP)

* [ ] Definir critério simples de chunk:

  * [ ] Por parágrafo
  * [ ] Por tamanho de tokens (limite fixo)
* [ ] Garantir que cada chunk seja semanticamente minimamente completo
* [ ] Padronizar estrutura do chunk:

  * [ ] ID do chunk
  * [ ] Texto
  * [ ] Documento origem
* [ ] Implementar função única e reutilizável de slicing (padronizar uso)
* [ ] Garantir leitura sequencial dos chunks pelo agente

### ⚠️ Ajustes importantes identificados

* [ ] Evitar perda de contexto entre chunks
* [ ] Validar se chunking é necessário para documentos pequenos
* [ ] Permitir execução sem chunking (modo direto)

### 🔮 Refinamentos futuros (não prioritários)

* [ ] Estrutura para paralelização por chunk
* [ ] Evolução para RAG mais sofisticado (ex: árvore)
* [ ] Estratégia de recomposição de contexto global

---

## 🔹 1.2 Glossário

### ✔️ Estrutura básica (MVP)

* [ ] Definir estrutura do glossário:

  * [ ] termo
  * [ ] definição
  * [ ] referências (chunks)
  * [ ] versão/timestamp

### ✔️ Operações essenciais

* [ ] Implementar:

  * [ ] buscar_termo_glossario
  * [ ] adicionar_termo_glossario
  * [ ] atualizar_termo_glossario

### ✔️ Estratégia de atualização

* [ ] NÃO editar no meio do documento
* [ ] Sempre:

  * [ ] Criar nova versão do termo no final
  * [ ] Marcar versão mais recente como válida
* [ ] (Opcional) manter histórico de versões

### ✔️ Comportamento do agente

* [ ] Antes de criar termo:

  * [ ] Verificar se já existe no glossário
* [ ] Se existir:

  * [ ] Ignorar OU
  * [ ] Atualizar (preferível)
* [ ] Se novo documento:

  * [ ] Permitir sobrescrita lógica do termo

### ⚠️ Simplificações importantes

* [ ] NÃO implementar:

  * [ ] rastreabilidade complexa
  * [ ] encadeamento tipo árvore
  * [ ] dependência entre documentos

### 🔧 Refatoração arquitetural

* [ ] Transformar glossário em tool (não sub-agent)
* [ ] Remover dependência entre agentes

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
