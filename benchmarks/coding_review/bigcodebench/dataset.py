"""Ingestão do dataset BigCodeBench (split `complete`).

O BigCodeBench (`bigcode/bigcodebench`, arXiv:2406.15877) traz 1.140 tarefas que
compõem chamadas a bibliotecas de terceiros. No Hugging Face as *versões* do
dataset são os splits (``v0.1.4`` etc.); "complete" vs "instruct" é a escolha do
prompt: aqui usamos SEMPRE ``complete_prompt`` (assinatura + docstring completa).

Campos usados de cada linha:

- ``task_id``: identificador (ex.: ``"BigCodeBench/0"``).
- ``complete_prompt``: imports + ``def task_func(...)`` + docstring (o enunciado).
- ``entry_point``: sempre ``"task_func"``.
- ``test``: código com a classe ``unittest.TestCase`` oficial (``TestCases``).
- ``libs``: bibliotecas esperadas (string com a repr de uma lista).
- ``canonical_solution``: corpo da solução de referência (só para validar o ambiente).

O parquet do split é baixado do espelho de conversão do próprio Hugging Face e
lido com `pyarrow` (já listado em `adk/requirements.txt`).
"""

from __future__ import annotations

import ast
import random
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# Versão (split) do dataset fixada para reprodutibilidade.
DEFAULT_HF_VERSION = "v0.1.4"
DEFAULT_DATASET_URL = (
    "https://huggingface.co/datasets/bigcode/bigcodebench/resolve/"
    f"refs%2Fconvert%2Fparquet/default/{DEFAULT_HF_VERSION}/0000.parquet"
)
# Seed fixa da amostragem aleatória (mesmas tarefas em runs diferentes).
DEFAULT_SEED = 42


@dataclass(frozen=True)
class BigCodeBenchProblem:
    """Uma tarefa do BigCodeBench (split complete)."""

    task_id: str
    prompt: str  # complete_prompt
    entry_point: str
    test: str
    libs: tuple[str, ...] = ()
    canonical_solution: str = ""

    @property
    def slug(self) -> str:
        """Identificador seguro para nomes de arquivo (ex.: ``BigCodeBench_0``)."""
        return self.task_id.replace("/", "_")


def _task_number(task_id: str) -> int:
    """Número da tarefa (``BigCodeBench/12`` → 12), para ordenação estável."""
    try:
        return int(task_id.rsplit("/", 1)[-1])
    except ValueError:
        return 0


def _parse_libs(raw: object) -> tuple[str, ...]:
    """Converte o campo ``libs`` (string com repr de lista) em tupla de nomes."""
    if isinstance(raw, (list, tuple)):
        return tuple(str(x) for x in raw)
    if not raw:
        return ()
    try:
        valor = ast.literal_eval(str(raw))
    except (ValueError, SyntaxError):
        return ()
    return tuple(str(x) for x in valor) if isinstance(valor, (list, tuple)) else ()


def ensure_dataset(dest_path: Path, *, url: str = DEFAULT_DATASET_URL) -> Path:
    """Garante o parquet local, baixando-o se ainda não existir."""
    if dest_path.is_file() and dest_path.stat().st_size > 0:
        return dest_path

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[dataset] Baixando BigCodeBench de {url} …")
    with urllib.request.urlopen(url) as resp:
        dados = resp.read()
    dest_path.write_bytes(dados)
    print(f"[dataset] Salvo em {dest_path} ({len(dados)} bytes).")
    return dest_path


def read_all_problems(dataset_path: Path) -> list[BigCodeBenchProblem]:
    """Lê TODAS as tarefas do parquet, ordenadas pelo número da tarefa."""
    import pyarrow.parquet as pq  # import tardio: só necessário ao ler o dataset

    linhas = pq.read_table(dataset_path).to_pylist()
    problemas = [
        BigCodeBenchProblem(
            task_id=raw["task_id"],
            prompt=raw["complete_prompt"],
            entry_point=raw["entry_point"],
            test=raw["test"],
            libs=_parse_libs(raw.get("libs")),
            canonical_solution=raw.get("canonical_solution", "") or "",
        )
        for raw in linhas
    ]
    return sorted(problemas, key=lambda p: _task_number(p.task_id))


def load_problems(
    dataset_path: Path,
    *,
    url: str = DEFAULT_DATASET_URL,
    limit: int | None = None,
    seed: int = DEFAULT_SEED,
    task_ids: list[str] | None = None,
) -> list[BigCodeBenchProblem]:
    """Carrega tarefas do BigCodeBench (baixa o dataset se preciso).

    Args:
        dataset_path: caminho local do parquet.
        url: origem do download (quando ausente localmente).
        limit: se informado, sorteia no máximo `limit` tarefas com `seed` fixa
            (amostra determinística; o resultado vem ordenado pelo nº da tarefa).
        seed: seed da amostragem aleatória.
        task_ids: se informado, filtra apenas estes `task_id` (aceita
            ``"BigCodeBench/0"`` e o slug ``"BigCodeBench_0"``) e ignora o sorteio.

    Returns:
        Lista de `BigCodeBenchProblem` ordenada pelo número da tarefa.
    """
    ensure_dataset(dataset_path, url=url)
    problemas = read_all_problems(dataset_path)

    if task_ids:
        alvo = set(task_ids)
        return [p for p in problemas if p.task_id in alvo or p.slug in alvo]

    if limit is not None and limit < len(problemas):
        amostra = random.Random(seed).sample(problemas, limit)
        problemas = sorted(amostra, key=lambda p: _task_number(p.task_id))

    return problemas
