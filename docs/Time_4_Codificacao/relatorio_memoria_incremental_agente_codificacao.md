# Relatório — Memória Incremental para o Agente de Codificação

> **Objeto:** levantamento, desenho, implementação e avaliação de uma camada de **memória
> que evolui entre execuções** para o pipeline de codificação (Time 4): o agente destila
> lições da própria execução, julga quais merecem sobreviver e as recebe de volta no prompt
> da execução seguinte.
>
> **Estado:** implementada e exercitada ao vivo. O código vive em `adk/shared/memory/` e
> `adk/src/agents/workflow_coding_review/memory_writer/`, na branch
> `feature/code/303-poc-memoria-incremental`.

---

## Sumário

1. [Contexto e problema](#1-contexto-e-problema)
2. [Levantamento das técnicas](#2-levantamento-das-técnicas)
3. [Arquitetura proposta](#3-arquitetura-proposta)
4. [Ferramentas avaliadas](#4-ferramentas-avaliadas)
5. [Análise de viabilidade](#5-análise-de-viabilidade)
6. [Principais gaps identificados](#6-principais-gaps-identificados)
7. [Recomendações de adoção](#7-recomendações-de-adoção)
8. [Referências](#8-referências)

---

## 1. Contexto e problema

O agente de codificação não acumula nada entre execuções, e a causa é estrutural, não de
modelo: `init_workspace()` executa `shutil.rmtree` sobre o diretório de saída inteiro no
início de cada execução (`adk/shared/workspace.py:134`). Tasks, código, `ExecutionReport`,
veredito e revisão — tudo é apagado antes da execução seguinte começar. Duas execuções sobre
o mesmo enunciado repetem os mesmos erros com a mesma probabilidade.

O único conhecimento que de fato se acumulou no pipeline está **escrito à mão** na seção
`# ERROS COMUNS — EVITE A TODO CUSTO` do prompt do coder
(`adk/src/agents/workflow_coding_review/coder/prompt.py:340`): lições reais de execuções
passadas que alguém observou, generalizou e transcreveu para uma string. O mecanismo funciona
— e é justamente por funcionar que serve de evidência de que o caminho tem valor. O que ele
não tem é automação: cada lição custa um humano lendo log.

O objetivo desta frente é automatizar esse caminho — com uma restrição de desenho vinda da
avaliação anterior da equipe: **conhecimento não pode viver acoplado ao código**, sob pena de
evoluir a base exigir um ciclo de PR, build e deploy.

---

## 2. Levantamento das técnicas

### 2.1 A distinção que organiza o campo

A literatura recente separa memória que **guarda conversa** (trajetória bruta, histórico,
perfil do usuário) de memória que **aprende com a experiência** (destila lição reusável). O
survey *From Storage to Experience* (Findings of ACL 2026) formaliza a evolução em três
estágios:

| Estágio | O que faz com a trajetória |
|---|---|
| **Storage** | preservação — guarda a trajetória |
| **Reflection** | refinamento — reescreve ou melhora a trajetória |
| **Experience** | **abstração** — extrai da trajetória algo que vale para outras tarefas |

O problema deste relatório está inteiramente no terceiro estágio. Essa distinção não é
acadêmica: ela determina que boa parte das ferramentas populares de "agent memory" seja
irrelevante aqui (§4.3).

### 2.2 Comparativo por eixo

Quatro eixos importam para a decisão de desenho. O último — ciclo de vida da biblioteca — é o
que responde à restrição registrada em §1.

| Trabalho | Unidade de conhecimento | Sinal que decide o que vira conhecimento | Consolidação | Ciclo de vida da biblioteca |
|---|---|---|---|---|
| **EvoLib** | skills (funções/sub-workflows) + insights em linguagem natural | auto-avaliação: testes sintéticos, votação majoritária, juiz-LLM | fusão semântica por embedding + peso por ganho de informação | runtime (snapshots ao lado do log) |
| **ReasoningBank** | estratégias de raciocínio, de sucesso **e** de falha | auto-julgamento, sem rótulo externo | *append* linear | runtime |
| **ArcMemo** | conceitos modulares em linguagem natural | auto-geração + atualização em test-time | recuperação seletiva por relevância | runtime |
| **AutoRefine** | *experience patterns* (subagentes + guidelines) | execução em ambiente | **pontua, poda e funde** — anti-degradação explícita | runtime |
| **Memp** | memória procedural em dois níveis | execução | regime **Build / Retrieval / Update**, com deprecação | runtime |
| **SPARK** | skills ancoradas em evidência | grau de ancoragem em evidência de execução | intervenção online na formação da skill | runtime |
| **SkillWeaver** | APIs Python verificadas | testes gerados automaticamente + feedback do ambiente | *honing* e depuração da API | runtime |
| **Voyager** | código executável | auto-verificação + erro de execução do ambiente | biblioteca cresce indexada | runtime |
| **ReGAL** | funções extraídas por refatoração | execução | refatoração elimina redundância | biblioteca **é** artefato de código |
| **Dynamic Cheatsheet** | snippets concisos e transferíveis | auto-curadoria | reescrita holística | runtime |
| **AWM** | workflows / receitas de tarefa | offline com anotação; online sem dado auxiliar | indução incremental | runtime |
| **ExpeL** | insights + trajetórias bem-sucedidas | reflexão sobre tarefas de treino | — | offline/treino |

Duas leituras dessa tabela orientaram o desenho:

**(a) A biblioteca é estado de runtime em praticamente todo o campo.** Ela não é versionada
junto com o código nem viaja no deploy. As exceções — ReGAL e a família de *library learning*
clássico — são exceções por construção, porque ali a biblioteca literalmente é código-fonte.
Manter conhecimento declarativo dentro do repositório seria o caso fora da curva.

**(b) A coluna do sinal mostra onde este projeto tem vantagem.** Quase todos os trabalhos
aprendem de **auto-avaliação** porque não têm verdade de campo: o próprio modelo julga se a
trajetória foi boa. O pipeline de codificação **tem** verdade de campo — o `ExecutionReport`
do harness, com estágios determinísticos e `error_code`, e o `ValidationVerdict` do
`implementation_validator`, produzido sem LLM. Os trabalhos cuja coluna de sinal diz
"execução" (SPARK, ReGAL, Voyager, SkillWeaver, Memp, AutoRefine) são os que partem do mesmo
chão e, por isso, os mais informativos para nós.

### 2.3 Risco e governança

Três trabalhos tratam do que pode dar errado quando um agente escreve a própria memória, e os
três deixaram marca no desenho:

- **GovMem — *When Not to Write Memory*.** Política conservadora de referência que estima
  suporte, busca contra-evidência, atribui escopo e emite **três** vereditos: promover,
  rejeitar e *precisa-de-revisão*. Os autores relatam que, em adjudicação humana de
  candidatos vindos de agentes de código, **nenhum** era seguro para promoção automática, e
  que o volume real se concentra na fatia intermediária — tratá-la como binária é o que
  produz falsa promoção.
- **OEP — envenenamento por experiências localmente corretas.** Descreve como uma experiência
  verdadeira *naquela* execução pode ser danosa como regra geral, e nomeia três modos de
  falha; o mais relevante aqui é o *perspective confinement* — confundir acerto localizado com
  regra amplamente válida.
- **SkillLens.** Estudo empírico do ciclo geração → extração → consumo, que reporta
  **transferência negativa não-trivial**: skills geradas por modelo ajudam na média, mas
  pioram parte dos casos, e extrator forte não implica consumidor forte.

### 2.4 Nível de verificação desta seção

Registro metodológico, para que ninguém cite este relatório como se fosse leitura primária: a
seção acima resulta de **busca bibliográfica**, e o único trabalho cujo **código-fonte foi
lido** para esta implementação é o ReasoningBank. Os números atribuídos a outros trabalhos
são reportados por seus autores e **não foram reproduzidos aqui**. Antes de usar qualquer
número deste relatório como argumento em decisão de projeto, abra o artigo correspondente
(§8).

---

## 3. Arquitetura proposta

### 3.1 Visão geral

```
execução N   ─┬─> ExecutionReport + ValidationVerdict        (evidência determinística)
              ├─> extract.destilar()   ≤3 itens, prompts do ReasoningBank
              ├─> judge.julgar()       promover / revisar / rejeitar, sem LLM
              └─> store.append()       JSONL em AI4ES_MEMORY_DIR, fora do repositório
                                                  │
execução N+1 ─── retrieve.recuperar() ────────────┘   pré-filtro determinístico
              └─> render_bloco() → prompt do coder          + ranking por cosseno
```

O ciclo tem quatro etapas nomeadas, e cada uma é um módulo com responsabilidade única:

| Etapa | Onde | Como decide |
|---|---|---|
| **Captura** | `memory_writer/agent.py` | 4º passo do pipeline; lê `state["validation"]` e o `ExecutionReport` ao final de cada execução |
| **Destilação** | `shared/memory/extract.py` | prompts do ReasoningBank, teto de 3 itens, enquadramento distinto para sucesso e falha |
| **Julgamento** | `shared/memory/judge.py` | veredito **ternário**, determinístico, sem LLM |
| **Curadoria** | `MemoryStatus` | só `promovido` chega ao prompt; `revisar` fica em quarentena auditável |
| **Recuperação** | `shared/memory/retrieve.py` | pré-filtro por `error_code` e escopo, depois ranking por cosseno |

### 3.2 Módulos

| Arquivo (em `adk/`) | Responsabilidade |
|---|---|
| `shared/memory/schemas.py` | `MemoryItem`, `MemoryStatus` (ternário), `MemoryProvenance` |
| `shared/memory/store.py` | banco JSONL fora do repositório; deduplicação; escrita atômica; kill switch |
| `shared/memory/extract.py` | prompts do ReasoningBank + parser de markdown tolerante |
| `shared/memory/judge.py` | curadoria ternária determinística |
| `shared/memory/retrieve.py` | pré-filtro + cosseno + renderização do bloco injetado |
| `shared/memory/trajectory.py` | `ExecutionReport` + histórico + manifesto → texto para o destilador |
| `src/agents/workflow_coding_review/memory_writer/agent.py` | `BaseAgent` custom, 4º sub-agente do pipeline (`workflow_coding_review/agent.py:60`) |

O diff sobre o pipeline existente é pequeno de propósito: o `memory_writer` entra como quarto
`sub_agent`, e a `instruction` do coder passa a ser um `InstructionProvider` que **prefixa** o
bloco de memória à instrução base, sem editá-la.

### 3.3 Quatro decisões de desenho, com o motivo

**(a) O banco vive fora do repositório e fora do workspace.** Em `AI4ES_MEMORY_DIR` (default
`~/.ai4es/memory/bank.jsonl`). Fora do workspace porque é a condição técnica sem a qual não
existe memória entre execuções — o `rmtree` de §1 apagaria tudo. Fora do repositório porque
conhecimento acoplado ao código exige ciclo de deploy para evoluir, e porque o levantamento
(§2.2a) mostra que o campo inteiro trata a biblioteca como estado de runtime. Endereçável por
variável de ambiente porque trocar de banco — ou zerá-lo para um braço de controle — não pode
exigir mudança de código.

**(b) O julgamento é determinístico e ternário.** Não há LLM no caminho de curadoria: o
julgador lê `error_code` do harness e os critérios reprovados do `ValidationVerdict`. Ternário
por causa do GovMem (§2.3): o default é a **quarentena**, e a promoção é o caso excepcional.
Um item sem escopo declarado não é promovido — regra que vem diretamente do *perspective
confinement* descrito pelo OEP.

**(c) O `memory_writer` é um `BaseAgent` custom, não um `LlmAgent`.** Um `LlmAgent` no papel
de escrita reproduziria dois modos de falha já observados neste pipeline: o agente que
**anuncia** a ação em texto e encerra o turno sem chamar a ferramenta, e o `output_schema` que
não é imposto ao provedor. Aqui **só a destilação** consulta o LLM; julgamento, escrita e
recuperação são Python puro.

**(d) O contrato de saída do destilador é markdown, não JSON.** É o formato do próprio
ReasoningBank, e a escolha tem consequência prática direta: sob o provedor atual o
`response_format` é descartado silenciosamente pelo cliente LiteLLM (`litellm.drop_params`),
de modo que um `output_schema` Pydantic valida **depois do fato** e derruba a execução quando
o modelo responde em prosa. Um parser de cabeçalhos markdown **degrada** — extrai o que
reconhece e ignora o resto — em vez de derrubar.

### 3.4 Recuperação: pré-filtro antes do vetor

O algoritmo de ranking é o do ReasoningBank — embutir a consulta, normalizar em L2, ranquear
por similaridade de cosseno, devolver o top-k. O que foi acrescentado é um **pré-filtro
determinístico** que roda antes:

- **Escopo:** item de outra stack é descartado; item genérico passa. Quando a stack da
  execução corrente é desconhecida, o filtro fica **mais** restritivo, não menos — só passam
  itens genéricos. Injetar lição de uma stack em projeto de outra é exatamente o
  *perspective confinement* do OEP.
- **`error_code`:** se a execução corrente falhou com códigos conhecidos, os itens que citam
  algum deles são relevantes **por construção**, não por proximidade de vetores. A
  similaridade entra depois, para ordenar o que sobrou e para cobrir o caso em que não há
  erro algum — que é a primeira execução.

Esse pré-filtro é possível justamente pela verdade de campo de §2.2b, e é a diferença de
desenho mais relevante em relação ao trabalho de origem.

### 3.5 Configuração

| Variável | Default | Para quê |
|---|---|---|
| `AI4ES_MEMORY_ENABLED` | `1` | Kill switch. Com `0`, injeção e escrita viram no-op e o pipeline volta a ser o de origem — é o braço de controle de qualquer comparação |
| `AI4ES_MEMORY_DIR` | `~/.ai4es/memory` | Onde o banco vive |
| `AI4ES_MEMORY_TOP_K` | `5` | Quantos itens entram no prompt |
| `AI4ES_MEMORY_EMBED_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Modelo de embedding |
| `AI4ES_MEMORY_TIMEOUT` | `90` | Timeout da destilação |

### 3.6 Degradação

A camada é acessório do prompt, não pré-requisito de execução, e todo caminho de falha
degrada em vez de propagar:

| Falha | Comportamento |
|---|---|
| Modelo de embedding indisponível (sem rede, download bloqueado) | recuperação cai para o pré-filtro determinístico + ordenação por recência; a falha é cacheada para não retentar a cada turno |
| LLM da destilação fora do ar, ou resposta ininteligível | nenhum item é escrito; a execução segue |
| `ExecutionReport` ausente ou ilegível | o passo de memória informa que não há o que aprender e encerra |
| Banco inexistente ou linha corrompida no JSONL | linha ignorada com aviso; o resto do banco carrega |
| `AI4ES_MEMORY_ENABLED=0` | injeção e escrita viram no-op |

---

## 4. Ferramentas avaliadas

### 4.1 Implementação de referência

| Ferramenta | Veredito | Por quê |
|---|---|---|
| **ReasoningBank** (Google, Apache-2.0) | **Adotada como base** | É o único trabalho do levantamento com implementação de referência **no nosso domínio** (variante para SWE-Bench). Dela vieram, sem edição, as instruções de sistema de destilação para sucesso e para falha, o contrato do item (`Title`/`Description`/`Content`), o teto de 3 itens por trajetória e o algoritmo de recuperação. Os prompts estão reproduzidos com atribuição no cabeçalho de `extract.py` |
| **EvoLib** (MIT) | Parcialmente | A ideia de consolidação semântica é a direção certa (§6), mas o mecanismo de pesagem por ganho de informação exige fluxo longo de tarefas curtas para ter significância estatística — não é o nosso regime |
| **Memp**, **AutoRefine** | Referência de desenho | Regime de *update*/deprecação e o mecanismo de poda-e-fusão são o modelo do que falta (§6), não do que foi implementado |
| **SPARK** | Referência de desenho | O índice de ancoragem em evidência é o critério de **qualidade** que o julgador atual não tem (§6, G4) |

### 4.2 Backend de embedding

O trabalho de origem usa `torch` + `transformers` com um modelo de 8B parâmetros, ou um SDK de
nuvem. Nenhum dos dois serve aqui:

| Opção | Veredito | Por quê |
|---|---|---|
| `torch` + `transformers` (modelo 8B) | Descartada | ~16 GB de download e dependência pesada para uma função acessória |
| SDK de nuvem do provedor original | Descartada | Exigiria credencial de outro provedor num projeto que já autentica em outro lugar |
| **`fastembed`** (ONNX, CPU) | **Adotada** | Já declarada e instalada no projeto — e, até esta frente, **não importada por nenhum módulo**. Roda em CPU, não arrasta `torch`, e o modelo multilíngue de ~120 MB é adequado a conteúdo em português. O algoritmo de recuperação continua sendo o do ReasoningBank; só o backend mudou |

### 4.3 Infraestrutura de memória de uso geral

**Mem0, Letta (ex-MemGPT), Zep/Graphiti, A-MEM, Cognee, LangMem** — todas avaliadas e
**descartadas**, por motivo estrutural e não de qualidade. A unidade de conhecimento delas é o
fato conversacional ou o episódio: extraem, consolidam e recuperam informação de diálogo, para
personalização. Pela taxonomia de §2.1 estão no estágio **Storage**, algumas tocando
*Reflection*. São infraestrutura de persistência — úteis se um dia o banco precisar de backend
com recuperação em escala, irrelevantes para o problema de **julgar o que merece virar
conhecimento**, que é o problema desta frente.

### 4.4 Persistência

| Opção | Veredito | Por quê |
|---|---|---|
| **JSONL + reescrita atômica** | **Adotada** | Mesmo formato do trabalho de origem; o banco é pequeno (dezenas de itens) e a reescrita completa mantém o arquivo sempre válido, mesmo se o processo morrer no meio. Legível e editável à mão, o que importa numa camada em avaliação |
| Banco vetorial dedicado | Adiada | Desnecessária no N atual; vira pertinente se o banco passar da ordem de dezenas de itens (§6, G2) |
| SQLite | Descartada | Ganho nulo nesta escala e perde a inspeção trivial por linha |

### 4.5 Avaliação

**SWE-Bench-CL** — benchmark de *continual learning* para agentes de código, com métricas de
*forgetting* e de transferência entre tarefas — foi identificado como o instrumento adequado
para medir retenção ao longo de várias execuções, e **não foi aplicado** nesta frente (§5.4).

---

## 5. Análise de viabilidade

### 5.1 Viabilidade técnica — a camada roda

A implementação está completa e exercitada em execução real do pipeline, não apenas em teste.
Foi conduzido um experimento A/B com dois braços — banco frio e banco quente —, mesmo enunciado
byte a byte, requisitos e design **congelados** e semeados nos dois braços para que a única
variável fosse o banco:

| | Braço A (memória fria) | Braço B (memória quente) |
|---|---|---|
| Arquivos gerados pelo coder | 44 | 54 |
| Iterações até `sucesso` do harness | 5 | 4 |
| Veredito do validador | reprovado | reprovado |
| Itens destilados → promovidos | 3 → 3 | 3 → 3 |
| Banco ao final | 3 itens | 6 itens |

**O ciclo fecha:** os três itens escritos no braço A foram recuperados e injetados no prompt do
coder no braço B, e o registro de uso ficou gravado no próprio banco — evidência durável, que
não depende de log. O diretório de trabalho do repositório permaneceu limpo durante os dois
braços: o conhecimento nunca entrou no código.

Cobertura automatizada: **119 testes** em seis arquivos `tests/unit/test_memory_*.py`, dentro
de uma suíte de **543 testes passando**. Cobrem o parser do formato de destilação (entrada
truncada, cercada em bloco de código, sem cabeçalho, acima do teto de itens), os três
vereditos do julgador, round-trip e deduplicação do banco, o pré-filtro por escopo e por
`error_code`, o ranking, todos os caminhos degradados de §3.6, o kill switch e o ciclo
completo "execução A escreve → execução B lê".

### 5.2 Custo

| Dimensão | Custo | Observação |
|---|---|---|
| Chamadas de LLM | **+1 por execução** | Só a destilação. Julgamento, escrita e recuperação não usam LLM |
| Tokens de entrada do coder | o bloco de memória, limitado por `AI4ES_MEMORY_TOP_K` (default 5 itens curtos) | O bloco declara-se subordinado ao contrato da tarefa, para não competir com ele |
| Embedding | modelo de ~120 MB baixado **uma vez**; inferência em CPU | Sem rede, a camada degrada em vez de falhar |
| Latência por turno do coder | leitura do banco + embedding dos candidatos | Aceitável na escala atual; recomputar embeddings a cada turno é um gargalo conhecido (§6, G6) |
| Armazenamento | dezenas de KB | JSONL fora do repositório |

### 5.3 Viabilidade operacional

Não há pré-requisito de infraestrutura novo: a camada não exige container, serviço externo,
banco de dados nem credencial adicional. É desligável por variável de ambiente, o que também a
torna trivialmente comparável contra a ausência dela. O pacote **não** importa o módulo de
sandbox do harness — evita, de propósito, arrastar dependências específicas de plataforma para
dentro de uma camada acessória.

### 5.4 Limites da evidência — o que este trabalho **não** estabelece

Registrado explicitamente para que o resultado não seja lido além do que sustenta:

- **Não mede desempenho.** n=1 por braço. A queda de 5 para 4 iterações é **indício na direção
  esperada, não resultado**: com um único par não há como separar efeito da memória de
  variância do modelo entre execuções.
- **Não testa retenção ao longo de várias execuções.** Houve um único salto entre execuções;
  *forgetting* e transferência exigiriam a instrumentação de §4.5.
- **Não avalia qualidade das lições** por outro critério além do formal do julgador — e
  justamente aí apareceu o achado mais informativo do experimento (§6, G4).
- **Não valida o efeito sobre o veredito final.** Os dois braços terminaram reprovados pelo
  validador. A memória influenciou o percurso, não o desfecho.

### 5.5 Riscos

| Risco | Evidência | Mitigação atual |
|---|---|---|
| **Transferência negativa** — a memória piorar o resultado | Documentada pelo SkillLens e **observada aqui** (§6, G4) | Kill switch; bloco declarado como aviso, não requisito |
| **Envenenamento por lição localmente correta** | OEP | Escopo obrigatório por stack; promoção exige ancoragem em evidência determinística |
| **Falsa promoção em escala** | GovMem | Veredito ternário com quarentena como default |
| **Degradação do banco com o crescimento** | AutoRefine, Memp | **Não mitigado** — é o gap G1/G2 |

---

## 6. Principais gaps identificados

Ordenados por impacto sobre a decisão de adotar.

**G1 — Não há consolidação semântica.** A deduplicação é por identificador derivado do título
normalizado: o caso degenerado da consolidação. Dois itens que dizem a mesma coisa com
palavras diferentes coexistem, e ambos podem ser injetados, gastando espaço do bloco com
redundância. É o mecanismo que EvoLib e AutoRefine implementam e que aqui está declarado como
evolução posterior, não como requisito.

**G2 — Não há deprecação nem esquecimento.** Nenhum decaimento temporal, nenhuma remoção de
item que envelheceu ou que se tornou falso. O banco só cresce. É o regime de *update* do Memp,
fora do escopo atual.

**G3 — Utilidade é registrada, mas não pondera.** O banco guarda em quais execuções cada item
foi injetado — deliberadamente uma lista de identificadores, não um contador, para que
"injetado na execução R" possa ser cruzado com "a execução R passou". Esse cruzamento **ainda
não é feito**: o ranking é por similaridade, não por utilidade medida. O dado necessário está
sendo coletado; falta o consumidor.

**G4 — O julgador afere ancoragem, não qualidade.** É o achado empírico mais importante do
experimento: no braço com memória quente, as lições produzidas saíram **visivelmente mais
fracas** que as do braço frio — as primeiras citam artefato e critério pelo nome, as segundas
beiram o truísmo ("trabalhar em ciclos curtos até convergir") — e **o julgador promoveu as
três**, porque elas satisfazem todos os critérios formais: têm escopo, têm rastro, citam
critérios reprovados. A hipótese mais plausível é que, com as lições anteriores já no prompt,
a instrução de não repetir itens sobrepostos empurre o modelo para um registro mais abstrato.
O efeito é o que o SkillLens descreve como transferência negativa, e a resposta apontada pela
literatura é um índice de ancoragem graduado (SPARK) em vez do critério binário atual.

**G5 — A injeção é global, não alinhada ao passo de decisão.** O bloco entra inteiro no topo
do prompt do coder. Há indicação na literatura de que injeção alinhada ao momento da decisão
rende mais que injeção global — hipótese testável e barata, não implementada.

**G6 — Os embeddings do banco são recomputados a cada turno.** A recuperação roda uma vez por
turno do coder e embute a consulta **e todos os candidatos** a cada chamada. Na escala atual
(dezenas de itens) o custo é aceitável; ele cresce linearmente com o banco. Cachear o vetor por
identificador de item é uma correção contida, e torna-se necessária antes de qualquer aumento
de escala.

**G7 — A camada depende de um contrato que nem sempre chega ao disco.** O escopo do item (a
stack do produto) vem do contexto macro produzido pela etapa anterior do pipeline. Quando esse
artefato não é persistido, a camada recorre ao estado da sessão como fonte de reserva — o que
resolve o sintoma, mas mantém a dependência de um artefato produzido por LLM. Um contrato
verificável entre as etapas eliminaria a classe inteira.

**G8 — Não há ritual de revisão da quarentena.** Itens em `revisar` acumulam sem que ninguém
seja obrigado a olhá-los. A quarentena é auditável por construção, mas auditoria que não
acontece não é curadoria.

---

## 7. Recomendações de adoção

### 7.1 Adotar agora

1. **Incorporar a camada com o kill switch documentado**, banco por desenvolvedor, fora do
   repositório. O custo é de uma chamada de LLM por execução e o risco é contido: qualquer
   caminho de falha degrada, e `AI4ES_MEMORY_ENABLED=0` restaura o comportamento anterior byte
   a byte.
2. **Tratar o bloco de memória como aviso, nunca como requisito.** Já é o que o texto injetado
   declara: em conflito com o contrato da tarefa, o contrato vence. Manter essa subordinação
   explícita em qualquer evolução do prompt.
3. **Manter a quarentena como default.** A promoção automática de todo candidato é
   precisamente o que a literatura de governança desaconselha para agentes de código.

### 7.2 Fazer antes de tirar conclusão de desempenho

4. **Repetir o experimento com n suficiente** e enunciados distintos, com entrada congelada e
   braço de controle, antes de qualquer afirmação sobre ganho. O resultado atual é indício.
5. **Adotar métricas de aprendizado contínuo** (§4.5) para medir retenção e transferência ao
   longo de várias execuções, em vez de um único salto.
6. **Prever por escrito que o braço com memória pode sair pior** — é fenômeno documentado, e
   registrá-lo antes do experimento evita que um resultado negativo seja lido como defeito de
   implementação.

### 7.3 Próximas evoluções, em ordem de retorno

7. **Dimensão de qualidade no julgador (G4).** É o gap com evidência empírica própria e o de
   maior impacto: sem ele, o banco tende a encher de lições genéricas que passam nos critérios
   formais.
8. **Consolidação semântica (G1)** e **cache de embedding por item (G6)** — ambas viram
   necessárias quando o banco crescer; a segunda é contida e pode ser feita a qualquer momento.
9. **Cruzar uso com desfecho (G3)** para ranquear por utilidade medida em vez de similaridade.
   O dado já está sendo coletado; falta o consumidor.
10. **Experimentar injeção alinhada ao passo de decisão (G5)** contra o bloco único atual.

### 7.4 Não adotar agora

- **Infraestrutura de memória de uso geral** (§4.3): resolve persistência, não curadoria.
- **Banco vetorial dedicado:** desnecessário na escala atual.
- **Pesagem por ganho de informação nos moldes do EvoLib:** exige um regime de execução que
  não é o nosso; sem fluxo longo de tarefas curtas, o estimador não tem significância.
- **Promoção automática sem dimensão de qualidade:** ver G4.

---

## 8. Referências

**Implementação de referência**

- ReasoningBank — [google-research/reasoning-bank](https://github.com/google-research/reasoning-bank)
  (Apache-2.0) · [blog](https://research.google/blog/reasoningbank-enabling-agents-to-learn-from-experience/)

**Taxonomia e levantamento**

- *From Storage to Experience: A Survey on the Evolution of LLM Agent Memory Mechanisms* — Findings of ACL 2026 · [arXiv 2605.06716](https://arxiv.org/abs/2605.06716)
- EvoLib — *Test-Time Learning with an Evolving Library* · [arXiv 2605.14477](https://arxiv.org/abs/2605.14477) · [microsoft/EvoLib](https://github.com/microsoft/EvoLib)

**Governança e risco**

- GovMem — *When Not to Write Memory* · [arXiv 2607.02579](https://arxiv.org/abs/2607.02579)
- SkillLens — *From Raw Experience to Skill Consumption* · [arXiv 2605.23899](https://arxiv.org/abs/2605.23899) · [microsoft/SkillLens](https://github.com/microsoft/SkillLens)
- OEP — *Poisoning Self-Evolving LLM Agents via Locally Correct but Non-Transferable Experiences* · [arXiv 2605.18930](https://arxiv.org/abs/2605.18930)
- SSGM — *Governing Evolving Memory in LLM Agents* · [arXiv 2603.11768](https://arxiv.org/abs/2603.11768)

**Desenho de destilação, consolidação e avaliação**

- SPARK — *Evidence Over Plans: Online Trajectory Verification for Skill Distillation* · [arXiv 2605.09192](https://arxiv.org/abs/2605.09192)
- Memp · [zjunlp/MemP](https://github.com/zjunlp/MemP) — regime Build / Retrieval / Update
- AutoRefine · [arXiv 2601.22758](https://arxiv.org/abs/2601.22758) — pontuação, poda e fusão de padrões
- ArcMemo · [matt-seb-ho/arc_memo](https://github.com/matt-seb-ho/arc_memo)
- SkillWeaver · [OSU-NLP-Group/SkillWeaver](https://github.com/OSU-NLP-Group/SkillWeaver)
- Voyager · [MineDojo/Voyager](https://github.com/MineDojo/Voyager)
- ReGAL · [esteng/regal_program_learning](https://github.com/esteng/regal_program_learning)
- Dynamic Cheatsheet · [suzgunmirac/dynamic-cheatsheet](https://github.com/suzgunmirac/dynamic-cheatsheet)
- AWM · [zorazrw/agent-workflow-memory](https://github.com/zorazrw/agent-workflow-memory)
- ExpeL · [LeapLabTHU/ExpeL](https://github.com/LeapLabTHU/ExpeL)
- SWE-Bench-CL · [thomasjoshi/agents-never-forget](https://github.com/thomasjoshi/agents-never-forget)

> Ver §2.4 sobre o nível de verificação destas referências.
