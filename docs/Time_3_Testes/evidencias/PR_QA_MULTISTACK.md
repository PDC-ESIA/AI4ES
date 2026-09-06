# QA multistack — geração, execução e evidências de testes

## Resumo

Este PR torna o QA Agent capaz de identificar a stack do projeto e trabalhar
com testes unitários, de integração e E2E por meio de perfis especializados.
A implementação cobre as famílias atualmente usadas pelo Coder:
Python/FastAPI, Node/Express com JavaScript ou TypeScript, Java/Spring e Go.

O fluxo comum dos três níveis é:

```text
entrada → planejamento → inspeção do projeto → seleção do perfil
        → geração → execução → normalização do resultado
```

A seleção usa primeiro o `tech_stack` persistido pelo Coder em seu contexto.
Quando essa informação não está disponível, os manifests, arquivos e
configurações encontrados no workspace são usados como evidência. Dessa forma,
o usuário não precisa informar manualmente um executor ou perfil.

## Cobertura implementada

| Nível | Python/FastAPI | Node/Express JS/TS | Java/Spring | Go |
| --- | --- | --- | --- | --- |
| Unitário | `python-pytest` | `node-vitest`, `node-jest`, `node-node-test` e `node-mocha` | `java-junit` | `go-testing` |
| Integração | `python-integration` | `node-integration` | `java-integration` | `go-integration` |
| E2E | `python-e2e` | `node-e2e` | `java-e2e` | `go-e2e` |

Os perfis unitários executam pytest, Vitest, Jest, `node:test`, Mocha,
JUnit com Maven ou Gradle e `go test`. Os perfis de integração utilizam o
runner declarado pelo projeto para cada stack. No E2E, os quatro perfis
compartilham Playwright com TypeScript e Chromium headless, pois a interação
ocorre pela interface web independentemente da linguagem do backend.

## Estrutura do QA Agent

- O `action_planner` limita a solicitação ao nível de teste correto e entrega
  um plano validado ao subagente responsável.
- O E2E recupera o plano canônico e a solicitação original do estado da sessão,
  preservando URL, jornada, ações e dados mesmo quando o modelo produz um
  resumo intermediário incompleto.
- O inspetor combina o contexto do Coder e sinais reais do projeto para
  selecionar um perfil compatível.
- O catálogo de perfis concentra stack, framework, arquivos reconhecidos e
  política de execução, permitindo adicionar suporte futuro sem duplicar o
  fluxo completo do agente.
- Os geradores de testes unitários, de integração e E2E trabalham somente nos
  arquivos de teste e mantêm o código da aplicação fora do escopo de alteração.
- Os adaptadores montam comandos determinísticos, executam sem shell e não
  instalam dependências durante o fluxo do agente.
- Ausência de runtime, dependência, manifesto ou contrato válido produz um
  bloqueio estruturado, em vez de tentar executar outra stack como fallback.
- O `pytest_runner` existente continua responsável pelo perfil Python unitário
  e não foi convertido em executor genérico.

## Resultado normalizado

Todos os níveis retornam o mesmo contrato básico:

- `status` e `tipo_teste`;
- evidências da `inspecao` e o `perfil` selecionado;
- `resumo`, `arquivos_gerados` e `detalhes` da execução;
- `bloqueios` estruturados quando a execução não pode prosseguir.

Integração e E2E também preservam comando, código de saída, `stdout`, `stderr`
e demais dados do executor em `resultado_bruto`. Isso permite que a Dev UI,
os testes automatizados e os coletores de evidência consumam o mesmo formato.

## Code Fix multistack

O Code Fix reconhece arquivos de teste gerenciados em Python, Node,
TypeScript, Java e Go. A validação do conteúdo corrigido e a reexecução são
roteadas para o executor do perfil detectado, mantendo a regra de alterar
somente testes. A evidência de Java/JUnit inclui uma asserção inválida
controlada, a correção do teste e a reexecução final com sucesso.

## Compatibilidade e isolamento

- O fluxo aceita caminhos e processos em Windows e Linux.
- A saída do processo é configurada em UTF-8 no Windows para que mensagens
  Unicode dos plugins do ADK não bloqueiem a Dev UI.
- O executor limita a execução ao workspace autorizado e valida os caminhos
  antes de acessar projetos ou testes.
- Comandos são representados como listas de argumentos e executados sem
  interpolação de shell.
- O perfil Node suporta arquivos JavaScript e TypeScript e respeita o runner
  configurado no projeto.
- Nomes alternativos de testes Java e Go preservam as convenções de descoberta
  dos respectivos runners quando já existe um arquivo com o nome preferencial.
