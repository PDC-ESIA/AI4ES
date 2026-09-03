# Teste de integração multistack na Dev UI

A ideia é conferir se o QA pega a stack certa, escolhe o perfil de integração,
gera o teste e consegue executar tudo normalmente.

Branch: `feature/376-qa-multistack`

| Stack | Perfil esperado | Executor esperado |
| --- | --- | --- |
| Python/FastAPI | `python-integration` | pytest |
| TypeScript/Node | `node-integration` | runner Node do projeto |
| Java/Spring | `java-integration` | JUnit com Maven ou Gradle |
| Go | `go-integration` | `go test` |

## Por onde testar

Todas as 4 stacks foram testadas pela opção `workflow_qa`, com o código-fonte
de cada fixture já materializado em workspaces isolados
(`evidencias_multilevel/dev_ui_workspaces/<perfil>/workspace_output/coder/src`),
com uma sessão nova por stack. A opção `orchestrator` não foi usada (deixaria
o Coder gerar o projeto do zero, o que não era necessário aqui).

## Prompt efetivamente usado (`workflow_qa`)

O prompt original do template ("Execute somente testes de integração para
este projeto `<STACK>`. O código já está em `workspace_output/coder/src`...")
precisou de dois ajustes, descobertos durante a execução:

1. **Não citar o caminho `workspace_output/coder/src` literalmente** — o LLM
   repassava essa string como parâmetro `workspace_projeto`, que já é
   resolvido relativo à raiz do workspace, duplicando o caminho e bloqueando
   com `PROJETO_INEXISTENTE`.
2. **Descrever um cenário concreto** — sem isso, o LLM monta
   `artefatos_json=[]` (vazio) e a execução falha sem gerar nada. Todas as 4
   fixtures implementam o mesmo `CheckoutService`/`InventoryRepository`, então
   a mesma frase de cenário serve para as 4 stacks.

Prompt final usado (trocando apenas `<STACK>`):

```text
Execute somente testes de integração para este projeto <STACK>. O código-fonte
já está persistido no workspace do Coder. Detecte automaticamente a stack e o
framework, sem usar stack_declarada. Não execute testes unitários ou E2E.
Valide o fluxo de checkout: reserva de estoque bem-sucedida deve confirmar o
checkout, e estoque insuficiente deve rejeitar o checkout com erro. Gere,
execute e retorne o resultado normalizado.
```

## Sessões

Não foi possível gerar/salvar prints `.png` — a ferramenta de screenshot usada
só devolve a imagem para visualização inline, sem opção de salvar em disco. Em
vez disso, o histórico completo de cada sessão (prompt, chamadas de tool,
detecção de perfil, geração e resultado normalizado) foi exportado do banco
de sessões do ADK (`adk/src/agents/workflow_qa/.adk/session.db`) para a pasta
[evidencias-integracao-multistack-dev-ui/](evidencias-integracao-multistack-dev-ui/),
em formato bruto (`.json`) e legível (`.md`):

| Perfil | Transcript legível | Eventos brutos |
| --- | --- | --- |
| `python-integration` | [python-integration-sessao.md](evidencias-integracao-multistack-dev-ui/python-integration-sessao.md) | [python-integration-sessao.json](evidencias-integracao-multistack-dev-ui/python-integration-sessao.json) |
| `node-integration` | [node-integration-sessao.md](evidencias-integracao-multistack-dev-ui/node-integration-sessao.md) | [node-integration-sessao.json](evidencias-integracao-multistack-dev-ui/node-integration-sessao.json) |
| `java-integration` | [java-integration-sessao.md](evidencias-integracao-multistack-dev-ui/java-integration-sessao.md) | [java-integration-sessao.json](evidencias-integracao-multistack-dev-ui/java-integration-sessao.json) |
| `go-integration` | [go-integration-sessao.md](evidencias-integracao-multistack-dev-ui/go-integration-sessao.md) | [go-integration-sessao.json](evidencias-integracao-multistack-dev-ui/go-integration-sessao.json) |

## Checklist — `python-integration`

```text
Stack: Python/FastAPI
Perfil esperado: python-integration
Entrada usada: workflow_qa
ID da sessão: bede6d15-887d-4f80-8829-0fdf182324c5
Tempo aproximado: ~1 min

[x] Encontrou ou criou o projeto na stack certa
[x] O QA selecionou somente integração
[x] Detectou o perfil esperado (python-integration)
[x] Escolheu o framework certo (pytest)
[x] Gerou o arquivo de integração
[x] Mostrou o comando executado
[x] Executou pelo menos um teste
[x] Retornou o resultado normalizado
[x] Não teve bloqueio inesperado

Status final: sucesso
Quantidade de testes: 2
Caminho do teste gerado: adk/evidencias_multilevel/dev_ui_workspaces/python-integration/workspace_output/coder/src/tests/integration/test_artefato_integration.py
Sessão completa: evidencias-integracao-multistack-dev-ui/python-integration-sessao.md
Observações: nenhuma.
```

## Checklist — `node-integration`

```text
Stack: TypeScript/Node/Express
Perfil esperado: node-integration
Entrada usada: workflow_qa
ID da sessão: 91ac4fa8-215a-492c-96db-0c2ad76008d6 (2ª tentativa, após fix)
Tempo aproximado: ~1 min

[x] Encontrou ou criou o projeto na stack certa
[x] O QA selecionou somente integração
[x] Detectou o perfil esperado (node-integration)
[x] Escolheu o framework certo (node:test)
[x] Gerou o arquivo de integração
[x] Mostrou o comando executado
[x] Executou pelo menos um teste
[x] Retornou o resultado normalizado
[x] Não teve bloqueio inesperado

Status final: sucesso
Quantidade de testes: 2
Caminho do teste gerado: adk/evidencias_multilevel/dev_ui_workspaces/node-integration/workspace_output/coder/src/tests/integration/artefato.integration.test.generated.ts
Sessão completa: evidencias-integracao-multistack-dev-ui/node-integration-sessao.md
Observações: 1ª tentativa (sessão 83df9c90, sem evidencias exportadas) falhou
  na execução — Node 22.17 instalado nesta máquina rejeita `.ts` no
  `node --test` sem a flag `--experimental-strip-types`. Corrigido em
  shared/testing/integration_adapters.py::_node_command. Reteste com sucesso.
```

## Checklist — `java-integration`

```text
Stack: Java/Spring
Perfil esperado: java-integration
Entrada usada: workflow_qa
ID da sessão: 3e687edc-87d4-448e-9d1e-6abcbcd785f5
Tempo aproximado: ~1 min

[x] Encontrou ou criou o projeto na stack certa
[x] O QA selecionou somente integração
[x] Detectou o perfil esperado (java-integration)
[x] Escolheu o framework certo (JUnit 5 / Maven)
[x] Gerou o arquivo de integração
[ ] Mostrou o comando executado (comando foi montado, mas não executou)
[ ] Executou pelo menos um teste
[x] Retornou o resultado normalizado
[ ] Não teve bloqueio inesperado

Status final: bloqueado
Quantidade de testes: 0
Caminho do teste gerado: adk/evidencias_multilevel/dev_ui_workspaces/java-integration/workspace_output/coder/src/src/test/java/com/example/CheckoutServiceIntegrationTest.java
Sessão completa: evidencias-integracao-multistack-dev-ui/java-integration-sessao.md
Observações: bloqueio ambiental, não é bug de código — ver seção "Se der
  algum erro" abaixo.
```

## Checklist — `go-integration`

```text
Stack: Go
Perfil esperado: go-integration
Entrada usada: workflow_qa
ID da sessão: 9afb2781-106e-4255-9d91-864885fd7888
Tempo aproximado: ~1 min

[x] Encontrou ou criou o projeto na stack certa
[x] O QA selecionou somente integração
[x] Detectou o perfil esperado (go-integration)
[x] Escolheu o framework certo (testing / go test)
[x] Gerou o arquivo de integração
[x] Mostrou o comando executado
[x] Executou pelo menos um teste
[x] Retornou o resultado normalizado
[x] Não teve bloqueio inesperado

Status final: sucesso
Quantidade de testes: 1 (cobre os dois cenários no mesmo teste)
Caminho do teste gerado: adk/evidencias_multilevel/dev_ui_workspaces/go-integration/workspace_output/coder/src/repository_integration_test.go
Sessão completa: evidencias-integracao-multistack-dev-ui/go-integration-sessao.md
Observações: nenhuma.
```

## Resumo

| Perfil | Entrada | Detecção | Geração | Execução | Status | Sessão |
| --- | --- | --- | --- | --- | --- | --- |
| `python-integration` | workflow_qa | ✅ pytest | ✅ | ✅ | sucesso | [ver](evidencias-integracao-multistack-dev-ui/python-integration-sessao.md) |
| `node-integration` | workflow_qa | ✅ node:test | ✅ | ✅ (após fix) | sucesso | [ver](evidencias-integracao-multistack-dev-ui/node-integration-sessao.md) |
| `java-integration` | workflow_qa | ✅ JUnit/Maven | ✅ | ❌ Maven ausente | bloqueado | [ver](evidencias-integracao-multistack-dev-ui/java-integration-sessao.md) |
| `go-integration` | workflow_qa | ✅ go-testing | ✅ | ✅ | sucesso | [ver](evidencias-integracao-multistack-dev-ui/go-integration-sessao.md) |

## Se der algum erro

```text
Stack: Java/Spring
App usado: workflow_qa
ID da sessão: 3e687edc-87d4-448e-9d1e-6abcbcd785f5
Etapa que falhou: execução (dentro de preparar_testes_integracao / execute_integration_adapter)
Perfil detectado: java-integration (framework JUnit 5 / Maven) — correto
Comando executado: não chegou a montar comando completo — bloqueado antes por
  ausência do executável
Mensagem completa: status=bloqueado, código RUNTIME_DEPENDENCY_MISSING,
  "Maven não está disponível."
Caminho do arquivo gerado: adk/evidencias_multilevel/dev_ui_workspaces/java-integration/workspace_output/coder/src/src/test/java/com/example/CheckoutServiceIntegrationTest.java
Sessão completa: evidencias-integracao-multistack-dev-ui/java-integration-sessao.md
```

Causa confirmada em terminal: `mvn` não está instalado no PATH desta máquina
e o fixture `java-integration` não tem wrapper `mvnw`. Não é um bug — a mesma
causa já derrubava esse perfil na suíte automatizada
`tests/integration/test_multistack_profiles_real.py` antes de qualquer
mudança (confirmado via `git stash`). Não instalei Maven por ser uma ação de
sistema fora do escopo desta tarefa.

## Correções de código aplicadas durante o teste

1. `adk/shared/cache/qa_agent_cache.py` — o cache do `qa_agent` acessava
   `callback_context.custom_metadata`, atributo que não existe na classe
   `Context` real do google-adk 1.33.0 (e o ADK cria uma instância nova de
   `CallbackContext` a cada hook before/after/on_error). Isso quebrava
   qualquer request ao `qa_agent`/`workflow_qa` pela Dev UI. Corrigido para
   usar um dicionário interno no próprio objeto de cache, chaveado por
   `id(callback_context.actions)`.
2. `adk/src/agents/qa_agent/subagents/integration_tests_agent/profile_generation.py`
   e `orchestration.py` — `preparar_testes_integracao` exigia estritamente o
   campo `conteudo` no artefato; agora aceita as mesmas variações já toleradas
   no fluxo unitário (`descricao`, `requisito`, `resumo`, `titulo`,
   `criterios_aceite`, `criterios_verificaveis`), e o docstring da tool passou
   a documentar o schema esperado.
3. `adk/shared/testing/integration_adapters.py` — comando do perfil
   `node-integration` passou a incluir `--experimental-strip-types` quando o
   teste gerado é `.ts`/`.mts`/`.cts`, necessário no Node 22.6+ sem isso
   habilitado por padrão.

Testes automatizados relevantes (`test_multistack_integration_adapters.py`,
`test_profile_based_test_agents.py`, `test_result_normalization.py`,
`test_qa_agent_cache.py` — 52 no total) passam após as correções. Nenhuma
mudança foi commitada.

## Reteste pós-pull (2026-09-02, 21h)

Repetido o mesmo processo (workflow_qa, mesmo prompt por stack, sessão nova
por perfil) após um `git pull` que trouxe mudanças na área de QA. Antes do
reteste, os workspaces de fixture (`evidencias_multilevel/dev_ui_workspaces/*`,
gitignorados) estavam com artefatos acumulados de execuções anteriores
(arquivos `*.generated.*` duplicados, Doubt Artifacts antigos em
`python-integration`) — foram limpos (apenas os testes/relatórios gerados,
preservando o código-fonte original de cada fixture) antes de rodar de novo.

**Achado principal:** o `code_fix_agent` deixou de ser Python-only. O pull
atualizou `shared/tools/qa_test_files.py` e o prompt do `code_fix_agent` para
reconhecer e corrigir testes gerenciados de Python, Node (Vitest/Jest/
node:test/Mocha), Java/JUnit e Go/testing (`_language()`, `_validate_corrected_content()`
por stack, `executar_teste_unitario_corrigido` roteando para o executor certo).

| Perfil | Nova sessão | Resultado |
| --- | --- | --- |
| `python-integration` | `bdd88270-0426-49de-af27-7aca1937ab3a` | sucesso — 2 passed in 0.18s |
| `node-integration` | `a541d363-ac2c-4bc2-a11d-9cdf5bf09a60` | sucesso |
| `java-integration` | `33b1f45b-2435-4b51-a471-9a3c17f5959b` | bloqueado — Maven ausente (mesma causa ambiental já documentada, não é regressão) |
| `go-integration` | `64616312-a342-4215-8e53-a34a6fe22b6d` | sucesso — `TestCheckoutService_Integration_SuccessAndFailure` PASS |

Observação: na primeira tentativa (sem limpar o fixture) o `python-integration`
falhou por um nome de arquivo gerado com ponto (`test_artefato_integration.generated.py`),
que o Python interpreta como pacote — `ModuleNotFoundError: 'test_artefato_integration.generated'
is not a package`. Após limpar o fixture, a geração produziu
`test_artefato_integration.py` (sem o `.generated` no meio) e o teste passou
normalmente. Também houve um `InternalServerError` transitório do provedor
`github_copilot` durante o teste `go-integration`, resolvido reenviando o
mesmo prompt na mesma sessão.
