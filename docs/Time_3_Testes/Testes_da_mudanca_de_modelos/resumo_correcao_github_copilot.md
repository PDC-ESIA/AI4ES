# Resumo da correcao

Data de referencia: 2026-06-01  
Commit relacionado: `63b9cce` ("correcao para sistema ficar agnostico")

## 1) Problema observado:

O modelo configurado como padrao (`github_copilot/gpt-4`) nao estava sendo identificado pelo ADK em alguns fluxos.  

### 1.1) Causa raiz

Mesmo com LiteLLM instalado, o registro de modelos do ADK nao cobria automaticamente os padroes `github_copilot/*` (e `github/*`) no runtime atual.

Em outras palavras:

- havia provedor LiteLLM disponivel;
- mas faltava registrar explicitamente os padroes de nome de modelo no `LLMRegistry`;
- por isso a resolucao de `github_copilot/...` falhava.

### 1.2) Mudancas feitas em `adk/app/main.py`

Foi adicionada a importacao de `LiteLlm` e `LLMRegistry` e feito o registro explicito dos padroes:

- `LLMRegistry._register(r"github_copilot/.*", LiteLlm)`
- `LLMRegistry._register(r"github/.*", LiteLlm)`

Efeito da mudanca: garante que modelos com prefixo `github_copilot/` (e `github/`) sejam roteados para o backend LiteLLM ja na inicializacao da aplicacao.

## 2) Mudancas feitas em `adk/.env.example`

Foram adicionadas orientacoes para uso com outros provedores/modelos e variaveis de ambiente para Vertex AI/Google:

- comentario para uso opcional de `gemini-2.5-flash` e `GOOGLE_API_KEY`;
- `GOOGLE_CLOUD_PROJECT`;
- `GOOGLE_CLOUD_LOCATION`;
- `GOOGLE_GENAI_USE_VERTEXAI=false`

Efeito da mudanca: o projeto fica mais agnostico de provedor e com configuracao explicita para cenarios Google/Vertex sem quebrar o fluxo com Copilot.

## 3) Adição de arquivos de teste dos modelos

Pasta: `docs/Time_3_Testes/Testes_da_mudanca_de_modelos`

Foram gerados/registrados testes em JSON para comparar comportamento entre modelos:

- `github_copilot_gpt-4/Teste_ola/Teste_ola_github_copilot_gpt-4.json`
- `github_copilot_gpt-4/Teste_calculadora/Teste_calculadora_github_copilot_gpt-4.json`
- `gemini-2.5-flash/Teste_ola/Teste_ola_gemini-2.5-flash.json`
- `gemini-2.5-flash/Teste_calculadora/Teste_calculadora_python_gemini-2.5-flash.json`

Resumo do que os testes mostram:

- cenarios `Teste_ola`: validam respostas iniciais e comportamento de onboarding dos pipelines;
- cenarios `Teste_calculadora`: registram execucoes com prompt de calculadora, artefatos gerados e diferencas de fluxo;


## 4) Resultado esperado apos a correcao

Com o registro explicito no `LLMRegistry`, o runtime passa a reconhecer e executar corretamente modelos `github_copilot/*`, evitando a falha de resolucao observada antes.

## 5) Outros modelos:

Para testar como outros modelos também foram feitas tentativas com o mistral e groq (llm's open-source), a mistral funcionou corretamente porém o groq teve problemas com chamadas de ferramentas (possível incapacidade própria nativa, tendo em vista que também já testei em outros sistemas e não obtive sucesso)
