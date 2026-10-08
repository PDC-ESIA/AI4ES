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


def caminho_relativo_interface(task_id: str) -> str:
    """Arquivo dos critérios de interface da task (produto web, Playwright).

    Separado do arquivo principal porque roda de outro jeito: contra a
    aplicação no ar, num navegador, e sem importar o código do projeto.
    """
    return f"{PASTA_ACEITE}/test_interface_{re.sub(r'[^A-Za-z0-9]', '_', task_id)}.py"


def e_arquivo_de_interface(arquivo_rel: str) -> bool:
    return PurePosixPath(arquivo_rel).name.startswith("test_interface_")


def caminho_mapa(tasks_dir: Path, task_id: str) -> Path:
    """Mapa critério→teste, fora do workspace de código (o coder não o alcança)."""
    return Path(tasks_dir) / f"{task_id}.acceptance.json"


def e_caminho_protegido(caminho: Optional[str], pasta: str = PASTA_ACEITE) -> bool:
    """Diz se um caminho relativo cai na `pasta` (padrão: testes de aceite)."""
    if not isinstance(caminho, str) or not caminho.strip():
        return False
    partes = PurePosixPath(caminho.strip().replace("\\", "/")).parts
    alvo = PurePosixPath(pasta).parts
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


def _arquivo_do_nodeid(nodeid: str) -> str:
    return nodeid.split("::", 1)[0]


def gravar_mapa(
    tasks_dir: Path,
    task_id: str,
    arquivo_rel: str,
    por_criterio: dict[str, list[str]],
    *,
    mesclar: bool = False,
    tecnicos: Iterable[str] = (),
) -> Path:
    """Grava o mapa da task. Com `mesclar`, soma ao mapa já gravado.

    Em produto web a task tem dois arquivos (o principal e o de interface); cada
    um é salvo por uma ferramenta própria e substitui só os próprios testes.
    `tecnicos`: ids dos critérios técnicos da task (nunca reprovam).
    """
    destino = caminho_mapa(tasks_dir, task_id)
    destino.parent.mkdir(parents=True, exist_ok=True)
    existente = ler_mapa(tasks_dir, task_id) if mesclar else None
    if existente:
        arquivos = [a for a in existente["arquivos"] if a != arquivo_rel] + [arquivo_rel]
        mapa: dict[str, list[str]] = {}
        for criterio, testes in existente["por_criterio"].items():
            mantidos = [t for t in testes if _arquivo_do_nodeid(t) != arquivo_rel]
            if mantidos:
                mapa[criterio] = mantidos
        for criterio, testes in por_criterio.items():
            mapa.setdefault(criterio, []).extend(testes)
        principal = existente["arquivo"]
        tecnicos = set(tecnicos) | set(existente["tecnicos"])
    else:
        arquivos, mapa, principal = [arquivo_rel], dict(por_criterio), arquivo_rel
    destino.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "arquivo": principal,
                "arquivos": arquivos,
                "por_criterio": mapa,
                "tecnicos": sorted(set(tecnicos)),
            },
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
    aceitas = dados.get("falhas_aceitas")
    arquivos = [a for a in dados.get("arquivos") or [] if isinstance(a, str)] or [arquivo]
    return {
        "task_id": task_id,
        "arquivo": arquivo,
        "arquivos": arquivos,
        "por_criterio": limpo,
        "tecnicos": [t for t in dados.get("tecnicos") or [] if isinstance(t, str)],
        "falhas_aceitas": [t for t in aceitas if isinstance(t, str)]
        if isinstance(aceitas, list)
        else [],
    }


def registrar_falhas_aceitas(tasks_dir: Path, task_id: str, nodeids: Iterable[str]) -> None:
    """Fecha a linha de base da task: testes dela que já falhavam ao encerrar.

    Uma task aceita com ressalvas deixa um teste de aceite falhando; sem esta
    marca, ele reprovaria como "regressão" todas as tasks seguintes — na run
    de validação, a TASK-003 passou nos próprios critérios e reprovou pelo
    CA-03 da TASK-002.
    """
    caminho = caminho_mapa(tasks_dir, task_id)
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(dados, dict):
        return
    dados["falhas_aceitas"] = sorted(set(nodeids))
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def falhas_aceitas_por_arquivo(tasks_dir: Path) -> dict[str, set[str]]:
    """`{arquivo de aceite: nodeids que já falhavam quando a task fechou}`."""
    aceitas: dict[str, set[str]] = {}
    for caminho in Path(tasks_dir).glob("*.acceptance.json"):
        task_id = caminho.name[: -len(".acceptance.json")]
        mapa = ler_mapa(tasks_dir, task_id)
        if not mapa:
            continue
        for arquivo in mapa["arquivos"]:
            aceitas.setdefault(arquivo, set())
        for nodeid in mapa["falhas_aceitas"]:
            aceitas.setdefault(_arquivo_do_nodeid(nodeid), set()).add(nodeid)
    return aceitas


def testes_tecnicos(tasks_dir: Path) -> set[str]:
    """Nodeids dos testes ligados a critérios técnicos, em todas as tasks.

    Falha neles nunca reprova (nem a task deles, nem as seguintes): critério
    técnico vira nota no relatório.
    """
    tecnicos: set[str] = set()
    for caminho in Path(tasks_dir).glob("*.acceptance.json"):
        mapa = ler_mapa(tasks_dir, caminho.name[: -len(".acceptance.json")])
        if not mapa:
            continue
        for criterio in mapa["tecnicos"]:
            tecnicos.update(mapa["por_criterio"].get(criterio, []))
    return tecnicos


def comando_de_aceite(comandos_de_teste: Iterable[str], arquivo_rel: str) -> Optional[str]:
    """Comando pytest que roda só o arquivo de aceite, derivado do `run.json`.

    Reaproveita o prefixo do primeiro comando com pytest (`venv/bin/python -m
    pytest`), para usar o mesmo ambiente; None se o manifesto não usa pytest.
    """
    for comando in comandos_de_teste:
        posicao = comando.find("pytest")
        if posicao >= 0:
            # Sem warnings e com traceback curto + resumo por falha: o motivo de
            # cada falha precisa caber no trecho de saída que chega ao coder.
            # Na validação, warnings de depreciação ocupavam o trecho inteiro e
            # o coder só via "FAILED", sem a asserção.
            return (
                f"{comando[: posicao + len('pytest')]} -v -p no:cacheprovider "
                f"-p no:warnings --tb=short -rfE {arquivo_rel}"
            )
    return None
