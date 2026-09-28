"""Ingestão do dataset MBPP — versão *sanitized* (download dinâmico + parsing).

Mesma decisão de versionamento do HumanEval: o dataset NÃO é versionado em
git, é baixado dinamicamente na primeira execução e cacheado localmente (ver
`benchmarks/coding_review/mbpp/datasets/`, listado no `.gitignore`).

Fonte: `sanitized-mbpp.json`, publicado pelos autores originais (Austin et
al., 2021) no repositório `google-research/google-research`. É um `.json`
(lista, não `.jsonl.gz`) com ~427 problemas — a curadoria oficial que remove
tarefas ambíguas/duplicadas do MBPP bruto (974 problemas), e é o padrão de
facto usado por harnesses de avaliação de geração de código single-shot
(bigcode-evaluation-harness, EvalPlus MBPP+).

Cada item do dataset tem os campos:

- ``task_id``: identificador numérico (ex.: ``2``).
- ``prompt``: descrição em linguagem natural da função a implementar.
- ``code``: solução de referência (NUNCA usada na avaliação — apenas para
  derivar, de forma determinística, o nome da função-alvo; ver
  `_derive_entry_point`).
- ``test_imports``: lista de instruções `import` exigidas pelos testes.
- ``test_list``: lista de `assert`s oficiais — o avaliador (ver `grading.py`).

Diferença estrutural em relação ao HumanEval: o MBPP *sanitized* não traz um
campo `entry_point` explícito. Ele é derivado a partir da solução de
referência (`code`): localizamos as funções definidas no nível de módulo via
AST e escolhemos a que é de fato referenciada em `test_list` (cross-check).
Essa estratégia foi validada contra os 427 problemas do dataset: resolve o
nome correto em 100% dos casos (12 problemas têm mais de uma função de nível
de módulo; em todos, exatamente uma delas aparece em `test_list`).

Somente a biblioteca padrão é usada (urllib/json/ast), evitando dependências
extras no ambiente do benchmark.
"""

from __future__ import annotations

import ast
import json
import re
import urllib.request
import warnings
from dataclasses import dataclass, field
from pathlib import Path

# Fonte oficial do dataset sanitized (raw do repositório google-research).
DEFAULT_DATASET_URL = (
    "https://raw.githubusercontent.com/google-research/google-research/"
    "master/mbpp/sanitized-mbpp.json"
)


@dataclass(frozen=True)
class MbppProblem:
    """Um problema do MBPP (sanitized), com os campos relevantes ao benchmark."""

    task_id: str
    prompt: str
    entry_point: str
    test_list: list[str]
    test_imports: list[str] = field(default_factory=list)
    canonical_solution: str = ""

    @property
    def slug(self) -> str:
        """Identificador seguro para nomes de arquivo (ex.: ``Mbpp_2``)."""
        return self.task_id.replace("/", "_")


def ensure_dataset(dest_path: Path, *, url: str = DEFAULT_DATASET_URL) -> Path:
    """Garante o `.json` local, baixando-o se ainda não existir.

    Args:
        dest_path: caminho local do arquivo.
        url: origem do download.

    Returns:
        O próprio `dest_path` (já existente em disco).
    """
    if dest_path.is_file() and dest_path.stat().st_size > 0:
        return dest_path

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[dataset] Baixando MBPP (sanitized) de {url} …")
    with urllib.request.urlopen(url) as resp:  # noqa: S310 — URL oficial fixa
        dados = resp.read()
    dest_path.write_bytes(dados)
    print(f"[dataset] Salvo em {dest_path} ({len(dados)} bytes).")
    return dest_path


def _top_level_function_names(code: str) -> list[str]:
    """Nomes de funções definidas no nível de módulo de `code`, em ordem."""
    try:
        # Soluções de referência usam regex em strings não-raw ("\w"), o que faz
        # o ast.parse emitir SyntaxWarning a cada carregamento do dataset.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            arvore = ast.parse(code)
    except SyntaxError:
        return []
    return [
        node.name
        for node in arvore.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _derive_entry_point(task_id: int, code: str, test_list: list[str]) -> str | None:
    """Deriva o nome da função-alvo a partir da solução de referência.

    O MBPP *sanitized* não expõe um campo `entry_point` (diferente do
    HumanEval). Estratégia: localizamos as funções de nível de módulo em
    `code` (via AST) e escolhemos a que é efetivamente chamada em
    `test_list` (cross-check por regex de fronteira de palavra) — isso é
    necessário porque vários `assert`s envolvem a chamada-alvo em outra
    chamada (ex.: ``assert set(func(x)) == set(y)``), então não dá para
    simplesmente pegar o primeiro identificador após ``assert``.

    Retorna `None` se nenhuma função de nível de módulo puder ser resolvida
    (o chamador decide como lidar: pular o problema com aviso).
    """
    candidatos = _top_level_function_names(code)
    if not candidatos:
        return None
    if len(candidatos) == 1:
        return candidatos[0]

    texto_testes = " ".join(test_list)
    referenciados = [
        nome
        for nome in candidatos
        if re.search(rf"\b{re.escape(nome)}\s*\(", texto_testes)
    ]
    if len(referenciados) == 1:
        return referenciados[0]

    # Ambíguo (0 ou >1 candidatos referenciados): heurística de fallback —
    # a última função definida costuma ser a "principal" (helpers vêm antes).
    escolhido = referenciados[-1] if referenciados else candidatos[-1]
    print(
        f"[dataset] Aviso: entry_point ambíguo para Mbpp/{task_id} "
        f"(candidatos={candidatos}, referenciados={referenciados}); "
        f"usando '{escolhido}'."
    )
    return escolhido


def load_problems(
    dataset_path: Path,
    *,
    url: str = DEFAULT_DATASET_URL,
    limit: int | None = None,
    task_ids: list[str] | None = None,
) -> list[MbppProblem]:
    """Carrega os problemas do MBPP a partir do `.json` (baixa se preciso).

    Args:
        dataset_path: caminho local do dataset.
        url: origem do download (quando ausente localmente).
        limit: se informado, retorna no máximo os `limit` primeiros problemas.
        task_ids: se informado, filtra apenas os `task_id` desta lista
            (aceita ``"Mbpp/2"``, o slug ``"Mbpp_2"`` ou o id bruto ``"2"``).

    Returns:
        Lista de `MbppProblem` na ordem do dataset. Problemas cujo
        entry_point não pôde ser derivado são omitidos (com aviso).
    """
    ensure_dataset(dataset_path, url=url)

    raw = json.loads(dataset_path.read_text(encoding="utf-8"))

    problemas: list[MbppProblem] = []
    for item in raw:
        raw_id = item["task_id"]
        code = item.get("code", "")
        test_list = item.get("test_list", [])

        entry_point = _derive_entry_point(raw_id, code, test_list)
        if entry_point is None:
            print(
                f"[dataset] Aviso: não foi possível derivar entry_point para "
                f"Mbpp/{raw_id}; problema omitido."
            )
            continue

        problemas.append(
            MbppProblem(
                task_id=f"Mbpp/{raw_id}",
                prompt=item["prompt"],
                entry_point=entry_point,
                test_list=test_list,
                test_imports=item.get("test_imports", []),
                canonical_solution=code,
            )
        )

    if task_ids:
        alvo = set(task_ids)
        problemas = [
            p
            for p in problemas
            if p.task_id in alvo
            or p.slug in alvo
            or p.task_id.split("/", 1)[-1] in alvo
        ]

    if limit is not None:
        problemas = problemas[:limit]

    return problemas
