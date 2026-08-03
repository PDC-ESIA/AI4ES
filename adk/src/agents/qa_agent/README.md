# QA Agent

## 1. O que é o Agente (Visão Geral)

### Identificação
**Nome:** QA Agent (Time 3 — PDC-AI4SE)  
**Domínio:** Engenharia de Requisitos e Testes de Software  

### Propósito
O **QA Agent** resolve o problema de criar suítes de testes baseadas em especificações funcionais. Ele transforma requisitos (RF, HU, UC, RNF, RN) e o código-fonte correspondente em testes automatizados completos. Seu propósito no ciclo de Engenharia de Software (ES) é garantir que o código desenvolvido atenda exatamente aos critérios de aceitação estipulados, reduzindo o esforço manual da equipe de QA e garantindo padronização e cobertura.

### Stacks, Tecnologias, Frameworks utilizados
- **Linguagem:** Python 3.14+
- **Gerenciamento de Pacotes:** `uv`
- **Frameworks de Agente:** Google ADK Framework (LlmAgent, LiteLlm)
- **Testes:** `pytest`
- **Servidor Web / Interface:** `uvicorn`, Dev UI (ADK)

---

## 2. Funcionalidades

O QA Agent possui responsabilidades bem definidas focadas na automação de testes de qualidade:

- **Análise de Requisitos e Código:** Interpreta vários tipos de artefatos de requisitos (HU, RF, UC, RNF, RN), regras de negócio e código-fonte, mapeando os critérios de aceitação para testes.
- **Geração Automática de Testes:** Cria de forma autônoma scripts de testes utilizando `pytest`, abrangendo testes unitários e casos de testes.
- **Planejamento, geração e execução E2E:** O subagente `action_planner` é chamado diretamente como primeiro passo, escolhe a estratégia, autoriza o fluxo e produz o handoff. Depois, e somente quando selecionado no plano, `e2e_test_generator` materializa cenários, gera um arquivo `.spec.ts` e pode executá-lo localmente em Chromium headless.
- **Execução e Validação:** Executa os testes gerados diretamente contra o ambiente local através da ferramenta `pytest_runner`.
- **Autocorreção (Code Fix):** Através de seus subagentes (`action_planner`, `code_fix_agent`), ele planeja ações e tenta corrigir os códigos de teste gerados caso haja falhas na execução.
- **Limites de Atuação:** O agente não implementa funcionalidades no código-fonte principal; sua atuação é estritamente limitada à criação, correção e execução do código de **testes**.

---

## 3. Como executar ou testar o Agente

### Pré-requisitos
- Python 3.14+
- Ferramenta `uv` instalada.
- Chaves de API necessárias para o modelo LLM (`ADK_LLM_MODEL`) configuradas no arquivo `.env`.

### Instalação
Na raiz do projeto (`adk/`), execute os seguintes comandos para criar e ativar o ambiente:

```bash
uv sync
cp .env.example .env
```

Opcionalmente, ative o ambiente virtual:

```bash
source .venv/bin/activate
```

