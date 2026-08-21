# Catálogo de Tools — Time 2 (Design)

**Última atualização:** 29/07/2026

Este documento formaliza, em um único lugar, **todas as tools usadas pelos agentes do Time 2** — o que cada uma faz, quem a chama, quais parâmetros espera e quais convenções (aliases de pasta, formato de retorno, mocks) já estão fixadas no código hoje.

Não substitui `README.md` (visão funcional do pipeline) nem `decisoes-formalizadas-e-pendencias.md` (decisões de produto/processo). Este documento é a referência técnica de **interface** — a de que qualquer pessoa do time (ou de outro time, integrando com o design) precisa para saber "qual tool chamo para fazer X, e o que ela devolve".

Fonte: código em `shared/tools/design_*.py`, `shared/tools/design_validate/`, e os `agent.py` de cada agente de design (import real das tools, não descrição de prompt).

---

## 1. Visão geral — quem usa o quê

| Tool | Módulo | `design_architect` | `mermaid_specialist` | `markdown_specialist` | `prototyping_specialist` | `validator` | `io_agent` | `pipeline_controller` |
| --- | --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| `current_date` | `design_date.py` | ✅ | ✅ | ✅ | ✅ | — | ✅ | — |
| `save_artifact` | `design_filesystem.py` | ✅ | ✅ | ✅ | — | — | ✅ | — |
| `append_artifact` | `design_filesystem.py` | — | ✅ | ✅ | — | — | ✅ | — |
| `append_architect_section` | `design_filesystem.py` | ✅ | — | — | — | — | — | — |
| `patch_section` | `design_filesystem.py` | ✅ | ✅ | ✅ | — | — | ✅ | — |
| `read_file` | `design_filesystem.py` | — | — | ✅ | — | — | ✅ | — |
| `read_analysis_sections` | `design_filesystem.py` | — | — | — | — | — | ✅ | — |
| `read_multiple_files` | `design_filesystem.py` | — | — | ✅ | — | — | ✅ | — |
| `list_design_files` | `design_filesystem.py` | ✅ | ✅ | ✅ | — | — | ✅ | — |
| `validate_analysis_sections` | `design_filesystem.py` | ✅ | — | — | — | — | ✅ | — |
| `check_active_blocks` | `design_filesystem.py` | — | — | ✅ | — | — | ✅ | — |
| `clear_design_folder` | `design_filesystem.py` | — | — | — | — | — | ✅ | — |
| `promote_artifact` | `design_filesystem.py` | — | — | — | — | — | ✅ | — |
| `check_lock` / `release_lock` / `list_versions` (mocks) | `design_filesystem.py` | — | — | — | — | — | ✅ | — |
| `validate_artifact` | `design_validate/gatekeeper_tool.py` | — | — | — | — | ✅ | — | — |
| `aguardar_resolucao_doubt` | `design_hitl_tool.py` | — | — | — | — | — | — | ✅ |
| `aguardar_decisao_validacao` | `design_hitl_tool.py` | — | — | — | — | ✅ | — | — |
| `AgentTool(io_agent)` | — | ✅ | ✅ | — | ✅ | ✅ | — | ✅ |
| `AgentTool(mermaid_specialist)` / `AgentTool(markdown_specialist)` | — | — | — | — | — | ✅ (chamada cruzada de correção) | — | — |

Notas de leitura da tabela:

- `markdown_specialist` recebe as tools de leitura **diretas** de `design_filesystem.py` (`read_file`, `read_multiple_files`, `check_active_blocks`) em vez de proxiar tudo pelo `io_agent` via `AgentTool` — é o único especialista de conteúdo com esse acesso direto de leitura, além do `io_agent` em si.
- `design_architect` e `mermaid_specialist` persistem **diretamente** via `save_artifact`/`append_architect_section`/`patch_section` — só usam `AgentTool(io_agent)` para leitura auxiliar, nunca para escrita.
- `prototyping_specialist` é o único especialista de conteúdo sem nenhum acesso direto a `design_filesystem.py` — depende inteiramente de `AgentTool(io_agent)` para qualquer I/O.
- `validator` é o único agente com acesso cruzado a outros dois especialistas (`mermaid_specialist`, `markdown_specialist`) como `AgentTool`, usado para pedir correção nas até 2 tentativas antes de escalar via `aguardar_decisao_validacao`.
- `design_orchestrator` não aparece na tabela porque não tem tools de filesystem próprias — expõe `design_pipeline` e cada especialista individualmente como `AgentTool`.

