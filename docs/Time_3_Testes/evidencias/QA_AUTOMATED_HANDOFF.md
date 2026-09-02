# Operação e reprodução do QA multistack

## Cobertura automatizada

- Unitário: sete perfis de Python, Node, Java e Go.
- Integração: Python, TypeScript/Node, Java e Go.
- E2E: quatro perfis executados com Playwright e Chromium em loopback.
- Todos os níveis retornam resultado normalizado com comandos, logs e bloqueios.

## Reproduzir

Execute na pasta `adk`:

```powershell
# Suíte automatizada de integração e E2E
.\.venv\Scripts\python.exe -m pytest tests/integration/test_multistack_profiles_real.py -q

# Evidências de integração e E2E
.\.venv\Scripts\python.exe scripts\qa_multilevel_evidence.py --level all --profile all

# Evidências dos perfis unitários
.\.venv\Scripts\python.exe scripts\unit_profile_evidence.py collect --profile all --bootstrap-runtime
```

## Evidências versionadas

- [Resultados unitários](evidencias_unit_profiles/runs/handoff-final-20260831/SUMMARY.md).
- [Resultados de integração e E2E](evidencias_multilevel/runs/handoff-final-20260831/SUMMARY.md).
- [Prints da Dev UI — unitários](evidencias_unit_profiles/DEV_UI_EVIDENCIAS.md).
- Cada perfil possui um `evidence.json` com runtime, comando, hashes, logs e
  resultado normalizado.

Os comandos de coleta salvam os relatórios por padrão nesta pasta de evidências
do Time 3. Os caminhos registrados nos JSONs descrevem o ambiente da execução
original e não foram reescritos durante a organização.

## Dev UI

Prepare um workspace unitário isolado:

```powershell
.\.venv\Scripts\python.exe scripts\unit_profile_evidence.py prepare-dev-ui --profile node-jest
```

Configure `WORKSPACE_OUTPUT_DIR` com o `workspace_output` criado, inicie a Dev
UI e execute o prompt registrado em `dev_ui_session.json`.

Para integração, use um projeto em
`tests/fixtures/integration_profiles/<perfil>/project` e solicite somente
testes de integração.

Para E2E, disponibilize a fixture local:

```powershell
.\.venv\Scripts\python.exe -m http.server 8765 --bind 127.0.0.1 --directory tests/fixtures/e2e_profiles
```

Solicite um teste E2E com Playwright para
`http://127.0.0.1:8765/index.html`. Capture a seleção do perfil, o arquivo
gerado e o resultado final sem expor credenciais.
