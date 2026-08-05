"""Probe HTTP injetável — cliente estático que bate nas rotas DE DENTRO do container.

`docker exec` roda um programa dentro do container, mas imagens enxutas
(`scratch`/distroless) não têm shell nem `curl`/`wget`/`python`. O probe é um
binário Go estático (`CGO_ENABLED=0`, ver `shared/probe/`): roda em qualquer
container Linux e é copiado para dentro via `put_archive` (o `docker cp` da API),
sem precisar de nada instalado lá.

Este módulo NÃO é chamado por nenhum estágio do harness ainda (Fatia C2a). As
Fatias C2b (liveness, Estágio 4) e C2c (validação de rotas, Estágio 7) o
consomem depois. Três capacidades:

1. `selecionar_binario` — escolhe amd64/arm64 pela arquitetura da imagem do
   container (`container.image.attrs["Architecture"]`).
2. `injetar_probe` — empacota o binário num TAR (modo 0o755) e o injeta via
   `put_archive`; o binário chega executável, sem `chmod` dentro do container.
3. `executar_probe` — injeta, grava o request-spec no container, invoca o
   binário SEM shell (`exec_run` com lista de args — funciona sem `/bin/sh`) e
   devolve os resultados como lista de dicts no formato do contrato de I/O.
"""

from __future__ import annotations

import io
import json
import logging
import tarfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Binários estáticos pré-compilados (ver shared/probe/build.sh). Não são
# compilados em runtime: o harness só precisa deles prontos em disco.
_DIR_BINARIOS = Path(__file__).resolve().parent.parent / "probe"
_BINARIO_POR_ARCH = {
    "amd64": "probe-linux-amd64",
    "arm64": "probe-linux-arm64",
}

# Onde o probe e o request-spec vivem dentro do container. /tmp existe e é
# gravável em praticamente toda imagem; `put_archive` exige um diretório já
# existente como destino. Nomes com prefixo próprio para não colidir com o app.
_DIR_NO_CONTAINER = "/tmp"
_NOME_PROBE = ".ai4es_probe"
_NOME_SPEC = ".ai4es_probe_request.json"
_CAMINHO_PROBE = f"{_DIR_NO_CONTAINER}/{_NOME_PROBE}"
_CAMINHO_SPEC = f"{_DIR_NO_CONTAINER}/{_NOME_SPEC}"


class ProbeError(RuntimeError):
    """Falha ao selecionar/injetar/executar o probe.

    NÃO representa um erro HTTP do alvo (4xx/5xx são dados, não exceção) nem uma
    falha de transporte de uma requisição (isso vem no campo `error` do
    resultado). É falha da mecânica do probe: arquitetura sem binário, binário
    ausente, `put_archive` recusado, saída não-JSON.
    """


def _tar_de_bytes(nome: str, dados: bytes, mode: int) -> bytes:
    """Empacota um único arquivo (em memória) num TAR para `put_archive`.

    `put_archive` não copia arquivo solto: precisa de um TAR, mesmo para um
    arquivo só. O `mode` é preservado no header do TAR — é assim que o binário
    chega `+x` sem precisar de `chmod` dentro do container.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        info = tarfile.TarInfo(name=nome)
        info.size = len(dados)
        info.mode = mode
        tar.addfile(info, io.BytesIO(dados))
    return buf.getvalue()


def selecionar_binario(container: Any) -> Path:
    """Escolhe o binário do probe conforme a arquitetura da imagem do container.

    `container.image.attrs["Architecture"]` é o mesmo campo que
    `docker image inspect` expõe ("amd64"/"arm64"). Levanta `ProbeError` se a
    arquitetura não for suportada ou o binário não estiver compilado em disco.
    """
    try:
        arch = (container.image.attrs or {}).get("Architecture")
    except Exception as e:  # imagem inacessível / atributos ausentes
        raise ProbeError(f"não foi possível inspecionar a arquitetura da imagem: {e}")

    nome = _BINARIO_POR_ARCH.get(arch or "")
    if nome is None:
        raise ProbeError(
            f"arquitetura de container não suportada pelo probe: {arch!r} "
            f"(suportadas: {sorted(_BINARIO_POR_ARCH)})"
        )

    caminho = _DIR_BINARIOS / nome
    if not caminho.is_file():
        raise ProbeError(
            f"binário do probe ausente: {caminho}. Compile com shared/probe/build.sh."
        )
    return caminho


def injetar_probe(container: Any) -> str:
    """Injeta o binário do probe no container e devolve seu caminho lá dentro.

    Escolhe o binário pela arquitetura, empacota em TAR (modo 0o755) e usa
    `put_archive` (equivalente a `docker cp`). Idempotente: reinjetar
    sobrescreve. Devolve o caminho absoluto do probe dentro do container.
    """
    binario = selecionar_binario(container)
    tar = _tar_de_bytes(_NOME_PROBE, binario.read_bytes(), 0o755)
    if not container.put_archive(_DIR_NO_CONTAINER, tar):
        raise ProbeError(f"put_archive falhou ao injetar o probe em {_DIR_NO_CONTAINER}")
    return _CAMINHO_PROBE


def executar_probe(
    container: Any, requisicoes: list[dict], base_url: str
) -> list[dict]:
    """Roda o probe contra `base_url` para a lista de requisições dada.

    Cada requisição é um dict no formato do contrato de I/O: `method` e `path`
    obrigatórios; `headers`, `body` e `timeout_ms` opcionais. Devolve a lista de
    resultados (dicts com method/path/status/latency_ms/error/body), na mesma
    ordem das requisições.

    Injeta o binário, grava o request-spec.json no container (também via
    `put_archive`) e invoca o probe SEM shell — `exec_run` com lista de args, que
    funciona mesmo sem `/bin/sh` na imagem.

    Levanta `ProbeError` se a mecânica falhar (binário/injeção/saída). Falhas de
    transporte de requisições individuais NÃO levantam — vêm no campo `error` de
    cada resultado.
    """
    caminho_probe = injetar_probe(container)

    spec_bytes = json.dumps(requisicoes).encode("utf-8")
    tar_spec = _tar_de_bytes(_NOME_SPEC, spec_bytes, 0o644)
    if not container.put_archive(_DIR_NO_CONTAINER, tar_spec):
        raise ProbeError("put_archive falhou ao gravar o request-spec no container")

    res = container.exec_run([caminho_probe, _CAMINHO_SPEC, base_url], demux=True)

    saida = res.output if isinstance(res.output, tuple) else (res.output, None)
    stdout = (saida[0] or b"").decode("utf-8", errors="replace")
    stderr = (saida[1] or b"").decode("utf-8", errors="replace")

    if res.exit_code != 0:
        raise ProbeError(
            f"probe saiu com código {res.exit_code}: "
            f"{stderr.strip() or stdout.strip() or '(sem saída)'}"
        )
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise ProbeError(
            f"saída do probe não é JSON válido: {e}; stdout={stdout[:500]!r}"
        )
