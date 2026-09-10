# Benchmark de LLMs — Agente de Requisitos

Harness para comparar modelos de linguagem na tarefa de Engenharia de Requisitos,
usando **LLM-as-a-Judge**. 

O fluxo tem três fases:

```
executar + coletar  →  julgar  →  analisar
   (manual)           (auto)      (auto)
```

---

## 1. Instalação

Uma vez, na raiz do repositório:

```bash
cd adk
uv pip install pandas scipy scikit-posthocs
```

Todos os comandos abaixo assumem que você está na **raiz do repositório**
(`AI4ES/`) e usam o Python do venv do `adk/`.

---

## 2. Configuração

Tudo que define o experimento está em [`config.py`](config.py). **Não redefina
esses valores em outro lugar** — a comparabilidade entre execuções depende de
todos os scripts lerem da mesma fonte.

| Constante | O que é |
| :--- | :--- |
| `CANDIDATOS` | Modelos **avaliados** — produzem os artefatos pontuados |
| `JUIZES` | Modelos que **aplicam a rubrica**. Lista independente de `CANDIDATOS` |
| `EXCLUIR_AUTOAVALIACAO` | `True` — um modelo nunca pontua a própria resposta |
| `CRITERIOS` | Os 8 critérios da rubrica, em ordem fixa |
| `TEMPERATURA_JUIZ` | `0.0` — sem isso o julgamento não é reprodutível |
| `ALFA` | `0.05`, nível de significância dos testes |

### Candidatos e juízes são conjuntos independentes

Os dois papéis foram desacoplados: as listas podem ser disjuntas, parcialmente
sobrepostas ou idênticas. Duas funções derivam o comportamento:

- `juizes_de(candidato)` — juízes elegíveis para aquele candidato.
- `intersecao()` — modelos que atuam nos dois papéis.

O que fazer quando um candidato também é juiz é controlado por
`EXCLUIR_AUTOAVALIACAO`:

| Valor | Comportamento | Custo |
| :--- | :--- | :--- |
| `False` *(atual)* | O modelo avalia a própria resposta, **às cegas** | Viés de auto-preferência |
| `True` | A autoavaliação é descartada | Desenho desbalanceado: esse candidato fica com um juiz a menos |

**Configuração atual — teste piloto.** `EXCLUIR_AUTOAVALIACAO = False`, e como
`JUIZES` — `gpt-5-mini` e `gemini-3.6-flash` — é subconjunto de `CANDIDATOS`,
ambos avaliam a si mesmos. Todo candidato recebe os mesmos dois juízes, o que
mantém o desenho balanceado.

Os julgamentos gravam o campo `autoavaliacao` (booleano), permitindo comparar
notas próprias e cruzadas na análise. **Para o experimento definitivo, mude para
`True`** ou use juízes disjuntos dos candidatos.

### Antes de trocar qualquer modelo

O catálogo do Copilot muda com frequência e **constar em `/models` não garante
que o modelo funcione**: alguns são listados mas recusados pelo endpoint de
chat, com `not accessible via the /chat/completions endpoint`. Valide os IDs
com uma chamada real antes de iniciar a campanha:

```bash
./adk/.venv/bin/python - <<'PY'
import sys; sys.path.insert(0, "benchmark"); sys.path.insert(0, "adk")
import litellm; litellm.suppress_debug_info = True
from config import CANDIDATOS, JUIZES, modelo_litellm
from shared.llm import copilot_completion_kwargs
for nome in [*CANDIDATOS, *JUIZES]:
    m = modelo_litellm(nome)
    try:
        litellm.completion(model=m, messages=[{"role": "user", "content": "ok"}],
                           timeout=90, **copilot_completion_kwargs(m))
        print(f"  [OK]    {nome}")
    except Exception as e:
        print(f"  [FALHA] {nome}: {str(e)[:110]}")
PY
```

A recusa tem duas causas distintas, e só uma é fatal:

| Mensagem | Causa | Saída |
| :--- | :--- | :--- |
| `not accessible via the /chat/completions endpoint` | O modelo só expõe `/responses` | Usável pela ponte (abaixo) |
| `The requested model is not supported` | O ID não existe no catálogo | Sem saída — confira o nome |

Para inspecionar quais endpoints um modelo aceita:

```bash
./adk/.venv/bin/python - <<'PY'
import json, pathlib, requests
api = json.loads((pathlib.Path.home() / ".config/litellm/github_copilot/api-key.json").read_text())["token"]
r = requests.get("https://api.githubcopilot.com/models",
                 headers={"Authorization": f"Bearer {api}", "Editor-Version": "vscode/1.99.0"}, timeout=20)
for m in sorted(r.json()["data"], key=lambda x: x["id"]):
    print(f"{m['id']:24s} {m.get('supported_endpoints')}")
PY
```

### Modelos que só aceitam `/responses`

A OpenAI vem migrando os modelos novos para a Responses API. No catálogo atual,
`gpt-5.5`, `gpt-5.4-mini` e toda a família `gpt-5.6-*` listam apenas
`/responses`, enquanto `gpt-5.4` e `gpt-5-mini` ainda aceitam os dois.

