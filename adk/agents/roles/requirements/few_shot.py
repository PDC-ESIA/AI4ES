"""
Este arquivo contém exemplos de Few-Shot baseados no sistema TACO-IDE para calibrar
o comportamento do Agente Analista de Requisitos Crítico.
"""

FEW_SHOT_HU = """
### EXEMPLO DE HISTÓRIA DE USUÁRIO (PADRÃO TIME 1 - TACO-IDE)

**CONTEXTO DE ENTRADA:**
"O professor precisa criar um exercício novo para os alunos resolverem, colocando o enunciado e como vai testar se o código está certo."

**PROCESSO ANALÍTICO (CHAIN OF THOUGHT):**
1. Identificado Ator: Professor.
2. Identificada Ação: Criar exercício.
3. Identificados Componentes: Enunciado e Casos de Teste.
4. Mapeamento de Metadados: Status 'Rascunho', Origem 'Contexto Estruturado'.

**SAÍDA ESPERADA (HISTÓRIA DE USUÁRIO):**
{
 # HU-001 — Criação de Exercícios de Programação

## Metadados
| Campo         | Valor                        |
|---------------|------------------------------|
| ID            | HU-001       |
| Data geração  | 2026-04-10                  |
| Origem        |  Chunk 02|
| Versão        | 1.0 |
| Status        | Rascunho |
| Prioridade    | Alta   |

## História

> Como PROFESSOR,
> quero CRIAR UM EXERCÍCIO DE PROGRAMAÇÃO,
> para que OS ALUNOS POSSAM PRATICAR E APRENDER CONCEITOS DE PROGRAMAÇÃO DE FORMA PRÁTICA.

## Critérios de Aceitação

<!-- INSTRUÇÃO: crie um item CA-N para cada critério verificável identificado no contexto. Não há limite de quantidade. -->
- [ ] CA-1: O sistema deve permitir a inserção de um enunciado em formato Markdown.
- [ ] CA-2: O sistema deve permitir a configuração de múltiplos casos de teste (entrada e saída esperada).
- [ ] CA-3: O sistema deve validar se todos os campos obrigatórios foram preenchidos antes de salvar.

---
}
"""

FEW_SHOT_RF = """
### EXEMPLO DE REQUISITO FUNCIONAL (PADRÃO TIME 1 - TACO-IDE)

**CONTEXTO DE ENTRADA:**
"O sistema tem que rodar o código do aluno num lugar seguro pra não quebrar o servidor."

**SAÍDA ESPERADA (REQUISITOS FUNCIONAIS):**
{
# Requisitos Funcionais

<!-- INSTRUÇÃO: crie uma linha por requisito funcional identificado no contexto. Não há limite de quantidade. -->
| ID       | Descrição                          | Prioridade    | Relacionado a     |
|----------|------------------------------------|---------------|-------------------|
| RF-001   | O sistema deve executar o código submetido pelo aluno em ambiente isolado (sandbox/container) sem acesso direto ao servidor host. | Alta | UC-001 |
| RF-002   | O sistema deve aplicar limites de tempo e memória na execução do código do aluno. | Alta | UC-001 |
| RF-003   | O sistema deve registrar e retornar ao aluno o resultado da execução (sucesso, erro de compilação, erro em tempo de execução ou timeout). | Média | UC-001 |

---
}
"""

