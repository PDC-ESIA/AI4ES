"""Perfis de execução plugáveis, selecionados pela superfície do produto.

Cada `ExecutionProfile` descreve, de forma declarativa, COMO o harness deve se
comportar para uma dada superfície (`service`/`command`/`none`) — quais estágios
são críticos, se o estágio 4 sobe um serviço e faz healthcheck, e se o estágio 7
deriva checagens HTTP. O harness (executor fino) consulta o perfil em vez de
embutir `if product_type == ...` espalhados.

Padrão espelhado de `shared/review/capability.py`: um `REGISTRY` de perfis e um
seletor. Estender o sistema para uma nova superfície é adicionar um perfil ao
registry — sem tocar nos estágios.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from shared.execution.manifest import Surface

# Nomes canônicos dos estágios do harness (espelham StageName em
# harness_schemas.py). Mantidos como strings para desacoplar este módulo do
# schema do harness — o harness faz a correspondência.
_STAGE_PREPARACAO = "preparacao_ambiente"
_STAGE_IMPLANTACAO = "implantacao_artefato"
_STAGE_INICIALIZACAO = "inicializacao_aplicacao"


@dataclass(frozen=True)
class ExecutionProfile:
    """Comportamento declarativo do harness para uma superfície de produto.

    Attributes:
        name: Identificador curto do perfil (S/C/B).
        surface: Superfície de execução à qual o perfil se aplica.
        starts_service: Se o estágio 4 sobe um serviço e faz healthcheck.
        validates_http: Se o estágio 7 deriva checagens HTTP dos critérios.
        critical_stages: Estágios cuja falha aborta os dependentes.
    """

    name: str
    surface: Surface
    starts_service: bool
    validates_http: bool
    critical_stages: tuple[str, ...] = field(default_factory=tuple)


# Perfil S — serviço de rede: sobe o processo, faz healthcheck HTTP e deriva
# checagens HTTP dos critérios. A inicialização é crítica (sem serviço no ar,
# nada a validar).
_PROFILE_SERVICE = ExecutionProfile(
    name="S",
    surface="service",
    starts_service=True,
    validates_http=True,
    critical_stages=(_STAGE_PREPARACAO, _STAGE_IMPLANTACAO, _STAGE_INICIALIZACAO),
)

# Perfil C — comando: o `run` executa e termina; o exit-code é o sinal. Não há
# serviço a subir (estágio 4 é pulado) nem checagem HTTP no estágio 7.
_PROFILE_COMMAND = ExecutionProfile(
    name="C",
    surface="command",
    starts_service=False,
    validates_http=False,
    critical_stages=(_STAGE_PREPARACAO, _STAGE_IMPLANTACAO),
)

# Perfil B — sem superfície de topo (library, etc.): foco em build + testes.
# Sem serviço e sem HTTP; a implantação (build) permanece crítica.
_PROFILE_NONE = ExecutionProfile(
    name="B",
    surface="none",
    starts_service=False,
    validates_http=False,
    critical_stages=(_STAGE_PREPARACAO, _STAGE_IMPLANTACAO),
)

# Registry plugável: superfície → perfil. Adicionar uma superfície é adicionar
# uma entrada aqui.
REGISTRY: dict[Surface, ExecutionProfile] = {
    "service": _PROFILE_SERVICE,
    "command": _PROFILE_COMMAND,
    "none": _PROFILE_NONE,
}


# Mapeamento product_type → superfície de execução. O vocabulário de
# product_type é definido pelo context_engineer; superfícies desconhecidas
# degradam para 'none' (sem serviço), a escolha mais conservadora.
_SURFACE_BY_PRODUCT_TYPE: dict[str, Surface] = {
    "web_app": "service",
    "api_service": "service",
    "cli": "command",
    "data_pipeline": "command",
    "library": "none",
    "desktop_app": "none",
    "mobile_app": "none",
    "outro": "none",
    "a definir": "none",
}


def surface_for_product_type(product_type: str) -> Surface:
    """Deriva a superfície de execução a partir do product_type.

    product_type desconhecido/ausente degrada para 'none' (mais conservador:
    sem subir serviço nem exigir HTTP).
    """
    if not product_type:
        return "none"
    return _SURFACE_BY_PRODUCT_TYPE.get(product_type.strip().lower(), "none")


def select_profile(surface: str) -> ExecutionProfile:
    """Seleciona o perfil de execução para a superfície informada.

    Raises:
        ValueError: se a superfície não estiver registrada.
    """
    try:
        return REGISTRY[surface]  # type: ignore[index]
    except KeyError:
        raise ValueError(f"Superfície de execução desconhecida: '{surface}'.") from None
