# Benchmark BigCodeBench (complete) — Coder Agent

Executa o benchmark [BigCodeBench](https://huggingface.co/datasets/bigcode/bigcodebench)
([arXiv:2406.15877](https://arxiv.org/abs/2406.15877)) usando o **Coder Agent**
(`adk/src/agents/workflow_coding_review/coder/`) como gerador, e os **testes
oficiais** do dataset como avaliador, executados em um **container Docker
isolado**.

Enquanto o HumanEval cobre funções curtas e autocontidas, o BigCodeBench exige
compor chamadas a **bibliotecas de terceiros** (1.140 tarefas, 139 bibliotecas) a
partir de instruções longas — o cenário real do `workflow_coding_review`.

> Esta suíte **mede** o `cr_coder`; não altera o prompt nem o comportamento do agente.

## Escopo

- Apenas o split **complete** (usa o campo `complete_prompt`: assinatura + docstring
  completa). O formato **instruct** está fora de escopo.
- Por padrão, **50 tarefas sorteadas** com seed fixa (`--seed 42`) — suficiente para
  validar o pipeline e obter um baseline inicial; rodar as 1.140 é outra etapa.
- Versão do dataset fixada em `v0.1.4`.

## Separação de responsabilidades

| Etapa | Responsável | Detalhe |
| ----- | ----------- | ------- |
| Geração | `cr_coder_agent` (real) | Implementa `task_func` em `solution.py`. |
| Avaliação | Teste oficial do BigCodeBench | Classe `unittest.TestCase` do dataset, rodada num container Docker. |
| Classificação | `grading.classify_failure` | Separa falha de biblioteca × lógica. |
| Métricas | `metrics.py` | pass@1, falhas por categoria, comparação com HumanEval. |

O grading **não é reimplementado**: o código do coder e o teste oficial são
concatenados num único módulo (como no avaliador do BigCodeBench) e executados com
o `unittest` padrão. Os testes que o coder eventualmente escreva **nunca** entram
na nota.

## Pré-requisitos

- Ambiente Python do `adk/` instalado (inclui `pyarrow` e `docker`).
- **Docker em execução** (Docker Desktop/daemon). A imagem do sandbox é construída
  automaticamente no primeiro uso (`sandbox/Dockerfile`; vários minutos e alguns GB
  — contém tensorflow, scikit-learn, pandas etc.).
- Credencial do LLM no `adk/.env` e modelo via `--model` (**obrigatório**).
- Internet no primeiro uso (dataset do Hugging Face + build da imagem).

## Uso

A partir da raiz do repositório:

```bash
# Run do critério de aceite: 50 tarefas, com a comparação com o HumanEval
python -m benchmarks.coding_review.bigcodebench.run --model <modelo> --limit 50 \
  --baseline benchmarks/coding_review/humaneval/results/<run_humaneval>

# Smoke test barato, validando antes que o sandbox executa as soluções canônicas
python -m benchmarks.coding_review.bigcodebench.run --model <modelo> --limit 3 --verify-canonical

# Tarefas específicas
python -m benchmarks.coding_review.bigcodebench.run --model <modelo> --task-ids BigCodeBench/0 BigCodeBench/1

# Retomar um run interrompido
python -m benchmarks.coding_review.bigcodebench.run --model <modelo> --limit 50 \
  --resume-dir benchmarks/coding_review/bigcodebench/results/<run>
```

O baseline vem de um run do HumanEval **com o mesmo modelo**:

```bash
python -m benchmarks.coding_review.humaneval.run --model <modelo> --limit 50
```

### Principais flags

| Flag | Default | Descrição |
| ---- | ------- | --------- |
| `--model` | **obrigatório** | Modelo LLM. |
| `--limit` | 50 | Nº de tarefas sorteadas (de 1.140). |
| `--seed` | 42 | Seed do sorteio — mesmas tarefas em runs diferentes. |
| `--task-ids` | — | Tarefas específicas (ignora `--limit`/`--seed`). |
| `--timeout` | 120 | Teto (s) por avaliação no container. |
| `--baseline` | — | `report.json` (ou diretório) do HumanEval para a comparação. |
| `--verify-canonical` | off | Roda as soluções de referência no sandbox antes de gerar. |
| `--image` / `--rebuild-image` | build local | Imagem do sandbox / força reconstrução. |
| `--allow-network` | off | Liga a rede no container (default: sem rede). |
| `--output-dir` | `results/` | Base dos relatórios. |
| `--resume-dir` | — | Retoma um run (valida `metadata.json`). |

## Saídas

Cada run cria `results/run_<timestamp>_<modelo>_n<N>/` com:

- `report.json` — relatório completo (métricas + por tarefa).
- `report.md` — resumo legível com as três métricas.
- `metadata.json` — parâmetros do run (`model`, `limit`, `seed`, `timeout`, …).
- `progress.jsonl` e `workspace/` — checkpoint e workspace do coder (não versionados).

## O que cada métrica significa

1. **Pass@1** — fração das tarefas cuja solução passa em **todos** os testes
   oficiais na primeira (única) tentativa.
2. **Falhas por import/dependência × lógica** — cada reprovação é classificada pelo
   stderr do `unittest`:

   | Grupo | Categoria | Significado |
   | ----- | --------- | ----------- |
   | Biblioteca | `missing_dependency` | `ModuleNotFoundError`: importou um módulo que não existe no ambiente. |
   | Biblioteca | `import_error` | `ImportError`: símbolo inexistente no módulo importado. |
   | Biblioteca | `api_misuse` | `AttributeError`/`TypeError` ligados a API de biblioteca (atributo/argumento inexistente, erro dentro de `site-packages`). |
   | Lógica | `logic` | `AssertionError` nos testes oficiais. |
   | Lógica | `runtime_error` | Outras exceções em tempo de execução. |
   | Outras | `syntax`, `timeout`, `no_solution`, `generation_error` | Sintaxe inválida, estouro de tempo, sem `solution.py`, falha do LLM. |

   Precedência quando há mais de um erro: dependência > import > API > asserção > runtime.
3. **Comparação com o HumanEval** — pass@1 do mesmo modelo nos dois benchmarks,
   variação em pontos percentuais e queda relativa. Quantifica o quanto o
   desempenho cai quando há bibliotecas reais.

## Sandbox

O código gerado por LLM roda **somente** em container (`DockerSandbox` do
`shared/execution/sandbox.py`), nunca no ambiente do dev:

- imagem `ai4se-bigcodebench-sandbox:v0.1.4` com as bibliotecas das tarefas
  (`sandbox/requirements.txt`, pinadas como no avaliador oficial) e dados do NLTK;
- **sem rede** (`network_mode=none`), 4 GB de RAM, 2 CPUs, timeout por avaliação;
- container efêmero, removido ao fim de cada avaliação.

## Limitações

- **Amostra pequena (50 tarefas)**: com n=50 o intervalo de confiança do pass@1 é
  largo (≈ ±14 p.p. a 50%). Serve para validar o pipeline e dar um baseline
  inicial, não para ranquear modelos.
- **Tarefas diferentes entre benchmarks**: a comparação com o HumanEval compara
  taxas de conjuntos distintos de problemas; indica a ordem de grandeza da queda,
  não uma diferença pareada.
- **`api_misuse` é heurístico**: baseia-se em tipo de exceção + marcadores no
  traceback. Pode classificar como `runtime_error` um uso incorreto de API que
  levantou outra exceção, e vice-versa.
- **Sem rede**: tarefas cujo teste exige rede real falham mesmo com solução
  correta. Use `--verify-canonical` para identificar tarefas em que até a solução
  de referência falha no ambiente (e `--allow-network` se necessário).
- **Ambiente ≠ ambiente do coder**: as versões das bibliotecas são as do avaliador
  oficial (Python 3.10); o coder não executa o código nessa imagem.
- **1 amostra por tarefa**: só pass@1 (sem `--samples`/pass@k nesta versão).
- Sem o split `instruct` e sem as 1.140 tarefas (fora de escopo desta etapa).

## Arquitetura dos módulos

- `bootstrap.py` — reutiliza o do HumanEval (`sys.path`, `.env`, provider, workspace).
- `dataset.py` — download do parquet (HF), parsing e amostragem com seed.
- `contract.py` — tarefa → contrato de task + mensagem de entrada do coder.
- `coder_runner.py` — invoca o `cr_coder_agent` (reusa helpers do HumanEval).
- `grading.py` — teste oficial no container + classificação da falha.
- `categories.py` — categorias/grupos de falha.
- `sandbox_image.py` + `sandbox/` — imagem Docker de avaliação.
- `metrics.py` — pass@1, falhas por categoria, baseline.
- `run.py` — orquestrador CLI.