Além disso, **todo** agente criado por `create_se_agent()` (todos os listados acima) recebe também, sem opt-out, a tool genérica `tool_ask_clarification_adk` injetada por `shared/agent_factory.py` — não é uma tool do design, é infraestrutura compartilhada (ver `decisoes-formalizadas-e-pendencias.md`, seção 3)

---

## 2. Convenções que atravessam todas as tools de `design_filesystem.py`

Estas convenções valem para toda tool desta seção, salvo indicação contrária:

- **Assinatura padrão:** `(..., caller: str | None = "unknown", base_dir: str | None = None)`. `caller` identifica o agente chamador para fins de log (`design_logger.py`); `base_dir` permite escopar a chamada a um workspace isolado — sem ele, usa-se a raiz fixa e compartilhada `DESIGN_DIR` (comportamento histórico, o mesmo para todos os agentes do pipeline).
- **Resolução de caminho por alias de pasta:** qualquer argumento de nome de arquivo aceita um prefixo de alias simbólico (`ANALYSIS/`, `DIAGRAMS/`, `PROTOTYPE/`, `REPORT/`, `DOUBT/`, `TEMPLATE/` — case-insensitive, com ou sem sufixo `_dir`/`_folder`). Sem alias, a busca de leitura percorre automaticamente `ANALYSIS → DIAGRAMS → PROTOTYPE`; a escrita sem alias decide o destino pela extensão (`.html`/`global.css` → `PROTOTYPE`, `.mmd` → `DIAGRAMS`, demais → `ANALYSIS`).
- **`validation` não é um alias de escrita hoje.** `design/validation/` é tratado como pasta de primeira classe por `check_active_blocks` e pelo Manifesto de Fase (leitura), mas `_folder_aliases()` não tem entrada para ela — nenhuma tool consegue gravar ali (lacuna já registrada em `decisoes-formalizadas-e-pendencias.md`).
- **Backups automáticos:** `save_artifact` cria backup (`_backup_*`) antes de sobrescrever um arquivo existente; `append_*` e `patch_section` não criam backup — a documentação de cada tool abaixo marca essa diferença explicitamente.
- **Retorno em dict estruturado**, nunca exceção "crua" para o agente: as tools devolvem um dicionário (tipicamente com uma chave de sucesso/erro e uma mensagem legível) para que o LLM chamador possa decidir o próximo passo sem precisar interpretar um traceback.

---

## 3. Tools de leitura

### `read_file(filepath, caller="unknown", base_dir=None)`
Lê e retorna o conteúdo completo de um arquivo. Aceita alias de pasta; sem alias, busca em `ANALYSIS → DIAGRAMS → PROTOTYPE`.
**Usada por:** `markdown_specialist`, `io_agent`.

### `read_analysis_sections(filepath, sections, caller="unknown", base_dir=None)`
Lê apenas as seções indicadas (por número) de um arquivo `analise_tecnica_*.md`, sem trazer o arquivo inteiro — pensada para reduzir o contexto repassado a especialistas que só precisam de parte da análise (ex.: `mermaid_specialist` só precisa da seção de componentes/arquitetura).
**Usada por:** `io_agent`.

### `read_multiple_files(filepaths, caller="unknown", base_dir=None)`
Lê vários arquivos em uma única chamada; arquivos ausentes ou inacessíveis são reportados individualmente, sem interromper a leitura dos demais.
**Usada por:** `markdown_specialist`, `io_agent`.

### `list_design_files(filetype="", folder="", caller="unknown", base_dir=None)`
Lista os arquivos presentes numa pasta do design (ou em todas, se `folder` vazio). Ignora automaticamente backups (`_backup_*`) e o arquivo de log.
**Uso central:** é a tool que o `pipeline_controller` consulta para confirmar que `analise_tecnica_*.md` foi de fato persistido antes de avançar de etapa.
**Usada por:** `design_architect`, `mermaid_specialist`, `markdown_specialist`, `io_agent`.

### `validate_analysis_sections(filename, caller="unknown", base_dir=None)`
Verifica **deterministicamente** (não por autoavaliação do LLM) se um `analise_tecnica_*.md` contém as 8 seções obrigatórias, cada uma delimitada por `<<<FIM_SECAO>>>` e com conteúdo além do título. Retorna quais seções estão ausentes (`missing_sections`) ou vazias (`empty_sections`). É a verificação que substitui qualquer "li o arquivo e achei que estava completo" — já pegou em produção um caso de arquivo com só a Seção 1.
**Usada por:** `design_architect` (autoconfirmação antes de reportar conclusão), `io_agent` (verificação estrutural pedida pelo `pipeline_controller` nas Etapas 2 e 4 do pipeline).