- O E2E aceita somente aplicação local em loopback. Quando não há um
  inicializador local reconhecido, a aplicação deve estar disponível na
  `base_url` informada.
- Runtime, gerenciador de build, Playwright, navegador e dependências do projeto
  devem existir no ambiente antes da execução.

## Automação e reprodução

Foram adicionadas fixtures isoladas, scripts de coleta e duas matrizes de CI:

- `unit-profile-matrix.yml`: executa os sete perfis unitários com os runtimes
  correspondentes e publica os arquivos de evidência;
- `qa-multilevel-matrix.yml`: executa os quatro perfis de integração e os
  quatro perfis E2E, incluindo a preparação do Chromium para Playwright.

Na pasta `adk`, a validação local pode ser reproduzida com:

```powershell
# Contratos, seleção de perfil, adaptadores e normalização
.\.venv\Scripts\python.exe -m pytest `
  tests/unit/test_profile_based_test_agents.py `
  tests/unit/test_multistack_integration_adapters.py `
  tests/unit/test_result_normalization.py -q

# Execução real da matriz de integração e E2E
.\.venv\Scripts\python.exe -m pytest `
  tests/integration/test_multistack_profiles_real.py -q

# Coleta reproduzível dos sete perfis unitários
.\.venv\Scripts\python.exe scripts\unit_profile_evidence.py `
  collect --profile all --bootstrap-runtime

# Coleta reproduzível dos quatro perfis de integração e quatro perfis E2E
.\.venv\Scripts\python.exe scripts\qa_multilevel_evidence.py `
  --level all --profile all
```

## Resultados automatizados

| Escopo | Perfis validados | Resultado registrado |
| --- | ---: | --- |
| Unitário | 7 | todos detectados e executados com sucesso |
| Integração | 4 | 8 testes aprovados, 2 por stack |
| E2E | 4 | 4 testes Playwright aprovados, 1 por stack |

Cada execução gera um `evidence.json` próprio com perfil, runtime, comando,
hashes dos arquivos, logs, contagens e resultado normalizado. Os resumos
consolidados estão disponíveis em:

- [resultados automatizados dos perfis unitários](evidencias_unit_profiles/runs/handoff-final-20260831/SUMMARY.md);
- [resultados automatizados de integração e E2E](evidencias_multilevel/runs/handoff-final-20260831/SUMMARY.md).

## Evidências na Dev UI

### Testes unitários

Os sete perfis foram exercitados na Dev UI com detecção automática e execução
real. As capturas registram:

| Perfil | Resultado exibido na Dev UI |
| --- | --- |
| `python-pytest` | 10 aprovados e 100% de cobertura |
| `node-vitest` | 13 aprovados |
| `node-jest` | 13 aprovados e 100% de cobertura |
| `node-node-test` | 12 aprovados |
| `node-mocha` | 13 aprovados |
| `java-junit` | Code Fix validado e 12 aprovados no resultado final |
| `go-testing` | 21 aprovados e 100% de cobertura |

As capturas completas estão no
[resumo visual dos testes unitários](evidencias_unit_profiles/DEV_UI_EVIDENCIAS.md).

### Testes de integração

As sessões registram a solicitação, o planejamento, a seleção do perfil, o
teste gerado e o resultado normalizado das quatro stacks. Python, Node e Go
possuem execução bem-sucedida registrada. Na máquina usada para a captura de
Java, o perfil e o JUnit/Maven foram identificados e o teste foi gerado, mas a
execução retornou o bloqueio ambiental esperado porque Maven não estava no
`PATH`. O mesmo perfil Java está aprovado na matriz automatizada, executada em
ambiente com o runtime preparado.

As transcrições legíveis e os eventos brutos estão no
[resumo das sessões de integração](evidencias_integracao_dev_ui/RESUMO.md).

### Testes E2E

Os quatro perfis foram executados pela Dev UI contra uma aplicação local. As
capturas comprovam a seleção de `python-e2e`, `node-e2e`, `java-e2e` e
`go-e2e`, a execução pelo Playwright e o resultado final de 1 teste aprovado e
0 falhas em cada stack.

Os quatro prints estão no
[resumo visual dos testes E2E](evidencias_e2e_dev_ui/RESUMO.md).

## Resultado do PR

O QA Agent passa a oferecer uma interface única para testes multistack sem
transformar um runner específico em interpretador universal. O comportamento
comum — inspeção, seleção, isolamento, bloqueios e normalização — é
compartilhado, enquanto geração e execução permanecem especializadas por nível
e perfil. A entrega inclui cobertura automatizada, fixtures reproduzíveis,
matrizes de CI, resultados estruturados e evidências de uso real pela Dev UI.
