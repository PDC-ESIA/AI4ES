"""Impressão digital do conteúdo de um workspace, para detectar não-progresso.

Motivação (issue #394): um dos sinais de que o loop `coder ↔ executor` travou é
o coder devolver o turno sem ter alterado nada — a rodada seguinte reproduziria
exatamente a mesma falha, ao custo de build, sandbox e duas chamadas de LLM.
Antes, perceber isso dependia do LLM do executor notar e declarar por conta
própria (o "protocolo anti-estagnação" do prompt), o que era frágil e
imprevisível. Este módulo torna a checagem determinística: duas rodadas com o
mesmo conteúdo produzem a mesma impressão digital.

Decisões que importam para a corretude:

- **Conteúdo, não `mtime`.** O artefato é copiado para o sandbox a cada rodada
  e recriado por ferramentas; `mtime` mudaria sem o código mudar, o que
  esconderia a estagnação exatamente quando ela existe.
- **Caminho entra no hash.** Renomear um arquivo sem alterar o conteúdo é uma
  alteração real e precisa mudar a impressão digital.
- **Ordem estável.** Os caminhos são ordenados antes de hashear: a ordem de
  iteração do filesystem não é garantida, e sem isso a mesma árvore poderia
  produzir hashes diferentes entre rodadas.
- **Tudo conta como artefato, não só código.** Mexer no `run.json` ou num
  arquivo de dependências é progresso tanto quanto mexer num `.py` — o gate
  `verificar_executabilidade` já trata esses arquivos como parte do artefato.

Este módulo NÃO decide nada sobre o loop: ele só mede. A decisão de parar é da
política em `loop_policy.py`, que combina este sinal com a evolução da nota.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from shared.tools.coding_tools.filesystem_coding import DIRETORIOS_PROIBIDOS

logger = logging.getLogger(__name__)

# Lido em blocos: um artefato pode conter arquivos grandes (dumps, binários), e
# carregá-los inteiros na memória só para hashear seria desperdício.
_TAMANHO_BLOCO = 64 * 1024

# Separador entre os campos que compõem o hash. O byte nulo não aparece em
# caminho de arquivo, então ele delimita sem ambiguidade: sem um separador,
# (caminho="ab", conteúdo="c") e (caminho="a", conteúdo="bc") colidiriam.
_SEPARADOR = b"\0"

# Marcador para arquivo que existe mas não pôde ser lido. Entra no hash no lugar
# do conteúdo para que a impressão digital continue determinística — e para que
# o arquivo ficar legível depois seja detectado como mudança, que é o que é.
_ILEGIVEL = b"<ilegivel>"


def _arquivos_versionaveis(raiz: Path) -> list[tuple[str, Path]]:
    """Arquivos do workspace que contam como artefato, em ordem estável.

    Mesma caminhada e mesmas exclusões de `verificar_executabilidade`, de
    propósito: os dois olham o mesmo workspace e precisam concordar sobre o que
    é conteúdo do artefato e o que é ruído gerado (`__pycache__`, `node_modules`,
    `.venv`, `.git`).

    Links simbólicos são ignorados: seguir um poderia levar para fora do
    workspace (ou a um ciclo), e o alvo não é conteúdo produzido pelo coder.
    """
    if not raiz.exists():
        return []

    encontrados: list[tuple[str, Path]] = []
    for caminho in raiz.rglob("*"):
        if caminho.is_symlink():
            continue
        if DIRETORIOS_PROIBIDOS.intersection(caminho.parts):
            continue
        if not caminho.is_file():
            continue
        encontrados.append((caminho.relative_to(raiz).as_posix(), caminho))

    encontrados.sort(key=lambda item: item[0])
    return encontrados


def fingerprint_workspace(raiz: Path) -> str:
    """Impressão digital (SHA-256) do conteúdo do workspace.

    Args:
        raiz: Raiz do workspace a inspecionar (para o loop de codificação, o
            workspace do coder).

    Returns:
        Hash hexadecimal, estável para o mesmo conteúdo. Um workspace vazio e um
        inexistente produzem o mesmo valor — em ambos não há artefato nenhum, e
        para o propósito desta medida isso é a mesma situação.
    """
    hasher = hashlib.sha256()

    for relativo, caminho in _arquivos_versionaveis(raiz):
        hasher.update(relativo.encode("utf-8"))
        hasher.update(_SEPARADOR)
        try:
            with caminho.open("rb") as arquivo:
                while bloco := arquivo.read(_TAMANHO_BLOCO):
                    hasher.update(bloco)
        except OSError as erro:
            # Não derruba a rodada por um arquivo ilegível: a impressão digital
            # segue determinística, e o pior caso é uma comparação conservadora.
            logger.warning(
                "[FINGERPRINT] Arquivo ilegível em %s (%s); entrando no hash "
                "como marcador.",
                relativo,
                type(erro).__name__,
            )
            hasher.update(_ILEGIVEL)
        hasher.update(_SEPARADOR)

    return hasher.hexdigest()
