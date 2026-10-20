# Revisão de guardrails do QA — P6

Branch revisada: `feat/guard-rails-qa-agent`.

Este documento registra a revisão inicial. A implementação posterior das
melhorias e suas limitações de validação estão em
[QA — melhorias adicionadas](qa-guardrails-melhorias-implementadas.md).

## O que já estava implementado

`write_qa_test` já chama `validar_seguranca_codigo` antes de substituir o
arquivo corrigido. O agente de correção usa essa ferramenta. Os testes
existentes verificam rejeição de leitura de ambiente, rede externa,
credenciais literais e imports de fora da suíte, preservando o arquivo anterior.
O gerador Playwright também já inspecionava o conteúdo antes da escrita.

## Lacunas corrigidas nesta revisão

- O detector de credenciais não reconhecia chaves entre aspas em JSON ou
  dicionários Python. Agora reconhece também esse formato e Authorization.
- A redação de segredos podia deixar partes de valores com espaços ou aspas
  escapadas. Esses valores agora são ocultados integralmente, com testes de
  preservação da estrutura JSON e de campos não sensíveis.
- A inspeção TypeScript ignorava `page.goto`, métodos de `request`, destinos
  por variável, chamadas em várias linhas, URLs começando com `//`, imports
  ES/`node:` e acesso `process['env']`. Esses casos agora são rejeitados.
  A mensagem de rejeição não reproduz a URL potencialmente sensível.
- `DoubtArtifactGenerator` já ocultava motivo e trecho suspeito, mas o outro
  gerador, `gerar_doubt_artifact`, ainda persistia os dados brutos. Ambos agora
  sanitizam o documento final; o identificador também é sanitizado antes de
  virar nome de arquivo. O primeiro gerador passa a normalizar o nome.
- O pytest sanitizava o log, mas extraía `linhas_com_erro` da saída original.
  A extração agora recebe a saída sanitizada.

Os testes incluem rejeição antes da persistência de specs, preservação do
teste anterior em correções rejeitadas e ausência de segredos nos documentos
de dúvida e nos erros estruturados. Nos documentos de dúvida a política é
ocultar o segredo e preservar o diagnóstico, em vez de rejeitar o documento.

## Validação

132 testes passaram no Python 3.14.4 / Windows:

```text
python -m pytest --noconftest -q -p no:cacheprovider
  tests/unit/test_security_guardrails.py
  tests/unit/test_pipeline_artifact_handoff.py
  tests/unit/test_qa_workspace_binding.py
  tests/unit/test_receive_requirements_sanitizer.py
  tests/unit/test_path_validation_regressions.py
  tests/unit/test_inspecionar_projeto_e2e_workspace.py
```

Os argumentos acima devem ser passados na mesma chamada. A execução normal
com o conftest global falha na coleta no Windows: ele importa
`shared.execution.sandbox`, que importa `resource` (Unix). Por isso os testes
focados foram executados sem esse conftest. A suíte completa não foi validada.

## Melhorias prioritárias ainda pendentes

1. **Isolar filesystem e rede do processo de testes.** O runner executa
   `subprocess.run` no host com ambiente filtrado. Isso não restringe arquivos
   acessíveis pelo usuário nem conexões de rede. A inspeção Python não bloqueia,
   por exemplo, `open(...)` e `Path.read_text(...)`. Um teste pode ler um arquivo
   sensível e incluir seu conteúdo em uma falha sem que ele tenha formato de
   credencial reconhecido. Executar em ambiente descartável, com montagem
   limitada à suíte e rede restrita, é a próxima barreira necessária.
2. **Não tratar AST/regex como garantia contra código hostil.** A análise
   Python não acompanha todas as atribuições/aliases; a TypeScript usa padrões
   textuais, que ainda admitem ofuscação e falsos positivos em strings ou
   comentários. Um parser TypeScript e análise mais estruturada podem melhorar
   a precisão, mas não substituem o isolamento de execução.
3. **Definir política de divulgação de prompts e código.** Detectar padrões
   de credenciais não identifica um prompt interno ou código privado copiado
   como texto comum. Os controles desta revisão não garantem prevenção desses
   vazamentos; os canais de leitura, persistência e entrega ao modelo precisam
   de uma política explícita de conteúdo permitido.
