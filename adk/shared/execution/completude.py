"""Checagem determinística de completude do artefato, antes do harness.

Motivação (medida numa run real de 8 tasks): o coder encerra o turno ao emitir
texto sem tool call, e acabou entregando **um arquivo por iteração**. O harness
rodou 37 vezes; em ~13 delas o workspace tinha um único arquivo novo — ou
nenhum. Cada uma dessas rodadas custou build, subida de serviço e testes, além
das chamadas de LLM do executor e do validador, para produzir uma falha que já
era conhecida antes de começar.

Este módulo responde, em Python puro, a uma pergunta anterior à do harness:
**há artefato suficiente para valer a pena executar?** Ele não julga qualidade
nem critério de aceite — isso é do validador — e não descreve execução — isso é
do harness. Só recusa o que não tem como rodar.

Duas camadas, por confiabilidade da evidência:

- **dura**: condições que o harness também reprovaria no estágio 1 (sem
  `run.json`, manifesto incoerente, nenhum código). Falso positivo é impossível
  por construção: são exatamente as pré-condições da execução.
- **branda**: arquivos declarados em `contract.outputs` que não aparecem no
  workspace. É indício, não prova — contratos são escritos por LLM e os
  caminhos divergem na prática (`models/ensaio.py` declarado,
  `app/models/ensaio.py` criado). Por isso a comparação é por NOME de arquivo,
  e por isso quem consome esta camada deve limitar quantas vezes a respeita.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from shared.execution.manifest import ManifestError, load_manifest
from shared.tools.coding_tools.filesystem_coding import arquivos_do_workspace

_MANIFEST_FILENAME = "run.json"

# Arquivos que DESCREVEM o artefato em vez de compô-lo. Um workspace só com
# eles não tem o que executar: plano, leia-me e manifestos de dependência não
# são implementação. A lista cobre as stacks mais comuns e é conservadora —
# qualquer arquivo fora dela conta como código.
_ARQUIVOS_META = frozenset(
    {
        "run.json",
        "readme.md",
        "plan.md",
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "go.mod",
        "go.sum",
        "cargo.toml",
        "cargo.lock",
        "gemfile",
        "composer.json",
        "dockerfile",
        "docker-compose.yml",
        "makefile",
    }
)

# Entradas de `contract.outputs` que não descrevem um arquivo verificável:
# diretórios de runtime (`ensaios/<id>/fotos/`) e caminhos com placeholder.
_PLACEHOLDER_RE = re.compile(r"[<>{}*]")


@dataclass(frozen=True)
class ResultadoCompletude:
    """O que impede a execução agora, separado por confiabilidade da evidência."""

    bloqueios_duros: tuple[str, ...] = ()
    pendencias_brandas: tuple[str, ...] = ()
    arquivos: tuple[str, ...] = ()

    @property
    def completo(self) -> bool:
        return not self.bloqueios_duros and not self.pendencias_brandas

    @property
    def motivos(self) -> tuple[str, ...]:
        """Duros têm precedência: sem eles, não há execução possível."""
        return self.bloqueios_duros or self.pendencias_brandas


def _e_meta(caminho: str) -> bool:
    nome = caminho.rsplit("/", 1)[-1]
    return nome.startswith(".") or nome.casefold() in _ARQUIVOS_META


def _verificavel(saida: str) -> bool:
    """False para diretórios e caminhos com placeholder — não são arquivos."""
    texto = str(saida).strip()
    if not texto or texto.endswith("/"):
        return False
    return not _PLACEHOLDER_RE.search(texto)


def verificar_completude(
    coder_dir: Path,
    outputs_esperados: Sequence[str] = (),
) -> ResultadoCompletude:
    """Diz se o artefato tem o mínimo para ser executado pelo harness.

    Args:
        coder_dir: Raiz do código do coder (`coder/src/`).
        outputs_esperados: `contract.outputs` da task da vez. Opcional — sem
            eles, só a camada dura se aplica.

    Returns:
        ResultadoCompletude com os motivos, separados por camada.
    """
    arquivos = tuple(arquivos_do_workspace(coder_dir))
    duros: list[str] = []

    manifesto = coder_dir / _MANIFEST_FILENAME
    if not manifesto.is_file():
        duros.append(
            f"`{_MANIFEST_FILENAME}` ausente na raiz do seu workspace — sem ele "
            "o harness não sabe como construir, executar nem testar o artefato."
        )
    else:
        try:
            load_manifest(manifesto)
        except ManifestError as exc:
            duros.append(f"`{_MANIFEST_FILENAME}` inválido ou incoerente: {exc}")

    codigo = [caminho for caminho in arquivos if not _e_meta(caminho)]
    if not codigo:
        presentes = ", ".join(arquivos) if arquivos else "nenhum"
        duros.append(
            "nenhum arquivo de código no workspace — só há arquivos de "
            f"plano/manifesto ({presentes}). Não há o que executar."
        )

    if duros:
        # A camada branda não é calculada quando a dura já reprovou: listar
        # outputs faltando junto com "não há código" é ruído, não informação.
        return ResultadoCompletude(bloqueios_duros=tuple(duros), arquivos=arquivos)

    nomes_existentes = {caminho.rsplit("/", 1)[-1] for caminho in arquivos}
    faltando = [
        str(saida)
        for saida in outputs_esperados or ()
        if _verificavel(saida)
        and str(saida).strip().rsplit("/", 1)[-1] not in nomes_existentes
    ]
    if faltando:
        return ResultadoCompletude(
            pendencias_brandas=(
                "arquivos declarados em `contract.outputs` desta task que não "
                "existem no workspace: " + ", ".join(faltando),
            ),
            arquivos=arquivos,
        )

    return ResultadoCompletude(arquivos=arquivos)
