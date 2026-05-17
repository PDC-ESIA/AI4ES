# Investigação do bug interno do design_pipeline

**Data:** 2026-05-17
**Timebox:** 30 min
**Status:** completed

## Sintoma observado

Invocação do `workflow_design_pipeline` com uma HU mínima de healthcheck FastAPI percorre os 3 primeiros passos com sucesso:

1. `design_architect` → `"Análise salva em staging: analise_tecnica_HU-001.md"`
2. `mermaid_specialist` → `"O artefato 'diagrama_HU-001_healthcheck.mmd' foi gerado e salvo com sucesso."`
3. `markdown_specialist` → **retorna string vazia (`"result":""`)**.

O orquestrador `design_pipeline` (LLM) lê a resposta vazia, classifica corretamente como falha do passo 3, pula `validator`, e encerra com status `"falha"`:

> O pipeline falhou durante a geração do relatório Markdown. O `markdown_specialist` não retornou o nome do arquivo do relatório.

Estado do disco após a execução (em `adk/temp/staging/`):

- `analise_tecnica_HU-001.md` (criado)
- `diagrama_HU-001_healthcheck.mmd` (criado)
- `relatorio_HU-001_*.md` (**NÃO criado**)

Em `io_operations.log`, o `markdown_specialist` chegou a LER template + análise + diagrama, mas a operação SAVE do relatório nunca foi registrada.

## Trace relevante

Da resposta `/tmp/design-debug.json`:

```json
{
  "functionCall": {"name": "markdown_specialist", "args": {"request": "diagrama_HU-001_healthcheck.mmd"}}
}
...
{
  "functionResponse": {
    "name": "markdown_specialist",
    "response": {"result": ""}
  }
}
```

Última operação registrada por `io_agent` antes do colapso:

```
[2026-05-17T13:45:49.946169] READ    | file=relatorio_design_template.md
[2026-05-17T13:45:58.011565] READ    | file=analise_tecnica_HU-001.md
[2026-05-17T13:46:07.607322] READ    | file=diagrama_HU-001_healthcheck.mmd
```

Não há linha `SAVE | file=relatorio_*.md`. O `markdown_specialist` parou de gerar entre o último READ (13:46:07) e o retorno vazio ao pipeline pai (13:46:16, ~9s de silêncio).

Não há `MALFORMED_FUNCTION_CALL` no trace nem no `/tmp/ai4es-uvicorn-8081.log`. O log do uvicorn não mostra exceção Python.

## Classificação

**inline_content** (com causa raiz adjacente de **token overflow no sub-agente**).

A causa raiz mais provável: o `markdown_specialist` (Gemini 2.5 Flash) tenta emitir uma `functionCall` para `io_agent` com o relatório Markdown COMPLETO embutido inline no argumento `request` (string). O template oficial + diagrama embutido + 7 seções da análise produz facilmente >4-6k tokens de output, que ao ser concatenado dentro do thoughtSignature + tool args estoura o cap de output do modelo. A geração é interrompida antes de fechar o JSON da function call, então o ADK degrada para resposta vazia (não emite `MALFORMED_FUNCTION_CALL` porque não há JSON parcial — apenas nenhuma `Part` válida).

Por que **não é** token_overflow no sentido "estouro do contexto da sessão":
- promptTokenCount do markdown_specialist é apenas 1339 tokens — sessão está enxuta.
- Sessões dos AgentTool sub-agentes são isoladas (cada `AgentTool.run` cria contexto novo).

Por que **é** inline_content / saída inflada:
- O prompt do `markdown_specialist` (passo 4, etapa 1) instrui: `"Salve o arquivo <nome>.md em staging com o seguinte conteúdo: <conteúdo completo do relatório>"`. Isso obriga o LLM a gerar o relatório INTEIRO como string dentro do argumento da function call ao `io_agent`. Em seguida o `io_agent` repete isso ao chamar `save_artifact`. Cada salto de AgentTool dobra a pressão sobre o output budget.
- Sintoma idêntico ao listado em CLAUDE.md como falha conhecida do Gemini 2.5 Flash com saídas longas em function calls.

## Decisão

**prosseguir** com Task 9 + Task 10, **com escopo de fix conservador**.

