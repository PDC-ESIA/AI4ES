# Evidências dos perfis unitários

Esta pasta reúne resultados automatizados e prints opcionais da Dev UI para os
sete perfis unitários de Python, Node, Java e Go. TypeScript é coberto pelos
perfis Node.

Os prints consolidados da execução estão em
[`DEV_UI_EVIDENCIAS.md`](DEV_UI_EVIDENCIAS.md).

O conjunto automatizado versionado está em `runs/handoff-final-20260831/`.
Cada `evidence.json` registra detecção, runtime, comando, contagens, cobertura,
hashes e saída da execução realizada.

Os relatórios ficam neste diretório. Os PNGs são armazenados na
[pasta de evidências visuais no Google Drive](https://drive.google.com/drive/folders/1Q7TkGS9jmEaVFtBcthiBC8BNfmP9-mMF?usp=sharing)
e vinculados em [`DEV_UI_EVIDENCIAS.md`](DEV_UI_EVIDENCIAS.md).
Workspaces locais da Dev UI continuam separados, na pasta `adk`.

## Validar pela Dev UI

Configure o workspace do projeto e inicie a aplicação:

```powershell
$env:WORKSPACE_OUTPUT_DIR = "evidencias_unit_profiles/dev_ui_workspaces/node-jest/workspace_output"
uvicorn app.main:app --reload --port 8081
```

Abra `http://127.0.0.1:8081/dev-ui/?app=workflow_qa` e solicite testes
unitários para a stack que deseja validar.

## Prints

Capture temporariamente por perfil e envie os arquivos ao Google Drive:

1. `01_prompt.png` — solicitação completa;
2. `02_profile_detection.png` — perfil detectado;
3. `03_execution_result.png` — testes e cobertura;
4. `04_generated_file.png` — caminho do teste gerado, quando exibido.

Não inclua tokens, cookies ou credenciais.