### `check_active_blocks(caller="unknown", base_dir=None)`
Verifica se há `Doubt_Artifact` com status bloqueante em qualquer uma das pastas varridas (`doubts/`, `analysis/`, `diagrams/`, `prototype/`, `report/`, `validation/`). Reconhece dois marcadores: `**Status:** Bloqueado` e o cabeçalho `EXECUÇÃO PAUSADA`. É o elo entre "algo travou" e o pipeline realmente pausar — o `pipeline_controller` chama isso antes de liberar cada etapa, e o Manifesto de Fase usa o mesmo marcador para derivar `bloqueante` em `ManifestDoubt`, mantendo as duas fontes de verdade consistentes.
**Usada por:** `markdown_specialist`, `io_agent`.

---

## 4. Tools de escrita

### `save_artifact(filename, content, caller="unknown", base_dir=None)`
Salva (sobrescrevendo, com backup automático se o arquivo já existir) em uma das pastas do design. Sem alias, o destino é decidido pela extensão.
**Usada por:** `design_architect`, `mermaid_specialist`, `markdown_specialist`, `io_agent`.

### `append_artifact(filename, content, caller="unknown", base_dir=None)`
Adiciona conteúdo ao final de um arquivo existente sem apagar o que já está lá; cria o arquivo se ele não existir (mesmo comportamento de destino que `save_artifact`).
**Sem backup.**
**Usada por:** `mermaid_specialist`, `markdown_specialist`, `io_agent`.

### `append_architect_section(filename, content, caller="design_architect", base_dir=None)`
Variante de `append_artifact` **exclusiva do `design_architect`** (o próprio `caller` já vem com esse default). Existe para que o arquiteto persista a análise técnica seção por seção, intercalando raciocínio e gravação, em vez de produzir tudo de uma vez e arriscar truncamento em lotes grandes de HUs.
**Sem backup** — para substituir o arquivo inteiro, usar `save_artifact`; para corrigir uma seção já escrita, usar `patch_section`.
**Usada por:** `design_architect` (exclusivo).

### `patch_section(filename, section_id, new_content, caller="unknown", base_dir=None)`
Substitui uma seção específica de um Markdown já existente, sem tocar nas demais — identifica a seção por marcador de ID ou de título (primeiro match vence). É a ferramenta de correção cirúrgica, usada tipicamente em resposta a um apontamento do `validator`.
**Usada por:** `design_architect`, `mermaid_specialist`, `markdown_specialist`, `io_agent`.

### `promote_artifact(filename, caller="unknown", base_dir=None)`
Copia um relatório aprovado para `REPORT_DIR` (diretório oficial permanente). Só deve ser usada depois que o status do relatório tiver sido alterado explicitamente para "Aprovado" — a própria tool bloqueia a promoção se ainda encontrar o marcador `**Status:** Em análise` no conteúdo.
**Usada por:** `io_agent`.

### `clear_design_folder(caller="unknown", base_dir=None)`
Remove todos os arquivos de `design/` e subpastas (preserva a estrutura de diretórios). **Irreversível — sem backup.** Uso exclusivo no início de um novo ciclo do pipeline (Etapa 1 do `pipeline_controller`).
**Usada por:** `io_agent`.

---

## 5. Tools de mock (ainda não implementadas de fato)

### `check_lock(filepath)` / `release_lock(filepath)` / `list_versions(filepath)`
Assinatura simplificada (`filepath` apenas — sem `caller`/`base_dir`, diferente de todo o resto do módulo). Hoje são **mocks**: não implementam de fato controle de concorrência nem versionamento de artefatos. Estão presentes no `io_agent` para reservar o ponto de extensão futuro, mas nenhum agente depende do resultado real delas hoje.
**Usadas por:** `io_agent` (mock).

---

## 6. Tools de validação determinística (Gatekeeper)

### `validate_artifact(content, format)`
Módulo: `shared/tools/design_validate/gatekeeper_tool.py` (adapta `ArtifactGatekeeper` como `FunctionTool`).

Valida deterministicamente um artefato `.mmd` ou `.md` — parsing e gramática, **sem julgamento de LLM**. Retorna:

```python
{
    "valid": bool,
    "error_type": str | None,      # ex.: "INVALID_GRAMMAR"
    "error_message": str | None,
    "line_number": int | None,
    "suggested_fix": str | None,
}
```

