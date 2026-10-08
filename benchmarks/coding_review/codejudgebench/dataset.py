"""Ingestão do split CodeRepair do CodeJudgeBench (download dinâmico + amostragem).

Fonte: `mattymchen/codejudgebench` no Hugging Face (arXiv:2507.10535), config
`coderepair`. O config tem um split por modelo que GEROU as respostas:
`claude_3.7_sonnet` (878 pares), `gemini_2.5_flash` (654) e `gemini_2.5_pro` (877).

Cada linha é um par com os campos relevantes ao benchmark:

- ``question_content`` / ``starter_code``: enunciado do problema (AtCoder,
  LeetCode ou Codeforces) e, no LeetCode, a assinatura esperada.
- ``wrong_code`` / ``wrong_meta``: solução com bug e o erro observado ao
  executá-la (ex.: ``Wrong answer at output_line_idx=3: NO != YES``).
- ``pos_response``: tentativa de correção que PASSA nos testes ocultos.
- ``neg_response``: tentativa de correção que FALHA.

O download usa a API de linhas do Hugging Face (datasets-server) e somente a
biblioteca padrão, como no benchmark HumanEval. O resultado é cacheado em JSONL
junto de um `.meta.json` com a revisão do dataset, para que runs posteriores
sejam reproduzíveis a partir do cache.

Amostragem: o split tem vários pares por problema (207 problemas distintos em
878 pares no split claude_3.7_sonnet). Por padrão só um par por problema entra
na amostra, para que os pares avaliados sejam independentes entre si.
"""

from __future__ import annotations

import json
import random
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DATASET_ID = "mattymchen/codejudgebench"
CONFIG = "coderepair"
SPLITS = ("claude_3.7_sonnet", "gemini_2.5_flash", "gemini_2.5_pro")

# Split padrão: respostas geradas por um modelo de família diferente do modelo
# padrão do reviewer (gemini-2.5-flash), para reduzir viés de auto-preferência.
DEFAULT_SPLIT = "claude_3.7_sonnet"
DEFAULT_SEED = 42
DEFAULT_MAX_PER_QUESTION = 1

_ROWS_URL = "https://datasets-server.huggingface.co/rows"
_INFO_URL = f"https://huggingface.co/api/datasets/{DATASET_ID}"
_PAGE_SIZE = 100  # máximo aceito pela API de linhas
_HTTP_TIMEOUT_S = 60


@dataclass(frozen=True)
class RepairPair:
    """Um par do CodeRepair: o mesmo reparo tentado duas vezes, uma certa e uma errada."""

    pair_id: str
    split: str
    row_idx: int
    question_id: str
    question_title: str
    question_content: str
    platform: str
    difficulty: str
    starter_code: str
    wrong_code: str
    pos_response: str
    neg_response: str
    wrong_meta: dict = field(default_factory=dict)

    @property
    def slug(self) -> str:
        """Identificador seguro para nomes de arquivo (ex.: ``claude_3_7_sonnet_0042``)."""
        return f"{self.split.replace('.', '_')}_{self.row_idx:04d}"


def _validar_split(split: str) -> None:
    if split not in SPLITS:
        raise ValueError(f"Split '{split}' inválido. Opções: {', '.join(SPLITS)}.")


def _get_json(url: str) -> dict:
    """GET de um endpoint JSON (isolado para ser substituído nos testes)."""
    with urllib.request.urlopen(url, timeout=_HTTP_TIMEOUT_S) as resp:  # noqa: S310 — URLs fixas do HF
        return json.loads(resp.read().decode("utf-8"))


def _revisao_dataset() -> str | None:
    """SHA do commit atual do dataset no Hub; None se a consulta falhar."""
    try:
        return _get_json(_INFO_URL).get("sha")
    except Exception:  # noqa: BLE001 — metadado opcional, não bloqueia o download
        return None


def cache_path(cache_dir: Path, split: str) -> Path:
    """Caminho do JSONL cacheado de um split."""
    return cache_dir / f"{CONFIG}_{split}.jsonl"


def meta_path(cache_dir: Path, split: str) -> Path:
    """Caminho do `.meta.json` que acompanha o JSONL cacheado."""
    return cache_dir / f"{CONFIG}_{split}.meta.json"


def _baixar_linhas(split: str) -> list[dict]:
    """Baixa todas as linhas do split, página a página."""
    linhas: list[dict] = []
    total: int | None = None
    offset = 0
    while total is None or offset < total:
        params = urllib.parse.urlencode(
            {
                "dataset": DATASET_ID,
                "config": CONFIG,
                "split": split,
                "offset": offset,
                "length": _PAGE_SIZE,
            }
        )
        pagina = _get_json(f"{_ROWS_URL}?{params}")
        total = pagina["num_rows_total"]
        rows = pagina["rows"]
        if not rows:
            break
        truncadas = [r["row_idx"] for r in rows if r.get("truncated_cells")]
        if truncadas:
            # Uma resposta truncada seria julgada incompleta pelo reviewer e
            # contaminaria a medição — melhor falhar do que medir errado.
            raise RuntimeError(
                f"A API devolveu células truncadas nas linhas {truncadas[:5]} do "
                f"split '{split}'."
            )
        for r in rows:
            linhas.append({"row_idx": r["row_idx"], **r["row"]})
        offset += len(rows)

    if total is not None and len(linhas) != total:
        raise RuntimeError(
            f"Download incompleto do split '{split}': {len(linhas)} de {total} linhas."
        )
    return linhas