FEW_SHOT_RNF = """
### EXEMPLO DE REQUISITO NÃO FUNCIONAL (PADRÃO TIME 1 - TACO-IDE)

**CONTEXTO DE ENTRADA:**
"O sistema tem que rodar o código do aluno num lugar seguro pra não quebrar o servidor."

**SAÍDA ESPERADA (REQUISITOS NÃO FUNCIONAIS):**
{
# Requisitos Não Funcionais

<!-- INSTRUÇÃO: crie uma linha por requisito não funcional identificado. Use as categorias: Desempenho, Segurança, Disponibilidade, Usabilidade, Manutenibilidade, Escalabilidade. Adicione outras se necessário. -->
| ID        | Categoria       | Descrição                  | Métrica / Critério          |
|-----------|-----------------|----------------------------|-----------------------------|
| RNF-001   | Segurança       | O ambiente de execução deve isolar processos, sistema de arquivos e rede para impedir impacto no servidor principal. | 100% das execuções em sandbox com usuário sem privilégio e sem acesso ao host. |
| RNF-002   | Desempenho      | A validação da submissão deve concluir em tempo adequado para feedback pedagógico. | 95% das execuções finalizadas em até 5 segundos (excluindo timeout configurado). |
| RNF-003   | Disponibilidade | O serviço de execução de código deve permanecer disponível para uso contínuo em períodos letivos. | Uptime mensal >= 99,5%. |

---
}
"""
FEW_SHOT_UC = """
### EXEMPLO DE CASO DE USO (PADRÃO TIME 1 - TACO-IDE)

**CONTEXTO DE ENTRADA:**
"Quando o aluno submete o código, o sistema deve rodar ele num ambiente isolado."

**SAÍDA ESPERADA (CASO DE USO):**
# UC-001 - Submeter Codigo para Execucao Segura

## Metadados
| Campo         | Valor                        |
|---------------|------------------------------|
| ID            | UC-001                       |
| Data geração  | 2026-05-06                   |
| Ator principal| Aluno                        |
| HUs relacionadas | HU-002                    |
| Status        | Rascunho                     |

## Descrição Breve

Este caso de uso descreve a submissao de codigo por um aluno para avaliacao automatica.
O sistema executa o codigo em ambiente isolado e devolve o resultado com seguranca.

## Atores

- **Primário:** Aluno
- **Secundário:** Servico de Execucao Isolada (Sandbox)

## Pré-condições
<!-- INSTRUÇÃO: liste todas as condições necessárias antes do início. Sem limite de quantidade. -->
- O aluno deve estar autenticado no sistema.
- A atividade deve estar aberta para submissao.
- O servico de execucao isolada deve estar operacional.

## Fluxo Principal

<!-- INSTRUÇÃO: descreva todos os passos do fluxo principal em ordem. Não há limite de quantidade — use quantos passos forem necessários para descrever o fluxo completo. -->
1. O aluno seleciona a atividade e envia o codigo fonte.
2. O sistema valida formato e tamanho da submissao.
3. O sistema encaminha o codigo para o ambiente isolado.
4. O ambiente isolado compila e executa o codigo com limites definidos.
5. O sistema coleta logs e status da execucao.
6. Sistema retorna resultado da submissao ao aluno.

## Fluxos Alternativos

<!-- INSTRUÇÃO: crie uma seção FA-N para cada desvio do fluxo principal identificado no contexto. Não há limite de quantidade. Se não houver, escreva "Nenhum identificado." -->
### FA-1: Erro de compilacao
- **Condição:** O codigo submetido nao compila.
- **Passos:**
  1. O ambiente isolado identifica erro de compilacao.
  2. O sistema retorna ao aluno a mensagem de erro e encerra a execucao.

### FA-2: Timeout de execucao
- **Condição:** O codigo excede o tempo maximo permitido.
- **Passos:**
  1. O ambiente isolado interrompe o processo ao atingir o limite de tempo.
  2. O sistema registra timeout e informa o aluno.

## Fluxos de Exceção

<!-- INSTRUÇÃO: crie uma seção FE-N para cada situação de erro ou falha identificada. Não há limite de quantidade. Se não houver, escreva "Nenhum identificado." -->
### FE-1: Falha no servico de sandbox
- **Condição:** O servico de execucao isolada esta indisponivel.
- **Tratamento:** O sistema nao executa o codigo, registra incidente e retorna mensagem de indisponibilidade temporaria.

## Pós-condições
<!-- INSTRUÇÃO: liste todos os estados possíveis do sistema após execução. Sem limite de quantidade. -->
- A submissao fica registrada com status final (sucesso, erro, timeout ou falha tecnica).
- O aluno visualiza o feedback da execucao.

---
}
"""
FEW_SHOT_RN = """
### EXEMPLO DE REGRA DE NEGÓCIO (PADRÃO TIME 1 - TACO-IDE)

**CONTEXTO DE ENTRADA:**
"A inteligência artificial do sistema deve ajudar o aluno quando ele estiver travado."

**SAÍDA ESPERADA (REGRA DE NEGÓCIO):**
{
# Regras de Negócio

| ID     | Regra | Descrição | Violação / Consequência |
|--------|-------|-----------|--------------------------|
| RN-001 | Nível de Ajuda Progressiva | A IA deve fornecer ajuda em etapas progressivas (dica conceitual -> sugestao de estrategia -> exemplo parcial), sem entregar a solucao completa na primeira interacao. | Se a resposta completa for fornecida de imediato, registrar violacao pedagogica e bloquear a resposta final. |
| RN-002 | Bloqueio de Resposta Pronta | A IA nao deve gerar codigo completo quando identificar tentativa de obter "resposta pronta" para atividade avaliativa ativa. | O sistema deve recusar a geracao completa e orientar o aluno com perguntas guiadas. |
| RN-003 | Rastreabilidade de Interacoes | Toda interacao de ajuda da IA deve ser registrada com timestamp, nivel de ajuda e usuario associado para auditoria didatica. | Interacoes sem registro sao invalidas para monitoramento e devem gerar alerta operacional. |

---
}
"""

FEW_SHOT_DOUBT = """
### EXEMPLO DE DÚVIDA CRÍTICA (AMBIGUIDADE NO TACO)

**CONTEXTO DE ENTRADA:**
"A inteligência artificial do sistema deve ajudar o aluno quando ele estiver travado."

**PROCESSO ANALÍTICO:**
1. O termo "ajudar" é vago.
2. A ajuda pode ser: explicar o erro, dar a resposta pronta, dar uma dica progressiva ou sugerir documentação.
3. Decisão: Bloquear a especificação dessa funcionalidade e questionar a regra pedagógica.

**SAÍDA ESPERADA (DOUBT ARTEFACT):**
{
  "id_duvida": "D-002",
  "trecho": "IA deve ajudar o aluno",
  "duvida": "O termo 'ajudar' não define o nível de interferência pedagógica da IA.",
  "impacto": "Risco de a IA fornecer a resposta completa, invalidando o aprendizado (plágio/cola).",
  "sugestao": "Definir se a IA deve atuar como um tutor Socrático (apenas dicas) ou como um assistente de correção (aponta o erro exato)."
}
"""

FEW_SHOT_GLOSSARY = """
### EXEMPLO DE TERMO TÉCNICO (GLOSSÁRIO TACO)

**CONTEXTO DE ENTRADA:**
"O aluno faz a submissão e a IA usa um LLM para analisar o código."

**SAÍDA ESPERADA (GLOSSÁRIO):**
{
  "term": "LLM",
  "definition": "Large Language Model. Modelo de inteligência artificial treinado em vastas quantidades de texto, capaz de compreender e gerar linguagem humana ou código de programação.",
  "source": "Documento de Especificação de Requisitos - Seção 1.3"
}
"""
