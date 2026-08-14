"""Persistência do banco de memória — JSONL fora do repositório.

## Por que fora do repositório

Esta é a resposta direta à **crítica 1** que recusou o PR da camada de
feedforward: *"não há separação real de conhecimento e código"*. Lá a base de
conhecimento vivia no mesmo repositório, entrava no mesmo PR e viajava na mesma
imagem Docker — evoluir o conhecimento exigia um ciclo de deploy.

O `LEVANTAMENTO_TRABALHOS_MEMORIA_EXPERIENCIA.md` (§2a) mostra que somos o caso
fora da curva: em praticamente todo o campo — EvoLib, ReasoningBank, ArcMemo,
Memp, Voyager — a biblioteca é **estado de runtime**. As únicas exceções, ReGAL
e Leroy, são exceções por serem *library learning* clássico, onde a biblioteca
literalmente **é** código-fonte.

Aqui o banco vive em `AI4ES_MEMORY_DIR` (default `~/.ai4es/memory/`), que:

- não é o `workspace_output/`, então **sobrevive ao `shutil.rmtree` do
  `init_workspace()`** — que é a razão técnica de o agente nunca ter evoluído
  entre runs;
- não é o repositório, então não entra em PR, em review nem na imagem;
- é endereçável por env var, então trocar o banco (ou zerá-lo para um braço de
  controle A/B) não exige tocar em código.

O formato — um JSON por linha — é o mesmo do ReasoningBank
(`memory/memory_management.py`, `./memories/embeddings.jsonl`).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Iterable, Optional

from .schemas import MemoryItem, MemoryStatus

logger = logging.getLogger(__name__)

_ENV_MEMORY_DIR = "AI4ES_MEMORY_DIR"
_DEFAULT_MEMORY_DIR = "~/.ai4es/memory"
_BANK_FILENAME = "bank.jsonl"


def get_memory_dir() -> Path:
    """Resolve o diretório do banco, expandindo `~` e caminhos relativos.

    Espelha a semântica de `shared.workspace.get_workspace_root()` para não
    introduzir uma segunda convenção de resolução de caminho no projeto.
    """
    raw = os.environ.get(_ENV_MEMORY_DIR, _DEFAULT_MEMORY_DIR)
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def memoria_habilitada() -> bool:
    """Kill switch da camada inteira (`AI4ES_MEMORY_ENABLED`, default ligado).

    Com `0`/`false`/`no`, tanto a injeção no coder quanto a escrita do
    `memory_writer` viram no-op e o pipeline se comporta exatamente como em
    `develop` — o que também serve de braço de controle para o A/B.
    """
    return os.environ.get("AI4ES_MEMORY_ENABLED", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


class MemoryStore:
    """Banco append-only de `MemoryItem`, em JSONL.

    Deduplicação por `id` (hash do título normalizado). É deliberadamente o
    caso degenerado da consolidação: consolidar semanticamente exigiria
    embeddings no caminho de escrita, e o levantamento (§7, item 7) trata isso
    como evolução posterior, não como requisito desta PoC. O que a PoC precisa
    garantir é que rodar duas vezes não duplique a mesma lição.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path is not None else get_memory_dir() / _BANK_FILENAME

    # -- leitura -----------------------------------------------------------

    def load(self) -> list[MemoryItem]:
        """Carrega todos os itens. Linha corrompida é ignorada, não fatal.

        Um banco parcialmente ilegível não pode derrubar o pipeline: a memória
        é um acessório do prompt, não um pré-requisito de execução.
        """
        if not self.path.is_file():
            return []

        itens: list[MemoryItem] = []
        for n, linha in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            linha = linha.strip()
            if not linha:
                continue
            try:
                itens.append(MemoryItem.model_validate_json(linha))
            except Exception:
                logger.warning(
                    "[MEMORY] Linha %d de %s ilegível; ignorada.", n, self.path
                )
        return itens

    def promovidos(self) -> list[MemoryItem]:
        """Só os itens aprovados na curadoria — os únicos que vão ao prompt."""
        return [i for i in self.load() if i.status == MemoryStatus.PROMOVIDO]

    # -- escrita -----------------------------------------------------------

    def append(self, itens: Iterable[MemoryItem]) -> list[MemoryItem]:
        """Acrescenta os itens ainda não presentes. Devolve os efetivamente novos.

        Reescreve o arquivo inteiro de forma atômica em vez de fazer append
        direto: o banco é pequeno (dezenas de itens) e a reescrita mantém o
        arquivo sempre válido, mesmo se o processo morrer no meio — o pipeline
        já morre de formas suficientes sem que a memória contribua.
        """
        existentes = self.load()
        conhecidos = {i.id for i in existentes}

        # O `conhecidos.add` dentro do laço também deduplica DENTRO do lote:
        # uma mesma trajetória pode render dois itens com o mesmo título.
        novos: list[MemoryItem] = []
        for item in itens:
            if item.id in conhecidos:
                continue
            conhecidos.add(item.id)
            novos.append(item)

        if not novos:
            return []

        self._escrever(existentes + novos)
        logger.info("[MEMORY] %d item(ns) novo(s) gravado(s) em %s", len(novos), self.path)
        return novos

    def registrar_uso(self, ids: Iterable[str]) -> None:
        """Incrementa `times_retrieved` dos itens injetados num prompt.

        É o contador de utilidade bruta. Não pondera nada hoje — mas é o dado
        mínimo sem o qual não dá para, mais adiante, rankear por utilidade
        medida em vez de por similaridade (levantamento, §7 "Não fazer").
        """
        alvos = set(ids)
        if not alvos:
            return
        itens = self.load()
        for item in itens:
            if item.id in alvos:
                item.times_retrieved += 1
        self._escrever(itens)

    def _escrever(self, itens: list[MemoryItem]) -> None:
        """Serializa o banco inteiro atomicamente (tmp + os.replace)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conteudo = "".join(
            json.dumps(i.model_dump(mode="json"), ensure_ascii=False) + "\n"
            for i in itens
        )
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(conteudo)
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    # -- diagnóstico -------------------------------------------------------

    def stats(self) -> dict[str, int]:
        """Contagem por status — usado no log do `memory_writer` e na demo."""
        itens = self.load()
        return {
            "total": len(itens),
            **{s.value: sum(1 for i in itens if i.status == s) for s in MemoryStatus},
        }
