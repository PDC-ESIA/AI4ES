# Relatório — Camada de Feedforward para o Agente de Codificação

> **Time 4 — Codificação** · Pipeline analisado: `workflow_coding_review` (`coding_review_pipeline`)
> **Estado do código de referência:** branch `develop` @ `4c9d482` (pós-merge do PR #348; inclui o **PR #324** — harness de execução + `implementation_validator` — e a reorganização das tools de codificação em `shared/tools/coding_tools/`)
> **Referência conceitual primária:** Böckeler, B. *"Harness Engineering for Coding Agents"*. martinfowler.com, 02/04/2026. <https://martinfowler.com/articles/harness-engineering.html>

---

## 1. Objetivo e escopo

Projetar e validar uma **camada de Feedforward** para o agente de codificação: um componente responsável por preparar e disponibilizar, **antes da execução**, o contexto necessário para maximizar a qualidade da primeira resposta e reduzir ciclos de retrabalho.

O relatório cobre: (i) o levantamento das fontes de contexto relevantes, (ii) o mapeamento das técnicas de construção de pipelines de Feedforward, (iii) a avaliação de ferramentas open source, (iv) a arquitetura proposta para a camada, (v) a análise de viabilidade, (vi) os gaps identificados e (vii) as recomendações de adoção estagiadas.

**Fora de escopo:** refatoração do orquestrador, remoção da trava de stack do pipeline e automação da destilação de lições. Cada um é registrado como recomendação com fase própria (§12).

### 1.1 Estado de implementação

O trabalho ocorre em duas frentes, com maturidades diferentes. Esta seção declara o estado de cada uma para que o leitor não confunda o que já roda em produção com o que está especificado.

| Componente | Estado | Onde |
|---|---|---|
| Etapa 0 "Plano-Contrato" no `cr_coder` (feedforward de processo) | ✅ **Implementado** (PR #340) | `adk/src/agents/workflow_coding_review/cr_coder.py` |
| Leitura do contrato em disco pelo coder (`tool_ler_workspace`/`tool_listar_workspace`) | ✅ **Implementado** (PR #340) | idem |
| Análise estática pré-LLM no reviewer (Ruff + Bandit) | ✅ **Implementado** (PR #318) | `adk/shared/review/capability.py` |
| Harness de execução determinístico — 9 estágios, `ExecutionReport` estruturado | ✅ **Implementado** (PR #324) | `adk/shared/tools/coding_tools/harness_execucao.py` |
| Veredito determinístico em 2 camadas (`implementation_validator`) | ✅ **Implementado** (PR #324) | `adk/src/agents/implementation_validator/` |
| `ErrorReport` determinístico devolvido ao coder | ✅ **Implementado** (PR #324) | `cr_executor.py::montar_error_report` |
| Camada de provisionamento de contexto (`cr_feedforward` + `knowledge/`) | 🚧 **Implementada, entregue neste PR** (§8, §10) | `workflow_coding_review/cr_feedforward.py` + `adk/knowledge/` |
| Gate estático de dependências pré-build | 🚧 **Implementado, entregue neste PR** (§8.3, §10) | `coding_tools/verificacao_dependencias.py` + estágio `verificacao_estatica` no harness |
| Protocolo de validação quantitativa | 📋 **Especificado** (§11) — execução pendente | — |

> Entre o PR #340 e a redação final deste relatório entraram 8 PRs que reconstruíram o executor. Sobre o impacto disso na durabilidade das referências de código, ver §13.

> **⚠️ Leia isto antes do resto — a análise está ancorada em `develop` @ `4c9d482`.** Os dois componentes marcados 🚧 acima **já estão implementados** na branch `feature/303-camada-feedforward` e chegam ao `develop` **neste mesmo PR**, junto deste documento — a entrega da issue #303 é única, com todos os commits:
>
> - **Gate estático do §8.3** — commit `983e114`, 30 testes unitários e uma execução real ponta a ponta.
> - **Camada de provisionamento do §8.2** — `cr_feedforward` (`BaseAgent` sem LLM) + a KB em `adk/knowledge/`, com 36 testes. O bloco `ERROS COMUNS` foi migrado do prompt do `cr_coder` para a KB no mesmo PR, então o conhecimento de convenções deixou de viver em string Python (§7/G1).
>
> Onde o texto descreve esses dois como ausentes — "nenhum estágio faz verificação estática" (§7/G4), conhecimento "hardcoded em string Python" (§7/G1) —, leia **"não existia em `4c9d482`, a base da análise"**. A única linha 📋 que continua sem código é o **protocolo de validação quantitativa** (§11): os 15 runs ainda não foram executados, e nenhuma afirmação de ganho é feita aqui (§13).

---

## 2. Glossário

- **Feedforward (guides):** mecanismos que antecipam o comportamento do agente e o direcionam **antes** de ele agir. Aumentam a probabilidade de um bom resultado na primeira tentativa.
- **Feedback (sensors):** mecanismos que observam **depois** da ação e permitem auto-correção. São mais potentes quando produzem sinais otimizados para consumo por LLM.
- **Harness:** o conjunto de guides + sensors que envolve o agente. *Harness engineering* é a prática contínua de iterar sobre esse conjunto.
- **Context Pack:** artefato único, montado deterministicamente, que consolida as fontes de contexto e é injetado no prompt do agente antes da execução.
- **Enforcement:** compilação de uma regra/lição em verificação executável que bloqueia a conclusão da tarefa, em oposição à mesma regra expressa como texto no prompt.
- **Memória experiencial:** store de lições derivadas de execuções passadas, recuperado em execuções futuras. É a fonte de contexto *cross-run* do feedforward.
- **Granularidade dupla:** representação simultânea da lição em dois níveis — estratégia abstrata (transferível) e regra acionada por evento (específica).
- **Texto passivo:** instrução presente no contexto do agente mas sem mecanismo que force conformidade. Termo tomado do ContextCov.
- **Oráculo executável:** verificador automático que decide objetivamente se uma tentativa passou. No pipeline, são o harness de execução (coleta a evidência) e o `implementation_validator` (emite o veredito).
- **Long-context baseline:** empacotar todo o histórico/lições disponíveis no contexto, sem retrieval seletivo. É o baseline de controle obrigatório em avaliações de memória.

---

## 3. Fundamentação conceitual

### 3.1 A dicotomia guides/sensors

Böckeler organiza o harness de um agente de codificação em dois eixos complementares. **Feedforward** antecipa e direciona antes da ação; **feedback** observa e corrige depois. O argumento central é que os dois isolados falham de formas simétricas: um harness só-de-feedback produz *"an agent that keeps repeating the same mistakes"*, e um harness só-de-feedforward produz *"an agent that encodes rules but never finds out whether they worked"*.

O artigo nomeia como elementos de feedforward: arquivos de convenção (`AGENTS.md`), documentação de arquitetura, how-to guides com scripts de bootstrap, documentação de referência/API, especificações funcionais, integração LSP e servidores MCP. Como técnicas: *fitness functions*, *approved fixtures*, *service templates*, **harness templates** (bundles de guides e sensors por stack) e a **Lei de Ashby** — travar a topologia reduz a variedade que o agente precisa administrar, e isso **é** feedforward.

### 3.2 A lacuna memória ↔ enforcement

A literatura recente de memória experiencial para agentes acrescenta um resultado que reorganiza o desenho da camada: **tornar a lição visível não força conformidade**.

- **TRACE** mede o Mem0 deixando **57,5%** das checagens de preferência aplicáveis violadas *mesmo com a memória disponível no contexto*. Compilar a mesma lição em verificação executável reduz a violação de 100,0% para **2,0%** em tarefas out-of-distribution.
- **ContextCov** parte do diagnóstico de que instruções em arquivo de convenção *"remain passive text rather than executable specifications"* e as compila em checagens executáveis (AST via Tree-sitter, shims de shell, validadores de arquitetura). Em SWE-bench Lite (12 repositórios, 300 tasks), a conformidade final sobe para **88,3%**, contra 67,0% do agente sem feedback e **50,3% de um crítico LLM** — que fica **pior que não ter crítico nenhum**.
- **Anatomy of Agentic Memory** (survey) aponta que as métricas de avaliação usuais estão desalinhadas com utilidade semântica, que o desempenho varia fortemente com o backbone e que os custos de latência/throughput são rotineiramente ignorados. Levanta ainda o risco de *context saturation*: muitos benchmarks de memória cabem inteiros na janela de contexto atual e, portanto, não exigem memória para serem resolvidos.

**Implicação para o desenho desta camada:** separar (i) o store de conhecimento, (ii) a montagem/recuperação e (iii) um **gate de enforcement** que verifica executavelmente as regras que o guia enuncia. O terceiro item não é um detalhe de implementação — é o que diferencia um guia que funciona de um guia que o agente lê e ignora.

> **Nota de taxonomia.** Um gate que executa é, no vocabulário de Böckeler, um *sensor*. Não o classificamos como feedforward. O que a evidência acima estabelece é uma relação de dependência: **o feedforward só tem força vinculante quando pareado com um sensor que verifique a mesma regra**. Guia e gate são peças distintas do mesmo harness, e este relatório os trata assim deliberadamente, em vez de borrar a distinção.

### 3.3 Evidência interna: o pipeline convergiu para o mesmo padrão

O PR #324 é uma confirmação independente da tese do §3.2, produzida dentro do próprio projeto e sem referência a essa literatura.

O `implementation_validator` codifica a política de veredito em `montar_veredito()` — **determinística, em Python, fora do alcance do LLM**. A **Camada 1** estabelece que execução precede julgamento: se o `overall_status` do `ExecutionReport` for `erro` ou `falha`, o veredito é `reprovado` imediatamente, todos os critérios viram `inconclusivo` e a Camada 2 nem roda. A **Camada 2** agrega de forma conservadora — `aprovado` só se *todos* os critérios forem `atendido`, e lista vazia reprova (evita aprovação vácua por `all([]) is True`).

Isso é exatamente "compilar a regra em verificação executável que bloqueia a conclusão", em vez de instruir o LLM a não aprovar código quebrado. O mesmo raciocínio aparece no `ErrorReport`: o `after_agent_callback` do `cr_executor` **substitui a prosa do LLM** por um relatório montado deterministicamente a partir do veredito e do `ExecutionReport` — e o docstring é explícito sobre o limite do escopo: *"o ErrorReport diz o QUE falhou e mostra o material bruto do POR QUÊ. Ele NÃO prescreve correção"*.

A consequência para este relatório é uma inversão do argumento: a recomendação do §12.2 (enforcement antes de memória) não pede ao time que adote um padrão novo — pede que **estenda um padrão que ele já provou funcionar** a uma classe de falha que continua sem cobertura (§7, G4).

---

## 4. Fontes de contexto relevantes (inventário)

O pipeline **não parte do zero**: já existe um proto-harness. A tabela classifica cada mecanismo presente hoje na taxonomia do §3.

| Fonte / mecanismo | Onde no código | Classificação | Natureza |
|---|---|---|---|
| Tasks contextualizadas — `macro_context` + `contract{inputs, outputs, interfaces}` | `cr_context_engineer.py`; schema em `src/agents/context_engineer/schemas.py` | Feedforward | Dinâmico (LLM, por run) |
| Contrato lido do disco pelo coder na Etapa 0 | `cr_coder.py` §`ETAPA 0`; `tool_ler_workspace("coder/tasks/…")` | Feedforward | Dinâmico (por run) |
| `PLAN.md` — manifesto de arquivos, plano de dependências, checklist de interfaces | `cr_coder.py` §`ETAPA 0` | Feedforward auto-gerado | Dinâmico (intra-run) |
| Prompt estático: modo de operação, workspace, entrega Docker obrigatória, completude | `cr_coder.py:89–283` | Feedforward | Estático (hardcoded em Python) |
| Seção `# ERROS COMUNS — EVITE A TODO CUSTO` | `cr_coder.py:286–368` **em `4c9d482`** | Feedback destilado manualmente em feedforward | Estático (hardcoded) — 🚧 **migrado para `adk/knowledge/` neste PR**, deixando de ser hardcoded (§12.3) |
| Contexto das fases anteriores (requisitos, design) | `_build_input` em `orchestrator/_helpers.py:117–129` | Feedforward degradado | Dinâmico, **truncado em 8.000 chars por fase** |
| Harness de execução — 9 estágios determinísticos (preparação → implantação → logs → inicialização → logs → testes → validações → consolidação → relatório) | `shared/tools/coding_tools/harness_execucao.py` (988 linhas) | Feedback (sensor) | **Oráculo executável**; produz `ExecutionReport` (`<task_id>.report.json`) e nunca emite veredito |
| Veredito determinístico em 2 camadas | `implementation_validator/agent.py::montar_veredito` | **Enforcement** | Camada 1: execução falha → reprova sem julgar. Camada 2: agregação conservadora |
| `ErrorReport` — o que falhou + evidência bruta, sem prescrever correção | `cr_executor.py::montar_error_report` (`after_agent_callback`) | Feedback otimizado para LLM | Substitui a prosa do LLM na saída do turno |
| `{execution_result?}` → modo correção no loop | `cr_coder.py` §`MODO DE OPERAÇÃO` + `output_key="execution_result"` | Ciclo feedback→correção | Intra-run; hoje transporta o JSON do `ErrorReport` |
| Análise estática Ruff + Bandit | `shared/review/capability.py`, via `_inject_static_findings` | Feedback (sensor) | Pós-execução, sem poder de bloqueio |

### 4.1 Fontes ausentes

Fontes que a literatura identifica como relevantes e que **não existem** no pipeline:

1. **Base de conhecimento versionada** — convenções, regras de consistência e restrições de stack como artefatos revisáveis por PR, e não como string Python.
2. **Memória cross-run** — lições de execuções anteriores. `init_workspace()` apaga e recria o `workspace_output/` a cada fresh run (`orchestrator/agent.py`, `_handle_fresh_run`), destruindo inclusive os `ExecutionReport` (`<task_id>.report.json`) do run anterior.
3. **Exemplares (few-shot)** — apps que passaram no executor nunca são reaproveitados como referência.
4. **Allowlist de dependências** — o `requirements.txt` é gerado do zero pelo LLM a cada run.
5. **Artefatos upstream íntegros** — os arquivos de `requirements/` e `design/` ficam em disco e não são lidos por nenhum agente do pipeline de codificação.

### 4.2 Como o contexto efetivamente chega ao coder

```
user_text (verbatim, nunca truncado)
  └─► outputs upstream truncados em 8.000 chars/fase  ─┐
                                                       ├─► sessão do coding_review_pipeline
  tasks JSON do cr_context_engineer (histórico) ───────┘         │
                                                                 ▼
  instrução estática do cr_coder + {execution_result?}  ──► LLM do coder
                                                                 │
  contrato relido do disco na Etapa 0 (tool_ler_workspace) ◄─────┘
```

Dois fatos operacionais relevantes para o desenho:

- **`{execution_result?}` prova que injeção via template de estado funciona.** É o ponto de acoplamento natural para um `{context_pack?}`.
- **`macro_context` não é persistido em disco**, mas **está em `state["tasks"]`** (`cr_context_engineer.py` grava com `output_schema=TasksOutput`). Um componente determinístico posterior ao context engineer consegue ler `tech_stack` sem LLM e sem alterar o CE.

---

## 5. Levantamento das técnicas

### 5.1 Técnicas de montagem e provisionamento de contexto

| Técnica | Descrição | Aderência ao AI4ES |
|---|---|---|
| **Context pack estruturado** | Consolidar as fontes num artefato único, com política de crescimento explícita, injetado antes da execução | **Alta** — já parcialmente presente via Context Windows do CE |
| **Convention files** (`AGENTS.md`, `CLAUDE.md`) | Convenções como artefato versionado, revisável por PR | **Alta** — ataca diretamente o conhecimento hardcoded |
| **Repo-map** (tree-sitter + ranking) | Mapa estrutural do repositório para orientar navegação | **Baixa hoje** — a geração é greenfield; relevante só se o coder evoluir para brownfield |
| **RAG / retrieval seletivo** | Recuperar do store apenas o relevante para a task | **Baixa na PoC** — o store desta camada é curado e pequeno; §5.4 põe o ônus da prova no retrieval, e §12.4 registra onde ele se justifica |
| **Few-shot dinâmico** | Injetar exemplares aprovados como referência | **Média** — depende de política de curadoria; fase 3 |
| **Harness templates** | Bundle de guides + sensors por stack tecnológica | **Alta** — é a forma correta de indexar a KB por stack |
| **Redução de variedade (Ashby)** | Travar a topologia reduz o espaço que o agente precisa administrar | **Alta** — o pipeline já faz isso (porta 8000, entrega Docker obrigatória) |

### 5.2 Técnicas de memória experiencial

O eixo *cross-run*. A evidência abaixo vem de estudos com backbones, scaffolds e benchmarks distintos — **os números não são comparáveis entre si**, apenas dentro de cada estudo.

**Granularidade.** O achado mais replicado (Memp, CODESKILL, ExpeRepair, SWE-Exp) é que **granularidade dupla vence granularidade única**:

- *Trajetória bruta*: pior generalização; útil só para tarefas quase idênticas.
- *Script/estratégia abstrata*: melhor transferência, mas sozinha perde detalhe acionável (*brevity bias*).
- *Combinação*: ótima. O CODESKILL usa skills de nível de tarefa (estratégia) **+ skills acionadas por evento** (trigger = falha de comando, mensagem de erro, padrão de teste).

Para o problema concreto do AI4ES — *o agente repete os mesmos erros* — a granularidade **acionada-por-evento-de-erro** (trigger = assinatura do erro; corpo = instrução de correção) é a mais direta.

**Política de escrita/update.** Ordenadas da pior para a melhor:

1. *Vanilla add* — acumular tudo. É a prática corrente que o Memp critica, embora nos experimentos dele **as três políticas melhorem** o desempenho.
2. *Filtragem por validação executável* — guardar só o que passou no oráculo. Melhora robusta, e é o modo privilegiado em código, onde o oráculo existe.
3. *Reflexão / revisão in-place* — revisar em vez de acumular. Identificada pelo Memp como a mais eficaz.
4. *Delta incremental* — o ACE demonstra que a reescrita completa do store causa *context collapse* (a reescrita iterativa erode detalhes) e *brevity bias*; updates delta preservam conhecimento e escalam.

Complementarmente: deduplicação, deprecação e consolidação são necessárias para manter o store estável. O GovMem acrescenta uma restrição forte de governança — na adjudicação humana de 133 candidatos reais de agentes de código, **nenhum** foi considerado seguro para promoção automática; todos os positivos do gate de verificação foram rejeitados como boilerplate ou artefato de ferramenta compartilhada.

**Retrieval.**

- Existe um **k ótimo com curva de sino**: aumentar *k* ajuda até um platô e depois prejudica.
- **Similaridade semântica (tipo de issue, padrões de erro) supera similaridade estrutural** (sobreposição superficial de tokens do patch) — recomendação de design do SWE-Bench-CL, derivada da baixa similaridade estrutural medida entre tasks (Jaccard médio 0,111).
- **Retrieval sem filtro discriminante degrada.** No CTIM-Rover, injetar todos os itens de memória sem filtro de relevância custou 11 pontos ante a baseline; os próprios autores apontam retrieval por embedding como o conserto que não testaram. No SWE-Bench-CL, prepender contexto irrelevante induz *drift* semântico médio de 0,45 na solução gerada.

### 5.3 Enforcement

- **Compilação de lição em check executável** — regra de linter custom, teste de regressão, hook de pre-commit/CI que **bloqueia a conclusão**.
- **Derivação de checks a partir de correções do reviewer** — cada correção humana vira uma regra atômica + um verificador.
- **Fitness functions / testes estruturais de arquitetura** — verificam características arquiteturais, não comportamento.

### 5.4 O baseline de long-context — o achado que condiciona todo o resto

A técnica mais simples possível é também a mais difícil de superar: **colocar tudo no contexto e deixar o modelo filtrar**. Quatro fontes independentes medem isso, e em todas o long-context vence os sistemas de memória e de retrieval:

| Fonte | Evidência |
|---|---|
| **Mem0**, Tabela 2 (LOCOMO completo) | Full-context **72,90** > Mem0g 68,44 > Mem0 66,88 > melhor RAG 60,53 |
| **TRACE**, §3.2 (6 modelos, 29 checagens) | *All Rules* **55,0** > *Relevant Rules* 54,0 > Mem0 42,5 |
| **AMA-Bench**, Tabela 6 (mesmo agente, só a memória varia) | LongContext **47,5** > Embedding 37,5 > MemoryBank 31,5 > Mem0 30,0 |
| **AMA-Bench**, Motivation 1 | *"the long context baseline is consistently strong and often achieves the best performance"* |

O caso do Mem0 é o mais notável: **a tabela principal do próprio artigo mostra o full-context com o maior score de qualidade**. O ganho do Mem0 é inteiramente em **latência (−91% no p95) e custo (−93% de tokens)**, não em qualidade.

O **ACE** (ICLR 2026) dá o argumento teórico correspondente: *"contexts should function **not as concise summaries**, but as comprehensive, structured playbooks (…) LLMs are more effective when provided with long, detailed contexts and **can distill relevance autonomously**"*. Comprimir para caber num orçamento é a *brevity bias* que o artigo nomeia como modo de falha.

**Quando o retrieval compensa, então?** A leitura cruzada das fontes indica que a variável decisiva é a **qualidade do store**, não o método:

| Store | Estratégia indicada | Evidência |
|---|---|---|
| **Curado, pequeno, alta precisão** (convenções, regras de consistência) | **Despejar** — filtrar só remove informação útil | TRACE (29–47 regras), ACE, Mem0 (full-context) |
| **Autogerado, grande, ruidoso** (trajetórias destiladas por LLM) | **Filtrar ou governar** — sem filtro, degrada | CTIM-Rover (−11 pp sem filtro de relevância), GovMem, MemGovern (cards governados) |

**Consequência de projeto:** o default desta camada deve ser **acumular**, com controle de crescimento pelo `grow-and-refine` do ACE (append + update in-place + dedup por embedding), truncando apenas ao atingir o limite físico de contexto — e não por orçamento arbitrário. E o braço long-context (§11.2) deixa de ser controle metodológico para se tornar **o favorito a bater**.

---

## 6. Ferramentas avaliadas

Critérios (alinhados ao `relatorio_pesquisa_ferramentas_para_tools_workspace.md`): **aderência funcional**, **maturidade**, **facilidade de integração**, **compatibilidade com a arquitetura existente** (ADK + LiteLLM + workspace efêmero) e **custo de manutenção**.

Vereditos: **Adotar** · **Adotar (princípio)** — replicar o mecanismo sem importar o código · **Referência** — citar como fundamentação, não integrar · **Descartar (por ora)** — reavaliar sob gatilho declarado.

### 6.1 Memória experiencial

| Ferramenta | O que faz | Aderência | Maturidade | Integração | Compat. | Veredito |
|---|---|---|---|---|---|---|
| **Mem0** (`mem0.ai/research`) | Memória de longo prazo: extração assíncrona + update via tool call (`ADD`/`UPDATE`/`DELETE`/`NOOP`) + retrieval; variante com grafo (Neo4j) | Média | Alta — lib publicada, avaliada em LOCOMO | Média — exige vector store; grafo exige Neo4j | Baixa — assume agente conversacional | **Referência** (arquitetura + argumento de custo) |
| **Memp** (`zjunlp/MemP`) | Memória procedural com granularidade combinada; operador formal `Add ⊖ Del ⊕ Update` com deprecação | Alta | Média — código de pesquisa | Baixa | Média | **Adotar (princípio)** — o operador de update e a política de deprecação |
| **CODESKILL** | Skills de nível de tarefa + skills acionadas por evento de erro; bank em tamanho estável. **Cada skill é um arquivo markdown** com título, condição de gatilho e instruções acionáveis | **Alta** | Média — publicação recente | Baixa — exige treinar política com GRPO | Média | **Adotar (princípio)** — o formato `trigger → corpo` em markdown é o modelo do item de memória. Pegar o **formato**, não o método de treino |
| **ExpeRepair / SWE-Exp** (`YerbaPage/SWE-Exp`) | Memória dual (episódica + semântica) para reparo de programas | Média | Média | Baixa — scaffold MCTS/AutoCodeRover | Baixa — incompatível com ADK | **Referência** (evidência de ablação e de custo) |
| **ACE** (ICLR 2026) | Playbook com update delta-incremental e *grow-and-refine*; evita *context collapse* e *brevity bias* | Alta | **Alta — peer-reviewed (ICLR 2026)** | Média | Alta | **Adotar (princípio)** — update delta e *grow-and-refine*, nunca reescrita completa nem compressão por orçamento |
| **Dynamic Cheatsheet** (`suzgunmirac/dynamic-cheatsheet`) | "Cheatsheet" textual atualizada incrementalmente e reinjetada no contexto | Alta | Média | **Alta** — é essencialmente um arquivo + política | Alta | **Adotar com ressalva** — é a implementação mais barata, mas é o sistema em que o ACE documenta o *context collapse* (18.282 tokens/66,7% → 122 tokens/57,1%, abaixo do baseline de 63,7%). Adotar **apenas** com update delta, nunca com reescrita monolítica |

**Sobre o Mem0 especificamente.** É a ferramenta mais madura do grupo e a referência de arquitetura (extração → update via `ADD`/`UPDATE`/`DELETE`/`NOOP` → retrieval), com **91% menos latência p95** e **>90% menos tokens** que a abordagem full-context. **Não é recomendado para adoção direta**, por quatro motivos: (i) o benchmark é conversacional (LOCOMO), sem transferência demonstrada para código; (ii) exige infraestrutura (vector store, opcionalmente Neo4j) desproporcional ao volume atual de conhecimento; (iii) é o sistema em que o TRACE mede 57,5% de violação de preferências aplicáveis; e (iv) **na tabela principal do próprio artigo o full-context tem qualidade superior** (J = 72,90 contra 66,88 do Mem0) — o ganho é de custo e latência, não de acurácia. O "+26% relativo" do abstract usa como âncora o método com o terceiro pior score da tabela. Ver §5.4.

### 6.2 Enforcement

| Ferramenta | O que faz | Estado no repo | Veredito |
|---|---|---|---|
| **Ruff** | Lint e estilo Python, saída JSON estruturada | Já integrado (`RuffCapability`, PR #318) — roda **pós**-execução no reviewer, sem poder de bloqueio | **Adotado** — manter onde está. Promovê-lo a gate bloqueante exigiria distinguir achado de estilo de defeito real; fora do escopo desta camada |
| **Bandit** | Análise de segurança | Já integrado (`BanditCapability`) | **Adotar** — manter pós-execução |
| **Semgrep** | Regras declarativas customizadas, multi-linguagem | Ausente | **Adotar** na fase 2 — é o veículo natural para "lição → regra executável"; multi-linguagem sobrevive à remoção da trava de stack |
| **uv** (`uv pip compile`) | Resolução e pin de dependências | Já é o gerenciador do projeto | **Adotar** — validação de resolubilidade do `requirements.txt` gerado |
| **ArchUnit / OpenRewrite** | Fitness functions estruturais / codemods | Ausente | **Referência** — ecossistema JVM, citadas por Böckeler como "feedforward computacional" |

### 6.3 Montagem e transporte de contexto

| Ferramenta | O que faz | Veredito | Gatilho de reavaliação |
|---|---|---|---|
| **repomix / code2prompt** | Empacotam repositório em prompt/context pack | **Referência** — inspiração de formato para o `context_pack.md` | — |
| **aider (repo-map)** | Mapa do repo via tree-sitter + PageRank | **Descartar (por ora)** | Quando o coder passar a modificar código existente (brownfield) |
| **MCP** | Padrão aberto de transporte de contexto e tools | **Referência** — candidato a interface da KB no longo prazo | Quando a KB precisar ser consumida por mais de um agente/produto |
| **Continue.dev (context providers)** | Providers plugáveis de contexto | **Referência de arquitetura** — o padrão espelha o `ReviewCapability` Protocol já existente no repo | — |
| **LlamaIndex / LangChain** | Frameworks de retrieval/RAG | **Descartar (por ora)** — não pelo custo (a stack já está declarada no `pyproject.toml`, ver §9.2), mas porque o store desta camada é **curado e pequeno**, e §5.4 mostra que store curado se despeja, não se filtra | KB acima de ~50 itens **com evidência medida** de estouro do limite físico de contexto, ou store autogerado em operação (§12.4) |
| **Chroma / LanceDB** | Vector stores embarcáveis | **Descartar (por ora)** — idem; o projeto já carrega Qdrant embedded não utilizado | Idem acima |
| **AMA-Agent** (`tool-augmented retrieval`) | Retrieval acionado pelo próprio agente via tool, em vez de pré-injeção por similaridade | **Referência — caminho preferencial se o retrieval entrar** | É a única abordagem que supera o baseline de long-context na Tabela 6 do AMA-Bench, e resolve o problema de *quando* o retrieval dispara: quem formula a query é o agente, no momento da dúvida concreta |

---

## 7. Gaps identificados

| # | Gap | Evidência | Severidade |
|---|---|---|---|
| **G1** | Conhecimento de convenções **hardcoded em string Python**, não em KB versionada. Reenquadrado pela literatura: é **texto passivo** (ContextCov) — regra enunciada sem mecanismo que force conformidade | `cr_coder.py:89–366` (o arquivo cresceu de 353 para 397 linhas entre o PR #340 e o #348) | **Alta** — 🚧 **majoritariamente fechado nesta entrega**: o bloco `ERROS COMUNS` migrou para `adk/knowledge/`, versionada e montada pelo `cr_feedforward` (§8.2); a instrução composta caiu de ~330 para 246 linhas. Sobram duas seções ainda em string (`REGRA OBRIGATÓRIA — DOCKERFILE` e `DIRETRIZES DE CODIFICAÇÃO`), mantidas de propósito: a KB só as substitui parcialmente, e a segunda vem do prompt canônico compartilhado com o `coder` role |
| **G2** | **Sem memória cross-run.** As lições morrem no wipe do workspace; a destilação falha→regra é manual (dev edita `cr_coder.py`). A política de escrita efetiva é **vanilla add**, sem validação, dedup ou deprecação — o oposto do que o Memp (`Add ⊖ Del ⊕ Update`) e o ACE (*grow-and-refine*) recomendam | `orchestrator/agent.py`, `_handle_fresh_run`; commits que adicionam blocos ao `ERROS COMUNS` | Alta |
| **G3** | **Handoff upstream lossy** — artefatos de `requirements/` e `design/` ficam em disco; ao pipeline de codificação chega o último texto de cada fase truncado em 8.000 chars | `_helpers.py:128` | Média |
| **G4** | **Dependências não aterradas** — `requirements.txt` gerado do zero a cada run; é a classe de falha nº 1 (metade do `ERROS COMUNS` trata de PyPI/imports). Em `4c9d482`, **nenhum estágio do harness fazia verificação estática**: não havia `ast.parse`, nem confronto `import ↔ requirements`, nem Ruff/Semgrep antes do build — o erro só aparecia como falha de build no estágio 2, depois de pago o custo da imagem | `cr_coder.py` §`ERROS COMUNS`; ausência verificada em `harness_execucao.py` | **Alta** — 🚧 **em fechamento**: o estágio `verificacao_estatica` do §8.3 está implementado e é entregue neste PR (ver §1.1). A parte de *aterramento* do gap (allowlist por stack) segue aberta |
| **G5** | **Sem exemplares** — apps aprovados nunca viram referência | — | Baixa |
| **G6** | Coder não relia contexto sob demanda | `cr_coder.py` | ✅ **Fechado** no PR #340 |
| **G7** | `tech_stack` inferida por run, com fallback `["a definir"]`; a stack real não vem de fonte de conhecimento | `context_engineer/prompt.py:77` | Média |
| **G8** | **Trava Python-only — migrou de lugar, continua aberta.** O estágio 1 do harness (`preparacao_ambiente`, crítico) aborta com *"Nenhum arquivo Python encontrado no workspace do coder"* antes de tentar buildar o Dockerfile. **O harness é a trava de stack real, não o prompt** | `coding_tools/harness_execucao.py:135` (antes: `cr_executor.py:249`) | Alta |
| **G9** | **Parcialmente fechado no PR #324.** A Camada 1 do `implementation_validator` impede que código com execução falha seja aprovado *dentro do loop*. Mas o `cr_reviewer` **continua sem consultar** o veredito, e há **dois caminhos** que o alcançam com código quebrado: encerramento por **estagnação** (status `bloqueado`) e esgotamento de `max_iterations` | `cr_reviewer.py` (sem referência a `validation`/`error_report`); `agent.py` (fallback do `LoopAgent`) | Média |

> **G8 e G9 foram descobertos em execução**, não em leitura de código: num run do orquestrador o `cr_context_engineer` escolheu Node/Express/MongoDB por conta própria, o coder obedeceu fielmente ao contrato, o executor abortou sem tentar o build e o reviewer emitiu APROVADO racionalizando a falha como "problema de ambiente". O PR #324 fechou o caminho principal do G9; o G8 sobreviveu à reescrita do executor, apenas mudando de arquivo.

> **Nota sobre `_last_exec_status`.** A chave foi **removida** no PR #324 — há inclusive um teste que afirma sua ausência (`tests/unit/test_cr_executor.py:88`). Documentos anteriores que a citam como fonte de sinal estão desatualizados; o substituto é `state['validation']` (`ValidationVerdict`) mais o `ExecutionReport` em disco. Ver §11.1.

---

## 8. Arquitetura proposta

### 8.1 Princípio organizador

O `cr_context_engineer` faz **decomposição de tarefa** — LLM, por run, específico do pedido. A camada de Feedforward faz **provisionamento de conhecimento** — determinístico, cross-run, independente do pedido. São complementares, e esta issue trata da segunda.

A camada tem **dois componentes**, pelas razões estabelecidas em §3.2: um provisiona o guia, o outro lhe dá força vinculante.

```
   FONTES                        MONTAGEM                       CONSUMO                VERIFICAÇÃO

┌────────────────────────┐
│ state["tasks"]         │
│  └ macro_context       │──┐
│  └ contract/interfaces │  │  ┌──────────────────────┐
├────────────────────────┤  ├─►│  cr_feedforward      │      LoopAgent
│ adk/knowledge/         │  │  │  BaseAgent           │   ┌──────────────────────┐
│  ├ core/               │──┤  │  DETERMINÍSTICO      │──►│  cr_coder            │
│  │   conventions.md    │  │  │  (sem LLM)           │   │  {context_pack?}     │
│  │   consistency.md    │  │  │                      │   └──────────┬───────────┘
│  │   lessons.md ◄──────┼──┤  │  seleciona core/ +   │              │ escreve
│  └ stacks/<stack>/     │──┘  │  stacks/<tech_stack> │              ▼
│      deps.md           │     │  acumula + dedup     │   ┌──────────────────────┐
│      pitfalls/lessons  │     │  (grow-and-refine)   │   │  HARNESS (9+1 estág.)│
└────────────────────────┘     └──────────┬───────────┘   │  1. preparacao       │
   versionado no git,                     │                │ [1b. verif. estática │
   FORA de workspace_output/              ▼                │      imports↔reqs ]  │◄─ NOVO
                                 state["context_pack"]      │  2. implantacao      │
                                 coder/context/             │  ...                 │
                                   context_pack.md          │  → ExecutionReport   │
                                                            └──────────┬───────────┘
                                                                       ▼
                                                            ┌──────────────────────┐
                                                            │ implementation_      │
                                                            │ validator            │
        destilação curada ◄─────────────────────────────────┤ Camada 1: exec falha │
        (humana na PoC)     <task_id>.report.json            │  → reprova sem julgar│
                            + ValidationVerdict              │ Camada 2: agregação  │
                                                            └──────────┬───────────┘
                                                                       │ reprovado
                                                                       ▼
                                                              ErrorReport → cr_coder
```

> O bloco tracejado é a única peça nova do lado da verificação (§8.3). O resto — harness, validador em duas camadas e `ErrorReport` — **já existe** desde o PR #324.

### 8.2 Componente 1 — `cr_feedforward` (provisionamento)

**Natureza:** `BaseAgent` custom **sem LLM**, inserido no `SequentialAgent` entre o `cr_context_engineer` e o `LoopAgent`.

**Responsabilidades:**

1. Ler `state["tasks"]` e extrair `macro_context.tech_stack` — sem LLM, sem alterar o context engineer.
2. Ler a KB de `adk/knowledge/`: `core/` sempre; `stacks/<tech_stack>/` quando a stack for reconhecida.
3. Montar o `context_pack.md` **acumulando por padrão** (§5.4), com controle de crescimento por `grow-and-refine` — append, update in-place, dedup por embedding — e truncagem só ao atingir o limite físico de contexto.
4. Gravar em `state["context_pack"]` e persistir em `coder/context/context_pack.md` para auditoria.

**Consumo:** via `{context_pack?}` na instrução do `cr_coder` — mecanismo idêntico ao `{execution_result?}`, já em produção.

> **Restrição arquitetural dura.** A KB **precisa** morar fora de `workspace_output/`, porque `init_workspace()` apaga esse diretório a cada fresh run. Mas as tools de leitura do coder são bindadas ao `workspace_root` (`agent_factory.py:137–139`) e `_resolver_caminho` rejeita caminhos absolutos e `..` (`coding_tools/filesystem_coding.py:59–79`). **Logo a KB é inalcançável pelas tools do coder, e o consumo tem obrigatoriamente que ser por injeção no prompt.** Isso não é uma preferência de design — é o que o código permite.

### 8.3 Componente 2 — Gate de pré-voo (enforcement)

**Natureza:** verificação estática determinística posicionada **dentro do harness**, entre `preparacao_ambiente` e `implantacao_artefato`.

**Precedente arquitetural — já não é hipótese.** O projeto tem três instâncias do mesmo padrão em produção: `run_capabilities()` chamado no `before_agent_callback` do `cr_reviewer` (PR #318); `montar_veredito()` codificando a política de veredito fora do LLM (PR #324); e `montar_error_report()` substituindo a saída do LLM por um artefato determinístico (PR #324). "Trabalho determinístico em Python, LLM só onde há julgamento" é o padrão da casa.

**O que falta:** um estágio que verifique **antes de buildar**. Hoje o primeiro sinal sobre dependências vem do estágio 2 (`implantacao_artefato`), ou seja, depois de pagar o custo de construir a imagem — e uma dependência inexistente derruba o build inteiro por uma linha de texto.

**Verificação proposta:** `import ↔ requirements.txt` — parseia os imports via AST, descarta stdlib, imports relativos e módulos locais, e reporta cada import de terceiros sem linha correspondente. Ataca G4 **deterministicamente**, em vez de depender de o LLM lembrar de uma regra do prompt.

**Forma de integração — duas opções, ambas viáveis:**

1. **Estágio novo no harness** (`verificacao_estatica`), crítico, antes de `implantacao_artefato`. Falha aqui produz `StageResult` com `error_code` próprio, e a Camada 1 do validador reprova sem julgar critérios — **o caminho de enforcement já existe e não precisa ser construído**. É a opção recomendada: o achado entra no `ExecutionReport` e chega ao coder pelo `ErrorReport`, sem mecanismo novo.
2. **Capability adicional** em `shared/review/capability.py`, reusando o `Protocol` `ReviewCapability` e um registry alternativo em `run_capabilities()`. Mais barata de escrever, mas o resultado precisaria de um caminho próprio até o coder.

A opção 1 tem custo de integração maior e valor maior: aproveita o `ExecutionReport`, o veredito e o `ErrorReport` que já existem.

> **Estado (05/08): a opção 1 foi implementada** — `verificar_dependencias()` como função pura em `coding_tools/verificacao_dependencias.py` (só stdlib, sem dependência do harness) e o estágio `verificacao_estatica` em 2º lugar numa sequência que passou de nove para **dez estágios**. A cascata é controlada por uma flag `static_ok` no contexto do harness, não pela lista de estágios críticos — esta última só afeta o `overall_status`. 30 testes unitários. Aguarda PR (§1.1).

**Política de falha — híbrida, e deliberadamente assimétrica.** Nome de import ≠ nome de pacote PyPI (`jose`→`python-jose`, `PIL`→`Pillow`, `bs4`→`beautifulsoup4`, …), e nenhuma tabela de alias fica completa. Logo o falso positivo é certeza estatística, não risco hipotético — e num estágio crítico ele **aborta o run**, devolve ao coder um erro inexistente e pode induzi-lo a declarar um pacote que não existe, transformando um falso alarme em falha real de build. A assimetria decide a primeira versão: **o pior caso do modo permissivo é o comportamento de hoje; o pior caso do modo bloqueante é pior que hoje.** Portanto:

- **Bloqueia** (`fail-closed`) apenas o caso inequívoco: **não existe `requirements.txt`** e há imports de terceiros. Não depende de tabela de alias, não admite falso positivo.
- **Registra evidência sem reprovar** (`fail-open`) em toda divergência de nome, alias desconhecido ou dúvida de correspondência. O achado chega ao coder como informação, sem poder de veto.
- **Instrumenta para reavaliar.** A taxa de falso positivo do estágio é coletada nos runs do §11 e decide a promoção a `fail-closed` num PR posterior — trocar o modo é uma flag no `StageResult`.

Essa é a única concessão ao ContextCov, que defende `fail-closed` com dados a favor (conformidade 67,0%→88,3% e resolução funcional 53,0%→57,3%, *p*=0,031, ou seja: bloquear não atrapalhou o agente). O argumento deles é forte no regime permanente — gate que nunca bloqueia não cria incentivo para corrigir a tabela de alias e apodrece. Por isso a decisão é **adiada com prazo e critério**, não descartada.

> **Primeiro dado de campo (05/08) — a política permissiva se justificou na estreia.** Num run completo pelo `orchestrator`, o `LoopAgent` esgotou as 5 iterações e o estágio rodou nas 5, sempre com **zero achados bloqueantes**: nenhum run foi abortado pelo gate. O único achado recorrente foi `import starlette` em 7 arquivos com o `requirements.txt` declarando apenas `fastapi` — que traz o starlette **transitivamente**. É um verdadeiro positivo de baixa severidade, não um erro de alias: o import funciona, o app subiu e respondeu, e ainda assim a dependência é usada sem ser declarada. Um gate `fail-closed` ingênuo — que reprovasse qualquer divergência — teria abortado um run que funcionou. **O caso reforça a assimetria acima e acrescenta uma categoria que a tabela de alias não cobre: dependência transitiva usada diretamente.** N=1; sem valor estatístico, com valor de sanidade.

**Ganho colateral:** falhar antes do build economiza a operação mais cara do loop.

### 8.4 Ciclo de realimentação (fase 3)

O `ExecutionReport` (`<task_id>.report.json`) e o `ValidationVerdict` são o oráculo. A destilação `ExecutionReport → knowledge/core/lessons.md` fecha o ciclo feedback→feedforward que hoje é feito manualmente por edição de código.

**Política de escrita, conforme a evidência do §5.2:** só escrever após `state['validation'].status == "aprovado"` (validação executável); update delta-incremental, nunca reescrita; deprecação e dedup ativas; e **curadoria humana obrigatória** — o resultado do GovMem (nenhum de 133 candidatos reais seguro para promoção automática) torna a automação da promoção uma decisão a evitar nesta fase.

**Chave de indexação da lição:** `stages[].error_code`. O harness já tipa a classe da falha (`TASK_NAO_ENCONTRADA`, `APP_NAO_INICIALIZOU`, …), fornecendo exatamente a chave por *padrão de erro* que o SWE-Bench-CL recomenda priorizar — e sem depender de embedding no primeiro nível de seleção.

---

## 9. Análise de viabilidade

### 9.1 Custo de acoplamento

| Item | Tipo | Arquivos tocados |
|---|---|---|
| `adk/shared/feedforward/` (montador + testes) | Módulo novo | — |
| `adk/knowledge/` (KB semente) | Diretório novo, versionado | — |
| `cr_feedforward` no `SequentialAgent` | **Acoplamento** | `workflow_coding_review/agent.py` — uma linha em `sub_agents` |
| Seção `{context_pack?}` na instrução | **Acoplamento** | `cr_coder.py` — uma seção no `workspace_section` |
| `verificar_dependencias()` — função pura | Código novo | `shared/` (módulo próprio) |
| Estágio `verificacao_estatica` no harness | **Acoplamento** | `harness_execucao.py` + `StageName` em `executor/schemas.py` |

**Três pontos de acoplamento**, todos aditivos — o último toca dois arquivos (a sequência de estágios e o enum). Nenhuma alteração de comportamento existente: um estágio novo em falha reusa o caminho de reprovação que a Camada 1 já implementa. Todo o resto é código novo.

### 9.2 O que o repositório já tem a favor

Quatro ativos reduzem materialmente o custo desta camada:

1. **O oráculo executável já existe e é estruturado.** O harness produz um `ExecutionReport` com estágios tipados, `status` e `error_code` por estágio, e o `implementation_validator` emite um `ValidationVerdict` com veredito por critério. Na maioria dos trabalhos citados no §5.2, construir esse oráculo foi parte substancial do esforço — aqui ele está pronto, e num formato melhor que o exigido pela política de escrita do §8.4.
2. **A infraestrutura de verificação determinística já existe em duas formas.** `run_capabilities()` é plugável via `Protocol`, com isolamento de falhas e timeout; e o harness tem uma sequência de estágios tipados com dependências declaradas. Acrescentar uma verificação é acrescentar uma peça, não um subsistema.
3. **O caminho do sinal até o coder já está em produção.** O `ErrorReport` determinístico chega ao coder via `{execution_result?}` — o mesmo mecanismo de injeção que o `{context_pack?}` usaria.
4. **A infraestrutura de retrieval já está declarada e nunca foi exercitada.** O `adk/pyproject.toml:14-20` traz `qdrant-client`, `langchain-qdrant` e `fastembed` (embeddings locais ONNX — sem chave de API e sem custo por chamada), com **zero referência** em código. Isso remove a objeção de custo de entrada de qualquer proposta futura de retrieval: quando o gatilho do §6.3 disparar, o trabalho é de curadoria de corpus, não de infraestrutura.

### 9.3 Custos e riscos quantificáveis

- **Pressão de tokens e o trade-off qualidade × custo.** O input do coder cresce com o pack, e é aqui que a evidência da §5.4 impõe uma escolha explícita: o full-context entrega **mais qualidade** e o pack seletivo entrega **menos custo** (o Mem0 mede −91% de latência p95 e −93% de tokens, ao preço de 6 pontos de qualidade). A decisão de projeto é acumular por padrão e medir o custo no braço C, não presumir que compressão é gratuita. O truncamento cego de 8.000 chars do `_build_input` continua sendo o anti-exemplo — corta pelo meio, sem critério.
- **Duplicação prompt × pack** durante a migração. Regra: o que entra na KB **sai** do prompt no mesmo PR, para evitar instrução repetida e divergente.
- **Risco de degradação.** O CTIM-Rover não supera sua baseline em nenhuma configuração (n=45), e a variante que injeta memória sem filtro fica 11 pontos abaixo. Mais relevante: **quatro fontes independentes mostram o baseline de long-context vencendo memória e retrieval** (§5.4). Daí a exigência dos três braços (§11.2) e dos *kill-switches* (§12.4).
- **Bloqueadores.** **G8** limita o alcance, não a execução: enquanto o harness só aceitar Python, uma KB indexada por stack terá **uma stack testável na prática** — a PoC roda, mas nenhuma afirmação multi-stack pode ser feita. **G9 deixou de ser bloqueador** com o PR #324: a métrica de validação passou a sair de `state['validation']`, que é determinística, e não do veredito do reviewer (§11.1).

---

## 10. PoC mínima — especificação

Escopo desenhado para cobrir o critério de aceitação sem depender de infraestrutura nova.

### 10.1 Entregas

1. **`adk/shared/feedforward/`** — `build_context_pack(tasks: dict, knowledge_root: Path, limite_contexto: int | None = None) -> str`, determinístico e testável sem LLM. O parâmetro é o **limite físico de contexto**, não um orçamento de compressão: o default acumula (§5.4, §8.2).
2. **`adk/knowledge/`** — KB semente versionada:
   ```
   adk/knowledge/
   ├── core/                         ← agnóstico de stack (sempre entra no pack)
   │   ├── conventions.md            ← SRP, limite de ~150–200 linhas, arquivos que o pytest exige
   │   ├── consistency-rules.md      ← import↔requirements, COPY/CMD↔manifesto, compose↔Dockerfile
   │   └── lessons.md                ← APENAS estratégias transversais (§12.4); nasce vazio
   └── stacks/
       └── python-fastapi/
           ├── deps.md               ← dependências conhecidamente boas + versões
           ├── pitfalls.md           ← semente manual; ex.: API do Jinja2Templates.TemplateResponse
           └── lessons.md            ← destino **default** das lições destiladas desta stack
   ```
3. **`cr_feedforward`** — `BaseAgent` determinístico inserido no `SequentialAgent`.
4. **`{context_pack?}`** na instrução do `cr_coder`, com migração do conteúdo correspondente para fora do prompt.
5. **Estágio `verificacao_estatica`** no harness (§8.3), com `verificar_dependencias()` como função pura reutilizável.
6. **`tests/unit/test_feedforward.py`** e **`tests/unit/test_verificacao_dependencias.py`**, no padrão da suíte existente — mais dois casos de integração provando que a falha do estágio propaga até a reprovação na Camada 1.

### 10.2 Decisão de escopo registrada

A versão inicial desta PoC previa um `requirements.txt` de referência pinado para FastAPI. Isso foi **rejeitado**: equivale a um *service template* amarrado a uma stack, e contraria a intenção declarada de remover a trava de stack do pipeline.

A forma adotada é a **allowlist indexada por stack** (`knowledge/stacks/<stack>/deps.md`, selecionada pelo `tech_stack` do contrato). Preserva o ataque a G4 sem amarrar o pipeline: a KB deixa de ser "a stack certa" e passa a ser "o que sabemos sobre cada stack". Quando a trava sair (G8), a KB escala por adição de diretório em vez de virar dívida técnica.

---

## 11. Protocolo de validação

O objetivo declarado da issue — *maximizar a qualidade da primeira resposta e reduzir ciclos de retrabalho* — é diretamente mensurável com sinais que o pipeline já registra.

### 11.1 Métricas

| Métrica | Fonte | Por que |
|---|---|---|
| **Veredito na 1ª iteração do loop** | `state['validation'].status` (`ValidationVerdict`) após a primeira passagem coder→executor | Operacionaliza literalmente "qualidade da primeira resposta" |
| **Nº de iterações até `aprovado`** | Campo `iteration` do `ExecutionReport`; teto em `AI4ES_MAX_LOOP_ITERATIONS` (default 5) | Operacionaliza "ciclos de retrabalho" |
| **Distribuição de classes de falha** | `ExecutionReport.stages[].error_code` + `status`, por iteração | Mostra *qual* classe de erro a camada elimina |
| **Modo de encerramento do loop** | `aprovado` · estagnação (`bloqueado`) · esgotamento de `max_iterations` | Distingue convergência real de desistência |
| **Tokens de entrada do coder** | Telemetria do LiteLLM / LangFuse | Custo da camada |
| **Disparos e acertos do `verificacao_estatica`** | `StageResult` do estágio + conferência do achado contra o `requirements.txt` real | Mede a **taxa de falso positivo do gate** — é o dado que decide a promoção de `fail-open` para `fail-closed` (§8.3) |

> **Mudança de instrumentação (PR #324).** A chave `_last_exec_status`, usada no desenho original deste protocolo, **não existe mais**. O substituto é estritamente melhor para a medição: a distribuição de classes de falha, que antes exigiria parsear um markdown, agora vem tipada em `stages[].error_code`. Os relatórios ficam em `<task_id>.report.json` no workspace do `cr_executor`.

**O veredito do `cr_reviewer` não é métrica válida** — ele não consulta o `ValidationVerdict` (G9). Use `state['validation']`, que é a fonte determinística.

### 11.2 Braços experimentais

A literatura impõe um controle que o desenho inicial não previa — e a verificação das fontes primárias mostrou que ele é mais que um controle. **Quatro fontes independentes medem o long-context vencendo memória e retrieval** (§5.4), incluindo a tabela principal do próprio Mem0. Portanto três braços, não dois — e o braço B é o **favorito a bater**, não uma formalidade:

| Braço | Descrição |
|---|---|
| **A — baseline** | Pipeline atual, sem context pack |
| **B — long-context** | Todo o conteúdo da KB despejado no prompt, sem seleção por stack |
| **C — camada** | `context_pack` seletivo por stack + estágio `verificacao_estatica` |

**C só é adotável se superar A *e* B.** Superar apenas A não distingue o efeito da camada do efeito de simplesmente ter mais contexto.

### 11.3 Procedimento

1. Fixar o requisito de entrada e o modelo (`ADK_LLM_MODEL` explícito — o default do código é `gemini-2.5-flash`).
2. **Declarar a stack explicitamente na prompt** enquanto G7/G8 estiverem abertos.
3. N execuções por braço (N=5 como piso), reportando variância — o não-determinismo do LLM é o confundidor principal.
4. Coletar as métricas do §11.1 a partir dos `<task_id>.report.json` (JSON — agregável por script) e do `state['validation']`.

> **Confundidor a controlar.** A Etapa 0 (PR #340) foi mergeada sem baseline comparativo próprio — a validação atual é N=1. Se a camada entrar antes de esse baseline ser levantado, os dois efeitos ficam misturados e nenhum fica medido. **O braço A deve ser executado com a Etapa 0 já presente**, isolando o efeito da camada.

> **Operacional.** Cada run exige daemon Docker no host, ADK rodando **localmente** via uvicorn (nenhum compose monta `/var/run/docker.sock`) e a porta 8000 livre — em caso de sucesso o container permanece de pé (`docker rm -f cr-executor-run` entre runs).

---

## 12. Recomendações de adoção

### 12.1 Estágio 0 — Instrumentação (pré-requisito)

1. **Medir a taxa de repetição de erro por categoria** a partir de `ExecutionReport.stages[].error_code` acumulados. Sem a linha de base não há como saber se a camada ajudou — e, com o PR #324, esse dado sai tipado, sem parsing.
   > ⚠️ **Pré-requisito de código — 🚧 resolvido, aguardando PR.** "Acumulados" não era executável em `4c9d482`: `init_workspace()` (`shared/workspace.py:99`) apaga o `workspace_output/` a cada fresh run, e o harness grava o relatório em `coder/execution/` (`coding_tools/harness_execucao.py:880`) — dentro da árvore apagada. **O problema era pior que o diagnóstico original:** o nome do arquivo não carrega a iteração, então cada iteração sobrescrevia a anterior **dentro do mesmo run**, e não apenas entre runs.
   >
   > A correção acompanha o gate (§8.3): cópia persistente em `adk/.ai4es_history/<data>/<hora>_<task_id>_iter<N>.report.json`, fora do workspace e com a iteração no nome. Medido no run de 05/08: **5 arquivos, um por iteração**, enquanto `coder/execution/` guardou **um só** — a iteração 5. A métrica "distribuição de classes de falha por iteração" (§11.1) saiu de inobtenível para obtida já nesse run: `APP_NAO_INICIALIZOU` (iterações 1–2) → sucesso (3–4) → `TESTES_FALHARAM` (5).
   >
   > ⚠️ **Ressalva de instrumentação que permanece:** o campo `iteration` do `ExecutionReport` é **auto-relatado pelo LLM** do `cr_executor` (é argumento da tool), não vem do contador do `LoopAgent`. Para a métrica "nº de iterações até `aprovado`" (§11.1), conte os relatórios persistidos em vez de confiar no campo.
2. **Fechar o resíduo do G9** — fazer o `cr_reviewer` consultar `state['validation']`. A Camada 1 já protege o caminho principal; falta cobrir os dois caminhos que alcançam o reviewer com código quebrado (estagnação e esgotamento de `max_iterations`). Menor prioridade que antes, mas ainda necessário para que o veredito do reviewer volte a significar algo.
3. **Levantar o braço A** (§11.2) com a Etapa 0 e o harness presentes.

### 12.2 Estágio 1 — Enforcement primeiro

Recomendação deliberadamente contra-intuitiva, e é o principal ajuste que a revisão de literatura impôs a este desenho: **implementar o gate de pré-voo antes da base de conhecimento**.

Justificativa: TRACE mostra que compilar a lição em verificação reduz violação de 100% para 2%, enquanto a mesma lição disponível como texto no contexto deixa 57,5% de violações. Aplicado ao G4 — a classe de falha nº 1 — um check de 30 linhas que confronta imports com o `requirements.txt` tem impacto esperado maior que qualquer quantidade de instrução em prompt.

**Threshold de decisão:** se o enforcement sozinho eliminar **>80%** da repetição medida no Estágio 0, adiar a memória procedural complexa e consolidar o que já funciona.

### 12.3 Estágio 2 — Provisionamento de contexto

> 🚧 **Entregue neste PR.** O `cr_feedforward`, a KB em `adk/knowledge/` e a injeção `{context_pack?}` estão implementados, com o `ERROS COMUNS` migrado do prompt no mesmo PR. O que segue é a especificação de origem. Duas diferenças conscientes em relação a ela: (i) os campos de governança abaixo **ainda não são escritos por item** — resolvem problemas do Estágio 3 (destilação automática), que não existe nesta issue, e o `knowledge/README.md` registra o formato para quando existir; (ii) a seleção de stack casa por substring, não por igualdade.

Implementar `cr_feedforward` + `knowledge/` + `{context_pack?}`, migrando o conteúdo do `ERROS COMUNS` do prompt para a KB no mesmo PR. Formato do item de conhecimento, seguindo o padrão do CODESKILL — **arquivo markdown com título, condição de gatilho e instruções acionáveis** — acrescido dos campos de governança que o Memp e o GovMem indicam:

```yaml
trigger:      assinatura do erro ou contexto de ativação
granularidade: evento | estratégia
corpo:        instrução acionável
evidencia:    <task_id>.report.json / teste que a validou
escopo:       core | stack:<nome>
status:       ativo | deprecado
proveniencia: run/PR de origem
```

O campo `escopo` determina o arquivo de destino, e o **default é `stack:<nome>`** — `core` exige o critério de promoção do §12.4. O `trigger` costuma ser o `error_code` do harness, que é agnóstico de stack; o **corpo** é que é específico. Mesma classe de falha, instrução diferente por stack.

### 12.4 Estágio 3 — Memória cross-run

Destilação `ExecutionReport → lessons.md` com curadoria humana. A política de escrita segue o GovMem: **coleta automática, promoção revisada** — vale notar que, no artigo, a baseline simples *review-all-correlated* atinge praticamente a mesma segurança da política sofisticada (falso-promotion 0,033 vs 0,032) com quase o dobro do recall, o que dispensa construir governança elaborada. Este é o único store do projeto que é **autogerado e ruidoso** e, portanto, o único que exige filtro em vez de despejo (§5.4): chavear por `error_code` antes de semântica, com *k* pequeno (1–3).

**Onde a lição é gravada — a stack, não o `core/`.** A proveniência de toda lição é um `<task_id>.report.json` produzido por um run com uma stack concreta, e o mecanismo de seleção do §8.2 injeta `core/` **sempre**. Uma lição de SQLAlchemy em `core/` seria despejada num run Node — exatamente o contexto irrelevante que o CTIM-Rover mede como −11 pontos e o SWE-Bench-CL como *drift* de 0,45. Por isso:

- **Destino default:** `stacks/<stack>/lessons.md`. É onde cai a regra acionada por evento — a granularidade que o CODESKILL mede como a mais eficaz (*event-driven* 62,00 contra 58,67 de *task-level*).
- **`core/lessons.md` é a exceção**, reservada às **estratégias transversais** — a metade abstrata da granularidade dupla do Memp. Exemplo do que qualifica: *"todo import de terceiro precisa de linha correspondente no manifesto de dependências"* (a forma do erro existe em npm, cargo, go.mod). Exemplo do que não qualifica: *"`ForeignKey` recebe `'users.id'`, não `'User.id'`"*.
- **Critério de promoção para `core/`:** o mesmo padrão observado em **duas stacks diferentes**. É falsificável e dispensa julgamento subjetivo do curador — a promoção vira `report → lição da stack → lição transversal`, com dois níveis de revisão em vez de um.
- **`pitfalls.md` e `lessons.md` convivem no mesmo diretório de stack** porque têm **políticas de escrita diferentes**: o primeiro é semente escrita à mão e estável; o segundo sofre `grow-and-refine` com dedup e deprecação. O campo `proveniencia` do frontmatter (§12.3) distingue a origem de cada item.

> **Nota de calendário.** Enquanto o G8 estiver aberto, só uma stack acumulará lições e a distinção será teórica. A decisão é antecipatória, mas é **gratuita agora** (escolha de diretório) e cara depois (migrar itens já referenciados por `proveniencia`).

**Duas formas de retrieval foram avaliadas para este estágio:**

| Proposta | Descrição | Veredito | Fundamento |
|---|---|---|---|
| **Memória de erros do próprio pipeline** | Indexar pares (falha validada → correção validada) extraídos do loop, recuperados por `error_code` | **Adotar quando o Estágio 3 iniciar** — é a forma correta de consumir este store | É o único store do projeto autogerado e ruidoso, e §5.4 mostra que store dessa natureza exige filtro. O CTIM-Rover aponta retrieval por embedding como o conserto que não testou; o CODESKILL mede *event-driven* (62,00) acima de *task-level* (58,67) e da ausência de skill (57,33) |
| **Corpus externo de código aberto por stack** | Indexar repositórios de terceiros como exemplares | **Descartar** na forma proposta; **reavaliar** na forma de documentação oficial pinada ou de *cards* governados | Repositórios reintroduzem *version skew* — a assinatura antiga do `Jinja2Templates.TemplateResponse` predomina no FastAPI open source e é exatamente o bug corrigido em `6a35751`. O MemGovern obtém +4,65 pp com corpus externo, mas indexando **cards estruturados de issue-tracking** (135 mil, curadoria industrial), não código bruto |

**Pré-condição comum às duas:** qualquer retrieval precisa ser medido contra o braço B (§11.2), não contra o baseline atual. Quatro fontes independentes preveem que o long-context vence — superar apenas o braço A não sustenta adoção.

**Kill-switches — desligar a camada se:**

- a taxa de sucesso cair em relação ao braço B (long-context) em qualquer subconjunto;
- o store crescer monotonicamente sem ganho de sucesso;
- tokens/iterações subirem sem ganho de resolução;
- houver queda de desempenho logo após a injeção de lições novas (*false promotion*).

### 12.5 Recomendações transversais

- **Corrigir G8** — hoje em `coding_tools/harness_execucao.py:135`. É o desbloqueador de qualquer trabalho multi-stack e a trava de stack real do pipeline. Correção mínima: trocar "existe ao menos um `.py`" por "existe `Dockerfile` **ou** código reconhecível" — o build Docker em si já é agnóstico de linguagem; só o gate não é.
- **Reavaliar o truncamento de 8.000 chars** do `_build_input` (G3). Fora do escopo desta camada, mas o braço B do experimento já produz o dado necessário para decidir.
- **Tratar o `ERROS COMUNS` como store de memória, não como prompt** — 🚧 **primeira metade entregue neste PR.** O bloco saiu de `cr_coder.py` e virou `adk/knowledge/`, versionada e editável por PR de documentação, com dedup por item na montagem do pack. O que **não** foi entregue é a política de escrita: as lições continuam sendo adicionadas à mão, sem deprecação e sem verificação automática — as operações que o Memp (`Add ⊖ Del ⊕ Update`) e o ACE (*grow-and-refine*) identificam como necessárias e que dependem do Estágio 3.

---

## 13. Limitações deste relatório

- **Comparabilidade dos números.** Os resultados quantitativos do §5.2 vêm de estudos com backbones, scaffolds e subsets distintos. Devem ser lidos como deltas internos a cada estudo, nunca comparados entre si. Vale especial atenção ao achado de que modelos menores se beneficiam desproporcionalmente de memória estruturada — o ganho aparente é função da fraqueza do backbone.
- **Maturidade das fontes.** Parte substancial da literatura de memória experiencial citada é composta por preprints recentes. **Todas as 12 fontes foram verificadas por leitura integral dos PDFs.** Ressalvas que permanecem: os 133 candidatos do GovMem são um pacote de alto impacto **selecionado entre os mais suspeitos**, com concordância entre anotadores de κ=0,208; o TRACE trata de **correções de usuário**, não de erros de execução; os benchmarks do Memp (TravelPlanner, ALFWorld) e do AMA-Bench (BabyAI, TextWorld, Spider2) **não são de reparo de código**.
- **Validação pendente.** As métricas do §11 ainda não foram levantadas. A Etapa 0 foi validada em **N=1**, sem baseline comparativo, e o gate do §8.3 tem **um** run real — que prova que ele executa e não bloqueia indevidamente, e nada além disso. Nenhuma afirmação de ganho quantitativo é feita aqui sobre a camada proposta.
- **Velocidade de mudança do pipeline.** O inventário do §4 e as referências de arquivo/linha refletem `develop` @ `4c9d482`. O executor foi integralmente reescrito entre duas redações deste documento (PR #324), e o `Catalogo_de_tools_do_fluxo.md` já estava desatualizado no dia em que foi mergeado. Confirme as referências de código antes de reusá-las; a análise conceitual (§3, §5, §6, §12) não depende delas.
- **Escopo da transferência.** O Mem0, principal referência de arquitetura de memória, é avaliado em benchmark conversacional. A transferência de suas conclusões para agentes de codificação é uma extrapolação, sinalizada como tal em §6.1.
- **A avaliação de retrieval é documental.** Nenhuma configuração de RAG foi executada ou medida neste projeto. Os vereditos do §6.3 e do §12.4 derivam da literatura verificada e das características do store, não de experimento interno.

---

## 14. Referências

**Conceituais**

1. Böckeler, B. *Harness Engineering for Coding Agents*. martinfowler.com, 02/04/2026. <https://martinfowler.com/articles/harness-engineering.html>
2. Chhikara, P.; Khant, D.; Aryan, S.; Singh, T.; Yadav, D. *Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory*. arXiv:2504.19413, abr/2025.

**Memória experiencial e enforcement** — consolidadas em estudo interno de revisão; ver §13 quanto à maturidade das fontes.

3. *Memp: Exploring Agent Procedural Memory* — arXiv:2508.06433 (granularidade combinada; operador de update com deprecação).
4. *ReasoningBank* — arXiv:2509.25140 (memória de estratégias; SWE-bench Verified).
5. *ACE: Agentic Context Engineering* — arXiv:2510.04618 (update delta-incremental; *context collapse*, *brevity bias*).
6. *ExpeRepair* — arXiv:2506.10484 · *SWE-Exp* — arXiv:2507.23361 (memória dual para reparo de programas).
7. *CODESKILL* — arXiv:2605.25430 (skills acionadas por evento de erro).
8. *TRACE* — arXiv:2606.13174 (lacuna memória↔enforcement; compilação de lições em verificação executável).
9. *ContextCov* — arXiv:2603.00822, *"Bridging the Gap Between Developer Intent and Autonomous Agent Execution"* (instruções como texto passivo; 88,3% de conformidade contra 67,0% e 50,3% em SWE-bench Lite).
10. *GovMem* — arXiv:2607.02579 (governança de escrita; *false promotion*).
11. *CTIM-Rover* — arXiv:2505.23422 (resultado negativo com n=45: memória injetada **sem filtro de relevância** degrada em 11 pontos; os autores apontam retrieval por embedding como conserto não testado).
12. *SWE-Bench-CL* — arXiv:2507.00014 (proposta de benchmark; *prompt poisoning* com drift 0,45; recomenda similaridade semântica sobre estrutural) · *AMA-Bench* — arXiv:2602.22769 (*"memory systems fall short of the long-context baseline"*; AMA-Agent com *tool-augmented retrieval*).
13. *MemGovern* — arXiv:2601.06789 (governança de experiência externa em *cards* estruturados a partir de issue-tracking; +4,65 pp de resolução em SWE-bench Verified).
14. *Dynamic Cheatsheet* — arXiv:2504.07952 (playbook incremental).

**Documentação do projeto**

15. `AI4ES/adk/README.md` — receita end-to-end do pipeline.
16. `docs/Time_4_Codificacao/relatorio_pesquisa_ferramentas_para_tools_workspace.md` — gaps de Tools/Workspace (PR #310).
17. `docs/Time_4_Codificacao/Analise_Gaps_Melhorias_Revisor.md` — gaps do reviewer.
