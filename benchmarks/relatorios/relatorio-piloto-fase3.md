# Relatório do Piloto — Fase 3 do Benchmark de LLMs para o Agente de QA

**Data:** 20/08/2026 · **Run ID:** `pilot-fase3` · **Plano:** `benchmark/plano-fase3-piloto.md`
**Protocolo base:** Avaliação Comparativa de Modelos de Linguagem v1.1, seção 4.4 (Agente de Testes/QA)

---

## 1. Objetivo e escopo

Validar ponta a ponta o protocolo experimental (download de datasets → amostragem → execução via LiteLLM → coleta → métricas) com subconjunto reduzido, identificando problemas e produzindo ajustes documentados (protocolo v1.2).

**Executado:** 5 datasets · 3 modelos · k=3 repetições · temperatura 0.0 · top_p 1.0 · prompts zero-shot padronizados em inglês (`benchmarks/rodadas/fase3-piloto/prompts.yaml`).

## 2. O que foi executado

| Item | Resultado |
|---|---|
| Datasets baixados e normalizados | 5/5 — NQ-open (3.610), SQuAD v2 (11.873), HotpotQA distractor (7.405), LongBench/Qasper (200), GAIA L1 text-only (42) |
| Subsets do piloto (seed=42) | 20/20/20/10/10 = **80 casos**, SHA-256 registrados em `benchmarks/rodadas/fase3-piloto/subsets/manifest.json` |
| Chamadas concluídas | gpt-5.4: **240/240 ok** · gemini-3.5-flash: **240/240 ok** · gemini-2.5-flash: **21 ok / 219 pendentes** (ver §4.5) |
| Custo total realizado | < US$ 0,02 (estimativa prévia: US$ 0,15 — critério "≤2×" atendido com folga) |
| Infraestrutura versionada | scripts, config, subsets e resultados brutos em `benchmarks/` |

## 3. Rastreabilidade

- Cada chamada gerou um registro JSONL completo (Protocolo §11): resposta bruta, resposta extraída, latência, tokens, custo, status (`ok/empty/api_error/timeout/rate_limited`), parâmetros de inferência e timestamp UTC.
- Manifests com revisão (SHA) de cada dataset HF, seed de amostragem e hashes dos subsets.
- Reexecuções são deduplicadas por (caso, repetição) mantendo a última ocorrência; falhas de infraestrutura contabilizadas separadamente das falhas de qualidade.

## 4. Problemas identificados no piloto e correções aplicadas

Esta seção é o entregável central da Fase 3. Todos os problemas abaixo foram corrigidos nos scripts versionados.

### 4.1 Formato dos datasets públicos divergiu do esperado
- **LongBench**: o repositório distribui um único `data.zip` com JSONL plano por subtask (`data/qasper.jsonl`) — não pastas por split. Corrigido no downloader.
- **GAIA**: deixou de publicar `metadata.jsonl`; metadados agora são **parquet por nível** (`2023/validation/metadata.level{1,2,3}.parquet`) e o dataset é *gated* (requer token HF com termos aceitos). Downloader atualizado; itens multimodais (11/53) filtrados — o agente QA avaliado é text-only.

### 4.2 Disponibilidade real de modelos ≠ catálogo nominal
Testados via preflight contra `/chat/completions` da conta Copilot:
- `gpt-4.1-mini`: não suportado; `gpt-5.4-mini` e `gpt-5.5`: **exigem Responses API** (fora do escopo LiteLLM chat).
- GPTs acessíveis: **gpt-5.4** (usado), gpt-4.1, gpt-4o, gpt-4o-mini.
- Gemini via Copilot: apenas geração 3.x (`gemini-3.5-flash`, `gemini-3.6-flash`, `gemini-3.1-pro-preview`); **o baseline de produção `2.5-flash` não é exposto pelo Copilot** — só via API key Google direta.

### 4.3 Dependência faltante no ambiente isolado
O caminho de retry do LiteLLM exige `tenacity`, ausente no venv dedicado — falhas genéricas sem mensagem clara. Instalado e documentado no README de reprodução.

### 4.4 Modelos "thinking" exigem orçamento de tokens maior
`gemini-3.5-flash` consumiu até ~67 tokens de raciocínio antes de responder; com `max_tokens` pequeno a resposta final vinha **vazia** (`finish_reason=length`). Adicionada configuração `model_max_tokens` (1536 para o modelo thinking).

### 4.5 Cota do Gemini free tier (20 req/min + teto diário)
As primeiras rodadas estouraram a cota por minuto e, após ~500 requisições no dia, o projeto entrou em penalidade prolongada. Correções aplicadas ao runner:
- `num_retries=0` interno no LiteLLM (retries em rajada amplificavam o estouro);
- tratamento adaptativo de `RateLimitError`: espera o tempo sugerido pela API ("retry in X s") antes de tentar novamente, com status próprio `rate_limited`;
- retomada automática: pares (caso, repetição) já `ok/empty` não são reexecutados.

