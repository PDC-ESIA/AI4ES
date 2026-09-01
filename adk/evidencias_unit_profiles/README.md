# Evidências dos perfis unitários

Esta pasta reúne resultados automatizados e prints opcionais da Dev UI para os
sete perfis unitários de Python, Node, Java e Go. TypeScript é coberto pelos
perfis Node.

## Coletar evidências

Na pasta `adk`:

```powershell
.\.venv\Scripts\python.exe scripts\unit_profile_evidence.py collect `
  --profile all `
  --bootstrap-runtime
```

O comando cria um `SUMMARY.md` e um `evidence.json` por perfil. Os JSONs
registram detecção, runtime, comando, contagens, cobertura, hashes e saída.

O conjunto versionado está em `runs/handoff-final-20260831/`.

## Validar pela Dev UI

Prepare um workspace isolado:

```powershell
.\.venv\Scripts\python.exe scripts\unit_profile_evidence.py prepare-dev-ui `
  --profile node-jest
```

Configure e inicie a aplicação:

```powershell
$env:WORKSPACE_OUTPUT_DIR = "evidencias_unit_profiles/dev_ui_workspaces/node-jest/workspace_output"
uvicorn app.main:app --reload --port 8081
```

Abra `http://127.0.0.1:8081/dev-ui/?app=workflow_qa` e use o prompt salvo em
`dev_ui_session.json`.

## Prints

Salve em `dev_ui/<perfil>/`:

1. `01_prompt.png` — solicitação completa;
2. `02_profile_detection.png` — perfil detectado;
3. `03_execution_result.png` — testes e cobertura;
4. `04_generated_file.png` — caminho do teste gerado, quando exibido.

Não inclua tokens, cookies ou credenciais. Para gerar o índice com hashes:

```powershell
.\.venv\Scripts\python.exe scripts\unit_profile_evidence.py index-screenshots `
  --profile node-jest `
  --minimum 3
```
