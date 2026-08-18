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

Escopo deliberadamente restrito: apenas condições que o harness TAMBÉM
reprovaria no estágio 1 (sem `run.json`, manifesto incoerente, nenhum código).
Falso positivo é impossível por construção — são exatamente as pré-condições da
execução —, e por isso a checagem não precisa de teto de tentativas nem de
nenhum parâmetro de tolerância.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shared.execution.manifest import ManifestError, load_manifest
from shared.tools.coding_tools.filesystem_coding import DIRETORIOS_PROIBIDOS

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


@dataclass(frozen=True)
class ResultadoCompletude:
    """O que impede a execução agora, com o inventário que embasa a decisão."""

    bloqueios: tuple[str, ...] = ()
    arquivos: tuple[str, ...] = ()

    @property
    def completo(self) -> bool:
        return not self.bloqueios


def _arquivos(raiz: Path) -> tuple[str, ...]:
    """Caminhos relativos dos arquivos do workspace, ignorando gerados."""
    if not raiz.exists():
        return ()
    return tuple(
        sorted(
            caminho.relative_to(raiz).as_posix()
            for caminho in raiz.rglob("*")
            if caminho.is_file()
            and not DIRETORIOS_PROIBIDOS.intersection(caminho.parts)
        )
    )


def _e_meta(caminho: str) -> bool:
    nome = caminho.rsplit("/", 1)[-1]
    return nome.startswith(".") or nome.casefold() in _ARQUIVOS_META


def verificar_completude(coder_dir: Path) -> ResultadoCompletude:
    """Diz se o artefato tem o mínimo para ser executado pelo harness.

    Args:
        coder_dir: Raiz do código do coder (`coder/src/`).

    Returns:
        ResultadoCompletude com os bloqueios encontrados e o inventário atual.
    """
    arquivos = _arquivos(coder_dir)
    bloqueios: list[str] = []

    manifesto = coder_dir / _MANIFEST_FILENAME
    if not manifesto.is_file():
        bloqueios.append(
            f"`{_MANIFEST_FILENAME}` ausente na raiz do seu workspace — sem ele "
            "o harness não sabe como construir, executar nem testar o artefato."
        )
    else:
        try:
            load_manifest(manifesto)
        except ManifestError as exc:
            bloqueios.append(f"`{_MANIFEST_FILENAME}` inválido ou incoerente: {exc}")

    if not [caminho for caminho in arquivos if not _e_meta(caminho)]:
        presentes = ", ".join(arquivos) if arquivos else "nenhum"
        bloqueios.append(
            "nenhum arquivo de código no workspace — só há arquivos de "
            f"plano/manifesto ({presentes}). Não há o que executar."
        )

    return ResultadoCompletude(bloqueios=tuple(bloqueios), arquivos=arquivos)
