"""Manifesto declarativo de execução (`run.json`) emitido pelo coder.

O harness deixou de inferir stack/entrypoint a partir dos arquivos: agora
consome um contrato explícito produzido pelo coder, o `run.json`. Este módulo
define o modelo (`RunManifest`) e o carregador/validador (`load_manifest`).

Princípio: a **coerência** entre `surface` e os campos obrigatórios é validada
aqui, na carga — o harness recebe um manifesto já garantido. Isso mantém os
estágios do harness livres de regras condicionais espalhadas.

O manifesto é agnóstico de tecnologia: descreve *comandos* (build/run/test) e a
*superfície* do produto, não uma linguagem ou framework específico. Serve tanto
para um serviço de rede quanto para uma CLI, um pipeline de dados ou uma
biblioteca.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

logger = logging.getLogger(__name__)

# Superfície de execução do produto — determina qual perfil o harness aplica.
#   service → sobe um serviço de rede e faz healthcheck (web_app, api_service)
#   command → executa um comando que roda e termina (cli, data_pipeline)
#   none    → não há serviço nem comando de topo; foco em build/testes (library…)
Surface = Literal["service", "command", "none"]

# Estratégia de isolamento. `direct` (subprocess efêmero) é o padrão por ser
# ordens de magnitude mais barato em benchmarks; `docker` é opt-in.
SandboxKind = Literal["direct", "docker"]


class ManifestError(Exception):
    """Erro ao localizar, parsear ou validar a coerência do `run.json`."""


class RunManifest(BaseModel):
    """Contrato coder→harness: como construir, executar e testar o artefato.

    Campos em inglês (nomes de contrato); descrições em português. A validação
    de coerência `surface`↔campos acontece em `_check_coherence`, garantindo que
    um manifesto inválido nunca chegue aos estágios do harness.
    """

    schema_version: str = Field(
        default="1", description="Versão do schema do manifesto (compatibilidade futura)."
    )
    surface: Surface = Field(description="Superfície de execução do produto.")
    build: list[str] = Field(
        default_factory=list,
        description="Comandos de build/preparação, executados em ordem antes do run/test.",
    )
    run: Optional[str] = Field(
        default=None,
        description="Comando principal (serviço em service; execução única em command).",
    )
    test: list[str] = Field(
        default_factory=list,
        description="Comandos que executam a suíte de testes do artefato.",
    )
    port: Optional[int] = Field(
        default=None,
        description="Porta em que o serviço escuta (obrigatório quando surface=service).",
    )
    healthcheck: Optional[str] = Field(
        default=None,
        description="Rota de healthcheck do serviço (default '/' quando surface=service).",
    )
    workdir: str = Field(
        default=".",
        description="Diretório de trabalho relativo à raiz do artefato para os comandos.",
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Variáveis de ambiente adicionais para build/run/test.",
    )
    sandbox: SandboxKind = Field(
        default="direct",
        description="Estratégia de isolamento: 'direct' (padrão) ou 'docker' (opt-in).",
    )
    acceptance_tests: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Mapa critério de aceite → testes que o comprovam. A chave é o id "
            "do critério na Task (CA-01, CA-02...); o valor, os identificadores "
            "dos testes que o cobrem, no formato com que a suíte nomeia um "
            "teste individual (em pytest, o nodeid "
            "'tests/test_x.py::test_y'). Vazio quando o coder não declarou "
            "nenhuma cobertura."
        ),
    )

    @field_validator("acceptance_tests", mode="before")
    @classmethod
    def _coerce_acceptance_tests(cls, v: Any) -> dict[str, list[str]]:
        """Aceita o que der para aproveitar; NUNCA invalida o manifesto.

        Este campo é o único do manifesto cujo conteúdo malformado não pode
        derrubar a carga, e a assimetria é deliberada: `run`/`port`/`build`
        descrevem COMO executar — sem eles não há execução, e falhar cedo é
        correto. O mapa de testes é BOOKKEEPING; recusá-lo faria o estágio 1
        (crítico) abortar a execução inteira, zerando a nota técnica do coder
        por um erro de anotação — punindo-o tecnicamente por algo que não é
        defeito do artefato.

        Só a FORMA é tratada aqui. Se as chaves são ids de critério que existem
        na Task é outra pergunta, respondida onde a Task é conhecida (ver
        `normalizar_mapa_de_testes`, em `coding_tools/criterios_aceite.py`).
        """
        if not isinstance(v, dict):
            if v not in (None, ""):
                logger.warning(
                    "run.json: 'acceptance_tests' é %s; esperado objeto. "
                    "Nenhum vínculo teste↔critério será considerado.",
                    type(v).__name__,
                )
            return {}

        normalizado: dict[str, list[str]] = {}
        for chave, valor in v.items():
            if not isinstance(chave, str):
                logger.warning(
                    "run.json: chave de 'acceptance_tests' de tipo %s ignorada.",
                    type(chave).__name__,
                )
                continue
            # Um teste só, escrito sem lista, é erro comum de LLM e não custa
            # nada absorver — mesma tolerância de `Contract._coerce_interfaces`.
            bruto = [valor] if isinstance(valor, str) else valor
            if not isinstance(bruto, list):
                logger.warning(
                    "run.json: 'acceptance_tests[%s]' é %s; esperado lista de "
                    "strings. Entrada ignorada.",
                    chave,
                    type(valor).__name__,
                )
                continue
            testes = [t.strip() for t in bruto if isinstance(t, str) and t.strip()]
            if testes:
                normalizado[chave] = testes
        return normalizado

    @model_validator(mode="after")
    def _check_coherence(self) -> "RunManifest":
        """Garante que os campos obrigatórios existem para cada superfície."""
        if self.surface == "service":
            if not self.run:
                raise ValueError("surface=service exige o campo 'run'.")
            if self.port is None:
                raise ValueError("surface=service exige o campo 'port'.")
            if self.healthcheck is None:
                # Default seguro: raiz do serviço.
                object.__setattr__(self, "healthcheck", "/")
        elif self.surface == "command":
            if not self.run:
                raise ValueError("surface=command exige o campo 'run'.")
        elif self.surface == "none":
            # Foco em build/testes; nenhum comando de topo é obrigatório. Ainda
            # assim, um manifesto totalmente vazio não descreve nada verificável.
            if not self.build and not self.test:
                raise ValueError(
                    "surface=none exige ao menos 'build' ou 'test' (nada a executar)."
                )
        return self


def load_manifest(path: Path) -> RunManifest:
    """Carrega e valida o `run.json` no caminho informado.

    Args:
        path: Caminho do arquivo `run.json`.

    Returns:
        RunManifest já validado (coerência `surface`↔campos garantida).

    Raises:
        ManifestError: se o arquivo não existe, não é JSON válido ou é incoerente.
    """
    if not path.is_file():
        raise ManifestError(f"Manifesto de execução não encontrado: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Manifesto '{path}' não é JSON válido: {exc}") from exc
    try:
        return RunManifest.model_validate(raw)
    except ValidationError as exc:
        raise ManifestError(f"Manifesto '{path}' é incoerente: {exc}") from exc
