"""Ingestão do SWE-bench Verified e sorteio determinístico das instâncias.

Fonte: o parquet `data/test-00000-of-00001.parquet` do dataset
`SWE-bench/SWE-bench_Verified` no Hugging Face (500 instâncias revisadas por
humanos). A REVISÃO do dataset é fixada (`DEFAULT_REVISION`): o schema desse
dataset já mudou ao longo do tempo (colunas `image`, `eval_script`,
`difficulty`), e uma linha de base só é reproduzível contra os mesmos dados.

O download usa `huggingface_hub` + `pyarrow`, que já fazem parte do ambiente do
`adk/` — sem adicionar o pacote `datasets`. O arquivo fica em cache em
`datasets/<revisão>/` (fora do git) e é o MESMO parquet entregue ao harness
oficial na correção, para que execução e gabarito usem exatamente os mesmos
dados.

Separação de campos: `SWEInstance` carrega também o gabarito (`patch`,
`test_patch`, `FAIL_TO_PASS`, `PASS_TO_PASS`, `eval_script`) e o `hints_text`,
porque a extração do patch precisa saber quais caminhos o `test_patch` toca e a
sanidade do ambiente do executor usa o patch e o comando de teste oficiais.
NENHUM desses campos pode chegar ao coder ou ao validador — ver `contract.py` e
o teste de vazamento em `test_contract.py`.
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

DATASET_REPO_ID = "SWE-bench/SWE-bench_Verified"
DATASET_FILENAME = "data/test-00000-of-00001.parquet"
# Revisão fixada em 2026-09-28 (última modificação do dataset: 2026-08-16).
DEFAULT_REVISION = "78f471bf655a3137b2e8a75af1501690ec009ec3"

DEFAULT_LIMIT = 30
DEFAULT_SEED = 42

# Formato das imagens oficiais, usado só quando a linha não traz a coluna `image`.
_IMAGE_TEMPLATE = "swebench/sweb.eval.x86_64.{slug}:latest"
_DIFF_HEADER_RE = re.compile(r"^diff --git a/(\S+) b/(\S+)$", re.MULTILINE)


@dataclass(frozen=True)
class SWEInstance:
    """Uma instância do SWE-bench Verified.

    Os campos do bloco "gabarito" existem apenas para a extração do patch e para
    o registro; nunca entram em contrato, mensagem ou workspace do coder.
    """

    instance_id: str
    repo: str
    base_commit: str
    version: str
    problem_statement: str
    image: str
    difficulty: str = ""
    created_at: str = ""
    # --- gabarito (nunca exposto ao loop) ---
    patch: str = field(default="", repr=False)
    test_patch: str = field(default="", repr=False)
    fail_to_pass: tuple[str, ...] = field(default=(), repr=False)
    pass_to_pass: tuple[str, ...] = field(default=(), repr=False)
    hints_text: str = field(default="", repr=False)
    # Script oficial de avaliação: traz o comando dos testes do gabarito. Usado
    # só pela sanidade do ambiente do executor (`executor_sanity.py`).
    eval_script: str = field(default="", repr=False)

    @property
    def test_patch_paths(self) -> tuple[str, ...]:
        """Caminhos que o `test_patch` cria, altera ou remove."""
        return paths_touched_by_diff(self.test_patch)


def paths_touched_by_diff(diff: str) -> tuple[str, ...]:
    """Extrai, dos cabeçalhos `diff --git a/X b/Y`, os caminhos envolvidos."""
    caminhos: set[str] = set()
    for origem, destino in _DIFF_HEADER_RE.findall(diff or ""):
        caminhos.add(origem)
        caminhos.add(destino)
    return tuple(sorted(caminhos))


def image_for(instance_id: str, image: str | None = None) -> str:
    """Imagem Docker oficial da instância (coluna `image` quando disponível)."""
    if image:
        return image
    slug = instance_id.replace("__", "_1776_").lower()
    return _IMAGE_TEMPLATE.format(slug=slug)


def _as_str_tuple(valor: Any) -> tuple[str, ...]:
    """Normaliza `FAIL_TO_PASS`/`PASS_TO_PASS`: lista ou string JSON (schema antigo)."""
    if valor is None:
        return ()
    if isinstance(valor, str):
        valor = json.loads(valor) if valor.strip() else []
    return tuple(str(item) for item in valor)


def instance_from_row(row: dict[str, Any]) -> SWEInstance:
    """Converte uma linha do parquet em `SWEInstance`."""
    instance_id = str(row["instance_id"])
    return SWEInstance(
        instance_id=instance_id,
        repo=str(row["repo"]),
        base_commit=str(row["base_commit"]),
        version=str(row.get("version") or ""),
        problem_statement=str(row["problem_statement"]),
        image=image_for(instance_id, row.get("image")),
        difficulty=str(row.get("difficulty") or ""),
        created_at=str(row.get("created_at") or ""),
        patch=str(row.get("patch") or ""),
        test_patch=str(row.get("test_patch") or ""),
        fail_to_pass=_as_str_tuple(row.get("FAIL_TO_PASS")),
        pass_to_pass=_as_str_tuple(row.get("PASS_TO_PASS")),
        hints_text=str(row.get("hints_text") or ""),
        eval_script=str(row.get("eval_script") or ""),
    )


def ensure_dataset(cache_dir: Path, *, revision: str = DEFAULT_REVISION) -> Path:
    """Garante o parquet local da revisão pedida, baixando-o se preciso."""
    destino = cache_dir / revision
    local = destino / DATASET_FILENAME
    if local.is_file() and local.stat().st_size > 0:
        return local

    from huggingface_hub import hf_hub_download

    print(f"[dataset] Baixando {DATASET_REPO_ID}@{revision[:8]} …")
    caminho = hf_hub_download(
        repo_id=DATASET_REPO_ID,
        filename=DATASET_FILENAME,
        repo_type="dataset",
        revision=revision,
        local_dir=destino,
    )
    return Path(caminho)


def load_instances(parquet_path: Path) -> list[SWEInstance]:
    """Carrega todas as instâncias do parquet, ordenadas por `instance_id`."""
    import pyarrow.parquet as pq

    linhas = pq.read_table(parquet_path).to_pylist()
    return sorted(
        (instance_from_row(linha) for linha in linhas), key=lambda i: i.instance_id
    )


def select_instances(
    instances: Iterable[SWEInstance],
    *,
    limit: int | None = DEFAULT_LIMIT,
    seed: int = DEFAULT_SEED,
    instance_ids: list[str] | None = None,
) -> list[SWEInstance]:
    """Seleciona o subconjunto do run, de forma reproduzível.

    - Com `instance_ids`: usa exatamente essas instâncias (erro se faltar
      alguma); `limit`, se dado, trunca a lista.
    - Sem `instance_ids`: sorteio simples de `limit` instâncias com
      `random.Random(seed)`, sobre a lista ORDENADA por id — a ordem do arquivo
      não influencia o resultado. `limit=None` seleciona todas.

    O retorno é sempre ordenado por `instance_id` (ordem de execução estável).
    """
    ordenadas = sorted(instances, key=lambda i: i.instance_id)

    if instance_ids:
        por_id = {i.instance_id: i for i in ordenadas}
        faltando = [iid for iid in instance_ids if iid not in por_id]
        if faltando:
            raise ValueError(
                "instance_id(s) inexistente(s) no dataset: " + ", ".join(faltando)
            )
        escolhidas = sorted(
            {por_id[iid] for iid in instance_ids}, key=lambda i: i.instance_id
        )
        return escolhidas[:limit] if limit is not None else escolhidas

    if limit is None or limit >= len(ordenadas):
        return ordenadas
    if limit < 1:
        raise ValueError("--limit deve ser >= 1.")
    sorteadas = random.Random(seed).sample(ordenadas, limit)
    return sorted(sorteadas, key=lambda i: i.instance_id)


def distribution_by_repo(instances: Iterable[SWEInstance]) -> dict[str, int]:
    """Quantidade de instâncias por repositório (maior para menor)."""
    contagem = Counter(i.repo for i in instances)
    return dict(sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0])))
