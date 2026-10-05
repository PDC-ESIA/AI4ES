# Benchmark SWE-bench Verified — loop coder → executor

Linha de base reproduzível do **loop de codificação** do `workflow_coding_review`
(issue #417): o `cr_coder_agent` implementa, o `cr_executor_agent` roda o harness
e obedece ao `implementation_validator`, e a política de progresso
(`executor/loop_policy.py`) decide quando parar. Até aqui só o coder tinha
benchmark ([HumanEval](../humaneval/README.md), [MBPP](../mbpp/README.md)).

Os problemas vêm do [SWE-bench Verified](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified):
500 issues reais de 12 projetos Python, revisados por humanos. A correção é feita
pelo **harness oficial do SWE-bench**, com os testes escondidos do dataset —
nunca com os testes que o coder escreveu.

> **Este benchmark mede; não corrige.** Nenhum arquivo daqui altera o executor, o
> validador ou a `loop_policy`.

## O que é medido

| # | Métrica | Pergunta | Fonte |
| - | ------- | -------- | ----- |
| 1 | **Taxa de resolução** | De N instâncias, quantas o loop resolveu de fato? | Harness oficial: `FAIL_TO_PASS` passam **e** `PASS_TO_PASS` continuam passando |
| 2 | **Rodadas e motivo de parada** | Quantas rodadas o loop gastou, e quem mandou parar? | Plugin de guarda (rodadas) + `classificar_desfecho` da produção (motivo) |
| 3 | **Concordância do validador** | Quando o validador disse "aprovado", o bug estava resolvido? | Último veredito do validador × `resolved` oficial |

Detalhes de cálculo:

- **Métrica 1:** resolvidas ÷ **todas** as instâncias do run. Patch vazio,
  patch que não aplica, timeout dos testes oficiais, erro de avaliação, falha na
  preparação e instância não avaliada contam como não resolvidas (e aparecem
  discriminados, com a causa). Sempre com intervalo de confiança de Wilson
  (95%). Se o `--gold-sanity` foi rodado, a taxa sai também **sem** as instâncias
  que nem o patch oficial resolve.
- **Métrica 2:** uma rodada = um turno do executor (inclusive as recusadas pelo
  gate de executabilidade). O motivo é classificado nesta ordem:
  1. `aprovado` → **aprovação do validador**;
  2. `bloqueado_*` / `aceito_com_ressalvas_*` → **política de progresso**, com o
     sub-motivo (`plato_nota`, `erro_repetido`, `sem_alteracao_arquivos`,
     `orcamento_de_falhas_distintas`);
  3. erro/timeout da instância → **outro**;
  4. rodadas ≥ teto (`AI4ES_MAX_LOOP_ITERATIONS`, padrão 20) → **`max_iterations`**
     (a produção não tem rótulo próprio para esse caso);
  5. o resto → **outro** (ex.: o LLM do executor chamou `exit_loop` sem aprovação).
- **Métrica 3:** matriz de confusão completa (a issue pede os falsos positivos;
  a matriz sai de graça), com precisão, recall e a taxa de falsos positivos entre
  as aprovações. Entram só instâncias com gabarito conhecido: ficam fora erro de
  avaliação, falha na preparação (o validador nem rodou) e as excluídas pelo
  `--gold-sanity` (gabarito não confiável). Cada aprovação é **qualificada**,
  porque o validador aprova pelo status técnico da suíte que o **próprio coder**
  declarou:
  - `suite_vazia_ou_pulada` — nenhum teste declarado (o harness aceita `PULADO`);
  - `patch_vazio` — aprovou sem nenhuma mudança de código;
  - `testes_nao_identificados` — havia comandos de teste, mas o harness não
    reconheceu testes individuais (a leitura por teste só entende pytest).

## Como cada instância é executada

1. **Preparação.** O `/testbed` é copiado de dentro da imagem oficial da
   instância (`swebench/sweb.eval.x86_64.<id>`) para `coder/src/` — os mesmos
   bytes que o harness oficial usa na correção. Uma fotografia git desse estado é
   tirada, e o benchmark grava na raiz `Dockerfile`, `.dockerignore` e `run.json`.
   A task (`TASK-001.json`) é montada a partir do `problem_statement`.
2. **Loop.** O `code_execute_loop` roda até parar sozinho, no ramo "projeto
   existente" do workflow (ver decisões abaixo). O coder e o validador **nunca**
   veem `patch`, `test_patch`, `FAIL_TO_PASS`, `PASS_TO_PASS` nem `hints_text`.
3. **Registro.** Rodadas, desfecho, último veredito, evidências do último
   `ExecutionReport`, ocorrências do plugin de guarda e uso de tokens vão para o
   `progress.jsonl`.
4. **Patch.** O diff entre a fotografia e o estado final, sem os arquivos do
   benchmark, `PLAN.md`, caches e os caminhos que o `test_patch` toca. O git
   roda com configuração neutra (a config global do host não muda o patch), o
   diff é montado arquivo a arquivo, e um arquivo cujo conteúdo não é UTF-8 sai
   como `GIT binary patch` em vez de corromper o patch inteiro. Arquivos novos
   escondidos pelo `.gitignore` do repositório não entram, mas ficam registrados
   (`ignorado_pelo_gitignore`).
5. **Correção** (depois de todas as instâncias). `predictions.jsonl` →
   `swebench.harness.run_evaluation` → `resolved` por instância. Quando o harness
   não grava o `report.json`, o log da instância diz se o patch não aplicou ou se
   os testes estouraram o timeout (não resolvida, como no SWE-bench) ou se foi
   erro de avaliação. O código de saída do harness vai para o cabeçalho do
   `report.md`, com alerta se não for zero.

Se a preparação de uma instância falhar (ex.: o pull da imagem caiu), ela é
registrada como `falha_preparacao` e **refeita** na retomada; se a falha
persistir, ela conta como não resolvida na métrica 1 e fica fora da métrica 3.

**Controle de ritmo.** O Copilot limita a **vazão** de tokens numa janela de
tempo, independentemente dos créditos do mês, e, depois de estourado, bloqueia
por um bom tempo (medido: ~50 min). Por isso, antes de cada chamada ao modelo
o plugin de guarda espera o necessário para a média ficar abaixo de
`--max-tokens-per-minute` (padrão **50.000**, entrada + saída; `0` desliga),
com 1 minuto de folga para rajadas. O padrão saiu do que foi medido: o bloqueio
veio com ~3 milhões de tokens em ~12 min, e a reposição estimada é de ~60 mil
tokens por minuto. A espera fica registrada à parte (`pausa_ritmo_s`) e não
entra na duração ativa do loop.

Se o **provedor de LLM** falhar no meio de uma instância (rate limit, cota,
credencial expirada, rede), o run **espera e refaz a instância do zero**: 10
minutos na primeira vez, dobrando a cada nova tentativa (`--provider-wait`,
`--provider-retries`; padrão 4 tentativas, ~2,5 h de espera no total). O
Copilot limita o ritmo de chamadas ("rate limit for utility models"), e um run
de 30 instâncias bate nesse limite várias vezes. Se o bloqueio persistir depois
das tentativas, o run **para** com o aviso de como retomar, e a instância fica
marcada como `falha_provedor`, a ser refeita na retomada. Nada disso conta como
falha do loop. Estouro de contexto **não** entra nessa regra: ele é resultado do
próprio loop. O `gpt-4` (32k de contexto) falhou já na 1ª instância com um
"Bad Request" genérico, atribuído ao limite de contexto; o `gpt-4.1` (128k) ainda
estourou no 1º turno de uma instância do astropy. A linha de base usa o
`gemini-3.7-flash` (200k de contexto), sem estouros.

## Decisões de desenho

| Decisão | O que foi feito | Por quê |
| ------- | --------------- | ------- |
| Entrada do loop | Roda o `_code_execute_loop` direto, com `execution_result` = marcador `NOVA_TASK:` e os arquivos do repositório registrados como herdados | Pelo `TaskIterator`, a 1ª task cai no ramo "crie o `PLAN.md` e implemente o projeto COMPLETO". O ramo `NOVA_TASK` é o que a produção usa da 2ª task em diante — nada muda no código de produção. O desfecho é classificado pela mesma `classificar_desfecho` |
| Ambiente do executor | `Dockerfile` `FROM` a imagem oficial, com o env conda `testbed` no `PATH`, o código editado em `/testbed` e `/app` → symlink para `/testbed` | O harness roda `/bin/sh -c` (sem ativar conda) em `/app`. O código fica no mesmo caminho da avaliação oficial, para onde aponta a instalação editável; o link no sentido inverso fazia o pytest carregar o mesmo `conftest.py` por dois caminhos (erro de coleta no astropy) |
| Guarda do ambiente | Plugin do `Runner` (só do benchmark) restaura `Dockerfile`, `.dockerignore` e `sandbox: docker` antes de cada turno do executor, e conta as rodadas | O prompt de sistema do coder manda usar `sandbox` direct e virtualenv — o que rodaria o repositório **no host**, sem dependências. Toda restauração é registrada |
| Base do patch | Fotografia git (índice temporário + `write-tree`), sem commit | O `/testbed` já vem modificado pelo `pre_install` de alguns projetos; um diff contra o `base_commit` quebraria o `git apply` da correção |
| Correção | Pacote `swebench` fixado, em venv separado, recebendo o **mesmo** parquet fixado | O `adk/` usa Python 3.14; o harness oficial não declara suporte a ela. Execução e gabarito usam os mesmos dados |
| Dataset | Revisão fixada (`78f471bf…`) via `huggingface_hub` + `pyarrow` | O schema do dataset já mudou; sem fixar, a linha de base não se reproduz |
| Memória (mem0) | Forçada **desligada** | Lições de uma instância vazariam para a seguinte |

## Pré-requisitos

- Ambiente do `adk/` instalado e credencial do LLM no `adk/.env`.
- Docker funcionando, em máquina **x86_64** (as imagens oficiais são x86_64).
- Disco: medido no primeiro run, cerca de **2,4 GB por instância** (imagens
  oficiais). Reserve ~70 GB para 30 instâncias. Para liberar depois:
  `docker rmi $(docker images 'swebench/sweb.eval.*' -q)`.
- Venv separado com o harness oficial, a partir da raiz do repositório:

```bash
uv venv --python 3.12 benchmarks/coding_review/swebench/.venv-swebench
uv pip install --python benchmarks/coding_review/swebench/.venv-swebench/bin/python \
  -r benchmarks/coding_review/swebench/requirements-grading.txt
```

(Outro caminho pode ser informado com `--swebench-python` ou `SWEBENCH_PYTHON`.)

## Uso

A partir da raiz do repositório:

```bash
# 1. Sorteio + tasks/mensagens que o coder receberia (sem LLM, sem Docker)
python -m benchmarks.coding_review.swebench.run --model <modelo> --limit 30 --dry-run

# 2. Sanidade do ambiente de correção: patches OFICIAIS no harness oficial (sem LLM)
python -m benchmarks.coding_review.swebench.run --model <modelo> --limit 30 \
  --gold-sanity --resume-dir benchmarks/coding_review/swebench/results/<run>

# 3. Sanidade do ambiente do EXECUTOR: solução oficial + harness do executor (sem LLM)
python -m benchmarks.coding_review.swebench.run --executor-sanity \
  --resume-dir benchmarks/coding_review/swebench/results/<run>

# 4. Run completo (loop + correção + relatório)
python -m benchmarks.coding_review.swebench.run --model <modelo> --limit 30 \
  --resume-dir benchmarks/coding_review/swebench/results/<run>

# Retomar um run interrompido (pula instâncias já concluídas)
python -m benchmarks.coding_review.swebench.run --model <modelo> --limit 30 --resume-dir <run>

# Só o loop agora; corrigir depois
python -m benchmarks.coding_review.swebench.run --model <modelo> --limit 30 --skip-grading
python -m benchmarks.coding_review.swebench.run --model <modelo> --limit 30 --grade-only --resume-dir <run>
```

Use o Python do venv do `adk/` (`adk/.venv/bin/python`). O `--model` é
obrigatório num run novo; na retomada, vale o modelo gravado no run original.
A retomada exige os mesmos `model`, `seed`, `limit`, revisão do dataset,
instâncias, `--instance-timeout` e `--grading-timeout` do run original.

Todo comando sem `--resume-dir` cria um diretório novo em `results/`, inclusive
`--dry-run` e `--gold-sanity`. Se um sorteio não for aproveitado, apague o
diretório antes do commit: ele não é ignorado pelo git.

### Principais flags

| Flag | Default | Descrição |
| ---- | ------- | --------- |
| `--model` | **obrigatório** | Modelo LLM do loop (coder, executor e validador) |
| `--limit` | 30 | Instâncias sorteadas |
| `--seed` | 42 | Seed do sorteio |
| `--instance-ids` | — | Usa estas instâncias em vez do sorteio |
| `--dataset-revision` | `78f471bf…` | Revisão do dataset no Hugging Face |
| `--max-tokens-per-minute` | 50000 | Teto de tokens por minuto enviados ao LLM (controle de ritmo; `0` desliga) |
| `--only-ids` | — | Roda, nesta execução, só estas instâncias; as demais pendentes ficam para outra retomada (o relatório cobre só as que têm registro) |
| `--instance-timeout` | 3600 | Teto (s) de TRABALHO do loop por instância: desconta as pausas do controle de ritmo e do rate limit. Aproximado: só é checado quando o harness devolve o controle, então pode passar pelo tempo de um build ou de uma bateria de testes |
| `--swebench-python` | `.venv-swebench/bin/python` | Python do harness oficial |
| `--grading-workers` | 2 | Workers do harness oficial |
| `--grading-timeout` | 1800 | Timeout (s) por instância na correção |
| `--dry-run` | — | Só sorteio + tasks/mensagens |
| `--gold-sanity` | — | Corrige os patches oficiais (valida o ambiente de correção) |
| `--executor-sanity` | — | Aplica a solução oficial e roda o harness do executor (valida o ambiente do executor) |
| `--skip-grading` / `--grade-only` | — | Separa o loop da correção |

## Saídas

Cada run cria `results/run_<timestamp>_<modelo>_n<N>/`:

| Arquivo | Conteúdo | Versionado |
| ------- | -------- | ---------- |
| `report.md` | Resumo com as três métricas | sim |
| `report.json` | Métricas + registro completo por instância | sim |
| `metadata.json` | Parâmetros, ids sorteados, commit, versão do swebench, teto do loop, variáveis `AI4ES_*` | sim |
| `progress.jsonl` | Checkpoint por instância (base da retomada) | sim |
| `predictions.jsonl` | Patches no formato do SWE-bench | sim |
| `patches/<id>.diff` | Patch de cada instância | sim |
| `grading.json` | Resultado oficial por instância + comando executado | sim |
| `sanidade_gold.json` | Resultado do `--gold-sanity` | sim |
| `sanidade_executor.json` / `.jsonl` | Resultado do `--executor-sanity` (e o checkpoint dele) | sim |
| `workspace/`, `dry_run/`, `grading/logs/`, `grading_gold/` | Cópia do repositório avaliado e logs brutos | **não** (`.gitignore`) |

## Validação antes do primeiro run completo

1. `--dry-run`: confira o sorteio e leia algumas `dry_run/<id>/mensagem_coder.md`.
2. `--gold-sanity`: as instâncias que **não** resolvem nem com o patch oficial
   têm problema de ambiente. Elas ficam em `sanidade_gold.json` e o relatório as
   aplica automaticamente: a métrica 1 sai com e sem elas, e a métrica 3 as
   deixa fora da matriz. Documente-as na nota da linha de base.
3. `--executor-sanity`: com o patch e os testes **oficiais** aplicados no
   workspace e o comando de teste oficial no `run.json`, o harness do executor
   deveria dar sucesso. Onde não dá (timeout de 120 s, falta de memória, teste
   que já falha naquele arquivo), a causa é o ambiente do executor, não o LLM:
   é um teto aproximado das aprovações confiáveis do validador. O resumo entra
   no `report.md`.
4. Uma instância de ponta a ponta: confirme no `report.md` que houve rodadas,
   que a guarda não precisou intervir o tempo todo e que o patch não saiu vazio.
   Um novo run com `--instance-ids <id> --limit 1` usa outro diretório; para
   manter o run principal intacto, rode essa instância à parte.
5. As 30 instâncias.

O mecanismo do ambiente (extração do `/testbed`, `Dockerfile` do benchmark, env
`testbed` no `PATH`, código editado em `/testbed` com `/app` → `/testbed`) foi
validado com o harness de produção sobre uma imagem de teste com o mesmo layout
das oficiais; o passo 3 confirma o mesmo numa imagem oficial.

## Limitações (leia antes de interpretar)

- **Amostra pequena.** Com 30 instâncias, cada uma vale 3,3 p.p.; para ~30% de
  resolução o IC 95% vai de ~17% a ~48%. A métrica 3 é ainda mais frágil: o
  denominador é o número de aprovações.
- **O gabarito também erra.** Os testes oficiais só cobrem o que o PR original
  testou (estudos estimam que ~8–11% dos patches "resolvidos" estão errados), e
  alguns testes exigem detalhes específicos da solução original. Revise à mão as
  discordâncias da métrica 3.
- **A métrica 3 mede o sinal de parada, não o "julgamento" de um LLM.** O
  validador aprova quando a suíte do coder passa. Um falso positivo pode ser
  teste fraco, ausência de teste ou validador permissivo — os qualificadores
  ajudam a separar, mas não resolvem sozinhos.
- **A métrica 1 depende mais do coder do que do executor.** O coder não tem
  ferramenta de busca e lê arquivos inteiros; em repositórios grandes, ele
  estoura o contexto do modelo. Medido: o `gpt-4` (32k) falhou já na 1ª
  instância com um "Bad Request" genérico, atribuído ao contexto, e o `gpt-4.1`
  (128k) estourou no 1º turno de uma instância do astropy (169 mil tokens). Esses casos saem com o motivo `estouro_de_contexto` (categoria
  "outro" na métrica 2). Os tokens ficam registrados por instância e por
  agente, incluindo o `implementation_validator` (contado pelo plugin, porque
  ele roda num Runner interno do `AgentTool`).
- **Conflitos com o prompt de sistema do coder.** Ele manda criar virtualenv e
  usar `sandbox` direct. A guarda restaura o `sandbox`, mas não reescreve os
  comandos do coder — instâncias com virtualenv no `run.json` são listadas no
  relatório.
- **Limites do container do executor** (constantes do executor, fora do escopo):
  512 MB de memória, 50% de uma CPU, 120 s por comando de teste, 300 s de build.
  Testes pesados podem estourar e virar sinal de falha para a política.
- **Leitura de testes só entende pytest.** Em Django (`runtests.py`) e SymPy
  (`bin/test`) o harness decide pelo exit code, sem contagem por teste.
- **Código compilado** (astropy, scikit-learn): uma correção em C/Cython exige o
  coder declarar a recompilação no `build`.
- **Não determinismo.** Uma execução por instância não separa dificuldade de
  sorte; para estimar a variância, repita um subconjunto.
- **Contaminação.** As issues são de 2012–2023 e públicas; o modelo pode lembrar
  a correção. Há ainda issues cujo texto já traz a correção proposta pelo autor
  (ex.: `sympy__sympy-16766`) — isso é entrada oficial do dataset, não vazamento
  do benchmark.
- **Reprodutibilidade.** Provedores atualizam modelos com o mesmo nome; o
  `metadata.json` registra o que foi possível (modelo, data, commit, versões).

## Arquitetura dos módulos

| Módulo | Responsabilidade |
| ------ | ---------------- |
| `bootstrap.py` | `sys.path`, `.env`, modelo, workspace, mem0 desligado, providers LLM |
| `dataset.py` | Download/cache do parquet fixado e sorteio determinístico |
| `contract.py` | Task + mensagem ao coder (sem nada do gabarito) |
| `environment.py` | Extração do `/testbed`, `Dockerfile`/`.dockerignore`/`run.json`, restauração |
| `guard_plugin.py` | Plugin do `Runner`: rodadas + guarda do ambiente |
| `loop_runner.py` | Roda o `code_execute_loop` numa instância e classifica o desfecho |
| `snapshot.py` / `patch.py` | Fotografia git e extração do patch filtrado |
| `grading.py` | Predições, chamada ao harness oficial e leitura do `report.json` |
| `executor_sanity.py` | Solução oficial + harness do executor (`--executor-sanity`) |
| `metrics.py` / `report.py` | As três métricas e o `report.md` |
| `run.py` | CLI, checkpoint/retomada, `--dry-run`, `--gold-sanity`, `--executor-sanity`, `--grade-only` |

## Testes

Sem LLM, sem rede e sem imagens do SWE-bench:

```bash
adk/.venv/bin/python -m pytest benchmarks/coding_review/swebench -q
```

Cobrem, entre outros: o **não vazamento do gabarito**, o sorteio determinístico,
a extração do patch sobre uma árvore "suja" de `pre_install` (e a aplicação dele
com `git apply`) — inclusive com uma config git hostil no host e com arquivos
que não são UTF-8 —, a guarda rodando dentro de um `Runner` real do ADK antes do
gate do executor, a classificação de todos os motivos de parada da produção, a
leitura dos relatórios e dos logs do harness oficial, a retomada (falha na
preparação refeita, checkpoint com linha truncada) e as exclusões do
`--gold-sanity`. Constantes da produção (nome dos
agentes, estágios do harness, motivos da política, workdir do sandbox) são
conferidas por AST, para o benchmark não se descolar do código medido.
