# Base multistack de testes de integração

Fluxo atual:

```text
QA Agent → action_planner → integration_tests_agent → perfil → geração → execução
```

O catálogo registra somente as famílias usadas pelo Coder: Python/FastAPI,
Node/Express (JavaScript e TypeScript), Java/Spring e Go. A stack vem primeiro
de `coder/tasks/_macro_context.json`; manifests do projeto são fallback.

Adaptadores ativos:

- Python/FastAPI: pytest;
- Node/Express JavaScript ou TypeScript: Vitest, Jest, Mocha ou `node:test`,
  conforme o manifesto do projeto;
- Java/Spring: JUnit por Maven ou Gradle;
- Go: pacote `testing` com `go test`.

Os comandos são fixados pelo adaptador, executados sem shell e nunca instalam
dependências. Todas as stacks retornam o mesmo envelope com status, resumo,
arquivos, detalhes e bloqueios. `stdout`, `stderr`, comando e código de saída
continuam preservados em `resultado_bruto`.

O `pytest_runner` unitário permanece inalterado e não é usado como fallback.
