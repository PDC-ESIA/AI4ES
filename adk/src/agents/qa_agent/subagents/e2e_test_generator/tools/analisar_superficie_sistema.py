"""Classificação conservadora da superfície do sistema alvo."""

import re

from ..schemas import (
    AnaliseSuperficie,
    EntradaE2ENormalizada,
    SuperficieContratoNegativo,
    TipoSistema,
)

_TERMOS_WEB = (
    "tela",
    "página",
    "pagina",
    "navegador",
    "browser",
    "botão",
    "botao",
    "formulário",
    "formulario",
    "galeria",
    "frontend",
    "html",
    "react",
    "vue",
    "angular",
    "upload",
)

_TERMOS_API = (
    "api",
    "endpoint",
    "rest",
    "graphql",
    "payload",
    "status code",
    "status http",
    "fastapi",
    "controller",
    "handler",
    "/api/",
)

_TERMOS_CLI = (
    "linha de comando",
    "command line",
    "argparse",
    "click cli",
    "comando no terminal",
)

_TERMOS_AGENTICOS = (
    "sistema agêntico",
    "sistema agentico",
    "llmagent",
    "agenttool",
    "tool call",
    "subagente",
    "multiagente",
)


def _encontrar_termos(texto: str, termos: tuple[str, ...]) -> list[str]:
    encontrados: list[str] = []
    for termo in termos:
        padrao = re.escape(termo)
        if termo.replace("/", "").replace(" ", "").isalnum():
            padrao = rf"(?<!\w){padrao}(?!\w)"
        if re.search(padrao, texto, flags=re.IGNORECASE):
            encontrados.append(termo)
    return encontrados


def analisar_superficie_sistema(
    entrada: EntradaE2ENormalizada,
) -> AnaliseSuperficie:
    """Classifica o sistema sem transformar sinais fracos em fatos confirmados."""

    informado = entrada.tipo_sistema_informado
    if informado is not None:
        suportado = informado in {
            TipoSistema.WEB,
            TipoSistema.API,
            TipoSistema.FULLSTACK,
        }
        return AnaliseSuperficie(
            tipo_sistema=informado,
            origem_classificacao="informado_pelo_solicitante",
            sinais_encontrados=[f"tipo_sistema={informado.value}"],
            suportado_no_p0=suportado,
            resumo=f"Sistema classificado explicitamente como {informado.value}.",
        )

    texto = "\n".join(item.conteudo for item in entrada.requisitos)
    texto += "\n" + "\n".join(item.conteudo for item in entrada.codigo_fonte)
    sinais_web = _encontrar_termos(texto, _TERMOS_WEB)
    sinais_api = _encontrar_termos(texto, _TERMOS_API)
    sinais_cli = _encontrar_termos(texto, _TERMOS_CLI)
    sinais_agenticos = _encontrar_termos(texto, _TERMOS_AGENTICOS)

    tem_web = bool(
        entrada.rotas_ou_telas
        or sinais_web
        or any(
            contrato.superficie == SuperficieContratoNegativo.WEB
            for contrato in entrada.contratos_negativos
        )
    )
    tem_api = bool(
        entrada.contratos_api
        or sinais_api
        or any(
            contrato.superficie == SuperficieContratoNegativo.API
            for contrato in entrada.contratos_negativos
        )
    )
    if entrada.base_url and not tem_api:
        tem_web = True

    sinais: list[str] = []
    if entrada.rotas_ou_telas:
        sinais.append("rotas_ou_telas fornecidas")
    if entrada.contratos_api:
        sinais.append("contratos_api fornecidos")
    if entrada.contratos_negativos:
        sinais.append("contratos_negativos explícitos fornecidos")
    if entrada.base_url:
        sinais.append("base_url fornecida")
    sinais.extend(f"termo web: {termo}" for termo in sinais_web)
    sinais.extend(f"termo API: {termo}" for termo in sinais_api)

    if tem_web and tem_api:
        tipo = TipoSistema.FULLSTACK
    elif tem_api:
        tipo = TipoSistema.API
    elif tem_web:
        tipo = TipoSistema.WEB
    elif sinais_cli:
        tipo = TipoSistema.CLI
        sinais.extend(f"termo CLI: {termo}" for termo in sinais_cli)
    elif sinais_agenticos:
        tipo = TipoSistema.AGENTICO
        sinais.extend(f"termo agêntico: {termo}" for termo in sinais_agenticos)
    else:
        tipo = TipoSistema.DESCONHECIDO

    suportado = tipo not in {TipoSistema.CLI, TipoSistema.AGENTICO}
    return AnaliseSuperficie(
        tipo_sistema=tipo,
        origem_classificacao="inferido_por_sinais_declarados",
        sinais_encontrados=list(dict.fromkeys(sinais)),
        suportado_no_p0=suportado,
        resumo=(
            f"Superfície inferida como {tipo.value} a partir de "
            f"{len(sinais)} sinal(is) declarado(s)."
        ),
    )
