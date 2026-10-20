# QA — melhorias de segurança adicionadas

## Implementação

- **Execução isolada:** pytest e Playwright usam contêiner descartável, sem
  rede externa, sem privilégios, com filesystem da imagem somente leitura e
  limites de CPU, memória, processos e tempo. Não há fallback para executar
  código gerado no host quando o Docker ou a imagem estiverem indisponíveis.
- **Entrada controlada:** somente uma cópia limitada dos arquivos da suíte e
  da aplicação é montada, em modo somente leitura. Links são rejeitados;
  arquivos de credenciais, `.env`, prompts conhecidos e diretórios internos
  são excluídos. O diretório original e o socket Docker não são montados.
- **E2E:** aplicação Uvicorn e Playwright executam no mesmo contêiner e se
  comunicam por loopback. O agente não inicia mais a aplicação no host nem
  instala dependências automaticamente durante os testes.
- **Inspeção de código:** aliases Python por atribuição e acesso ao ambiente
  completo passam a ser detectados. O sandbox adiciona análise sintática
  TypeScript antes da execução, com restrições a imports, imports dinâmicos,
  ambiente e avaliação dinâmica de código. As inspeções complementam o
  isolamento; não são tratadas como garantia contra toda forma de ofuscação.
- **Divulgação mínima:** o sandbox exporta somente contagens, cobertura e
  campos de erro permitidos. Logs brutos, screenshots, vídeos e traces não
  são exportados. Artefatos de dúvida e builders de correção omitem evidências
  livres, que poderiam conter prompts/código mesmo sem uma chave de API.
  O corretor continua podendo ler o teste autorizado com redação de segredos;
  a inspeção E2E também exclui arquivos de prompts conhecidos.

Principais arquivos: `adk/shared/qa_sandbox.py`, `adk/shared/qa_disclosure.py`,
`adk/qa_sandbox/` e ferramentas de execução, correção e dúvida do QA.

## Validação

**149 testes passaram; 7 foram ignorados por exigirem Docker.** Incluem testes
de bloqueio sem sandbox, configuração das restrições, limpeza após falha,
exclusão de arquivos sensíveis, divulgação e regressões do P6. Ruff e a
verificação de sintaxe dos scripts Node passaram.

O serviço Docker está indisponível neste ambiente. Portanto, **a imagem ainda
não foi construída e a execução real em contêiner não foi validada**, incluindo
o parser TypeScript com sua dependência instalada. Foram adicionadas provas
de integração para filesystem, rede, ambiente, parser e E2E local.

Os testes focados usaram `--noconftest`, pois o conftest global importa o módulo
Unix `resource` e impede a coleta no Windows. A suíte completa não foi validada.

## Preparação e impacto operacional

Com Docker Linux disponível, na raiz do repositório:

```powershell
docker build -t ai4es-qa-sandbox:local adk/qa_sandbox
cd adk
$env:QA_SANDBOX_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m pytest --noconftest -p no:cacheprovider tests/integration/test_qa_sandbox_isolation.py tests/unit/test_security_guardrails.py tests/unit/test_qa_workspace_binding.py
```

A imagem é preparada pelo operador; `QA_SANDBOX_IMAGE` permite selecionar
outra imagem confiável. Dependências adicionais precisam entrar nessa imagem,
pois a execução não tem acesso à internet. O daemon deve conseguir montar o
snapshot temporário local; execução com daemon remoto não foi validada.

**Mudança de compatibilidade:** por enquanto o E2E isolado aceita alvos Uvicorn
gerenciados. Serviços já iniciados no host e outros perfis ficam bloqueados.
Evidências brutas deixam de ser disponibilizadas para diagnóstico. A política
permite o código do teste e da aplicação explicitamente fornecidos ao QA;
não tenta identificar semanticamente todo conteúdo privado arbitrário.
