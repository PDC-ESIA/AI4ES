"""Teste de jornada do produto integrado (`AI4ES_JORNADA`).

Cada task do coder é validada isoladamente; ninguém testava o produto inteiro.
Na run do fotógrafo as 7 tasks passaram e o fluxo real quebrava nas costuras:
imagens com 404 (caminho relativo, sem rota servindo o storage), formulário de
álbum enviado a um endpoint que só aceitava JSON (422), nenhuma tela de upload.

Depois da última task, um agente escreve `tests/journey/test_jornada.py` a
partir das HUs — os fluxos de ponta a ponta, com checagem dos recursos que as
páginas referenciam — e este módulo o executa no mesmo ambiente do harness
(build do `run.json`, trilha). Falhou, vira uma task de integração.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from shared.execution.manifest import ManifestError, load_manifest
from shared.execution.sandbox import create_sandbox
from shared.execution.trilhas import ambiente_da_trilha
from shared.tools.coding_tools.aceite_independente import comando_de_aceite

logger = logging.getLogger(__name__)

PASTA_JORNADA = "tests/journey"
ARQUIVO_JORNADA = f"{PASTA_JORNADA}/test_jornada.py"

_TIMEOUT_BUILD = 300
_TIMEOUT_JORNADA = 180

PASSOU = "passou"
FALHOU = "falhou"
NAO_EXECUTADA = "nao_executada"


@dataclass
class ResultadoJornada:
    status: str
    motivo: str = ""
    testes: list[dict] = field(default_factory=list)
    falhas: list[str] = field(default_factory=list)
    saida: str = ""

    def como_dict(self) -> dict:
        return asdict(self)


def _cauda(texto: str, limite: int = 6000) -> str:
    texto = (texto or "").strip()
    return texto if len(texto) <= limite else "…" + texto[-limite:]


def executar_jornada(coder_dir: Path, trilha: Optional[dict] = None) -> ResultadoJornada:
    """Constrói o artefato como o harness e roda só o arquivo da jornada."""
    from shared.tools.coding_tools.harness_execucao import _testes_da_saida

    try:
        manifest = load_manifest(coder_dir / "run.json")
    except ManifestError as exc:
        return ResultadoJornada(NAO_EXECUTADA, motivo=f"run.json inválido: {exc}")
    workdir = (coder_dir / manifest.workdir).resolve()
    if not (workdir / ARQUIVO_JORNADA).is_file():
        return ResultadoJornada(NAO_EXECUTADA, motivo="teste de jornada não foi escrito")
    comando = comando_de_aceite(manifest.test, ARQUIVO_JORNADA)
    if comando is None:
        return ResultadoJornada(NAO_EXECUTADA, motivo="o run.json não usa pytest")
    # `comando_de_aceite` já pede traceback curto, resumo por falha e sem
    # warnings: a mensagem de cada jornada quebrada cabe na saída ao coder.

    sandbox = create_sandbox("direct", workdir_subpath=manifest.workdir)
    try:
        sandbox.setup(coder_dir)
        env = {**ambiente_da_trilha(trilha, sandbox.root), **(manifest.env or {})} or None
        for build in manifest.build:
            res = sandbox.exec(build, timeout=_TIMEOUT_BUILD, env=env)
            if res.timed_out or res.exit_code != 0:
                saida = "\n".join(p for p in (res.stdout, res.stderr) if p)
                return ResultadoJornada(
                    FALHOU, motivo=f"build falhou: {build}", saida=_cauda(saida)
                )
        res = sandbox.exec(comando, timeout=_TIMEOUT_JORNADA, env=env)
    finally:
        sandbox.cleanup()

    saida = "\n".join(p for p in (res.stdout, res.stderr) if p)
    testes = _testes_da_saida(saida)
    falhas = [t["nodeid"] for t in testes if t["outcome"] in ("falhou", "erro")]
    if res.timed_out:
        return ResultadoJornada(FALHOU, motivo="tempo limite", testes=testes, falhas=falhas, saida=_cauda(saida))
    if res.exit_code == 0 and testes and not falhas:
        return ResultadoJornada(PASSOU, testes=testes, saida=_cauda(saida, 1500))
    motivo = "testes da jornada falharam" if testes else "nenhum teste da jornada executou"
    return ResultadoJornada(FALHOU, motivo=motivo, testes=testes, falhas=falhas, saida=_cauda(saida))


def montar_task_integracao(resultado: ResultadoJornada, task_id: str, rodada: int) -> dict:
    """Task sintética que devolve ao coder as falhas da jornada.

    O único critério é a própria jornada passar; o mapa dela aponta para os
    testes da jornada, e o mecanismo de aceite independente o decide.
    """
    falhas = "\n".join(f"- {f}" for f in resultado.falhas) or f"- {resultado.motivo}"
    return {
        "id": task_id,
        "type": "integration",
        "complexity": "medium",
        "description": (
            f"Integração do produto (rodada {rodada}): a jornada de ponta a ponta "
            f"`{ARQUIVO_JORNADA}`, escrita a partir das HUs, falhou. Corrija o "
            "CÓDIGO para que os fluxos funcionem juntos — rotas, formulários, "
            "templates, arquivos estáticos e mídia servidos. Não edite o teste.\n\n"
            f"Falhas:\n{falhas}\n\nSaída (final):\n{resultado.saida[-2500:]}"
        ),
        "business_rules": [],
        "acceptance_criteria": [
            {
                "id": "CA-01",
                "description": f"A jornada de ponta a ponta `{ARQUIVO_JORNADA}` passa por inteiro.",
                "automatable": True,
            }
        ],
        "contract": {"inputs": [ARQUIVO_JORNADA], "outputs": [], "interfaces": []},
        "requirement_id": "",
        "requirement_refs": [],
        "design_refs": [],
    }
