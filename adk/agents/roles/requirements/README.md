# Requirements Agent (Analista de Requisitos)

Este diretório contém a implementação do **Requirements Agent**, um agente especializado em análise e estruturação de requisitos de software utilizando o Google ADK (Agent Development Kit).

## 📌 Objetivo

O Agente de Requisitos tem como função principal transformar descrições em linguagem natural, documentos de requisitos (PRDs) ou visões de projeto em artefatos técnicos estruturados, atômicos e verificáveis. Ele serve como a ponte inicial entre a visão de negócio e a implementação técnica.

## 📂 Estrutura de Arquivos

- `agent.py`: Definição principal do agente (`requirements_agent`) e do seu sub-agente (`glossario_agent`).
- `prompt.py`: Contém a `instruction` (System Prompt) e a `description` do agente.
- `schemas.py`: Define as estruturas de dados (Pydantic) para a saída do agente (`AnalystOutput`).
- `few_shot.py`: Exemplos de referência para guiar o comportamento do modelo.
- `knowledge/`: Pasta contendo base de conhecimento local, como o `glossario.md` gerado.
- `data/`: Diretório para armazenamento temporário de documentos (`matrix/`) e fatiamento (`chunks/`).

## 🤖 Funcionamento

O agente opera em duas camadas:

1.  **Requirements Agent (Principal):** Coordena a análise global, gera Histórias de Usuário (HUs), Requisitos Funcionais (RFs), Casos de Uso (UCs) e Regras de Negócio (RNs).
2.  **Glossário Agent (Sub-agente):** Focado exclusivamente em ler o documento-matriz, identificar termos técnicos e construir um glossário formal.

### Fluxo de Pensamento (Chain of Thought)

O agente segue obrigatoriamente 6 passos:
1.  **Elicitação:** Identificação de atores e processos.
2.  **Análise Crítica:** Detecção de ambiguidades ou contradições.
3.  **Classificação:** Separação entre RF, HU, RNF e RN.
4.  **Especificação:** Redação atômica dos itens.
5.  **Glossário:** Delegação ao sub-agente para definição de termos.
6.  **Validação:** Garantia de requisitos SMART.

## 🛠 Ferramentas (Tools)

O agente possui acesso a diversas ferramentas utilitárias:

- `run_slicer`: Fragmenta documentos grandes em chunks processáveis.
- `ler_chunk`: Lê partes específicas do contexto fatiado.
- `extract_text`: Extrai o texto integral de documentos na pasta `data/matrix/`.
- `add_to_glossary` / `check_glossary`: Gerenciamento do arquivo de glossário.
- `gerar_doubt_artifact`: Documenta incertezas que impedem a conclusão de um requisito.
- `tool_salvar_artefato_requisito`: Persiste os requisitos gerados em arquivos Markdown.

## 🚀 Como Executar

### Pré-requisitos

1.  Ambiente Python 3.10+ configurado.
2.  Dependências do ADK instaladas (`google-adk`).
3.  Variável de ambiente `ADK_LLM_MODEL` configurada (ex: `github_copilot/gpt-4o`).

### Exemplo de execução via código

```python
from adk.agents.roles.requirements.agent import agent

# Exemplo de entrada: um texto descrevendo um sistema
input_text = "Preciso de um sistema de login que suporte OAuth2 e tenha recuperação de senha via e-mail."

# Executando o agente
response = agent.run(input_text)

print(response.analysis_result)
```

## 🧪 Como Testar

Para testar o agente de forma isolada:

1.  **Teste de Glossário:** Forneça um documento técnico na pasta `data/matrix/` e peça ao agente para "gerar o glossário do documento". Verifique se o arquivo `knowledge/glossario.md` é criado/atualizado.
2.  **Teste de Ambiguidade:** Envie um prompt vago como "Faça um sistema pra mim". O agente deve utilizar a tool `gerar_doubt_artifact` e retornar um status `bloqueado` ou solicitar mais informações.
3.  **Teste de Requisitos:** Envie um PRD completo e valide se o JSON de saída (`AnalystOutput`) contém as HUs e RFs mapeados corretamente com IDs (ex: HU-001, RF-001).

## 📝 Saída Esperada

A saída final é um objeto estruturado seguindo o schema `AnalystOutput`, contendo listas de:
- `user_stories`
- `functional_requirements`
- `non_functional_requirements`
- `use_cases`
- `business_rules`
- `glossary`
- `status` (concluido/bloqueado)
