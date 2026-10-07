"""Testes de aceite independentes do coder (`AI4ES_ACEITE_INDEPENDENTE`).

Desde o #394 o harness não decide critério nenhum: o vínculo teste→critério
vinha do `run.json` do PRÓPRIO coder, e um vínculo errado creditava critérios
que o teste nem exercitava. Na run do fotógrafo isso virou o oposto — 21 de 21
critérios `nao_avaliado`, tasks com nota 10 e um produto que não funcionava
(CA-03 pedia 201, o código devolvia 303 e o teste do coder aceitava os dois).

Aqui o vínculo tem outra origem: um agente separado (`cr_acceptance_author`)
escreve UM arquivo de teste por task, a partir dos critérios, e o coder não pode
editá-lo. O mapa critério→teste não é declarado por ninguém: é extraído do
próprio arquivo, pelo nome das funções (`test_CA_01_...` → `CA-01`).

Este módulo é a parte determinística, compartilhada pelo autor (que grava), pelo
harness (que executa e decide) e pelo guard do coder (que protege).
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path, PurePosixPath
from typing import Iterable, Optional

# Pasta dos testes de aceite, relativa ao workdir do artefato.
PASTA_ACEITE = "tests/acceptance"

_FUNCAO_RE = re.compile(r"^test_CA_?(\d+)", re.IGNORECASE)


def nome_arquivo(task_id: str) -> str:
    """Nome do arquivo de testes de aceite da task (único entre tasks)."""
    return f"test_aceite_{re.sub(r'[^A-Za-z0-9]', '_', task_id)}.py"


def caminho_relativo(task_id: str) -> str:
    """Caminho do arquivo relativo ao workdir — é o prefixo dos nodeids."""
    return f"{PASTA_ACEITE}/{nome_arquivo(task_id)}"


def caminho_mapa(tasks_dir: Path, task_id: str) -> Path:
    """Mapa critério→teste, fora do workspace de código (o coder não o alcança)."""
    return Path(tasks_dir) / f"{task_id}.acceptance.json"


def e_caminho_protegido(caminho: Optional[str]) -> bool:
    """Diz se um caminho relativo cai na pasta de testes de aceite."""
    if not isinstance(caminho, str) or not caminho.strip():
        return False
    partes = PurePosixPath(caminho.strip().replace("\\", "/")).parts
    alvo = PurePosixPath(PASTA_ACEITE).parts
    return any(
        tuple(partes[i : i + len(alvo)]) == alvo for i in range(len(partes) - len(alvo) + 1)
    )


def _id_do_criterio(nome_funcao: str) -> Optional[str]:
    casado = _FUNCAO_RE.match(nome_funcao)
    return f"CA-{int(casado.group(1)):02d}" if casado else None


def extrair_mapa(
    codigo: str, ids_validos: Iterable[str], arquivo_rel: str
) -> dict[str, list[str]]:
    """`{CA-01: [nodeid, ...]}` a partir das funções `test_CA_NN_*` do arquivo.

    Funções de módulo e métodos de classes `Test*` contam; ids que não existem
    na task são descartados. Levanta `SyntaxError` se o código não compila.
    """
    validos = set(ids_validos)
    arvore = ast.parse(codigo)
    mapa: dict[str, list[str]] = {}

    def _registrar(nome: str, nodeid: str) -> None:
        criterio = _id_do_criterio(nome)
        if criterio in validos:
            mapa.setdefault(criterio, []).append(nodeid)

    for no in arvore.body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _registrar(no.name, f"{arquivo_rel}::{no.name}")
        elif isinstance(no, ast.ClassDef) and no.name.startswith("Test"):
            for metodo in no.body:
                if isinstance(metodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    _registrar(metodo.name, f"{arquivo_rel}::{no.name}::{metodo.name}")
    return mapa


def gravar_mapa(
    tasks_dir: Path, task_id: str, arquivo_rel: str, por_criterio: dict[str, list[str]]
) -> Path:
    destino = caminho_mapa(tasks_dir, task_id)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(
            {"task_id": task_id, "arquivo": arquivo_rel, "por_criterio": por_criterio},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return destino


def ler_mapa(tasks_dir: Path, task_id: str) -> Optional[dict]:
    """Mapa gravado para a task, ou None (ausente, corrompido ou de outra task)."""
    caminho = caminho_mapa(tasks_dir, task_id)
    if not caminho.is_file():
        return None
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(dados, dict) or dados.get("task_id") != task_id:
        return None
    por_criterio = dados.get("por_criterio")
    arquivo = dados.get("arquivo")
    if not isinstance(por_criterio, dict) or not isinstance(arquivo, str):
        return None
    limpo = {
        str(k): [str(t) for t in v if isinstance(t, str)]
        for k, v in por_criterio.items()
        if isinstance(v, list)
    }
    return {"task_id": task_id, "arquivo": arquivo, "por_criterio": limpo}


def comando_de_aceite(comandos_de_teste: Iterable[str], arquivo_rel: str) -> Optional[str]:
    """Comando pytest que roda só o arquivo de aceite, derivado do `run.json`.

    Reaproveita o prefixo do primeiro comando com pytest (`venv/bin/python -m
    pytest`), para usar o mesmo ambiente; None se o manifesto não usa pytest.
    """
    for comando in comandos_de_teste:
        posicao = comando.find("pytest")
        if posicao >= 0:
            return f"{comando[: posicao + len('pytest')]} -v -p no:cacheprovider {arquivo_rel}"
    return None