`valid=False` deve ser tratado pelo agente chamador como veredito absoluto — não há espaço para o LLM "interpretar" um artefato reprovado como aceitável. Implementa a Camada 1 (sintática) do `validator`; a Camada 2 (semântica — checklist de cabeçalho, convenção de nome, seções obrigatórias, consistência) continua sendo responsabilidade do próprio agente `validator`, sem tool dedicada.

**Usada por:** `validator` (exclusivo).

Por convenção de prompt, o nome literal `validate_artifact` não aparece no texto do prompt do `validator` — é referido como "validação sintática determinística".

---

## 7. Tools de pausa real (HITL)

Módulo: `shared/tools/design_hitl_tool.py`. Ambas são stubs assíncronos que sempre retornam `None`; empacotadas como `LongRunningFunctionTool`, isso faz o ADK emitir um `function_call` sem auto-resposta, devolvendo controle ao chamador — o `orchestrator` genérico já sabe pausar/retomar qualquer pipeline que emita esse tipo de `function_call`, em qualquer profundidade de aninhamento, sem nenhuma mudança necessária nele.

### `aguardar_resolucao_doubt(checkpoint_id, approval_question, allowed_decisions, pause_reason=None)`
Pausa o `design_pipeline` quando `check_active_blocks` reporta bloqueio ativo.
`allowed_decisions` fechado em `["retomar", "cancelar"]`. Chamada
obrigatoriamente **antes** de qualquer texto de bloqueio (nunca só narrado).
**Usada por:** `pipeline_controller` (Etapa 3).

### `aguardar_decisao_validacao(checkpoint_id, approval_question, allowed_decisions, pause_reason=None)`
Pausa quando o `validator` esgota as 2 tentativas de correção (sintática ou semântica). `allowed_decisions` fechado em `["resolvido", "abandonar_artefato"]` — **deliberadamente sem** opção de "prosseguir mesmo assim": a IA nunca deve autocorrigir além do limite nem deixar o erro passar silenciosamente. Vocabulário alinhado à convenção canônica de `Doubt_Artifact` (Bloqueado/Resolvido) do design.
**Usada por:** `validator`.

Ambas seguem o mesmo padrão já usado pelo Time 3/QA (`shared/tools/hitl_tool.py`), mas com tool e vocabulário próprios — não há reaproveitamento direto da instância entre times.

---

## 8. Utilitário de data

### `current_date()`
Módulo: `shared/tools/design_date.py`. Retorna a data atual em ISO (`YYYY-MM-DD`), sem hora. Uso: timestamping de operações, logs de observabilidade, versionamento de artefatos.
**Usada por:** `design_architect`, `mermaid_specialist`, `markdown_specialist`, `prototyping_specialist`, `io_agent`.

---

## 9. Logging

### `design_logger.py`
Não expõe uma tool chamável pelo LLM — é infraestrutura interna usada pelas tools de `design_filesystem.py` para registrar cada operação (`_write`, `_make_string`) no log de operações de I/O do design (`design/io_operations.log`, ignorado por `list_design_files` e pelo Manifesto de Fase).

---

## 10. Pendências relacionadas a este catálogo

- **Alias de escrita para `validation`** ainda não existe em `_folder_aliases()` — nenhuma tool listada aqui grava em `design/validation/` hoje, o que limita o Manifesto de Fase a nunca alcançar `status="ok"` pela via automática (ver seção 2 acima e `decisoes-formalizadas-e-pendencias.md`).
- **`tool_ask_clarification_adk`** (injetada globalmente por `shared/agent_factory.py`, fora do escopo deste catálogo porque não é uma tool do design) continua coexistindo, sem opt-in/opt-out, com as tools de pausa real listadas na seção 7.
- **Mocks da seção 5** (`check_lock`/`release_lock`/`list_versions`) não têm data prevista de implementação real; nenhum agente depende do resultado delas hoje, então não bloqueiam nenhum fluxo atual.

---

## Referências

- `shared/tools/design_filesystem.py` — núcleo de I/O.
- `shared/tools/design_date.py` — utilitário de data.
- `shared/tools/design_hitl_tool.py` — tools de pausa real (HITL).
- `shared/tools/design_logger.py` — logging de operações.
- `shared/tools/design_validate/gatekeeper_tool.py` (+ `artifact_gatekeeper.py`,
  `contentValidator.py`) — validação sintática determinística (Gatekeeper).
- `src/agents/*/agent.py` — declaração real de tools por agente (fonte usada para montar a tabela da seção 1).
- `decisoes-formalizadas-e-pendencias.md` — decisões de produto/processo.
