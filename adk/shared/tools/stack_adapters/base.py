"""Interface dos adapters de stack + tipos compartilhados.

Um *stack adapter* encapsula tudo que é específico de uma stack (linguagem +
ferramenta de testes) e que o harness genérico não deve conhecer: quais palavras
declaradas a reivindicam (Tier 1), quais manifestos a denunciam (Tier 2) e como
localizar/rodar/parsear a suíte de testes dentro do container implantado.

Decisão de acoplamento: o adapter NÃO importa os schemas do executor
(`StageStatus`/`StageResult`). Importá-los dispararia
`src.agents.executor.__init__` → agente → orchestrator → `harness_execucao`, um
ciclo (o harness já importa os schemas tardiamente, no fim do arquivo, por isso).
Em vez disso o adapter devolve um `ResultadoTestes` no seu próprio vocabulário, e
o harness — que já tem os schemas — faz o mapeamento para `StageResult`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Optional


# Primitiva genérica que o harness injeta no adapter: roda um comando shell no
# container e devolve (exit_code, stdout, stderr). Fica no harness
# (`_exec_no_container`) e é passada por parâmetro para não recriar o ciclo de
# import — qualquer adapter usa a mesma primitiva para rodar seu comando.
ExecNoContainer = Callable[[Any, str], "tuple[Optional[int], str, str]"]


@dataclass(frozen=True)
class FileMarker:
    """Manifesto que denuncia uma stack pela presença de um arquivo (Tier 2).

    `nome`: caminho relativo ao workspace do coder (ex.: "requirements.txt"),
        checado por `.is_file()` — fato binário, determinístico, sem LLM.
    `content_predicate`: hook OPCIONAL (Q4) para, quando a Fatia D chegar,
        exigir também que o conteúdo satisfaça uma condição além da presença —
        ex.: não só "existe package.json" mas "e tem express nas dependências".
        NÃO é usado nesta fatia; existe só para que markers com sniffing possam
        ser adicionados depois SEM redesenhar os adapters que dependem apenas de
        presença (como o Python). Quando None, só a presença conta.
    """

    nome: str
    content_predicate: Optional[Callable[[Path], bool]] = None

    def presente_em(self, coder_dir: Path) -> bool:
        alvo = coder_dir / self.nome
        if not alvo.is_file():
            return False
        if self.content_predicate is None:
            return True
        # Um predicado que estoure não pode derrubar a resolução de stack: um
        # marker que falha em avaliar conteúdo simplesmente não casa.
        try:
            return bool(self.content_predicate(alvo))
        except Exception:
            return False


@dataclass
class ResultadoTestes:
    """Resultado da execução de testes, no vocabulário do adapter.

    `status` usa os MESMOS valores textuais de `StageStatus`
    ("sucesso"/"falha"/"erro"/"pulado"), para o harness mapear com
    `StageStatus(res.status)` sem que o adapter importe os schemas do executor.
    `error_code`/`summary`/`evidence` alimentam diretamente o `StageResult` do
    Estágio 6 — o mesmo contrato que `_estagio_testes` produzia antes.
    """

    status: str
    summary: str
    error_code: Optional[str] = None
    evidence: dict = field(default_factory=dict)


class StackAdapter(ABC):
    """Contrato de um adapter de stack.

    As subclasses declaram `tech_stack_keywords` e `file_markers` (dados para os
    Tiers 1 e 2, que o resolver consome sem lógica central por-stack) e
    implementam `executar_testes` (o Estágio 6 específico da ferramenta).
    """

    #: Nome curto do adapter, para evidência/log (ex.: "python").
    nome: str = ""
    #: Palavras que reivindicam esta stack quando aparecem na tech_stack
    #: declarada (Tier 1), casadas case-insensitive.
    tech_stack_keywords: tuple[str, ...] = ()
    #: Manifestos cuja presença no workspace denuncia esta stack (Tier 2).
    file_markers: tuple[FileMarker, ...] = ()

    def keyword_casada(self, tech_stack: Iterable[str]) -> Optional[str]:
        """Tier 1: primeira `tech_stack_keyword` que aparece na stack declarada.

        Casamento case-insensitive por substring — "python" casa "Python" e
        "Python 3.12". Keywords devem ser específicas o bastante para não casar
        por acaso dentro de outra palavra (orientação para novos adapters).
        Devolve a keyword que casou (para a evidência), ou None.
        """
        entradas = [str(e).lower() for e in (tech_stack or [])]
        for kw in self.tech_stack_keywords:
            alvo = kw.lower()
            if any(alvo in entrada for entrada in entradas):
                return kw
        return None

    def manifesto_encontrado(self, coder_dir: Path) -> Optional[str]:
        """Tier 2: nome do primeiro `file_marker` presente no `coder_dir`.

        Devolve o nome do manifesto que casou (para a evidência), ou None.
        """
        for marker in self.file_markers:
            if marker.presente_em(coder_dir):
                return marker.nome
        return None

    @abstractmethod
    def executar_testes(
        self, exec_no_container: ExecNoContainer, container: Any, coder_dir: Path
    ) -> ResultadoTestes:
        """Executa a suíte de testes desta stack DENTRO do container implantado.

        `exec_no_container`: primitiva injetada pelo harness para rodar comandos
            no container (workdir já é o do artefato implantado).
        `container`: o container Docker em execução.
        `coder_dir`: workspace do coder no host, para localizar a suíte.

        Coleta apenas evidência — nenhum veredito. Devolve `ResultadoTestes`.
        """
        raise NotImplementedError
