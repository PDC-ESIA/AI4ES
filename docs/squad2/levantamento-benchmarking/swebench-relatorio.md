# Relatório: benchmark SWE-bench Verified do loop coder → executor

Issue: #417 · Código: [`benchmarks/coding_review/swebench/`](../../../benchmarks/coding_review/swebench/README.md) · Run de referência: `benchmarks/coding_review/swebench/results/run_20261001_122939_github_copilot-gemini-3.7-flash_n30/`

Este relatório reúne, num só lugar, o que o benchmark mede e por quê, como funciona, como foi construído, o que se obteve na linha de base e o que cuidar ao interpretar os números. As seções são independentes: quem só quer os números vai direto à seção 4; quem vai usar ou alterar o código, às seções 2 e 3; quem vai citar um resultado, à seção 5.

## Sumário

- [Resumo executivo](#resumo-executivo)
- [1. Contexto e escolha do benchmark](#1-contexto-e-escolha-do-benchmark)
  - [1.1 Por que um benchmark para o executor](#11-por-que-um-benchmark-para-o-executor)
  - [1.2 O que foi levantado](#12-o-que-foi-levantado)
  - [1.3 Por que o SWE-bench Verified](#13-por-que-o-swe-bench-verified)
- [2. Como o benchmark funciona](#2-como-o-benchmark-funciona)
  - [2.1 O que está sendo avaliado](#21-o-que-está-sendo-avaliado)
  - [2.2 O que é o SWE-bench Verified](#22-o-que-é-o-swe-bench-verified)
  - [2.3 Fluxo de uma instância](#23-fluxo-de-uma-instância)
  - [2.4 As três métricas](#24-as-três-métricas)
  - [2.5 Checagens que não usam LLM](#25-checagens-que-não-usam-llm)
  - [2.6 Como rodar](#26-como-rodar)
- [3. Implementação](#3-implementação)
  - [3.1 Visão geral dos módulos](#31-visão-geral-dos-módulos)
  - [3.2 O caminho de uma instância](#32-o-caminho-de-uma-instância)
  - [3.3 Decisões de desenho](#33-decisões-de-desenho)
  - [3.4 Cobertura de testes](#34-cobertura-de-testes)
- [4. Resultados da linha de base](#4-resultados-da-linha-de-base)
  - [4.1 Configuração do run de referência](#41-configuração-do-run-de-referência)
  - [4.2 Resultados (n = 26)](#42-resultados-n--26)
  - [4.3 Custo e tempo](#43-custo-e-tempo)
  - [4.4 Como se chegou a esse resultado](#44-como-se-chegou-a-esse-resultado)
  - [4.5 Ressalvas para a leitura](#45-ressalvas-para-a-leitura)
  - [4.6 Por que o `gemini-3.7-flash` foi o modelo da linha de base](#46-por-que-o-gemini-37-flash-foi-o-modelo-da-linha-de-base)
- [5. Pontos de atenção](#5-pontos-de-atenção)
  - [5.1 Limites da medição (previsíveis)](#51-limites-da-medição-previsíveis)
  - [5.2 O que apareceu ao executar](#52-o-que-apareceu-ao-executar)
  - [5.3 Checklist: antes de citar um número deste benchmark](#53-checklist-antes-de-citar-um-número-deste-benchmark)
- [6. Conclusões e próximos passos](#6-conclusões-e-próximos-passos)
- [7. Arquivos e referências](#7-arquivos-e-referências)
  - [7.1 Código e dados](#71-código-e-dados)
  - [7.2 Fontes externas](#72-fontes-externas)
  - [7.3 Nota de escolha do benchmark](#73-nota-de-escolha-do-benchmark)

## Resumo executivo

O `workflow_coding_review` implementa código num laço com três papéis: o `cr_coder_agent` gera, o `cr_executor_agent` verifica rodando o harness, e o `implementation_validator` (chamado pelo executor) julga se a implementação está aprovada; uma política de progresso decide quando parar. Só o coder tinha benchmark (HumanEval e MBPP). Este trabalho criou uma linha de base para o **loop inteiro**, usando o SWE-bench Verified: issues reais de projetos Python, corrigidas pelo harness oficial do SWE-bench com testes escondidos. Nada no executor, no validador ou na `loop_policy` foi alterado: o benchmark mede, não corrige.

**Resultado da linha de base** (`github_copilot/gemini-3.7-flash`, 26 das 30 instâncias sorteadas, execução única):

| Métrica | Valor |
| ------- | ----- |
| 1. Taxa de resolução | **20/26 (76,9%)**, IC 95%: 57,9% a 89,0% |
| 2. Rodadas e parada | Média 1,65 rodadas (mediana 1). 24 paradas por aprovação do validador, 2 por política de progresso, 0 por `max_iterations` |
| 3. Falsos positivos do validador | **5/24 aprovações (20,8%)**, IC 95%: 9,2% a 40,5%. Precisão 79,2%, recall 95% (19/20) |

> **Leia antes de citar qualquer número.** A linha de base cobre **26 das 30 instâncias sorteadas**: as outras 4 não foram refeitas após uma correção do benchmark, por falta de créditos do LLM. É **uma execução de um único modelo**, com amostra pequena. A taxa de resolução tende a estar **inflada**, porque saíram da amostra instâncias que o loop resolvia pior; o efeito sobre a precisão do validador é incerto. No primeiro passe, com as 30 instâncias e antes da correção do teto, o resultado era 20/30 (66,7%). Os dois números não são comparáveis.

> **Pendências frente à #417.** A issue pede "um run completo com **30 instâncias**" e uma linha de base **reproduzível**. Este baseline cobre 26 de 30 e não é reproduzível a partir de um único commit limpo (ver B9). Por isso o critério de aceite "run completo com 30 instâncias" **não está atendido** até as 4 instâncias restantes serem rodadas, idealmente num run único a partir de um commit limpo (ver próximos passos).

O que os números sustentam, com essas ressalvas:

- O loop resolveu cerca de três em cada quatro instâncias, na maioria das vezes na primeira rodada.
- Quando o validador aprovou, errou uma vez em cada cinco. Ele aprovou 24 das 26 instâncias e deixou de aprovar só 2: uma não resolvida e a `django-12125`, que o harness oficial resolve (ver 4.2), então o recall (95%) discrimina pouco.
- A política de progresso foi acionada em 2 casos, ambos em Django: um não resolvido (`django-16032`) e a `django-12125`, que o harness oficial resolve (o coder acertou o código, mas a suíte dele ficou vermelha, provavelmente por um teste existente que a correção torna obsoleto; ver 4.2). Nenhuma instância chegou ao teto de 20 rodadas.
- O ambiente do executor reprova até a solução oficial em 4 das 30 instâncias, o que limita o teto de aprovações confiáveis a cerca de 26 em 30.

**Modelo:** o `gemini-3.7-flash` foi escolhido por restrição de contexto e custo, depois que o `gpt-4` (32k) e o `gpt-4.1` (128k, bloqueado pelo rate limit do Copilot) não serviram; não é um ranking de modelos (ver [4.6](#46-por-que-o-gemini-37-flash-foi-o-modelo-da-linha-de-base)).

**Custo:** ~4.340 créditos do Copilot (~US$ 43) tirados do caixa da organização, bem acima do esperado, porque o coder reenvia a conversa inteira a cada chamada. **Três lições operacionais** pesam mais que os números: o controle de ritmo do próprio benchmark distorceu o teto de tempo por instância (corrigido); o rate limit do Copilot é de vazão, independente dos créditos; e o harness oficial reaproveitava o resultado de um patch antigo ao refazer uma instância, o que afetou a `django-12125` (apontado na revisão do PR, corrigido e regerado; ver B11).

## 1. Contexto e escolha do benchmark

### 1.1 Por que um benchmark para o executor

O `cr_coder` já tinha benchmarks de geração (HumanEval e MBPP), mas o `cr_executor`, o `implementation_validator` e a política de parada do loop (`executor/loop_policy.py`) não tinham medição nenhuma. O executor não gera código: ele **verifica** e, por meio do validador, **julga** o que o coder produziu e decide quando o loop para. Por isso métricas de geração como o pass@k não servem para ele. O que interessa é quanto o sinal de "aprovado" corresponde à realidade e como o loop gasta as suas rodadas.

### 1.2 O que foi levantado

Referências internas: os benchmarks de outras squads, que separam os resultados por dataset e nunca fundem métricas de fontes diferentes (Agente de QA, Fases 3 e 4); o harness LLM-as-a-Judge do Agente de Requisitos (`time1/benchmarking`); e o protocolo de avaliação comparativa de LLMs.

Candidatos externos avaliados para as funcionalidades do executor:

| Candidato | Cobriria | Situação |
| --------- | -------- | -------- |
| **SWE-bench Verified** | Juiz + harness + loop completo, com bugs reais e gabarito executável | **Escolhido** para a linha de base |
| CodeJudgeBench (split CodeRepair) | Julgamento de correção, sem execução | Fora do escopo da #417 |
| SlopCodeBench, AgentBoard (progress rate) | Dinâmica de iterações e platô | Fora do escopo da #417 |
| CUDABeaver, VRR-Stop | Sinais de estagnação e critério de parada | Fora do escopo da #417 |

Pela issue #417, os demais só entram em issue separada, **depois** da linha de base.

### 1.3 Por que o SWE-bench Verified

- São issues reais de projetos Python populares, revisadas por humanos, com gabarito executável (`FAIL_TO_PASS` e `PASS_TO_PASS`) e harness oficial (nada de reimplementar a correção).
- Rodando o loop do workflow sobre cada issue, um único dataset mede as três coisas pedidas: resolução, rodadas e motivo de parada, e concordância do validador.
- A arquitetura bate com a nossa: evidência determinística (testes) separada do veredito, como o harness (sensor) e o validador (juiz) do executor.
- Os testes do gabarito foram escritos por desenvolvedores humanos, então servem de evidência **independente** do coder.

As limitações assumidas (amostra de 30 instâncias, gabarito imperfeito, dataset só com projetos Python, possível contaminação dos modelos e aprovação do validador baseada na suíte que o próprio coder declara) estão detalhadas na [seção 5](#5-pontos-de-atenção). A nota resumida desta escolha continua em [swebench-verified-loop-coder-executor.md](swebench-verified-loop-coder-executor.md).

## 2. Como o benchmark funciona

Esta seção explica o que o benchmark mede e como, assumindo que o leitor não conhece o SWE-bench.

### 2.1 O que está sendo avaliado

O workflow `workflow_coding_review` implementa código em um laço
(`_code_execute_loop`) com três papéis. O laço tem **dois agentes**, o coder e o
executor; o validador é chamado pelo executor, como ferramenta, dentro do turno
dele:

| Papel | Agente | O que faz |
| ----- | ------ | --------- |
| Gerar | `cr_coder_agent` | Lê o repositório, edita arquivos e escreve testes |
| Verificar | `cr_executor_agent` | Roda o *harness* (build e testes) e junta as evidências |
| Julgar | `implementation_validator` (chamado pelo executor) | Decide, com as evidências, se a implementação está aprovada |

Cada passada do coder seguida do turno do executor é uma **rodada**.

Uma **política de progresso** (`executor/loop_policy.py`) decide quando parar
mesmo sem aprovação: a nota que o executor calcula a cada rodada estagnou, o
mesmo erro se repetiu, nenhum arquivo foi alterado, ou o orçamento de falhas
distintas acabou. Há ainda um teto de rodadas (`AI4ES_MAX_LOOP_ITERATIONS`,
padrão 20).

O `cr_coder` já tinha benchmarks de geração (HumanEval e MBPP). O executor, o
validador e a política de parada não tinham nenhum. O executor não gera código:
ele **verifica** e, por meio do validador, **julga**. Por isso a pergunta deste benchmark não é "o código gerado está
certo?", e sim:

1. O loop completo resolve problemas reais? (**métrica 1**)
2. Quantas rodadas ele gasta e quem decide parar? (**métrica 2**)
3. Quando o validador diz "aprovado", o problema estava mesmo resolvido?
   (**métrica 3**)

> **O benchmark mede; não corrige.** Nenhum arquivo do benchmark altera o
> executor, o validador ou a `loop_policy`.

#### Glossário rápido

- **Harness:** script que roda o build e os testes e produz um relatório. Há dois:
  o **harness do executor** (parte da produção, usado dentro do loop) e o
  **harness oficial do SWE-bench**, que só corrige no final.
- **Plugin de guarda:** código exclusivo do benchmark que conta as rodadas e
  protege o ambiente de teste durante o loop.
- **Intervalo de Wilson (95%):** faixa em que a taxa verdadeira provavelmente
  está, dado o número de instâncias.
- **Falso positivo / falso negativo:** o validador aprovou algo que não estava
  resolvido / deixou de aprovar algo que estava.

### 2.2 O que é o SWE-bench Verified

O [SWE-bench Verified](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified)
reúne 500 issues reais de 12 projetos Python populares (Django, scikit-learn,
SymPy, matplotlib, astropy, pytest e outros), revisadas por humanos. Cada
instância traz:

- o **repositório num commit específico** (`base_commit`), onde o bug existe;
- o **texto da issue** (`problem_statement`), que é o único enunciado do problema;
- o **patch oficial** (a correção feita pelos mantenedores) e os **testes
  oficiais** (`test_patch`), escritos por humanos;
- duas listas de testes, o gabarito:
  - **`FAIL_TO_PASS`**: testes que falham no commit com o bug e devem passar
    depois da correção. Provam que o problema foi resolvido.
  - **`PASS_TO_PASS`**: testes que já passavam e devem continuar passando.
    Provam que a correção não quebrou nada.
- uma **imagem Docker oficial** com o repositório e as dependências já
  instaladas (`swebench/sweb.eval.x86_64.<id>`).

Uma instância está **resolvida** quando todos os `FAIL_TO_PASS` passam **e**
todos os `PASS_TO_PASS` continuam passando, medidos pelo **harness oficial** do
SWE-bench, com os testes escondidos do dataset. A correção nunca usa os testes
que o coder escreveu.

### 2.3 Fluxo de uma instância

```
 dataset ──sorteio (seed fixa)──► N instâncias (padrão 30)
                                     │
        ┌────────────────────────────┘
        ▼
  imagem oficial ──extrai /testbed──► workspace do coder  (+ Dockerfile do benchmark)
        │                                  │
        │   task montada só com a issue    ▼
        │            ┌────────── code_execute_loop ──────────┐
        │            │  coder ─► executor(harness) ─► validador │  rodadas até parar
        │            └───────────────────┬───────────────────┘
        │                                ▼
        │                 patch = diff do workspace
        ▼                                │
  harness oficial do SWE-bench ◄─────────┘   (depois de TODAS as instâncias)
        │
        ▼
  resolved / unresolved  ──►  métricas 1, 2 e 3  ──►  report.md / report.json
```

Em palavras:

1. **Preparação.** O código da instância é copiado de dentro da imagem oficial
   para a área de trabalho do coder, e o benchmark grava um `Dockerfile`, um
   `.dockerignore` e um `run.json` que fazem o harness do executor rodar os
   testes dentro de um container baseado na imagem oficial (ver
   [implementação](#3-implementação)).
2. **Task.** O coder recebe o texto da issue, as regras do ambiente e um
   contrato de entrega. O coder e o validador **nunca** veem o patch oficial, o
   `test_patch`, `FAIL_TO_PASS`, `PASS_TO_PASS` nem as dicas do dataset
   (`hints_text`).
3. **Loop.** O mesmo `code_execute_loop` da produção roda até parar sozinho.
   Cada turno do executor é uma **rodada**.
4. **Patch.** Ao final, o diff entre o estado inicial e o final do workspace é
   o patch da instância (sem arquivos do próprio benchmark, caches, nem os
   caminhos que o `test_patch` toca).
5. **Correção.** Só depois de todas as instâncias, os patches vão para o
   harness oficial, que aplica cada um na imagem original, roda os testes
   escondidos e diz `resolved` ou não.

### 2.4 As três métricas

| # | Métrica | Pergunta | Como é calculada |
| - | ------- | -------- | ---------------- |
| 1 | **Taxa de resolução** | Quantas instâncias o loop resolveu de fato? | `resolved` do harness oficial ÷ todas as instâncias do run, com intervalo de confiança de Wilson (95%) |
| 2 | **Rodadas e motivo de parada** | Quantas rodadas o loop gastou e quem mandou parar? | Contagem do plugin de guarda; motivo pela mesma `classificar_desfecho` da produção |
| 3 | **Concordância do validador** | Quando o validador aprovou, o bug estava resolvido? | Último veredito do validador × `resolved` oficial, em matriz de confusão |

#### Métrica 1: taxa de resolução

Patch vazio, patch que não aplica, timeout dos testes oficiais, erro de
avaliação, falha de preparação, falha do provedor de LLM e instância não
avaliada contam como **não resolvidas**, discriminadas no relatório com a
causa. O intervalo de Wilson é obrigatório na leitura: com
poucas instâncias, a taxa pontual engana.

#### Métrica 2: rodadas e motivo de parada

O motivo segue esta ordem de classificação:

1. veredito `aprovado` → **aprovação do validador**;
2. `bloqueado_*` ou `aceito_com_ressalvas_*` → **política de progresso**, com o
   sub-motivo (`plato_nota`, `erro_repetido`, `sem_alteracao_arquivos`,
   `orcamento_de_falhas_distintas`);
3. erro operacional, timeout ou estouro de contexto da instância → **outro**;
4. rodadas ≥ teto do loop → **`max_iterations`** (a produção não tem rótulo
   próprio para esse caso; ele aparece como `reprovado_apos_loop` ou
   `validation_ausente_ou_invalida`);
5. o resto → **outro** (por exemplo, o LLM do executor chamou `exit_loop` sem
   aprovação, ou o veredito ficou ausente).

#### Métrica 3: concordância do validador

A matriz cruza o que o validador decidiu com o gabarito oficial:

| | Resolvida (oficial) | Não resolvida (oficial) |
| --- | --- | --- |
| **Validador aprovou** | acerto | **falso positivo** |
| **Validador não aprovou** | falso negativo | acerto |

O **falso positivo** é o caso que a issue #417 quer medir: o loop encerrou com
"aprovado", mas o problema continuava lá. O relatório traz também precisão,
recall e a taxa de falsos positivos entre as aprovações, todos com intervalo
de confiança.

Cada aprovação é **qualificada**, porque o validador aprova pelo status técnico
da suíte que o **próprio coder** declarou:

| Qualificador | Significa |
| ------------ | --------- |
| `suite_vazia_ou_pulada` | Nenhum teste declarado (o harness aceita `PULADO`) |
| `patch_vazio` | Aprovou sem nenhuma mudança de código |
| `testes_nao_identificados` | Havia comandos de teste, mas o harness não reconheceu testes individuais (a leitura por teste só entende pytest; no run de referência, 13 aprovações caíram aqui: todas as de Django, 11 de 11, a de SymPy e a `astropy-7166`) |

Só entram na matriz instâncias com gabarito conhecido (`resolved`,
`unresolved` e `empty_patch`; patch vazio entra como não resolvido). Ficam de
fora: erro de avaliação, instância não avaliada, falha de preparação (o validador
nem rodou), falha do provedor de LLM (o loop não chegou ao fim) e instâncias que
nem o patch oficial consegue resolver no ambiente (`--gold-sanity`).

### 2.5 Checagens que não usam LLM

Antes de gastar chamadas ao modelo, três comandos validam o ambiente:

| Comando | O que valida | Resultado esperado |
| ------- | ------------ | ------------------ |
| `--dry-run` | Sorteio e mensagens que o coder receberia | Instâncias plausíveis; nada do gabarito nas mensagens |
| `--gold-sanity` | Aplica os patches **oficiais** no harness oficial | 100% resolvidas; as que falham têm problema de ambiente e são excluídas da métrica 3 |
| `--executor-sanity` | Aplica patch e testes oficiais no workspace e roda o **harness do executor** | Sucesso; onde não der, o ambiente do executor é o limite, e não o LLM |

O `--executor-sanity` dá um **teto aproximado de aprovações confiáveis** neste
ambiente: se o harness do executor reprova até a solução oficial rodando o
comando de teste oficial, uma aprovação naquela instância só acontece se o coder
declarar um comando mais estreito, e é menos confiável.

Na implementação (`executor_sanity.py`), o `--executor-sanity` usa o comando de
teste oficial extraído do `eval_script` do dataset e roda o harness de produção
do executor.

### 2.6 Como rodar

A partir da raiz do repositório, com o Python do venv do `adk/`:

```bash
# sorteio e sanidades (sem LLM). Todo comando sem --resume-dir cria um diretório
# novo em results/, inclusive o --dry-run: ele é o <run> dos comandos seguintes.
adk/.venv/bin/python -m benchmarks.coding_review.swebench.run --model <modelo> --limit 30 --dry-run
adk/.venv/bin/python -m benchmarks.coding_review.swebench.run --model <modelo> --limit 30 \
  --gold-sanity --resume-dir benchmarks/coding_review/swebench/results/<run>
adk/.venv/bin/python -m benchmarks.coding_review.swebench.run --executor-sanity \
  --resume-dir benchmarks/coding_review/swebench/results/<run>

# run completo (loop, correção e relatório); retomável com o mesmo --resume-dir
adk/.venv/bin/python -m benchmarks.coding_review.swebench.run --model <modelo> --limit 30 \
  --resume-dir benchmarks/coding_review/swebench/results/<run>
```

Também existem `--skip-grading` (só o loop) e `--grade-only` (só a correção e o
relatório, a partir do checkpoint). Pré-requisitos (Docker em máquina x86_64, ~70 GB de disco, venv separado do
harness oficial) e todas as flags estão no
[README do benchmark](../../../benchmarks/coding_review/swebench/README.md).

Cada run grava em `results/run_<timestamp>_<modelo>_n<N>/` o `report.md` (resumo
das três métricas), o `report.json` (registro completo por instância), o
`progress.jsonl` (checkpoint que permite retomar), os patches e os resultados
oficiais.

## 3. Implementação

Esta seção descreve **como o benchmark foi construído**: os módulos, o caminho de uma instância de ponta a ponta e as decisões de desenho, com o motivo de cada uma. A regra que guiou tudo: **o benchmark mede; não corrige**. Nada em `adk/` foi alterado, e o executor, o validador e a `loop_policy` rodam exatamente como na produção.

### 3.1 Visão geral dos módulos

| Módulo | Responsabilidade |
| ------ | ---------------- |
| `bootstrap.py` | `sys.path`, `.env`, modelo, workspace, mem0 desligado, providers LLM |
| `dataset.py` | Download e cache do parquet fixado; sorteio determinístico |
| `contract.py` | Task e mensagem ao coder, sem nada do gabarito |
| `environment.py` | Extração do `/testbed`, `Dockerfile`/`.dockerignore`/`run.json`, restauração |
| `snapshot.py` / `patch.py` | Fotografia git e extração do patch filtrado |
| `guard_plugin.py` | Plugin do `Runner`: rodadas, guarda do ambiente, uso de tokens, pausas |
| `loop_runner.py` | Roda o `code_execute_loop` numa instância e classifica o desfecho |
| `grading.py` | Predições, chamada ao harness oficial e leitura dos resultados |
| `executor_sanity.py` | Solução oficial + harness do executor (`--executor-sanity`) |
| `metrics.py` / `report.py` | As três métricas e o `report.md` |
| `run.py` | CLI, checkpoint e retomada, e os modos `--dry-run`, `--gold-sanity`, `--executor-sanity`, `--skip-grading`, `--grade-only` |

Completam o diretório: `_testutils.py` (utilitários dos testes, entre eles a
leitura de constantes da produção por AST), `conftest.py` e
`requirements-grading.txt` (dependências do venv da correção). Os testes ficam
ao lado (`test_*.py`) e rodam sem LLM, sem rede e sem imagens do
SWE-bench:

```bash
adk/.venv/bin/python -m pytest benchmarks/coding_review/swebench -q
```

### 3.2 O caminho de uma instância

Antes de qualquer instância, `run.py` (`main`) carrega as instâncias do parquet
fixado, confere a versão instalada do `swebench` (avisa se diferir da validada),
testa a conexão com o modelo e o Docker e grava o ambiente no `metadata.json`.
Depois executa as instâncias **uma por vez, sempre no mesmo workspace**, com um
checkpoint (`progress.jsonl`) gravado ao fim de cada uma.

1. **Isolamento.** `environment.clear_directory` zera o diretório do coder
   (`coder/`); o `seed_workspace` zera de novo o `coder/src/`.
2. **Preparação** (`environment.seed_workspace`). O `/testbed` é extraído de
   dentro da imagem oficial (SDK do Docker, `get_archive` + `tarfile` com
   filtro) para `coder/src/`. Em seguida o `snapshot.take_snapshot` tira a
   fotografia git do estado inicial, e `write_benchmark_files` grava
   `Dockerfile`, `.dockerignore` e `run.json`.
3. **Task.** `contract.build_task_contract` e `build_coder_message` montam a
   `TASK-001.json` e a mensagem a partir do `problem_statement`.
4. **Loop** (`loop_runner.run_loop`). Roda o `_code_execute_loop` num `App` do
   ADK com o plugin de guarda, sob o teto de trabalho por instância. O desfecho
   é classificado pela `classificar_desfecho` da produção. Se o provedor de LLM
   falhar, os passos 1 a 4 se repetem para a mesma instância (ver [3.3.8](#338-checkpoint-retomada-e-falhas)).
5. **Patch** (`patch.extract_patch`). Diff entre a fotografia e o estado final,
   gravado em `patches/<instance_id>.diff`.
6. **Registro.** Rodadas, desfecho, último veredito, evidências, ocorrências da
   guarda e uso de tokens entram no `progress.jsonl`.
7. **Correção** (`grading`), depois de todas as instâncias: `predictions.jsonl`
   → `swebench.harness.run_evaluation` → `resolved` por instância.
8. **Relatório** (`metrics.aggregate` e `report`): `report.json` e `report.md`.

### 3.3 Decisões de desenho

#### 3.3.1 Entrada do loop: ramo "projeto existente"

O benchmark roda o `_code_execute_loop` **direto**, e não pelo `TaskIterator`.
Na primeira task, o iterator apaga o `execution_result`, o que manda o coder
para o ramo "primeira execução" do prompt: criar `PLAN.md` e implementar o
projeto **completo**, o que não faz sentido diante de um repositório existente.

Em vez disso, o estado inicial reproduz o que o iterator monta da 2ª task em
diante: `execution_result` = marcador `NOVA_TASK:` e os arquivos do repositório
registrados como herdados (`preparar_arquivos_herdados(primeira=False)`), o que
impede o coder de sobrescrever arquivos inteiros. É o ramo que já roda em
produção, então nenhuma linha de produção muda. O custo é que o ramo de criação
de projeto do zero não é medido (ver
[pontos de atenção](#5-pontos-de-atenção), A5).

#### 3.3.2 O ambiente do executor

O harness do executor roda os testes num container pelo `DockerSandbox`. Para
isso rodar dentro do ambiente oficial da instância:

- O **`Dockerfile`** do benchmark parte da imagem oficial, põe o env conda
  `testbed` no `PATH` (o harness roda `/bin/sh -c`, que não ativa conda),
  apaga o `/testbed` original, copia o código editado para `/testbed` e faz de
  `/app` (onde o sandbox executa os comandos) um **symlink para `/testbed`**.
- O código fica em `/testbed`, **o mesmo caminho da avaliação oficial**, que é
  para onde aponta a instalação editável. A primeira versão fazia o contrário
  (código em `/app` e `/testbed` como link), e o pytest carregava o mesmo
  `conftest.py` por dois caminhos (erro de coleta no astropy). Inverter o link
  subiu o `--executor-sanity` de 23 para 26 sucessos em 30.
- O **`.dockerignore`** tira o `.git` do contexto de build, porque o sandbox
  reconstrói a imagem a cada rodada.
- O **`run.json`** declara `sandbox: docker` e `surface: none`; o campo `test`
  fica para o coder preencher.

#### 3.3.3 Guarda do ambiente

O prompt de sistema do coder manda usar `sandbox` direct e virtualenv, o que
executaria o repositório **no host**, sem as dependências. O plugin de guarda
(`guard_plugin.BenchmarkGuardPlugin`, só do benchmark) restaura `Dockerfile`,
`.dockerignore` e `sandbox: docker` antes de cada turno do executor e registra
cada restauração como violação, com a rodada. Restaurar o ambiente não altera o
julgamento, apenas impede que a rodada meça o ambiente errado.

#### 3.3.4 O plugin de guarda

O ADK executa os callbacks de plugin **antes** dos callbacks do agente, então o
plugin roda antes do gate de executabilidade e do harness do executor. Ele faz
cinco coisas:

1. **Conta as rodadas.** Um turno do executor é uma rodada, inclusive as
   recusadas pelo gate. A contagem é mais confiável que o
   `progress_score_history`, que perde a rodada quando `state['validation']`
   não é gravado.
2. **Guarda o ambiente** ([3.3.3](#333-guarda-do-ambiente)).
3. **Soma o uso de LLM por agente** em `after_model_callback`. O
   `implementation_validator` roda como `AgentTool` num `Runner` interno cujos
   eventos não chegam ao loop externo. Como o ADK propaga os plugins para esse
   `Runner` (`include_plugins=True`), só por aqui o consumo dele é contado.
4. **Pausa em rate limit do provedor** (`on_model_error_callback`). Espera e
   repete a **mesma** chamada, com backoff dobrando (60 s, 120 s, 240 s…) até o
   teto acumulado de 3600 s (na prática, cinco pausas: 60, 120, 240, 480 e 960 s;
   a sexta, de 1920 s, não cabe e o erro volta ao loop), e o loop segue de onde
   estava. Refazer a instância do zero
   desperdiçaria as chamadas já feitas. Estouro de contexto e outros erros não
   são tocados: são resultado do loop.
5. **Controla o ritmo** (`before_model_callback`). Cada resposta soma ao
   plugin uma "dívida" de tempo, de `tokens ÷ tokens_por_minuto × 60 s`
   (`--max-tokens-per-minute`, padrão 50.000; `0` desliga). Antes da próxima
   chamada, ele espera o necessário para a média ficar abaixo do teto, com 1
   minuto de folga para rajadas. A dívida **não zera entre
   instâncias**, porque o provedor também não zera o limite dele.

O plugin não curto-circuita nenhum agente e não propaga falhas próprias: uma
falha da guarda vira ocorrência registrada, não queda do run.

#### 3.3.5 Teto de trabalho por instância

`run_loop` limita cada instância a `--instance-timeout` segundos (padrão 3600) de
**trabalho**. A função `loop_runner.aguardar_com_teto` mede o relógio corrido
menos `plugin.tempo_pausado_s()`, que soma o que a guarda passou dormindo no
controle de ritmo e no rate limit (inclusive a pausa em curso). Ao estourar, ela
cancela a tarefa e levanta `TimeoutError`, que vira o motivo
`timeout_da_instancia`. A versão inicial usava `asyncio.wait_for` com o relógio
corrido, o que fazia o controle de ritmo consumir o teto dormindo (ver
[pontos de atenção](#5-pontos-de-atenção), B4).

O corte continua sendo **aproximado**: as tools síncronas do harness rodam na
thread do event loop, e o cancelamento só ocorre quando a chamada em curso
devolve o controle.

#### 3.3.6 Patch: fotografia git em vez do `base_commit`

O `/testbed` já vem modificado pelo `pre_install` de alguns projetos. Um diff
contra o `base_commit` quebraria o `git apply` da correção. Por isso o patch é
calculado contra uma **fotografia git** do estado inicial (índice temporário via
`GIT_INDEX_FILE` + `write-tree`, sem commit). Detalhes:

- O git roda com **configuração neutra**: config global e do sistema do host
  desligadas, e as chaves que mudam o formato do diff fixadas por `-c`
  (prefixos `a/` e `b/`, sem detecção de renomeação, sem conversão de fim de
  linha), que é o que o `git apply` do harness oficial espera. Assim a config
  do host não muda o patch.
- O diff é montado **arquivo a arquivo**. Um arquivo cujo conteúdo não é UTF-8
  sai como `GIT binary patch`, em vez de corromper o patch inteiro.
- Ficam fora do patch: os arquivos do benchmark, `PLAN.md`, caches
  (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.tox`, `*.pyc`, `*.pyo`), o
  venv na raiz (`venv/`, `.venv/`) e os caminhos que o `test_patch` toca.
  Arquivos novos escondidos pelo `.gitignore` do repositório também não entram,
  mas ficam registrados (`ignorado_pelo_gitignore`), assim como um arquivo cujo
  diff nem em modo binário é UTF-8 (`diff_nao_utf8`).

#### 3.3.7 Correção oficial em venv separado

O `adk/` usa Python 3.14, e o harness oficial (`swebench==5.0.2`, fixado) não
declara suporte a ela. A correção roda num venv separado
(`benchmarks/coding_review/swebench/.venv-swebench`, Python 3.12), recebendo o
**mesmo parquet fixado** que serviu ao sorteio, então execução e gabarito usam
os mesmos dados. O dataset tem a revisão fixada
(`78f471bf655a3137b2e8a75af1501690ec009ec3`), porque o schema já mudou no
Hugging Face.

Quando o harness não grava o `report.json` de uma instância, `grading.parse_results`
lê o `run_instance.log`: `>>>>> Patch Apply Failed` e `Test timed out after`
contam como **não resolvida**, como no SWE-bench; o resto vira erro de avaliação.
O código de saída do harness vai para o cabeçalho do `report.md`, com alerta se
não for zero.

#### 3.3.8 Checkpoint, retomada e falhas

- **Checkpoint.** O `progress.jsonl` guarda um registro por instância. Na
  retomada (`--resume-dir`), as concluídas saem do cache, sem chamar o modelo.
- **Guarda de parâmetros.** A retomada exige os mesmos `model`, `seed`, `limit`,
  revisão do dataset, instâncias, `--instance-timeout` e `--grading-timeout`
  do run original, para não misturar configurações. Diferenças de ambiente
  (por exemplo, o commit do repositório) são aceitas e registradas em
  `ambientes_de_retomada` no `metadata.json`.
- **Falha de preparação** (ex.: o pull da imagem caiu): vira `falha_preparacao`,
  é refeita na retomada, e, persistindo, conta como não resolvida na métrica 1 e
  fica fora da métrica 3.
- **Falha do provedor** (rate limit, cota, credencial, rede) que escapa da
  pausa por chamada: o run espera e **refaz a instância do zero**. Por padrão
  são 4 novas tentativas, com espera de 10, 20, 40 e 80 minutos
  (`--provider-wait` 600 s, dobrando; `--provider-retries` 4). Se persistir, o run **para** com o aviso de como retomar, e a instância fica
  marcada como `falha_provedor`. Nada disso conta como falha do loop.
- **Estouro de contexto** não entra nessa regra: é resultado do loop e recebe o
  motivo próprio `estouro_de_contexto`.
- **`--only-ids`** roda, numa execução, só as instâncias listadas; as demais
  pendentes ficam para outra retomada, sem alterar o sorteio nem o run. Serve
  para controlar a ordem e o custo. O relatório de uma execução parcial cobre só
  as instâncias que já têm registro (o programa avisa quantas estão sem).
- **Saída imediata.** A saída é reconfigurada para linha a linha, para o
  progresso aparecer em tempo real com a saída redirecionada para arquivo.

#### 3.3.9 Métricas e relatório

`metrics.aggregate` calcula as três métricas e os agregados (por repositório e
operacionais), com intervalo de Wilson. A classificação do motivo de parada
segue a ordem descrita em [como funciona](#2-como-o-benchmark-funciona). A matriz
de confusão só inclui instâncias com gabarito conhecido, e cada aprovação recebe
os qualificadores. `report.py` renderiza o `report.md`, com alerta se o código
de saída da correção não for zero e com a seção do `--executor-sanity`.

#### 3.3.10 Outras decisões

| Decisão | O que foi feito | Por quê |
| ------- | --------------- | ------- |
| Memória (mem0) | Forçada **desligada** | Lições de uma instância vazariam para a seguinte |
| Não vazamento do gabarito | O coder e o validador nunca veem `patch`, `test_patch`, `FAIL_TO_PASS`, `PASS_TO_PASS` nem `hints_text` | O validador só recebe a task e as evidências do harness; um teste confere que a task e a mensagem ao coder não contêm nada do gabarito |
| Constantes da produção | Nomes de agentes, estágios do harness, motivos da política e workdir do sandbox são conferidos por AST nos testes | O benchmark não se descola do código medido |
| `conftest.py` do benchmark | Ignora `results/*`, `datasets/*` e `.venv-swebench/*` na coleta | O pytest chegou a coletar logs do harness (`test_output.txt`) como doctest |

### 3.4 Cobertura de testes

Os testes cobrem, entre outros: o não vazamento do gabarito, o sorteio
determinístico, a extração do patch sobre uma árvore "suja" de `pre_install` (e a
aplicação dele com `git apply`), inclusive com config git hostil no host e
arquivos fora de UTF-8; a guarda rodando dentro de um `Runner` real do ADK antes
do gate do executor; as pausas por rate limit e o controle de ritmo, também com
um agente real do ADK; o teto de trabalho descontando as pausas; a
classificação de todos os motivos de parada; a leitura dos relatórios e dos logs
do harness oficial; a retomada (falha de preparação refeita, checkpoint com
linha truncada, `--only-ids`) e as exclusões do `--gold-sanity`.

## 4. Resultados da linha de base

> **Leia antes de citar qualquer número daqui:** 26 das 30 instâncias, um único
> modelo, execução única. As ressalvas completas estão no
> [Resumo executivo](#resumo-executivo), em [4.5](#45-ressalvas-para-a-leitura) e na
> [seção 5](#5-pontos-de-atenção).

### 4.1 Configuração do run de referência

| Campo | Valor |
| ----- | ----- |
| Modelo (coder, executor e validador) | `github_copilot/gemini-3.7-flash` |
| Datas de execução | 01/10/2026 a 05/10/2026 |
| Dataset | `SWE-bench/SWE-bench_Verified` @ `78f471bf655a3137b2e8a75af1501690ec009ec3` |
| Sorteio | seed 42, limite 30 (as 30 instâncias estão no `metadata.json`) |
| Harness oficial | `swebench` 5.0.2 |
| Teto de rodadas do loop (`max_iterations`) | 20 |
| Teto de trabalho por instância | 3600 s, descontadas as pausas de ritmo e de rate limit |
| Controle de ritmo | 150.000 tokens por minuto (entrada + saída) |
| Commit do repositório | `0af110a`, com alterações locais (correção do teto e `--only-ids`; ver B4 e B9 em [5.2](#52-o-que-apareceu-ao-executar)) |
| Diretório do run | `benchmarks/coding_review/swebench/results/run_20261001_122939_github_copilot-gemini-3.7-flash_n30/` |

**Checagens sem LLM antes do loop** (29/09/2026):

| Checagem | Resultado |
| -------- | --------- |
| `--gold-sanity` (patches oficiais no harness oficial) | 30/30 resolvidas; **nenhuma instância excluída** |
| `--executor-sanity` (solução oficial no harness do executor) | **26/30** com sucesso. As 4 que falham são `matplotlib-25479`, `seaborn-3069`, `xarray-4687` e `pylint-7080`: têm testes que falham também na avaliação oficial, fora das listas `FAIL_TO_PASS`/`PASS_TO_PASS`. O SWE-bench os ignora, mas o executor julga pelo código de saída do comando inteiro e reprova |

O `--executor-sanity` indica um **teto aproximado de aprovações confiáveis do
validador neste ambiente: 26 de 30**.

### 4.2 Resultados (n = 26)

#### Resultado da métrica 1: taxa de resolução

| | Valor |
| - | ----- |
| Resolvidas | **20/26 (76,9%)** |
| IC 95% (Wilson) | 57,9% a 89,0% |
| Não resolvidas | 6 |

Resolvidas por repositório (instâncias do run):

| Repositório | Instâncias | Resolvidas | Aprovadas pelo validador |
| ----------- | ---------- | ---------- | ------------------------ |
| django/django | 13 | 9 | 11 |
| astropy/astropy | 4 | 4 | 4 |
| scikit-learn/scikit-learn | 4 | 4 | 4 |
| matplotlib/matplotlib | 1 | 0 | 1 |
| pydata/xarray | 1 | 1 | 1 |
| pylint-dev/pylint | 1 | 0 | 1 |
| pytest-dev/pytest | 1 | 1 | 1 |
| sympy/sympy | 1 | 1 | 1 |

O resultado mais fraco está em Django (9 de 13). Os repositórios com poucas
instâncias (1 cada) não permitem conclusão por repositório.

#### Resultado da métrica 2: rodadas e motivo de parada

| Rodadas | Instâncias |
| ------- | ---------- |
| 1 | 15 |
| 2 | 6 |
| 3 | 4 |
| 4 | 1 |

Média **1,65**, mediana 1, mínimo 1, máximo 4.

| Motivo de parada | Instâncias |
| ---------------- | ---------- |
| Aprovação do validador | 24 |
| Política de progresso | 2 |
| `max_iterations` | 0 |
| Outro (erro, timeout, estouro de contexto) | 0 |

As duas paradas pela política de progresso, ambas em Django, com o validador
reprovando. **Só uma é não resolvida**; a outra o harness oficial resolve:

| Instância | Rodadas | Sub-motivo | Observação |
| --------- | ------- | ---------- | ---------- |
| `django__django-12125` | 4 | `bloqueado_sem_alteracao_arquivos` | A nota ficou em 0,47 nas 4 rodadas, sem melhora. **O patch final resolve a instância no harness oficial** (ver abaixo) |
| `django__django-16032` | 3 | `bloqueado_erro_repetido` | Parou por repetir o mesmo erro |

Nenhuma instância chegou ao teto de 20 rodadas: nenhuma parou por
`max_iterations`. Com um coder desse porte, o loop quase sempre converge nas
primeiras rodadas ou é cortado cedo pela política. Para exercitar mais a parte
da política de progresso (estagnação, falhas distintas), seria preciso um modelo
mais fraco ou instâncias mais difíceis.

#### Resultado da métrica 3: concordância do validador

| | Resolvida | Não resolvida |
| --- | --- | --- |
| **Validador aprovou** | 19 | **5** (falso positivo) |
| **Validador não aprovou** | **1** (falso negativo: `django-12125`) | 1 |

| Indicador | Valor | IC 95% |
| --------- | ----- | ------ |
| Falsos positivos entre as aprovações | **5/24 (20,8%)** | 9,2% a 40,5% |
| Precisão do validador | 19/24 (79,2%) | 59,5% a 90,8% |
| Recall do validador | 19/20 (95%) | 76,4% a 99,1% |

As 5 instâncias com falso positivo, ou seja, o loop parou com "aprovado" e o
problema continuava lá: `django__django-11400`, `django__django-11734`,
`django__django-14034`, `matplotlib__matplotlib-20859` e
`pylint-dev__pylint-7080`.

Qualificadores das 24 aprovações:

| Qualificador | Aprovações | Entre os falsos positivos |
| ------------ | ---------- | ------------------------- |
| `suite_vazia_ou_pulada` | 0 | 0 |
| `patch_vazio` | 0 | 0 |
| `testes_nao_identificados` | 13 | 3 |

Nenhuma aprovação veio de suíte vazia ou patch vazio. Em 13 das 24 o harness não
identificou testes individuais (todas as de Django, 11 de 11, a de SymPy e a
`astropy-7166`), e a decisão se apoiou no código de saída. Esse qualificador, porém,
**não separa** os falsos positivos: a taxa é parecida com e sem ele (3 de 13
contra 2 de 11). Por repositório, Django tem 3 falsos positivos em 11 aprovações
e os demais 2 em 13, diferença pequena demais para concluir algo. A
`pylint-7080` (um dos 5) também falha no `--executor-sanity`, ou seja, o ambiente
do executor reprova até a solução oficial rodando o comando oficial; parte desse
falso positivo pode ser artefato do ambiente (o coder rodou poucos testes, e a
checagem roda o arquivo todo).

O validador aprovou 24 das 26 instâncias e deixou de aprovar apenas 2: uma das 6
não resolvidas (`django-16032`) e a `django-12125`, que estava **resolvida**. Ele
aprovou 5 das 6 não resolvidas (especificidade de 1/6), então o recall (95%) tem pouco
poder de discriminação: o validador aprova quase tudo.

**O único falso negativo (`django-12125`).** O coder acertou o código (o patch final
aplica e resolve a instância, com 0 falhas em `FAIL_TO_PASS` e `PASS_TO_PASS`,
confirmado em 4 avaliações oficiais: 3 do autor, contando a regeração do run, e 1 do
revisor; só o último log do harness fica no disco), mas o comando de teste dele, o
módulo `migrations` inteiro, ficou **vermelho nas 4 rodadas**. A causa **provável** é um
teste existente, `test_deconstruct_class_arguments`: reproduzido na imagem oficial, sem
as edições de teste do coder, ele falha com o patch do coder e **também com o oficial**,
e o `test_patch` oficial o **altera** (move a classe do teste para o nível do módulo).
O registro mostra que o coder alterou `tests/migrations/test_writer.py` (arquivo
excluído do patch por colidir com o `test_patch`), mas **não se sabe o que ele mudou**,
nem se o vermelho vinha só desse teste. O validador reprovou, e a política de progresso
encerrou o loop ao não haver mais alteração de arquivos. Ou seja, o "falso negativo"
provavelmente mede uma divergência de rótulo (o harness oficial substitui o arquivo de
testes pelo seu, o que torna a entrega resolvida), e não necessariamente um erro de
julgamento do validador diante de uma suíte vermelha. Detalhes e limites em
[swebench-revisao-falsos-positivos.md](swebench-revisao-falsos-positivos.md), seção 9.

Os testes e os patches dessas 5 instâncias foram **revisados à mão** e
documentados em [swebench-revisao-falsos-positivos.md](swebench-revisao-falsos-positivos.md).
Em resumo: um dos cinco (`matplotlib-20859`) provavelmente **não é um falso positivo
real** (o patch é equivalente ao oficial e passou em 5 de 5 reavaliações; a reprovação
veio de um teste que depende do relógio); os outros quatro são soluções realmente
erradas que o loop aprovou (duas correções incompletas, uma que contradiz o contrato do
projeto e uma sem efeito sobre o defeito), com testes do coder que não exercitavam o
defeito. Os números acima foram **mantidos como o harness os produziu** (na regeração
de 08/10/2026, ver B11); com o rótulo da `20859` corrigido, seriam 21/26 resolvidas
(80,8%, IC 95% 62,1% a 91,5%), 4/24 falsos positivos (16,7%, IC 95% 6,7% a 35,9%) e
recall de 20/21 (95,2%). Ver também [pontos de atenção](#5-pontos-de-atenção), A2 e A3.

### 4.3 Custo e tempo

| Item | Valor |
| ---- | ----- |
| Tokens de entrada das 26 instâncias (checkpoint final) | ~53,2 milhões (coder 38,8 M, executor 13,9 M, validador 0,5 M) |
| Chamadas ao LLM (26 instâncias) | 674 |
| Tempo de trabalho do loop (26 instâncias) | ~5.480 s (~1 h 31 min) |
| Espera do controle de ritmo (26 instâncias) | ~15.790 s (~4 h 23 min), cerca de três quartos do tempo total |
| Créditos do Copilot consumidos pelo benchmark | **~4.340** (~US$ 43), lidos do contador da conta |

Os tokens e o tempo da tabela são **tempo de máquina somado das 26 instâncias**
(21.262 s, ou 5 h 54 min), e não o calendário do run, que foi de 01/10 a 05/10.

O gasto de créditos é maior que o das 26 instâncias retidas, porque inclui
tentativas descartadas: as 6 instâncias que estouraram o teto no primeiro passe
(54,3 milhões dos 92,4 milhões de tokens daquele passe; os outros 38,1 milhões
são de instâncias retidas); a `matplotlib-25479`, interrompida sem terminar, que
sozinha consumiu ~930 créditos; o "lote 1" de 02/10 (`seaborn-3069`,
`xarray-4687` e `pytest-10356`), iniciado e interrompido sem gravar resultado; e a
primeira tentativa da `pylint-7080`. Os créditos são **somados
num caixa único da organização**, e cada usuário tem um teto individual; o
gasto deste run chegou perto do teto do executor do benchmark. Planeje o custo
antes de repetir (ver [pontos de atenção](#5-pontos-de-atenção), B6).

Medição de referência para escolha de modelo (5 chamadas encadeadas sobre ~35
mil tokens de código real; amostra pequena, valores aproximados): `gpt-5-mini`
~13,5 créditos por milhão de tokens de entrada, `gemini-3.7-flash` ~27 e
`claude-sonnet-5` ~104, já com o cache de prompt aplicado (a escolha do modelo está
em [4.6](#46-por-que-o-gemini-37-flash-foi-o-modelo-da-linha-de-base)).

### 4.4 Como se chegou a esse resultado

| Etapa | O que aconteceu |
| ----- | --------------- |
| `gpt-4` | Contexto de 32k. A 1ª instância (`astropy-14508`) falhou no 2º turno do coder com um "Bad Request" genérico, atribuído (por inferência, com uma só instância) ao limite de contexto. Descartado |
| `gpt-4.1` | Contexto de 128k. 1 instância concluída (`astropy-14508`) e 1 que estourou o contexto no 1º turno (`astropy-14539`, 169.117 tokens contra o limite de 128.000). Bloqueio do Copilot por "rate limit for utility models" (limite de vazão, independente de créditos), com bloqueios cada vez mais longos. Descartado |
| `gemini-3.7-flash`, 1º passe (30 instâncias) | 20/30 resolvidas (66,7%). **6 instâncias "estouraram" o teto de 1 hora** (`django-12125`, `django-16032`, `matplotlib-25479`, `seaborn-3069`, `xarray-4687`, `pytest-10356`) |
| Diagnóstico | Nessas 6, de 76% a 91% do tempo foi **espera do controle de ritmo**; o modelo trabalhou só de 337 s a 882 s. O teto contava o relógio corrido |
| Correção do benchmark | O teto passou a descontar as pausas (`aguardar_com_teto`, 5 testes novos; 146 no total). Nada no executor foi alterado |
| Refazimento | Das 6, só `django-12125` e `django-16032` foram refeitas (as duas pararam pela política de progresso; a `django-12125` o harness oficial resolve). A `matplotlib-25479` foi interrompida por créditos depois de ~930 consumidos. O lote seguinte (`seaborn-3069`, `xarray-4687`, `pytest-10356`) foi iniciado e interrompido sem gravar resultado, então essas três também não foram refeitas |
| Fechamento | `--grade-only` sobre as 26 instâncias com resultado válido. Depois da revisão do PR, regerado com a correção do cache do harness (a `django-12125` tinha sido avaliada com um patch antigo; ver B11) |

O primeiro passe está guardado em
`results/run_20261001_122939_.../v1_timeout_contava_o_ritmo/` (relatório e
checkpoint antigos), para comparação.

**Comparação com o primeiro passe** (n = 30, antes da correção do teto):

| | 1º passe (n = 30) | Final (n = 26) |
| - | ----------------- | -------------- |
| Resolvidas | 20/30 (66,7%), IC 48,8% a 80,8% | 20/26 (76,9%), IC 57,9% a 89,0% |
| Paradas | 24 aprovação + 6 timeout | 24 aprovação + 2 política de progresso |
| Falsos positivos | 5/24 (20,8%) | 5/24 (20,8%) |
| Recall do validador | 19/20 (95%) | 19/20 (95%) |

Os dois números de resolução **não são comparáveis**: a amostra mudou. Os 5
falsos positivos são os mesmos nos dois. No primeiro passe, a `django-12125` era um
timeout com patch que não aplicava; no final, é um falso negativo que o harness oficial
resolve.

### 4.5 Ressalvas para a leitura

1. **Amostra enviesada.** As 4 instâncias que ficaram de fora (`matplotlib-25479`,
   `seaborn-3069`, `xarray-4687`, `pytest-10356`) incluem as três que falham no
   `--executor-sanity`. Tirá-las tende a inflar a taxa de resolução. Na versão com
   as 30, a taxa era 66,7%. Detalhes em [B8](#b8-a-amostra-final-pode-ficar-enviesada-se-instâncias-forem-descartadas).
2. **Dois estados do código do benchmark.** As 24 instâncias do primeiro passe e
   as 2 refeitas rodaram com versões que diferem só na contagem do teto; a correção
   oficial foi regerada depois, com a correção do cache. Detalhes em
   [B9](#b9-o-resultado-mistura-estados-do-código-do-benchmark) e B11.
3. **Uma instância refeita por travamento** (`pylint-7080`): vale o resultado da
   segunda tentativa. Detalhes em [B5](#b5-o-corte-por-timeout-só-acontece-quando-a-chamada-em-curso-devolve-o-controle).
4. **Execução única, um modelo, 26 instâncias.** Cada instância vale 3,8 pontos
   percentuais. Não há medida de variância entre execuções. Diferenças entre
   runs só valem se os intervalos de confiança não se sobrepõem.
5. **Pendências frente à #417.** O critério "run completo com 30 instâncias" **não está atendido** (o baseline cobre 26) e o run não é reproduzível de um único commit limpo (B9). Ver o aviso no Resumo executivo.
6. **O que o benchmark não cobre.** Mede o ramo "projeto existente" do
   workflow (não a criação de projeto do zero) e só projetos Python.

### 4.6 Por que o `gemini-3.7-flash` foi o modelo da linha de base

A escolha foi **pragmática**, por restrição de contexto e de custo, e não por
ranking de qualidade: nenhum outro modelo rodou o benchmark inteiro, então não
há base para dizer que o `gemini-3.7-flash` seja o melhor para este loop.

**Por que os dois primeiros modelos não serviram:**

| Modelo | Contexto | Problema |
| ------ | -------- | -------- |
| `gpt-4` | 32k | A 1ª instância falhou com "Bad Request" genérico, atribuído ao contexto (ver B2) |
| `gpt-4.1` | 128k | `astropy-14539` estourou no 1º turno (169.117 tokens contra 128.000). Além disso, o Copilot bloqueou o modelo por "rate limit for utility models", um limite de vazão por usuário, sem relação com o saldo de créditos, com `retry-after` de 14.053 s (~3 h 54 min) na época. Liberar de novo e rodar tudo levaria dias (ver B3) |

**Alternativas testadas.** Como o limite era específico dos modelos "utility",
a hipótese foi que os modelos cobrados em créditos entrassem em outra
contabilidade. Em 01/10/2026, uma chamada de teste de ~60 mil tokens foi aceita
pelo `gpt-5-mini` e pelo `gemini-3.7-flash`, uma de ~168 mil tokens pelo
`claude-sonnet-5`, e recusada com 429 pelo `gpt-4.1`; o `gpt-5.4` recusou a
chamada de teste com HTTP 400 (não investigado). O custo foi medido com 5
chamadas encadeadas sobre ~35 mil tokens de código real do repositório, já com o
cache de prompt aplicado:

| Modelo | Contexto (lista do Copilot) | Créditos por milhão de tokens de entrada | Estimativa para 30 instâncias |
| ------ | --------------------------- | ---------------------------------------- | ----------------------------- |
| `gpt-5-mini` | 128k | ~13,5 | ~300 a 800 |
| `gemini-3.7-flash` | 200k | ~27 | ~600 a 1.600 |
| `claude-sonnet-5` | 200k | ~104 | ~3.000 a 8.800 |

A estimativa para as 30 instâncias supunha de 0,5 a 2 milhões de tokens de
entrada por instância, extrapolado de apenas duas instâncias medidas (~0,7
milhão cada, uma com o `gpt-4` e outra com o `gpt-4.1`).
O saldo do usuário na época era de ~4.590 créditos. O Claude, além de ~4 vezes
mais caro por token, contava ~40% mais tokens para o mesmo texto (50,6 mil contra
35,6 mil).

**Decisão.** O `claude-sonnet-5` não cabia no saldo. O `gpt-5-mini` era o mais
barato, mas tem o mesmo contexto de 128k do `gpt-4.1`, que já tinha estourado, e
é um modelo de raciocínio, o que tende a acrescentar tokens e latência. O
`gemini-3.7-flash` cabia no saldo e tinha 200k de contexto, o que reduzia o
risco de estouro. A escolha foi do responsável pelo run, a partir dessas
medições.

**O que a estimativa errou.** O custo real foi de ~4.340 créditos, cerca de 2,7
vezes o limite superior estimado (1.600). A estimativa não previu que o primeiro
passe consumiria ~3 milhões de tokens por instância (92,4 milhões nas 30), nem o
custo das tentativas descartadas e do refazimento (ver 4.3 e B6). Em compensação,
o modelo não encontrou o rate limit do Copilot (0 s de pausa por rate limit no
run) e não houve estouro de contexto. Se o benchmark for repetido, estime o custo
com a média de ~3 milhões de tokens por instância e reserve margem para
refazimento.

## 5. Pontos de atenção

Esta seção reúne o que pode distorcer a leitura dos números ou atrapalhar a execução. Os pontos estão em dois grupos: os **previsíveis** antes do primeiro run (A1 a A10, viraram limitações documentadas no README) e os que só apareceram **ao executar** (B1 a B11, viraram correções no código ou ressalvas nos resultados). Para cada ponto: o que é, que efeito tem e o que fazer.

### 5.1 Limites da medição (previsíveis)

#### A1. Amostra pequena

Com 30 instâncias, cada uma vale 3,3 pontos percentuais. Para uma resolução de
~30%, o intervalo de confiança de 95% vai de ~17% a ~48% (cálculo do README). A
métrica 3 é mais frágil ainda, porque o denominador é o número de aprovações.

- **Efeito:** diferenças de poucos pontos entre dois runs não significam nada.
- **O que fazer:** comparar sempre pelo intervalo de Wilson, nunca pela taxa
  pontual. Para decisões finas, ampliar a amostra ou repetir.

#### A2. O gabarito também erra

Os testes oficiais só cobrem o que o PR original testou. O README cita estudos
que estimam que ~8–11% dos patches "resolvidos" estão errados, e alguns testes
exigem detalhes específicos da solução original (uma solução correta pode ser
reprovada).

- **Efeito:** a métrica 1 pode estar enviesada nos dois sentidos, e parte dos
  "falsos positivos" do validador pode ser, na verdade, falso negativo do
  gabarito.
- **O que fazer:** revisar à mão as discordâncias da métrica 3 antes de
  concluir que o validador errou.

#### A3. A métrica 3 mede o sinal de parada, não o "julgamento" de um LLM

O validador aprova pelo status técnico da suíte que o **próprio coder**
declarou. Um falso positivo significa que a suíte do coder passou e o bug
continuou: teste fraco, ausência de teste ou validador permissivo. Os
qualificadores (`suite_vazia_ou_pulada`, `patch_vazio`,
`testes_nao_identificados`) ajudam a separar os casos, mas não bastam sozinhos.

- **Efeito:** atribuir ao validador um erro que pode ser do coder.
- **O que fazer:** olhar os qualificadores e os testes escritos em cada falso
  positivo, e não parar na taxa.

#### A4. A métrica 1 depende mais do coder do que do executor

O coder não tem ferramenta de busca e lê arquivos inteiros. Em repositórios
grandes, isso estoura o contexto do modelo (ver B2). A taxa de resolução mede o
loop inteiro, e o coder pesa mais que o executor. Já as métricas 2 e 3 olham
diretamente o executor, o validador e a política de parada.

#### A5. O benchmark mede o ramo "projeto existente" do workflow

O loop entra no ramo `NOVA_TASK`, o mesmo que a produção usa da 2ª task em
diante. Pela primeira task, o `TaskIterator` cai no ramo "crie o `PLAN.md` e
implemente o projeto completo", que **não** é exercitado aqui. Isso foi uma
escolha deliberada (nada muda no código de produção), mas o resultado vale para
tarefas sobre código existente, não para criação de projeto do zero.

#### A6. Leitura de testes só entende pytest

Em Django (`runtests.py`) e SymPy (`bin/test`), o harness do executor decide
pelo código de saída, sem contagem por teste. No run de referência, 13 das 24
aprovações caíram em `testes_nao_identificados` (todas as de Django, 11 de 11, a
única de SymPy e a `astropy-7166`), e 3 dos 5 falsos positivos estão entre elas.

#### A7. Conflitos com o prompt de sistema do coder

O prompt manda criar virtualenv e usar `sandbox` direct, o que rodaria o
repositório no host, sem as dependências. A guarda do benchmark restaura o
`sandbox`, mas não reescreve os comandos do coder. Instâncias em que o coder
usou virtualenv são listadas no relatório (no run de referência: zero).

#### A8. Limites do container do executor

São constantes do executor, fora do escopo do benchmark: 512 MB de memória, 50%
de uma CPU, 120 s por comando de teste e 300 s de build. Testes pesados podem
estourar e virar sinal de falha para a política de progresso.

#### A9. Código compilado

Em astropy e scikit-learn, uma correção em C/Cython exige que o coder declare a
recompilação no `build`.

#### A10. Não determinismo e contaminação

- Uma execução por instância não separa dificuldade de sorte. Para estimar a
  variância, repita um subconjunto.
- As issues são de 2012–2023 e públicas, e o modelo pode lembrar a correção.
  Algumas issues já trazem a correção proposta pelo autor (por exemplo,
  `sympy__sympy-16766`). Isso é entrada oficial do dataset, não vazamento do
  benchmark.
- Provedores atualizam modelos com o mesmo nome. O `metadata.json` registra
  modelo, data, commit e versões.

### 5.2 O que apareceu ao executar

#### B1. O ambiente do executor não passa nem com a solução oficial em 4 instâncias

O `--executor-sanity` aplica o patch e os testes oficiais e roda o harness do
executor: deu sucesso em **26 de 30**. As 4 restantes são `matplotlib-25479`,
`seaborn-3069`, `xarray-4687` e `pylint-7080`. Nelas, há testes que falham
também na avaliação oficial, fora das listas `FAIL_TO_PASS`/`PASS_TO_PASS`: o
SWE-bench os ignora, mas o executor julga pelo código de saída do comando
inteiro e reprova.

- **Efeito:** rodando o comando de teste oficial, o harness do executor reprova
  até a solução correta nessas 4. Uma aprovação ali só é possível se o coder
  declarar um comando de teste mais estreito que passe. Ela pode estar certa
  (a `seaborn-3069` foi resolvida no primeiro passe), mas é menos confiável. Por
  isso 26/30 é um **teto aproximado** de aprovações confiáveis, e não um limite
  rígido.
- **O que fazer:** manter o `--executor-sanity` como passo obrigatório e reportar
  o teto junto da taxa. **Não** tratar a diferença como defeito do executor sem
  antes olhar o motivo: é uma propriedade do par ambiente + dataset.

#### B2. Estouro de contexto do modelo

O coder reenvia a conversa inteira a cada chamada. No run abandonado do `gpt-4`
(32k de contexto), a 1ª instância (`astropy-14508`) falhou com um genérico "Bad
Request", atribuído ao limite de contexto (inferência a partir de uma única
instância; a mensagem não diz o motivo). Com o `gpt-4.1` (128k), a `astropy-14539`
estourou no 1º turno, com 169.117 tokens contra o limite de 128.000. Com o
`gemini-3.7-flash` (200k de contexto, segundo a lista de modelos do Copilot), não
houve estouro no run de referência.

- **Efeito:** com um modelo de contexto curto, a métrica 1 mede o limite do
  contexto, não o loop.
- **O que fazer:** usar modelo com contexto ≥ 128k, preferencialmente 200k. O
  estouro é registrado como `estouro_de_contexto`, resultado do próprio loop.

#### B3. Rate limit do Copilot é de vazão, e independe dos créditos

A mensagem "rate limit for utility models" é um limite de **tokens por janela de
tempo** (cabeçalho `x-ratelimit-exceeded: global-chat:tbb-utility-models...`),
independente do saldo de créditos do mês. Quem não consome créditos (como o
`gpt-4.1`, fora da tabela de preços) cai nele. O bloqueio **escala** quando se
insiste: um bloqueio medido no início durou ~50 minutos, e o seguinte vinha com
`retry-after` de 14.053 s (~3 h 54 min).

- **Efeito:** um run de 30 instâncias bate nesse limite várias vezes e pode
  levar dias.
- **O que fazer:** manter o controle de ritmo (ver B4), não insistir durante um
  bloqueio e preferir um modelo faturado por créditos para o run completo.

#### B4. O controle de ritmo distorceu o teto por instância (corrigido)

O plugin de guarda espera antes de cada chamada para a média ficar abaixo de
`--max-tokens-per-minute` (padrão 50.000; o run de referência usou 150.000). No
primeiro run completo, o teto de 3600 s por
instância contava o relógio corrido, **inclusive essas esperas**. Seis
instâncias estouraram o teto, mas trabalharam de fato só de 337 s a 882 s: de
76% a 91% do tempo foi espera. Elas apareciam como "timeout", mas eram efeito do
controle de ritmo do próprio benchmark.

- **Efeito:** a taxa de resolução e os motivos de parada ficavam distorcidos.
- **Correção:** o teto passou a descontar as pausas do ritmo e do rate limit
  (`aguardar_com_teto`, com testes). Duas das seis foram refeitas e terminaram
  pela política de progresso: `django-12125` (`bloqueado_sem_alteracao_arquivos`;
  787 s ativos em 3.651 s de relógio), que o harness oficial resolve (ver 4.2 e B11),
  e `django-16032` (`bloqueado_erro_repetido`; 365 s ativos em 2.419 s), não
  resolvida. O relógio
  da primeira passa de 3.600 s sem contradição, porque só o tempo ativo conta.
- **O que fazer:** nunca tratar timeout de instância como incapacidade do
  modelo sem checar `duracao_ativa_s` versus `pausa_ritmo_s` no `progress.jsonl`.

#### B5. O corte por timeout só acontece quando a chamada em curso devolve o controle

As tools síncronas do harness rodam na thread do event loop. Uma instância
(`pylint-7080`) seguia em andamento depois de ~2 h, quando devia ter sido
cortada em 1 h (o último registro do checkpoint é das 20:47 e a retomada, das
22:48 de 01/10, conforme o `run.log`); foi interrompida manualmente e refeita do
zero. O resultado usado é o da segunda tentativa, e a primeira não teve desfecho
registrado. Isso é um pequeno viés a favor de ter um resultado "limpo".

#### B6. Custo alto e imprevisível

Os créditos do Copilot Business são **somados num caixa único da organização**,
e cada usuário tem um teto individual definido pelo admin (neste caso, 5.000).
O custo por instância variou de poucos créditos a centenas:

- O primeiro passe das 30 instâncias usou 92 milhões de tokens de entrada (~3
  milhões por instância), bem acima do que as primeiras instâncias sugeriam
  (0,6 a 0,9 milhão cada).
- Uma instância sozinha (`matplotlib-25479`) consumiu ~930 créditos sem terminar.
  Esse gasto não aparece no `progress.jsonl`: o custo real inclui as tentativas
  descartadas (a `pylint-7080` travada, a `matplotlib-25479` e os lotes
  interrompidos). Os valores em créditos vêm do contador da conta do Copilot e
  não ficam versionados no repositório.
- O custo é puxado pelo reenvio da conversa inteira a cada chamada: o consumo
  acelera quando o loop não converge.

- **O que fazer:** antes de rodar, estimar o custo com a tabela de preços do
  modelo, avisar o admin do caixa, e usar uma trava automática de saldo para
  interromper o run abaixo de um piso. Cada instância concluída fica salva no
  checkpoint, então interromper não perde o já feito.

#### B7. Uso automatizado do Copilot em volume

Na leitura da equipe, as políticas de uso aceitável do GitHub (Acceptable Use
Policies) vedam atividade automatizada em massa e excessiva, e os Termos de
Serviço (seção sobre uso da API) permitem suspender o acesso em caso de abuso.
O texto foi consultado em 01/10/2026; confirme a versão vigente em
`docs.github.com/en/site-policy/github-terms/github-terms-of-service`. O cliente
do projeto se identifica como o Copilot Chat do VS Code e, por padrão, envia
`X-Initiator: user` (`adk/shared/llm.py`), mesmo em chamadas automatizadas. Segundo
o responsável pelo run, houve autorização do administrador, que não está
registrada no repositório; o controle de ritmo ficou ligado.

- **O que fazer:** confirmar a autorização do admin antes de qualquer run longo,
  manter o controle de ritmo e parar se o GitHub enviar qualquer aviso à conta.

#### B8. A amostra final pode ficar enviesada se instâncias forem descartadas

No run de referência, 4 das 30 instâncias não foram refeitas após a correção do
teto, por falta de créditos (ver B4 e B6): `matplotlib-25479`, `seaborn-3069`,
`xarray-4687` e `pytest-10356`. Três delas são justamente as que falham na
checagem do executor (B1); a quarta falha da checagem, `pylint-7080`, **ficou**
no n=26 e é um dos 5 falsos positivos, então dentro do n=26 o teto aproximado de
aprovações confiáveis é 25, e não 26. No primeiro passe, as 4 estavam entre as 6
com maior tempo de trabalho (337 a 882 s), mas esse tempo estava truncado pelo
teto; só a `matplotlib-25479` destoa (882 s, 4 rodadas). Tirar essas instâncias
deixa o n=26 com menos casos em que o loop teve mais dificuldade, o que tende a
**inflar a taxa de resolução**. O efeito sobre a precisão do validador é
incerto, porque ela só considera as instâncias que ele aprovou. Os dois números
lado a lado: 20/30 (66,7%) no primeiro passe, 20/26 (76,9%) no final.

- **O que fazer:** nunca comparar o n=26 com um run de n=30; sempre citar qual
  subconjunto foi usado e por quê.

#### B9. O resultado mistura estados do código do benchmark

O `metadata.json` registra o commit `0af110a` com árvore suja nas três retomadas e
**não distingue** os estados do código. A reconstrução é esta:

| O que | Código | Commit |
| ----- | ------ | ------ |
| Loop das 24 instâncias do primeiro passe | `0af110a` mais alterações locais (o teto de tempo antigo, sem o desconto do ritmo) | não commitado como tal |
| Loop das 2 instâncias refeitas | Teto de tempo corrigido (B4) | conteúdo commitado depois em `25ac3e5` (que também traz o `--only-ids`, acrescentado depois do refazimento e sem efeito nos resultados) |
| Correção oficial dos resultados commitados | Com a invalidação do cache do harness (B11, código em `28f72f9`) | Regerada em `cbb5e5b` (rodada com o código de `59bd066`) e de novo em `3dc60d6` (IC com 6 casas, tudo em cache) |

As 24 instâncias do primeiro passe que foram retidas terminaram todas abaixo do teto,
com no máximo 1.770 s de relógio, então a mudança do teto não as afetaria. A distinção
entre os estados só aparece nos marcadores `===` do `run.log` (local, não versionado) e
na pasta `v1_timeout_contava_o_ritmo/`. O run **não** é reproduzível a partir de um único
commit limpo: reproduzi-lo exigiria rerodar o loop de ponta a ponta a partir de
`25ac3e5` ou posterior.

#### B10. Detalhes de infraestrutura

- **Dataset:** o schema já mudou no Hugging Face, por isso a revisão é fixada
  (`78f471bf655a3137b2e8a75af1501690ec009ec3`).
- **Python do harness:** o `adk/` usa Python 3.14 e o harness oficial não
  declara suporte a ela, por isso a correção roda num venv separado (3.12).
- **Disco:** ~2,4 GB por instância (imagens oficiais), cerca de 70 GB para 30.
- **Máquina:** as imagens oficiais são x86_64. Um computador que entra em
  suspensão no meio do run atrasa tudo: no run de referência o log do sistema
  (`journalctl`) registra uma suspensão em 02/10 às 20:14, e o run só andou de
  novo em 05/10. O teto de instância usa `time.monotonic`, que em Linux não conta
  o tempo suspenso (não testado).
- **Runs abandonados:** a pasta `results/` guarda também os runs do `gpt-4` e do
  `gpt-4.1`, interrompidos e **não comparáveis** com o de referência.
- **Memória do mem0:** forçada desligada, senão as lições de uma instância
  vazariam para a seguinte.
- **`/testbed` já vem modificado** pelo `pre_install` de alguns projetos. Por
  isso o patch é calculado contra uma fotografia git do estado inicial, e não
  contra o `base_commit`.

#### B11. O harness oficial reaproveitava o resultado de um patch antigo (corrigido)

O harness oficial pula toda instância que já tem `report.json` no diretório do
`run_id`, **sem conferir se o patch mudou**. Ao refazer uma instância, o resultado do
patch antigo era reaproveitado em silêncio. Foi o que aconteceu com a `django-12125`:
a correção oficial a avaliou com o patch do **primeiro passe** (3.676 bytes, que não
aplicava), e não com o final do coder (1.769 bytes). Só ela divergia das 26 (conferido
byte a byte, patch avaliado contra `predictions.jsonl`). A `django-16032` escapou
porque o patch antigo estava vazio, e o harness não gera relatório para patch vazio.
Foi apontado pelo Copilot na revisão do PR, e não tinha sido percebido antes porque
a revisão dos falsos positivos só olhou instâncias que o validador **aprovou**.

- **Efeito:** a `django-12125` passou de "não resolvida" para **resolvida** (aplica,
  0 falhas em `FAIL_TO_PASS` e `PASS_TO_PASS`; reavaliada 3 vezes pelo autor e
  uma pelo revisor; só o último log do harness fica no disco). As resolvidas foram de 19/26 para 20/26 (73,1% para 76,9%) e o
  recall do validador, de 19/19 para 19/20, porque ela é um falso negativo. Falsos
  positivos, rodadas e motivos de parada não mudaram.
- **Correção:** `grading.invalidate_stale_reports` compara o `patch.diff` que o
  harness grava com o patch atual (bytes) e apaga o resultado quando difere ou não há
  como conferir, antes de chamar o harness. Cobre o fluxo normal e o `--grade-only`.
  Há testes, e um deles falha sem a chamada. Os artefatos do run foram regerados.
- **Limite:** a invalidação olha o patch. Se o `--grading-timeout`, o dataset ou a
  versão do `swebench` mudarem, um `report.json` antigo ainda seria reaproveitado;
  hoje o dataset e a versão são fixos.
- **Atenção ao `duracao_s`:** no `grading.json`, ele é a duração da **última** chamada ao harness. Com o `--grade-only` em cache, ele não reflete o tempo da avaliação real (a reavaliação da `django-12125` levou a execução de ~89 s registrada em `cbb5e5b`; a de `3dc60d6`, toda em cache, registra ~59 s).
- **O que fazer:** ao refazer qualquer instância, rodar a correção com este código (ou
  apagar o `grading/` do run) e conferir `patch.diff` contra `predictions.jsonl`.

### 5.3 Checklist: antes de citar um número deste benchmark

1. Diga qual run e quantas instâncias (n) entraram.
2. Cite o intervalo de confiança, não só a taxa.
3. Cite o teto do ambiente do executor (B1).
4. Informe quantas instâncias terminaram por timeout, estouro de contexto ou
   erro operacional, e confira se o timeout era trabalho ou espera (B4).
5. Revise à mão as discordâncias da métrica 3 (A2, A3).

## 6. Conclusões e próximos passos

**O que os números sustentam, com as ressalvas acima:**

- O loop completo resolveu **20 de 26** (76,9%) das instâncias, com mediana de
  uma rodada (IC 95%: 57,9% a 89,0%). O executor-sanity indica um teto
  aproximado de aprovações confiáveis de 26 em 30 (25 dentro das 26 retidas).
- Quando o validador **aprovou**, errou em cerca de **uma de cada cinco vezes**
  (5 de 24; IC 95%: 9,2% a 40,5%). Ele aprovou 24 das 26 instâncias e só deixou de
  aprovar 2 (uma não resolvida e uma que o harness oficial resolve), então o recall
  (95%) discrimina pouco.
  Não há evidência nos dados para atribuir os falsos positivos a Django ou à
  falta de testes identificados: as taxas são parecidas entre os grupos, e as
  amostras são pequenas.
- A política de progresso foi acionada em 2 casos: em um o loop não resolvia o
  problema (`django-16032`); no outro (`django-12125`) o código estava certo e a suíte
  do coder ficou vermelha, provavelmente por um teste existente que a correção torna
  obsoleto. Não houve caso
  de `max_iterations`.

**Próximos passos sugeridos:**

1. **Reavaliar os rótulos oficiais várias vezes**: a revisão dos falsos positivos
   (ver [swebench-revisao-falsos-positivos.md](swebench-revisao-falsos-positivos.md))
   mostrou um rótulo instável, então a variância da correção oficial deve ser medida
   para as demais instâncias (a revisão só reavaliou uma).
2. **Investigar o caso `django-12125`**: a suíte do coder fica vermelha, provavelmente por
   um teste existente que a correção certa torna obsoleto. Vale checar se o loop consegue (ou
   deveria) detectar que um teste falhando é consequência esperada da correção, em vez
   de encerrar por falta de progresso. É uma hipótese; a #417 só mede.
3. **Completar as 4 instâncias** (ou ao menos as 3 mais baratas) quando o teto de
   créditos do usuário for ampliado, e refazer o relatório com n = 30.
4. **Repetir um subconjunto** para estimar a variância entre execuções.
5. **Avaliar outros modelos** com o mesmo sorteio e o mesmo código, para
   comparação por intervalo de confiança.
6. Os demais benchmarks levantados (CodeJudgeBench, SlopCodeBench, CUDABeaver e
   outros) só entram em issue separada, depois desta linha de base, como pede a
   #417.

## 7. Arquivos e referências

### 7.1 Código e dados

| O que | Onde |
| ----- | ---- |
| Código do benchmark e README | `benchmarks/coding_review/swebench/` |
| Código medido (não alterado) | `adk/src/agents/workflow_coding_review/` (executor, validador, `loop_policy`, `task_iterator`) |
| Run de referência | `benchmarks/coding_review/swebench/results/run_20261001_122939_github_copilot-gemini-3.7-flash_n30/` |
| Primeiro passe, antes da correção do teto | `.../run_20261001_122939_.../v1_timeout_contava_o_ritmo/` |
| Runs abandonados (não comparáveis; versionados como histórico) | `results/run_20260929_..._gpt-4_n30/` e `results/run_20261001_104340_..._gpt-4.1_n30/`, sem relatório, porque não foram concluídos |
| Testes do benchmark | `adk/.venv/bin/python -m pytest benchmarks/coding_review/swebench -q` (146 testes) |

Dentro do run de referência: `report.md` (resumo das três métricas), `report.json` (registro por instância), `progress.jsonl` (checkpoint), `patches/`, `predictions.jsonl`, `grading.json`, `metadata.json`, `sanidade_gold.json`, `sanidade_executor.json` e `run.log`. O `run.log`, o `workspace/`, o `dry_run/` e os logs brutos do harness são locais e **não são versionados** (`.gitignore`); as referências ao `run.log` neste relatório não podem ser conferidas só pelo repositório.

### 7.2 Fontes externas

- Dataset: [SWE-bench Verified](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified), revisão fixada `78f471bf655a3137b2e8a75af1501690ec009ec3`.
- Harness oficial: pacote `swebench` 5.0.2.
- Preços e créditos do Copilot: [Models and pricing for GitHub Copilot](https://docs.github.com/en/copilot/reference/copilot-billing/models-and-pricing) e [Usage-based billing for organizations and enterprises](https://docs.github.com/copilot/concepts/billing/usage-based-billing-for-organizations-and-enterprises) (consultados em 01/10/2026).
- Termos de uso do GitHub: `docs.github.com/en/site-policy/github-terms/github-terms-of-service` (ver ponto B7 da [seção 5](#5-pontos-de-atenção)).

### 7.3 Nota de escolha do benchmark

A nota [swebench-verified-loop-coder-executor.md](swebench-verified-loop-coder-executor.md) preserva o resumo da escolha do dataset e a tabela da linha de base, e aponta para este relatório.