def ensure_dataset(cache_dir: Path, split: str = DEFAULT_SPLIT) -> Path:
    """Garante o JSONL local do split, baixando-o se ainda não existir.

    A escrita é atômica (arquivo temporário + rename): um download interrompido
    não deixa um cache parcial que pareça válido na próxima execução.

    Returns:
        O caminho do JSONL (já existente em disco).
    """
    _validar_split(split)
    destino = cache_path(cache_dir, split)
    if destino.is_file() and destino.stat().st_size > 0:
        return destino

    cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"[dataset] Baixando {DATASET_ID} ({CONFIG}/{split}) …")
    linhas = _baixar_linhas(split)

    temporario = destino.with_suffix(".jsonl.tmp")
    with temporario.open("w", encoding="utf-8") as fh:
        for linha in linhas:
            fh.write(json.dumps(linha, ensure_ascii=False) + "\n")
    temporario.replace(destino)

    meta_path(cache_dir, split).write_text(
        json.dumps(
            {
                "dataset": DATASET_ID,
                "config": CONFIG,
                "split": split,
                "revision": _revisao_dataset(),
                "num_rows": len(linhas),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[dataset] {len(linhas)} pares salvos em {destino}.")
    return destino


def dataset_metadata(cache_dir: Path, split: str) -> dict:
    """Metadados do cache (revisão, data do download); vazio se ausente."""
    caminho = meta_path(cache_dir, split)
    if not caminho.is_file():
        return {}
    return json.loads(caminho.read_text(encoding="utf-8"))


def _para_par(raw: dict, split: str) -> RepairPair:
    meta = raw.get("wrong_meta")
    return RepairPair(
        pair_id=f"{split}/{raw['row_idx']}",
        split=split,
        row_idx=int(raw["row_idx"]),
        question_id=str(raw["question_id"]),
        question_title=raw.get("question_title") or "",
        question_content=raw["question_content"],
        platform=raw.get("platform") or "",
        difficulty=raw.get("difficulty") or "",
        starter_code=raw.get("starter_code") or "",
        wrong_code=raw["wrong_code"],
        pos_response=raw["pos_response"],
        neg_response=raw["neg_response"],
        wrong_meta=meta if isinstance(meta, dict) else {},
    )


def load_all(cache_dir: Path, split: str = DEFAULT_SPLIT) -> list[RepairPair]:
    """Carrega todos os pares do split, na ordem do dataset (baixa se preciso)."""
    caminho = ensure_dataset(cache_dir, split)
    pares: list[RepairPair] = []
    with caminho.open("r", encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if linha:
                pares.append(_para_par(json.loads(linha), split))
    return pares


def select_pairs(
    pares: list[RepairPair],
    *,
    limit: int | None = None,
    seed: int = DEFAULT_SEED,
    max_per_question: int | None = DEFAULT_MAX_PER_QUESTION,
    pair_ids: list[str] | None = None,
) -> list[RepairPair]:
    """Seleciona a amostra de pares a avaliar.

    O embaralhamento é feito sobre o split INTEIRO com a seed e só então a lista
    é cortada. Isso torna a seleção estável por prefixo: com a mesma seed, a
    amostra de `limit=50` está contida na de `limit=100`, e um run maior pode
    ser comparado (ou retomado) a partir de um menor.

    Args:
        pares: todos os pares do split (saída de `load_all`).
        limit: tamanho máximo da amostra (None = todos os elegíveis).
        seed: semente do embaralhamento.
        max_per_question: máximo de pares por `question_id` (None ou 0 = sem limite).
        pair_ids: se informado, ignora a amostragem e devolve exatamente esses
            pares, na ordem do dataset.
    """
    if pair_ids:
        alvo = set(pair_ids)
        return [p for p in pares if p.pair_id in alvo]

    ordem = list(pares)
    random.Random(seed).shuffle(ordem)

    if max_per_question:
        por_questao: dict[str, int] = {}
        filtrados: list[RepairPair] = []
        for par in ordem:
            usados = por_questao.get(par.question_id, 0)
            if usados < max_per_question:
                por_questao[par.question_id] = usados + 1
                filtrados.append(par)
        ordem = filtrados

    if limit is not None:
        ordem = ordem[:limit]
    return ordem


def load_pairs(
    cache_dir: Path,
    *,
    split: str = DEFAULT_SPLIT,
    limit: int | None = None,
    seed: int = DEFAULT_SEED,
    max_per_question: int | None = DEFAULT_MAX_PER_QUESTION,
    pair_ids: list[str] | None = None,
) -> list[RepairPair]:
    """Atalho: carrega o split e aplica `select_pairs`."""
    return select_pairs(
        load_all(cache_dir, split),
        limit=limit,
        seed=seed,
        max_per_question=max_per_question,
        pair_ids=pair_ids,
    )
