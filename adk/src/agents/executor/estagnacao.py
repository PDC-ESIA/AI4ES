"""Detecção determinística de estagnação do loop `[coder → executor]`.

Não existe para evitar loop infinito — o `max_iterations` do `LoopAgent` já faz
isso. Existe para encerrar MAIS CEDO, com o status semântico certo
(`bloqueado`), quando o loop claramente não progride, em vez de queimar todas as
iterações e sair por esgotamento.

O mecanismo antigo dependia de um LLM lendo uma declaração do coder ("nenhuma
alteração necessária"). Sem LLM na orquestração, a estagnação passa a ser medida
por FATO OBSERVÁVEL: o par `(hash do código do coder, blocking_reason)` repetido
em 3 iterações CONSECUTIVAS.

As duas metades da chave cobrem falhas diferentes, e por isso andam juntas:
- o hash pega o caso "o coder não mexeu em nada";
- o `blocking_reason` pega o caso em que o coder mexe em arquivos (hash muda) e
  mesmo assim continua travado exatamente no mesmo ponto.

Qualquer mudança em um dos dois zera o contador — é "3 vezes seguidas", não "3
vezes no total". A 1ª reprovação estabelece o estado, a 2ª repetição não
encerra, a 3ª encerra: o coder tem duas chances reais de quebrar o padrão.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from .error_report import _MARCADOR_ESTAGNACAO

logger = logging.getLogger(__name__)

# Repetições consecutivas do mesmo par que caracterizam estagnação.
LIMITE_REPETICOES = 3

# Marcador do resumo de bloqueio. Reexportado do error_report para haver uma
# única fonte de verdade: é o mesmo texto que o builder procura para NÃO
# sobrescrever este resumo com um ErrorReport.
MARCADOR_ESTAGNACAO = _MARCADOR_ESTAGNACAO

_ARQUIVO_EXCLUSOES = ".dockerignore"

# Conteúdo ilegível não pode derrubar o loop nem tornar o hash indeterminado.
_SENTINELA_ILEGIVEL = b"<<ilegivel>>"


class _Exclusoes:
    """Subconjunto pragmático da sintaxe de `.dockerignore`.

    Cobre o que aparece na prática nesses arquivos: diretórios literais
    (`nome/`), extensões (`*.ext`) e nomes simples. Negações (`!`) e globs
    aninhados não são suportados — e não precisam ser: no host, `coder/src`
    contém só o que o coder autorou. Artefatos gerados (`__pycache__`,
    `node_modules`) nascem DENTRO do container, não aqui. As exclusões são
    defensivas; a corretude do hash não depende delas.
    """

    def __init__(self) -> None:
        self.diretorios: set[str] = set()
        self.sufixos: set[str] = set()
        self.nomes: set[str] = set()

    def ignora(self, relativo: Path) -> bool:
        partes = relativo.parts
        # Fallback universal: `.git` e qualquer dot-file/dot-cache, em qualquer
        # nível. Independe do .dockerignore existir.
        if any(p.startswith(".") for p in partes):
            return True
        if any(p in self.diretorios for p in partes[:-1]):
            return True
        nome = relativo.name
        if nome in self.nomes:
            return True
        return any(nome.endswith(s) for s in self.sufixos)


def _carregar_exclusoes(raiz: Path) -> _Exclusoes:
    """Lê as exclusões declaradas no `.dockerignore` da própria raiz.

    Dado declarativo do projeto sendo construído, não uma lista hardcoded por
    linguagem — é o mesmo arquivo que decide o que entra no build. Ausente ou
    ilegível: só o fallback universal.
    """
    exclusoes = _Exclusoes()
    manifesto = raiz / _ARQUIVO_EXCLUSOES
    try:
        linhas = manifesto.read_text(encoding="utf-8").splitlines()
    except OSError:
        return exclusoes

    for linha in linhas:
        entrada = linha.strip()
        if not entrada or entrada.startswith("#"):
            continue
        if entrada.startswith("!"):
            # Negação não é suportada. Ignorar a linha é o lado seguro: no
            # máximo hasheamos um arquivo a mais.
            logger.debug("estagnacao: negação ignorada no %s: %r",
                         _ARQUIVO_EXCLUSOES, entrada)
            continue
        if entrada.endswith("/"):
            exclusoes.diretorios.add(entrada.rstrip("/"))
        elif entrada.startswith("*."):
            exclusoes.sufixos.add(entrada[1:])
        else:
            exclusoes.nomes.add(entrada)

    return exclusoes


def hash_codigo(raiz: Path) -> str:
    """Hash do CONTEÚDO do código do coder — não de mtime.

    Percorre a raiz, ordena por caminho relativo e digere pares
    `(caminho, conteúdo)`. Ordenação e separadores explícitos tornam o
    resultado estável entre execuções e entre máquinas.

    Raiz inexistente devolve "" — dois "" seguidos comparam como iguais, que é
    exatamente a semântica desejada (nada mudou).
    """
    if not raiz.is_dir():
        return ""

    exclusoes = _carregar_exclusoes(raiz)
    digest = hashlib.sha256()

    arquivos = sorted(
        (p for p in raiz.rglob("*") if p.is_file()),
        key=lambda p: p.relative_to(raiz).as_posix(),
    )
    for arquivo in arquivos:
        relativo = arquivo.relative_to(raiz)
        if exclusoes.ignora(relativo):
            continue
        try:
            conteudo = arquivo.read_bytes()
        except OSError:
            logger.warning("estagnacao: arquivo ilegível ao hashear: %s", arquivo)
            conteudo = _SENTINELA_ILEGIVEL
        digest.update(relativo.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(conteudo)
        digest.update(b"\0")

    return digest.hexdigest()


def resumo_bloqueado(blocking_reason: str, repeticoes: int) -> str:
    """Resumo do encerramento por estagnação, no contrato que o reviewer espera.

    A PRIMEIRA linha é o marcador — é ele que preserva este texto: o builder do
    ErrorReport o reconhece e não sobrescreve o resumo.
    """
    return "\n".join([
        MARCADOR_ESTAGNACAO,
        blocking_reason or "sem blocking_reason.",
        (
            f"Encerrado por estagnação: o mesmo código e o mesmo bloqueio se "
            f"repetiram em {repeticoes} iterações consecutivas. O loop não "
            f"progride — o impedimento não está sendo resolvido por mudança de "
            f"código. NÃO é aprovação: o veredito permanece reprovado."
        ),
    ])