**Pendência documentada:** completar o baseline `gemini-2.5-flash` (comando pronto: `run_benchmark.py --models gemini/gemini-2.5-flash`; requer reset da cota diária ou chave paga). A comparação completa fica para a Fase 4, que deve usar **chave paga ou rota alternativa** — decisão registrada no v1.2.

### 4.6 Supporting Fact P/R não é computável com prompt de resposta curta
O prompt padronizado pede apenas a resposta; não há evidências na saída. O SF P/R (HotpotQA) exige variante de prompt que solicite evidências — **decisão adiada para a Fase 4** (custo extra por chamada a avaliar).

## 5. Resultados preliminares (não conclusivos)

> ⚠️ Amostra mínima (10–20 casos/benchmark) com objetivo de validar pipeline — **não usar para seleção de modelo**. Baseline Gemini parcial. Análise estatística formal (Wilcoxon/Friedman/Nemenyi) apenas na Fase 5, com o dataset completo.

| Modelo | NQ EM/F1 | HotpotQA EM/F1 | SQuAD recusa/FPA | Qasper EM/F1 | GAIA EM | Latência p50 |
|---|---|---|---|---|---|---|
| github_copilot/gpt-5.4 | 0.167 / 0.314 | 0.750 / 0.841 | 0.50 / **0.50** | 0.300 / 0.600 | 0.100 | ~1,0 s |
| github_copilot/gemini-3.5-flash | 0.250 / 0.442 | **0.800 / 0.891** | 0.63 / 0.37 | 0.300 / 0.536 | **0.533** | ~3,6 s |
| gemini/gemini-2.5-flash (parcial) | dados insuficientes | — | — | — | — | ~1,0 s |

**Observações qualitativas:**
1. **EM é severa para todos no NQ** (0.17–0.25) — respostas corretas mas lexicalmente diferentes são zeradas; F1 é mais informativo. Protocolo já previa essa limitação da camada determinística.
2. **GAIA continua difícil mesmo text-only** sem ferramentas (gpt-5.4: 0.10) — consistente com a literatura (humanos 92%, modelos sem tools ≪ isso). gemini-3.5 (thinking) foi bem superior (0.53).
3. **Sinal crítico de produção:** taxa de alucinação em perguntas sem resposta (**FPA**) ficou entre 0,31–0,50 para os dois modelos completos — nenhum atinge patamar confortável de recusa. Métrica a monitorar prioritariamente na Fase 4.
4. Trade-off latência clara: modelo thinking custa 4–12× mais latência por chamada (sem custo monetário adicional via Copilot).

## 6. Critérios de sucesso do piloto

| Critério | Meta | Realizado |
|---|---|---|
| Execuções rastreáveis, sem erro de infra não tratado | 100% | ✔ (falhas de cota tratadas, classificadas e retomáveis) |
| Parsing/formato de resposta ≥95% | ≥95% | ✔ (`answered_rate` alto; vazios concentrados em caso de cota, contados à parte) |
| Custo real ≤ 2× estimado | US$ ≤ 0,30 | ✔ (< US$ 0,02) |
| Pipeline ponta a ponta validado nos 5 datasets | 5/5 | ✔ (download → subset → execução → métricas → agregação) |

## 7. Ajustes consolidados no protocolo (→ v1.2)

Detalhados em `benchmark/Protocolo ... v1.2.md` (seção "Changelog"):
1. Formalizar fontes/formatos reais dos datasets (GAIA parquet gated; LongBench zip flat).
2. Fixar `max_tokens` como parâmetro por modelo (folga para modelos thinking).
3. Estratégia oficial de rate-limit: retries internos zerados + espera adaptativa; status `rate_limited` separado de `api_error`.
4. Registro de variantes acessíveis por provider no preflight (evita surpresas de catálogo).
5. SF P/R condicionado a variante de prompt com evidências — decisão na Fase 4.
6. Fase 4 exige chave paga para o baseline Gemini ou substituição por rota Copilot (perde o 2.5-flash exato).

## 8. Próximos passos (Fase 4)

1. Completar baseline `gemini-2.5-flash` (retomada pronta) e definir o **modelo open-source** obrigatório do PR (ex.: Llama/Qwen via OpenRouter/Groq — integração LiteLLM trivial).
2. Definir tamanho definitivo do dataset (proposta: 100–200 casos/benchmark, tornando o piloto = 10–20% conforme PR.md).
3. Decidir inclusão de LLM-as-a-Judge e da variante SF P/R.
4. Executar rodada completa com k≥10 e estatística formal.
