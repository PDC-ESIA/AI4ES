# Base multistack de testes E2E

Fluxo atual:

```text
QA Agent → action_planner → e2e_test_generator → perfil → Playwright
```

O catálogo registra somente as famílias usadas pelo Coder: Python/FastAPI,
Node/Express (JavaScript e TypeScript), Java/Spring e Go. A stack vem primeiro
de `coder/tasks/_macro_context.json`; manifests do projeto são fallback.

Os quatro perfis usam o mesmo adaptador Playwright TypeScript para gerar specs e
executar Chromium headless. Stack e framework do sistema alvo não alteram a API
do navegador.

Limites do adaptador:

- exige plano validado pelo Action Planner;
- aceita somente ambiente local e host loopback;
- não instala Node, Playwright, browser ou dependências do projeto;
- usa inicializador automático somente quando o runtime local é reconhecido;
- caso contrário, a aplicação alvo deve estar previamente disponível em `base_url`.

Todos os perfis retornam o mesmo envelope com status, resumo, arquivos,
detalhes e bloqueios. O retorno original do Playwright permanece em
`resultado_bruto`. A matriz automatizada está em
`.github/workflows/qa-multilevel-matrix.yml`.
