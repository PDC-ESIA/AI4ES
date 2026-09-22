"""Ingestão do dataset HumanEval (download dinâmico + parsing).

O dataset oficial é um JSONL comprimido (`HumanEval.jsonl.gz`) publicado no
repositório da OpenAI. Cada linha é um problema com os campos:

- ``task_id``: identificador (ex.: ``"HumanEval/0"``).
- ``prompt``: assinatura da função + docstring (o enunciado).
- ``entry_point``: nome da função a implementar (ex.: ``"has_close_elements"``).
- ``canonical_solution``: solução de referência (não usada na avaliação).
- ``test``: código Python que define ``check(candidate)`` — o teste canônico.

Somente a biblioteca padrão é usada (urllib/gzip/json), evitando dependências
extras no ambiente do benchmark.
"""

from __future__ import annotations

import gzip
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# Fonte oficial do dataset (raw do repositório openai/human-eval).
DEFAULT_DATASET_URL = (
    "https://github.com/openai/human-eval/raw/master/data/HumanEval.jsonl.gz"
)


@dataclass(frozen=True)
class HumanEvalProblem:
    """Um problema do HumanEval, com os campos relevantes ao benchmark."""

    task_id: str
    prompt: str
    entry_point: str
    test: str
    canonical_solution: str = ""

    @property
    def slug(self) -> str:
        """Identificador seguro para nomes de arquivo (ex.: ``HumanEval_0``)."""
        return self.task_id.replace("/", "_")


def ensure_dataset(dest_path: Path, *, url: str = DEFAULT_DATASET_URL) -> Path:
    """Garante o `.jsonl.gz` local, baixando-o se ainda não existir.

    Args:
        dest_path: caminho local do arquivo comprimido.
        url: origem do download.

    Returns:
        O próprio `dest_path` (já existente em disco).
    """
    if dest_path.is_file() and dest_path.stat().st_size > 0:
        return dest_path

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[dataset] Baixando HumanEval de {url} …")
    with urllib.request.urlopen(url) as resp:  # noqa: S310 — URL oficial fixa
        dados = resp.read()
    dest_path.write_bytes(dados)
    print(f"[dataset] Salvo em {dest_path} ({len(dados)} bytes).")
    return dest_path


def load_problems(
    dataset_path: Path,
    *,
    url: str = DEFAULT_DATASET_URL,
    limit: int | None = None,
    task_ids: list[str] | None = None,
) -> list[HumanEvalProblem]:
    """Carrega os problemas do HumanEval a partir do `.jsonl.gz` (baixa se preciso).

    Args:
        dataset_path: caminho local do dataset comprimido.
        url: origem do download (quando ausente localmente).
        limit: se informado, retorna no máximo os `limit` primeiros problemas.
        task_ids: se informado, filtra apenas os `task_id` desta lista
            (aceita tanto ``"HumanEval/0"`` quanto o slug ``"HumanEval_0"``).

    Returns:
        Lista de `HumanEvalProblem` na ordem do dataset.
    """
    ensure_dataset(dataset_path, url=url)

    problemas: list[HumanEvalProblem] = []
    with gzip.open(dataset_path, "rt", encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha:
                continue
            raw = json.loads(linha)
            problemas.append(
                HumanEvalProblem(
                    task_id=raw["task_id"],
                    prompt=raw["prompt"],
                    entry_point=raw["entry_point"],
                    test=raw["test"],
                    canonical_solution=raw.get("canonical_solution", ""),
                )
            )

    if task_ids:
        alvo = set(task_ids)
        problemas = [
            p for p in problemas if p.task_id in alvo or p.slug in alvo
        ]

    if limit is not None:
        problemas = problemas[:limit]

    return problemas