No Windows PowerShell:

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\Activate.ps1
```

**⚠️ IMPORTANTE:** No arquivo `.env`, utilize o diretório de agentes atual:
```env
ADK_AGENTS_DIR=src/agents
```

### Comando de Execução
Para rodar o ambiente de desenvolvimento e acessar a interface do agente:

```bash
uvicorn app.main:app --reload --port 8081
```

Acesse pelo navegador: [http://127.0.0.1:8081/dev-ui/?app=qa_agent](http://127.0.0.1:8081/dev-ui/?app=qa_agent)

### Suíte de Testes
Para validação ponta a ponta, siga o cenário recomendado no passo 5 (cenário do fotógrafo no `adk/README.md`).

Para validação focada no comportamento conversacional do QA Agent e do `code_fix_agent`, utilize também os casos em `adk/src/agents/qa_agent/TESTES.md`.

A validação é considerada bem-sucedida quando o agente gera os testes, executa o `pytest` e retorna resultados coerentes sem intervenção manual.

---

## 4. Possíveis Entradas e Saídas

**Entradas:**
- Arquivos de requisitos, como HU, RF, UC, RNF, RN, em Markdown (`.md`) ou formato equivalente.
- Arquivos de código-fonte em Python (`.py`) correspondentes à funcionalidade a ser testada OU não para gerar casos de teste.
- Prompt de instruções especificando quais níveis de teste e coberturas são desejadas.
- Solicitação explícita de plano E2E, acompanhada quando possível de URL, rotas/telas, perfis, dados, contratos API e passos de automação estruturados.

**Saídas:**
- Arquivo de testes gerado automaticamente (ex: `test_autenticacao_auto.py`).
- Logs de execução do `pytest` exibindo se os testes passaram ou falharam (relatório de cobertura).
- Artefatos de dúvida (`DoubtArtifact`) caso o agente identifique falta de contexto ou ausência de arquivos anexados.
- Plano E2E estruturado com cenários, nível de confiança e bloqueios; quando o contrato web estiver completo, arquivo Playwright `.spec.ts` no workspace.

---

## 5. Cenário de Teste Específico

### Cenário recomendado (fotógrafo)

Para validação ponta a ponta do fluxo completo com o ecossistema de agentes, o cenário recomendado é o **cenário do fotógrafo** descrito no README principal do ADK.

- Arquivo de referência: `adk/README.md`
- Seção: **Exemplo end-to-end: site de fotógrafo via Dev UI**
- Prompt: **Colar o prompt do fotógrafo**

Esse é o cenário de referência do projeto para execução guiada no Dev UI e inclui critérios de aceite e passos reproduzíveis.

---

## 6. Lista de Erros Identificados

| Problema / Erro | Causa Comum | Como Resolver |
| --- | --- | --- |
| **Erro de módulo / agente não aparece na Dev UI** | A variável de ambiente foi configurada com caminho antigo. | Confirme que `ADK_AGENTS_DIR=src/agents` está no `.env` (ou remova a variável para usar o padrão do `app/main.py`) e reinicie o servidor. |
| **Agente responde com "Doubt Artifact" e "conteúdo vazio"** | O agente não tem acesso local de leitura direta ao texto. | Isso indica que os arquivos não foram anexados. Anexe explicitamente os arquivos através da Dev UI (botão de upload local file). |
| **Testes gerados falham por importação incorreta (ModuleNotFoundError)** | O agente gerou caminhos relativos incompatíveis ou faltam arquivos `__init__.py` na estrutura de pacotes. | Confirme que o código gerado faz importações coerentes com o arquivo anexado. Assegure-se de que as pastas locais de teste possuem os arquivos `__init__.py` para que o Python reconheça como pacote. |
| **Lentidão na Resposta** | O uso dos subagentes gera encadeamento demorado de chamadas de LLM. | É esperado. A arquitetura de múltiplos agentes (recepção, planejamento, correção e pytest) pode levar alguns minutos para finalizar. |
| **Agente gerou um código de teste esqueleto (vazio ou comentado)** | Falha na propagação do contexto dos arquivos ou limite de tokens da janela de contexto atingido. | Certifique-se de anexar novamente os arquivos. Se os arquivos forem muito longos, tente reduzir ou dividi-los. Se o problema persistir, pode ser um erro de propagação de contexto no subagente `receive_requirements`. |
| **Pytest falha dizendo "arquivo de teste não encontrado"** | O agente gerou o conteúdo do código em texto, mas não escreveu o arquivo `.py` fisicamente no diretório antes de chamar o `pytest_runner`. | Peça ao agente explicitamente no prompt: "Certifique-se de salvar o código no arquivo antes de rodar os testes" ou envie o diretório para o agente.|
| **Erro de Timeout ou Limite de Taxa (Rate Limit)** | O excesso de subagentes comunicando-se simultaneamente (Code Fix + Action Planner) estourou o limite de quota da API do modelo configurado. | Aguarde alguns minutos antes de enviar a mensagem novamente ou altere a variável de ambiente `ADK_LLM_MODEL` para um modelo com cota maior. |