Rationale:
- O bug NÃO é catastrófico para o orquestrator. O pipeline detecta e reporta falha corretamente. Adicionando `design_pipeline` antes de `coding_review_pipeline` no orchestrator SDLC v3, a falha do design apenas resultará em "fase de design parcial", sem corromper requirements/coding/qa (sessões isoladas).
- Ainda assim, vale capturar o ganho fácil: reduzir a probabilidade do bug acontecer.

## Recomendação para Task 9

**Mudança alvo (mínima e isolada):** alterar o protocolo de persistência no prompt do `markdown_specialist` (e por simetria, `mermaid_specialist` e `design_architect`) para **não passar o conteúdo completo inline ao `io_agent`** quando o relatório for grande. Duas alternativas, em ordem de preferência:

**Alternativa A — gerar em chunks** (preferida)
Reformular `PASSO 4 — PERSISTÊNCIA E ENCAMINHAMENTO` em `adk/src/agents/markdown_specialist/prompt.py` para instruir o LLM a:
1. Gerar a versão final do relatório em texto plano dentro do thoughtSignature/raciocínio.
2. Chamar `io_agent` em UMA chamada apenas com `request="Salve o arquivo <nome>.md ..."` + conteúdo, mas **com instrução explícita "se o conteúdo for maior que 4000 caracteres, divida em N salvamentos sequenciais usando append"** — exige que o `io_agent` exponha um `append_artifact` ou aceite múltiplos SAVE com merge.

**Alternativa B — bypass do io_agent intermediário** (mais simples; recomendada para o fix v1)
Adicionar `save_artifact` (de `shared.tools.design_filesystem`) DIRETAMENTE ao `tools=[...]` do `markdown_specialist` (e do `mermaid_specialist` e `design_architect`), e ajustar o prompt para chamar `save_artifact` diretamente em vez de proxiar via `io_agent`. Isso elimina um salto LLM (e portanto metade da pressão de output token). O `io_agent` permanece útil para leituras (ele ainda lê o template, análise e diagramas via `read_file`).

Edits concretos para Alternativa B:

1. `adk/src/agents/markdown_specialist/agent.py`:
   ```python
   from shared.tools.design_filesystem import save_artifact, list_staging_files
   ...
   tools=[
       AgentTool(agent=io_agent),  # mantém para READS
       save_artifact,                # NOVO — escrita direta
       list_staging_files,           # NOVO — listagem direta
       current_date,
   ],
   ```

2. `adk/src/agents/markdown_specialist/prompt.py` PASSO 4 reescrito: substituir "Acione o Agente IO via AgentTool com a mensagem: 'Salve o arquivo <nome>.md ...'" por "Chame `save_artifact(filename='<nome>.md', conteudo='...')` diretamente".

3. Mesmo padrão aplicado a `design_architect` e `mermaid_specialist` (que sofrem do mesmo problema potencial, embora não tenham sido o ponto de falha hoje — provavelmente porque a análise e o .mmd são significativamente menores que o relatório.md completo).

**Adicional — verificação pré-merge:** após a alteração, rodar o mesmo prompt diagnóstico de healthcheck e confirmar que `temp/staging/relatorio_HU-001_2026-05-17.md` é criado e o pipeline retorna status `"concluido"`.

**Risco residual conhecido:** Mesmo após o fix, relatórios muito grandes (>50 HUs) podem voltar a esgotar o output budget. Solução definitiva exige streaming de SAVE incremental — fora do escopo de Task 9.

## Apêndice — Comandos de reprodução

```bash
bash .claude/skills/ai4es-e2e/scripts/start-server.sh
echo "Construa um sistema simples de healthcheck FastAPI: HU-001 - como Admin, quero ver /healthcheck retornar status 200 com body {'status':'ok'}." \
  | bash .claude/skills/ai4es-e2e/scripts/run-agent.sh workflow_design_pipeline > /tmp/design-debug.json 2>&1
cat /tmp/design-debug.json | python3 .claude/skills/ai4es-e2e/scripts/pretty-response.py
ls adk/temp/staging/   # confirma ausência de relatorio_*.md
bash .claude/skills/ai4es-e2e/scripts/stop-server.sh
```