O litellm traduz chat completions para a Responses API quando o nome do modelo
recebe o prefixo `responses/` **depois** do provider:

```
github_copilot/responses/gpt-5.6-terra   ✓
responses/github_copilot/gpt-5.6-terra   ✗  LLM Provider NOT provided
```

Tool calling e saída JSON sobrevivem à ponte — ambos verificados. Como
candidato, o modelo entra assim no `.env`:

```dotenv
ADK_LLM_MODEL=github_copilot/responses/gpt-5.6-terra
```

Em `CANDIDATOS` vai o nome **sem** o prefixo: ali ele é apenas rótulo de pasta e
filtro de linha de comando. O prefixo só importa para quem de fato chama o
modelo.

---

## 3. Fase 1 — Executar e coletar

Esta fase é manual e se repete para cada combinação **modelo × execução**.

### a) Definir o modelo em `adk/.env`

```bash
ADK_LLM_MODEL=github_copilot/gpt-5-mini
ADK_LOG_PLUGIN=file
```

`ADK_LOG_PLUGIN=file` gera o `adk_debug.yaml`, de onde saem tokens e latência.
Sem ele, essas métricas ficam ausentes do resultado.

O plugin abre esse arquivo em modo *append*, então ele acumula execuções de dias
diferentes. O `metrics.py` recorta só a mais recente: agrupa os documentos YAML
por sobreposição temporal — uma execução gera vários, um por sub-agente
invocado via `AgentTool`, e os filhos rodam dentro do intervalo do pai. O campo
`n_invocacoes_ignoradas` no `meta.json` mostra quantos ficaram de fora. Não é
preciso apagar o log entre execuções.

### b) Subir o servidor

```bash
cd adk && .venv/bin/uvicorn app.main:app --reload --port 8081
```

### c) Executar no Dev UI

Abra `http://127.0.0.1:8081/dev-ui/?app=workflow_requirements` e cole o
enunciado do caso.

### d) Coletar — imediatamente após terminar

```bash
./adk/.venv/bin/python benchmark/collect.py \
    --modelo gpt-5-mini --caso T1-C01 --execucao 1
```

> ### A regra que quebra tudo se esquecida
>
> **Colete antes de disparar a próxima execução.** O `init_workspace()` faz
> `rmtree` no `workspace_output` inteiro no início de cada run. O que não foi
> copiado está perdido, sem aviso e sem recuperação.

### Convenções

**`--caso`** é um rótulo livre que vira nome de pasta. Como a unidade
experimental é *tarefa × caso*, codifique as duas dimensões: `T1-C01` =
Tarefa 1 (Extração de Requisitos), Caso 01. Se duas tarefas diferentes
receberem o mesmo rótulo, o `analyze.py` as trata como o mesmo bloco e
compara coisas incomparáveis.

**`--execucao`** é numerada **por (modelo, caso)** — reinicia em 1 a cada
modelo novo, porque o destino já separa por pasta:

```
runs/<modelo>/<caso>/exec-NN/
├── artifacts/     cópia integral do workspace_output
└── meta.json      contagens, tamanho, duração, métricas do ADK
```

O desenho é **pareado**: `exec-03` precisa existir em *todos* os candidatos
para o bloco entrar na análise. Blocos incompletos são descartados.

### O que reinicia e o que não

| Local | Quando é apagado |
| :--- | :--- |
| `adk/workspace_output/` | A cada run, automaticamente |
| `benchmark/runs/` | Nunca — `collect.py` se recusa a sobrescrever |
| `benchmark/judgments/` | Nunca — `judge.py` pula os já gravados |
| `benchmark/results/` | Sobrescrito a cada `analyze.py` |

Trocar de modelo **exige reiniciar o uvicorn**: o `.env` é lido só no boot, e o
`--reload` observa arquivos `.py`, não o `.env`. Editar o `.env` com o servidor
no ar faz a run seguinte usar silenciosamente o modelo antigo.

---

## 4. Fase 2 — Julgar

Sempre comece pelo ensaio, que não gasta nenhuma chamada de LLM:

```bash
./adk/.venv/bin/python benchmark/judge.py --dry-run
```

Depois:

```bash
./adk/.venv/bin/python benchmark/judge.py
```

Filtros opcionais: `--modelo`, `--caso`.

O script é **idempotente** — julgamentos já gravados são pulados, então pode
reexecutar à vontade depois de uma queda no meio da campanha.

Cada resposta é avaliada por todos os modelos de `JUIZES` — descontando a
autoavaliação apenas se `EXCLUIR_AUTOAVALIACAO` estiver ligado. Na configuração
atual são 2 julgamentos por execução, para todos os candidatos.

### Cegamento

Antes do envio, nomes de fornecedores e modelos são substituídos por `[MODELO]`,
junto com o sufixo de versão: `Gemini 3.8 Flash` vira `[MODELO]` por inteiro, não
`[MODELO] 3.8 Flash`. Termos legítimos de requisitos são preservados — "flash da
câmera" e "login com Google" não são tocados.

