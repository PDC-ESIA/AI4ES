# Evidências do fix Coder → QA

## Resumo

O fix garante que o QA utilize os fontes persistidos pelo Coder, preserve a
estrutura do pacote, gere testes pytest executáveis e publique sucesso somente
quando houver testes realmente coletados e aprovados.

O escopo está restrito ao QA e às suas ferramentas compartilhadas. Não há
alterações nos agentes de Requirements, Context Engineer, Design, Validator ou
Coder.

## Problemas corrigidos

1. **Fontes ausentes no contexto do QA**
   - O QA descobre os fontes em `workspace_output/coder/src` mesmo sem um
     manifesto de Coding.
   - Os arquivos são copiados para a suíte de teste preservando caminhos como
     `src/modulo.py`.

2. **Imports resolvendo para o pacote errado**
   - Cada suíte recebe um `conftest.py` controlado pelo QA.
   - Quando necessário, a cópia materializada recebe `src/__init__.py` sem
     alterar os arquivos do Coder.
   - A raiz da suíte e sua pasta `src` têm precedência durante o pytest.

3. **Caminhos de teste inventados durante o handoff**
   - O Workflow QA chama `receber_requisitos` diretamente como `FunctionTool`.
   - `detalhes[].arquivo_gerado` é a única fonte de verdade para execução.
   - Caminhos sugeridos que não aparecem no retorno do receiver são ignorados.

4. **Falso sucesso do pytest**
   - Zero testes, erro de coleta, falhas ou testes ignorados impedem
     `resultado_resumo=sucesso_total`.
   - O manifesto QA é calculado a partir dos `report.json` e Doubt Artifacts
     persistidos.

5. **Autocorreção fora do escopo**
   - O `code_fix_agent` pode alterar somente um `test_*.py` existente dentro de
     `tests/inputs`.
   - Criação de testes paralelos, manipulação de `sys.path` e referência direta
     ao workspace do Coder são rejeitadas.

## Validação automatizada

```text
77 testes de regressão do Orchestrator/QA validados
ruff: All checks passed
git diff --cached --check: sem erros
```

Os testes cobrem, entre outros:

- descoberta de fontes sem manifesto;
- preservação de pacotes com múltiplos módulos;
- geração de `conftest.py` e `src/__init__.py` no workspace do QA;
- importação do pacote materializado pelo runner;
- rejeição de zero testes, `skip` e erro de coleta;
- uso exclusivo do caminho retornado pelo receiver;
- proibição de criar um teste ausente durante o code-fix;
- manifesto `ok` somente após execução válida.

## Evidência end-to-end de sucesso

Sessão ADK:

```text
fdcd2e6d-6322-437f-a5d3-3a9b2eefc834
```

Resultado observado:

```text
receiver: 1 artefato processado com sucesso
teste: tests/inputs/qa_e2e_handoff_1/test_qa_e2e_handoff_1.py
fontes materializados: src/__init__.py, src/shipping_rules.py, src/order_service.py
pytest: 27 passed, 0 failed, 0 skipped
resultado_resumo: sucesso_total
manifesto QA: ok
```

Os hashes SHA-256 dos três fontes materializados eram idênticos aos arquivos
persistidos pelo Coder. O runner executou exatamente o
`arquivo_gerado` retornado pelo receiver.

## Evidência de bloqueio seguro

Sessão ADK:

```text
9b984368-a3bf-4150-ba02-33a06dd9a427
```

O receiver processou dois artefatos e o QA executou ambas as suítes nos paths
canônicos:

```text
QA-INVOICE-002: 10 passed, 0 failed, 0 skipped, sucesso_total
QA-TAX-001:     17 passed, 1 failed, 0 skipped, falha_parcial
```

A falha de `QA-TAX-001` revelou uma divergência real no código de produção:
`calculate_tax(0.0, "ES")` retornava `0.0` antes de validar o estado. Após duas
tentativas de correção restritas ao mesmo arquivo de teste, o QA gerou um Doubt
Artifact e publicou:

```text
manifesto QA: blocked
resumo: 27 passed, 1 failed, 0 skipped, 1 dúvida bloqueante
```

O caminho não confiável `artefactsTests/billing/test_billing.py` não foi criado
nem executado. Essa sessão comprova que o fluxo não transforma uma falha real
em falso sucesso.

## Resultado

- Fontes persistidos chegam ao QA sem depender da memória do agente.
- A topologia dos módulos é preservada.
- O pytest executa os arquivos realmente gerados.
- O QA diferencia sucesso, falha e bloqueio usando evidência estruturada.
- Nenhum agente externo ao QA precisa ser alterado para o handoff funcionar.
