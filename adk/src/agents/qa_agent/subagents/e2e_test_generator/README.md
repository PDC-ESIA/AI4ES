# E2E Test Generator — geração Playwright

Este pacote implementa o executor E2E do QA Agent. O `action_planner` cria e
valida primeiro o plano operacional; somente depois este subagente recebe o
handoff, materializa os cenários e, quando o contrato de uma jornada web está
completo, grava e pode executar um arquivo Playwright `.spec.ts`.

Fluxo obrigatório:

```text
QA Agent → action_planner → e2e_test_generator
```

O JSON integral retornado pelo planner deve ser repassado como `plano_acao`.
Sem ele, ou quando o plano não selecionar/autorizar o E2E, a geração é
bloqueada antes de qualquer processamento ou escrita.

## O que ele faz

- normaliza requisitos em texto ou JSON;
- identifica conservadoramente superfícies `web`, `api` ou `fullstack`;
- mapeia fluxo feliz, falha externa, timeout e dados malformados;
- separa bloqueios de plano, geração de código e execução;
- gera TypeScript apenas a partir de ações e localizadores permitidos;
- grava o spec em `workspace_output/tests/e2e` por padrão;
- executa somente o spec recém-gerado em Chromium headless;
- consolida status, contagens, falhas, logs e artefatos do Playwright;
- mantém o fluxo pytest existente do QA Agent separado.

## Limites atuais

- a geração de código atende somente jornadas `web`;
- não aceita CSS, XPath nem código arbitrário como localizador;
- não instala dependências durante uma chamada do agente;
- não aceita shell, argumentos arbitrários, browser remoto ou ambiente externo;
- não calcula cobertura de código;
- não corrige código nem gera Doubt Artifacts.

API e fullstack ainda recebem um plano e bloqueios explícitos. CLI e sistemas
agênticos permanecem fora do escopo do gerador Playwright.

## Contrato para geração

Cada item de `rotas_ou_telas` deve conter `rota` e `passos_automacao`. As ações
aceitas são `preencher`, `clicar`, `marcar`, `desmarcar`, `selecionar`,
`pressionar`, `verificar_visivel`, `verificar_texto` e `verificar_url`.

Os localizadores aceitos são `role`, `label`, `text`, `test_id` e
`placeholder`. Valores podem ser declarados diretamente ou referenciados por
`chave_dado` em `dados_teste`. É necessário ao menos um passo de verificação.

## Runtime e execução

Instale o runtime uma vez na pasta `adk/`:

```powershell
npm install
npx playwright install chromium
```

O executável `node` deve estar no `PATH`. Como alternativa, configure
`PLAYWRIGHT_NODE_EXECUTABLE` no `.env` com o caminho absoluto de `node.exe`.

A execução é solicitada com:

```json
{
  "ambiente_execucao": {
    "tipo": "local",
    "browser": "chromium",
    "timeout_segundos": 120,
    "timeout_teste_ms": 30000
  },
  "comando_execucao": "npx playwright test"
}
```

`comando_execucao` é um perfil, não um comando de shell: o executor usa uma
lista fixa de argumentos, `shell=False`, Chromium headless e relatório JSON.

Exemplo:

```python
import json

from src.agents.qa_agent.subagents.e2e_test_generator import gerar_testes_e2e

resultado = gerar_testes_e2e(
    requisitos="Ao enviar o contato, exibir Mensagem enviada.",
    plano_acao=plano_json_retornado_pelo_action_planner,
    tipo_sistema="web",
    base_url="http://localhost:8000",
    rotas_ou_telas=json.dumps(
        [
            {
                "nome": "Contato",
                "rota": "/contato",
                "passos_automacao": [
                    {
                        "acao": "preencher",
                        "localizador": {"tipo": "label", "valor": "Nome"},
                        "chave_dado": "nome",
                    },
                    {
                        "acao": "clicar",
                        "localizador": {
                            "tipo": "role",
                            "valor": "button",
                            "nome_acessivel": "Enviar",
                        },
                    },
                    {
                        "acao": "verificar_visivel",
                        "localizador": {
                            "tipo": "text",
                            "valor": "Mensagem enviada",
                        },
                    },
                ],
            }
        ],
        ensure_ascii=False,
    ),
    dados_teste=json.dumps({"nome": "Ana"}, ensure_ascii=False),
    ambiente_execucao=json.dumps(
        {"tipo": "local", "browser": "chromium", "timeout_segundos": 120}
    ),
    comando_execucao="npx playwright test",
)
```

Nesse caso, o retorno usa `tipo_saida="executado"`, informa o caminho em
`arquivos_gerados` e preenche `resultado_execucao`. Se faltarem os passos
estruturados, o retorno continua sendo `plano_e2e`; se faltar apenas o runtime,
o spec permanece gerado e um bloqueio de infraestrutura explica o que instalar.
A chamada direta pressupõe que
`plano_json_retornado_pelo_action_planner` contenha o JSON integral validado.

## Dev UI

Na pasta `adk/`, execute:

```powershell
uvicorn app.main:app --reload --port 8081
```

Depois abra
`http://127.0.0.1:8081/dev-ui/?app=qa_agent`.
