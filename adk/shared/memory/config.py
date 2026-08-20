"""Factory de configuração do mem0 (OSS) — PoC de memória entre execuções.

Usa `AsyncMemory` (não `MemoryClient`): roda 100% localmente, sem depender do
serviço hospedado da Mem0 Platform (`MEM0_API_KEY`). LLM e embedder apontam
para Gemini via `GOOGLE_API_KEY` — mesma env var que `.env.example` já
documenta para "modelos Gemini nativos", nenhuma chave nova precisa ser
provisionada.

## Interruptor geral: `AI4ES_MEMORY_ENABLED`

A feature inteira é desligada por padrão — precisa de `AI4ES_MEMORY_ENABLED=true`
explícito pra ligar. Nenhum time (nem o nosso) deve ter esse mecanismo
rodando por padrão; quem quiser usar, liga de propósito. Com a flag
desligada, `memory_feedforward` (leitura) e `reviewer` (escrita) nem chamam
`get_memory()` — zero atividade, nenhum banco é sequer inicializado. Ver
`memoria_habilitada()` abaixo.

## Vector store: Postgres/pgvector quando configurado, Chroma local se não

Postgres só é considerado quando `AI4ES_MEMORY_USE_POSTGRES=true` — sem essa
flag (ausente, vazia, ou qualquer valor diferente de "true"), a feature
ignora totalmente Postgres e cai para Chroma em arquivo local
(`memory_store/chroma/`), mesmo que `AI4ES_MEMORY_DATABASE_URL` esteja
preenchida. Nenhuma equipe deve precisar rodar um banco de dados (Postgres
ou qualquer outro) só para executar o fluxo dos agentes — a flag garante
que isso nunca acontece por acidente (ex.: URL deixada preenchida num
`.env` copiado de outra máquina). Com a flag `true`,
a memória vive em Postgres — banco não-local, sobrevive a redeploys,
compartilhável entre instâncias. `mem0` cria a extensão `vector` sozinho
(`CREATE EXTENSION IF NOT EXISTS vector`) — só precisa estar disponível no
servidor Postgres de destino (ex.: imagem `pgvector/pgvector`).

Deliberadamente SEM fallback para outro Postgres já configurado no projeto:
mesmo que a URL resolvesse, aquele banco provavelmente não teria a extensão
`pgvector` disponível (imagem comum, não `pgvector/pgvector`) — o
`CREATE EXTENSION` falharia. E mesmo que tivesse, compartilhar a mesma
instância entre features diferentes acopla as duas sem necessidade (mudança
de credencial/capacidade feita por um lado afeta o outro sem aviso). Cada
feature com seu próprio banco, cada uma com seu ciclo de vida.

O caminho local, quando usado, fica fora de `WORKSPACE_OUTPUT_DIR` porque
`init_workspace()` apaga esse diretório a cada prompt novo (ver
`shared/workspace.py`); a memória precisa sobreviver a isso independente do
backend.

Nota sobre Chroma em vez de Qdrant (o default do mem0 e já dependência do
projeto) no caminho local: o provider Qdrant do mem0 (v3, busca híbrida BM25)
carrega `fastembed`, que usa ONNX Runtime nativo — e esse runtime SEGFAULTA
(`SIGSEGV`) neste ambiente Python 3.14, isolado e reproduzido chamando só o
`fastembed` sozinho, fora do mem0. Chroma não usa fastembed/ONNX.
"""

from __future__ import annotations

import os
from pathlib import Path

# Precisa rodar ANTES do `from mem0 import ...` — a env var é lida uma única
# vez, no import do módulo de telemetria do mem0. Desabilitado por padrão
# neste PoC: o conteúdo que passa por aqui é código gerado de um projeto
# universitário, sem necessidade de sair enviando eventos para o PostHog da
# Mem0 por padrão.
os.environ.setdefault("MEM0_TELEMETRY", "False")

from mem0 import AsyncMemory  # noqa: E402  (import após o setdefault acima, de propósito)

