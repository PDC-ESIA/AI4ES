# Benchmark CodeJudgeBench (CodeRepair) — Reviewer Agent

Mede a qualidade do julgamento do `cr_reviewer` do `workflow_coding_review`:
**com que frequência ele aprova código que não funciona, ou bloqueia código que
funciona?** Issue #421.

## O que é medido

O split CodeRepair do [CodeJudgeBench](https://arxiv.org/abs/2507.10535)
(`mattymchen/codejudgebench` no Hugging Face) traz, para cada problema de
programação competitiva, uma solução com bug e **duas tentativas de correção**:

| Campo | Rótulo |
| --- | --- |
| `pos_response` | passa nos testes ocultos do problema |
| `neg_response` | falha nos testes ocultos |

O rótulo vem da execução feita pelos autores do dataset. **Este benchmark não
executa código**: o reviewer julga cada resposta, e o veredito é comparado ao
rótulo.

## Como rodar

A partir da raiz do repositório, com o `adk/.venv` e as credenciais do `adk/.env`:

```bash
# piloto — confira custo e tempo antes do run completo
python -m benchmarks.coding_review.codejudgebench.run --model github_copilot/gpt-4 --limit 5

# run da issue #421
python -m benchmarks.coding_review.codejudgebench.run --model github_copilot/gpt-4 --limit 50

# retomar um run interrompido (cota, queda de rede, Ctrl+C)
python -m benchmarks.coding_review.codejudgebench.run --model github_copilot/gpt-4 --limit 50 \
    --resume-dir benchmarks/coding_review/codejudgebench/results/run_<ts>_<modelo>_n50
```

Antes de começar, o run faz uma chamada mínima ao modelo (pre-flight) e aborta
se ela falhar — por exemplo, com a cota mensal do GitHub Copilot esgotada.

**Com Gemini (Google AI Studio):** defina `GOOGLE_API_KEY` no `adk/.env` e passe
o nome do modelo sem prefixo — `--model gemini-2.5-flash`. O ADK resolve `gemini-*`
nativamente; o pre-flight testa o mesmo caminho. Mantenha o split padrão
(`claude_3.7_sonnet`): os splits `gemini_*` foram gerados por modelos da mesma
família do reviewer.

| Opção | Default | O que faz |
| --- | --- | --- |
| `--model` | obrigatório | Modelo do reviewer (sobrescreve `ADK_LLM_MODEL`) |
| `--limit` | todos | Número de pares |
| `--split` | `claude_3.7_sonnet` | Modelo que gerou as respostas: `claude_3.7_sonnet`, `gemini_2.5_flash`, `gemini_2.5_pro` |
| `--seed` | `42` | Semente da amostragem |
| `--max-per-question` | `1` | Pares por problema (`0` = sem limite) |
| `--pair-ids` | — | Avalia só os pares listados |
| `--max-retries` | `1` | Retries quando a revisão vem sem status |
| `--no-explanation` | — | Não envia o relato do coder (texto da resposta sem o código) |
| `--max-consecutive-operational` | `3` | Interrompe após N pares seguidos com falha de API |

## Saída

```
results/run_<timestamp>_<modelo>_n<N>/
├── metadata.json    parâmetros do experimento, revisão do dataset, versões do ambiente
├── progress.jsonl   checkpoint — um par por linha, gravado assim que o par termina
├── report.json      métricas + todos os pares
├── report.md        resumo legível
└── reviews/         markdown de cada revisão (<par>_pos.md, <par>_neg.md), para auditoria
```

`workspace/` (rascunho do reviewer durante o run) e `progress.jsonl` (checkpoint;
o `report.json` já contém todos os pares) não são versionados.

### Recalcular sem chamar o LLM

```bash
python -m benchmarks.coding_review.codejudgebench.regrade benchmarks/coding_review/codejudgebench/results/run_<ts>_<modelo>_n50
```

Relê os markdowns de `reviews/`, refaz a leitura das issues (severidade, camada)
com o parser atual e regrava `report.json` e `report.md`. Os vereditos não mudam:
vêm do manifesto no momento do run. Use depois de corrigir o parser, sem pagar
um novo run.

## Métricas

**As três da issue:**

| Métrica | Leitura |
| --- | --- |
| Acurácia do julgamento | Pares em que o reviewer aprovou a `pos` e bloqueou a `neg`. Empate conta como erro. Chute = 50% no melhor caso |
| Viés posicional | **Não se aplica ao modo pontual** — ver "Desenho do experimento" |
| Resposta inválida | Revisões sem status que o manifesto reconheça, na 1ª tentativa e após os retries. Mede se o pipeline consegue ler o veredito, não aderência ao `ReviewOutput`: o reviewer produz markdown, e o harness converte para o schema depois |

**Decisão por resposta** — responde diretamente à pergunta da issue:

| Métrica | Leitura |
| --- | --- |
| Aprovou código que falha (`false_approve_rate`) | `neg` aprovadas / `neg` julgadas |
| Bloqueou código que passa (`false_block_rate`) | `pos` bloqueadas / `pos` julgadas |
| Camadas dos bloqueios indevidos | Em que camada (completude, arquitetura, corretude, testes) caem as issues críticas das `pos` bloqueadas |

**Complementares:** decisividade (pares com vereditos diferentes), acurácia só
entre os decididos, acurácia com empate valendo ½, recorte por dificuldade,
falhas só de formato, tokens e tempo.

Toda proporção vem com intervalo de confiança de Wilson a 95% (protocolo §12).
Com 50 pares, a margem fica perto de ±13 pontos — leia os números com isso em mente.

### Desfechos de um par

| pos | neg | Desfecho |
| --- | --- | --- |
| APROVADO | BLOQUEADO | `correct` |
| BLOQUEADO | APROVADO | `wrong` |
| APROVADO | APROVADO | `tie_approve` |
| BLOQUEADO | BLOQUEADO | `tie_block` |

Ficam fora da acurácia: `invalid` (reviewer sem status — medido à parte),
`operational` (falha de API — refeito na retomada) e `no_code` (resposta do
dataset sem código).

## Desenho do experimento

O reviewer é medido **como está em produção**: prompt, schema, análise estática
(Ruff + Bandit) e gate de cobertura intactos. O harness recria em volta dele o
que o pipeline normalmente fornece.

- **Modo pontual.** O reviewer avalia um workspace e devolve APROVADO/BLOQUEADO;
  não há campo de preferência entre duas respostas. Cada resposta é revisada
  sozinha e a escolha é derivada dos dois vereditos. Por isso não existe ordem
  A/B a inverter, e o viés posicional não se aplica.
- **Veredito do pipeline.** O status é lido com a mesma função que o manifesto
  usa em produção (`manifest._validation_verdict`). Uma leitura tolerante do
  markdown registra à parte os casos em que o reviewer decidiu, mas escreveu o
  status fora do padrão.
- **`ReviewOutput`.** O reviewer produz markdown (o schema de `reviewer/schemas.py`
  não é usado pelo agente). O harness converte o markdown em `ReviewOutput`.
- **Gate de cobertura.** Sem `task_iteration_summary` no state, o gate força
  BLOQUEADO em toda revisão. O harness injeta um summary mínimo e válido; o
  resultado da task diz `status=nao_executado`, sem alegar que testes passaram.
- **Ambiente de execução.** O LiveCodeBench, de onde o CodeJudgeBench deriva,
  insere um cabeçalho de imports (`from typing import *`, `from collections
  import *`, …) antes de executar qualquer solução; os rótulos pos/neg foram
  gerados com ele. O `solution.py` traz o mesmo cabeçalho, delimitado e com
  `# ruff: noqa: F401, F403, F405`, e a task avisa o reviewer que ele não faz
  parte da resposta. Sem isso, respostas LeetCode corretas (que usam `List` sem
  importar) eram bloqueadas como `NameError` — 19 das 32 pos bloqueadas num run
  com gpt-5-mini antes da correção.
- **Entrada.** O código da resposta (último bloco `python`) vai para
  `coder/src/solution.py`, depois do cabeçalho. O enunciado, a solução com defeito e a falha observada
  seguem no formato de task do context_engineer. A explicação da resposta entra
  como relato do coder, sem o código (desligável com `--no-explanation`).
- **Amostra.** Embaralhamento do split inteiro com a seed, depois o corte — a
  amostra de 50 está contida na de 100. No máximo um par por problema, para
  que os pares sejam independentes.
- **Memória.** `AI4ES_MEMORY_ENABLED` é forçado para `false`: o benchmark nunca
  grava lições no mem0.

## Limitações

- **Programação competitiva ≠ projeto.** As soluções cabem num arquivo e não
  têm testes nem README. As camadas de completude, arquitetura e testes do
  reviewer podem bloquear respostas corretas por motivos alheios à corretude —
  a métrica de camadas dos bloqueios indevidos existe para medir isso.
- **Auto-preferência.** O split `gemini_2.5_flash` foi gerado pelo mesmo modelo
  padrão do reviewer. O default `claude_3.7_sonnet` evita esse cruzamento.
- **Ruff com `import *`.** Com o cabeçalho do ambiente, o Ruff não distingue um
  nome realmente indefinido de um nome vindo dos `import *` (F405 suprimido). É
  o mesmo comportamento do ambiente real; o reviewer continua lendo o código.
- **Uma execução por par.** O protocolo sugere 10 a 20 repetições por problema
  para medir estabilidade; este baseline tem uma. A variação entre execuções não
  é medida.
- **O reviewer fica fora do loop.** Na develop atual ele roda uma vez, depois do
  loop coder↔executor, e seu veredito define o status da fase no manifesto. O
  benchmark mede esse veredito, não a política de parada do loop.
- **Download pela API de linhas do Hugging Face.** A revisão do dataset é
  gravada no cache e no `metadata.json`; runs posteriores reusam o cache.

## Testes

```bash
python -m pytest benchmarks/coding_review/codejudgebench/ -q
```

No Windows com Controle de Aplicativo ativo, o plugin de pytest do LangSmith
(instalado como dependência) pode ter a DLL `_uuid_utils` bloqueada e derrubar a
coleta dos testes. O benchmark não usa o plugin; desligue-o com
`-p no:langsmith_plugin`.

Sem rede e sem LLM: a API do Hugging Face e o reviewer são simulados. Um dos
testes valida o summary sintético contra o gate real de `review_tools`.