O campo `marcas_removidas` registra quantas substituições ocorreram; um número
alto e inesperado merece inspeção do artefato.

> **O cegamento tem limite.** Ele remove menções explícitas, mas não impede que
> um modelo reconheça o próprio estilo de escrita. Em autoavaliação, o viés de
> auto-preferência continua possível e deve constar como ameaça à validade.

---

## 5. Fase 3 — Analisar

```bash
./adk/.venv/bin/python benchmark/analyze.py
```

Imprime as tabelas no terminal e grava em `results/`:

| Arquivo | Conteúdo |
| :--- | :--- |
| `consolidado.csv` | Uma linha por julgamento — a base de tudo |
| `descritivas.csv` | n, média, mediana, desvio, IC 95%, coef. de variação |
| `por_criterio.csv` | Nota média de cada modelo em cada critério |
| `pareado.csv` | Wilcoxon + Cliff's Delta par a par |
| `nemenyi.csv` | Post-hoc, **só se** o Friedman der `p < 0.05` |

### Testes aplicados

- **Friedman** (k ≥ 3 candidatos) ou **Wilcoxon** (k = 2), ambos não paramétricos
  e pareados por bloco `(caso, execucao)`.
- **Kendall's W** para concordância global.
- **Nemenyi** como post-hoc, para identificar quais pares diferem.
- **Cliff's Delta** como tamanho de efeito (limiares 0.147 / 0.33 / 0.474).

> Com poucos blocos o script avisa `blocos insuficientes para inferência`.
> Isso não é erro: é o teste se recusando a produzir um p-valor sem base.
> O protocolo pede **5 a 10 execuções** por tarefa.

---

## 6. Receita mínima de validação

Antes de investir numa campanha longa, rode **uma execução de cada candidato no
mesmo caso**. Isso exercita o caminho pareado de ponta a ponta e revela
problemas agora, em vez de no meio do experimento:

```bash
# para cada modelo: ajustar .env → reiniciar uvicorn → rodar no Dev UI → coletar
./adk/.venv/bin/python benchmark/collect.py --modelo <M> --caso T1-C01 --execucao 1

./adk/.venv/bin/python benchmark/judge.py
./adk/.venv/bin/python benchmark/analyze.py
```

> **`runs/`, `judgments/` e `results/` não são versionados.** O repositório
> guarda apenas o harness; os dados de cada campanha ficam locais. Se precisar
> compartilhar evidências com o time, anexe-as ao PR ou publique um pacote à
> parte — e lembre que apagar essas pastas é irreversível, porque não há cópia
> no git.

---

## 7. Limitações conhecidas

Estas não são bugs — são propriedades do desenho que precisam constar no
relatório final.

**O formato de saída do juiz é pedido em prosa.** O prompt instrui "responda
exclusivamente com JSON", mas nada obriga o modelo. Modelos que ignoram a
instrução e escrevem Markdown falham após 3 tentativas e a célula fica vazia
na matriz — e blocos incompletos são descartados silenciosamente pela análise.
Já aconteceu com um dos modelos testados. A solução robusta é *tool calling*
forçado, ainda não implementada. **Confira o número de julgamentos gravados
contra o esperado** ao fim de cada rodada.

**O agente precisa decidir chamar a tool.** O `workflow_requirements` é um
`LlmAgent`, então o candidato primeiro decide invocar o `requirements_agent`.
Um modelo que responde texto e não emite o `function_call` produz zero
artefatos, e o `collect.py` aborta com *"nenhum artefato .md"*. Isso é **falha
operacional, não qualidade baixa** — registre à parte e não pontue.

**Modelos da mesma família se favorecem.** Se dois candidatos forem da mesma
linhagem, eles se avaliam mutuamente e a auto-preferência vira viés sistemático.
Registre como ameaça à validade.

**O juiz continua sendo um LLM.** Como reconhece o próprio protocolo de
avaliação, o LLM-as-a-Judge não elimina subjetividade;
apenas a torna escalável e reprodutível.

---

## 8. Problemas comuns

| Sintoma | Causa |
| :--- | :--- |
| `invalid choice` no `--modelo` | O modelo não está em `CANDIDATOS` |
| `nenhum artefato .md em workspace_output` | A run falhou, ou uma run posterior já limpou o workspace |
| `<destino> já existe` | Número de execução repetido — o script protege dados existentes |
| `não devolveu JSON válido em 3 tentativas` | Aderência de formato; ver Limitações |
| `faltam dependências estatísticas` | Rode o `uv pip install` da seção 1 |
| `nenhuma execução encontrada` | `runs/` vazio — colete antes de julgar |
| Resultado com o modelo errado | O uvicorn não foi reiniciado após editar o `.env` |

Antes de qualquer rodada, uma checagem barata que pega erros de digitação:

```bash
./adk/.venv/bin/python -m compileall -q benchmark/
./adk/.venv/bin/python benchmark/judge.py --dry-run
```