_LLM_MODEL = "gemini-2.5-flash"
_EMBEDDER_MODEL = "gemini-embedding-001"
# mem0's GeminiLLM embedder faz fallback pra 768 quando embedding_dims não é
# especificado (mem0/embeddings/gemini.py). O pgvector precisa dessa dimensão
# declarada na criação da tabela — sem isso o default do provider é 1536
# (dimensão da OpenAI) e a escrita quebra por incompatibilidade de shape.
_EMBEDDING_DIMS = 768

_memory: AsyncMemory | None = None


def memoria_habilitada() -> bool:
    """Interruptor geral da feature — precisa estar "true", literalmente.

    Falsa por padrão: `memory_feedforward` (leitura) e `reviewer` (escrita)
    checam isso antes de qualquer chamada a `get_memory()`. Pública, de
    propósito — chamada de fora deste módulo. Ver docstring do módulo.
    """
    return os.environ.get("AI4ES_MEMORY_ENABLED", "").strip().lower() == "true"


def _usar_postgres() -> bool:
    """Gate explícito pro uso de Postgres — precisa estar "true", literalmente.

    Separado de `_database_url()` de propósito: uma URL preenchida sozinha
    NÃO basta pra usar Postgres (ex.: `.env` copiado de outra máquina/pessoa
    com a URL ainda lá) — precisa da flag explícita também. Ver docstring do
    módulo.
    """
    return os.environ.get("AI4ES_MEMORY_USE_POSTGRES", "").strip().lower() == "true"


def _database_url() -> str | None:
    """URL de conexão Postgres pro mem0 — exclusiva desta feature.

    Só lê `AI4ES_MEMORY_DATABASE_URL`, de propósito: sem fallback para outro
    Postgres do projeto (ver docstring do módulo). Ignorada por completo se
    `_usar_postgres()` for False.
    """
    if not _usar_postgres():
        return None
    return os.environ.get("AI4ES_MEMORY_DATABASE_URL") or None


def _dir_memory_store() -> Path:
    """Raiz do armazenamento local do mem0 — fora do workspace_output/.

    Mesmo idioma de `cr_feedforward.py::_dir_knowledge()` (override por env
    var + resolução relativa ao próprio arquivo para chegar em `adk/`).
    """
    override = os.environ.get("AI4ES_MEMORY_DIR")
    if override:
        return Path(override)
    # .../adk/shared/memory/config.py → parents[2] == adk/
    return Path(__file__).resolve().parents[2] / "memory_store"


def _vector_store_config() -> dict:
    """`pgvector` quando há URL de banco configurada; `chroma` local senão."""
    database_url = _database_url()
    if database_url:
        return {
            "provider": "pgvector",
            "config": {
                "collection_name": "ai4es_mem0_poc",
                "connection_string": database_url,
                "embedding_model_dims": _EMBEDDING_DIMS,
            },
        }
    raiz = _dir_memory_store()
    raiz.mkdir(parents=True, exist_ok=True)
    return {
        "provider": "chroma",
        "config": {
            "collection_name": "ai4es_mem0_poc",
            "path": str(raiz / "chroma"),
        },
    }


def get_memory() -> AsyncMemory:
    """Devolve a instância (singleton de módulo) do `AsyncMemory` do PoC.

    Criada sob demanda na primeira chamada — evita custo de inicialização
    (cliente Gemini, conexão com o vector store) em processos que nunca
    exercitam o caminho de memória (ex.: testes de outras partes do sistema).
    """
    global _memory
    if _memory is None:
        _memory = AsyncMemory.from_config(
            {
                "llm": {
                    "provider": "gemini",
                    "config": {"model": _LLM_MODEL, "temperature": 0.1},
                },
                "embedder": {
                    "provider": "gemini",
                    "config": {"model": _EMBEDDER_MODEL},
                },
                "vector_store": _vector_store_config(),
            }
        )
    return _memory
