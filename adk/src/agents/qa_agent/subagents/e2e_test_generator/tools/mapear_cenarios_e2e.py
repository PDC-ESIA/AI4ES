"""Mapeamento determinístico de requisitos para cenários E2E."""

from typing import Iterable

from ..schemas import (
    AnaliseSuperficie,
    CategoriaCenario,
    CenarioE2E,
    EntradaE2ENormalizada,
    PassoAutomacao,
    RequisitoNormalizado,
    TipoSistema,
    ValidacaoContratoE2E,
)


def _unicos(itens: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(item for item in itens if item))


def _resumir(texto: str, limite: int = 90) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def _precondicoes(entrada: EntradaE2ENormalizada) -> list[str]:
    itens: list[str] = []
    if entrada.base_url:
        itens.append(f"Sistema alvo acessível em {entrada.base_url}.")
    itens.extend(f"Perfil disponível: {perfil}." for perfil in entrada.perfis_usuario)
    itens.extend(
        f"Restrição respeitada: {restricao}." for restricao in entrada.restricoes
    )
    return _unicos(itens)


def _dados_declarados(entrada: EntradaE2ENormalizada) -> list[str]:
    dados: list[str] = []
    for conjunto in entrada.dados_teste:
        chaves = sorted(str(chave) for chave in conjunto)
        if chaves:
            dados.append("Conjunto informado com campos: " + ", ".join(chaves) + ".")
    return _unicos(dados)


def _dependencias_declaradas(entrada: EntradaE2ENormalizada) -> list[str]:
    dependencias: list[str] = []
    for indice, contrato in enumerate(entrada.contratos_api, start=1):
        valor = None
        for chave in ("servico", "service", "nome", "name", "endpoint", "url", "rota"):
            if contrato.get(chave):
                valor = str(contrato[chave]).strip()
                break
        if not valor and contrato.get("descricao"):
            valor = str(contrato["descricao"]).strip()
        dependencias.append(valor or f"Contrato API {indice}")
    return _unicos(dependencias)


def _requisitos_com_termos(
    requisitos: list[RequisitoNormalizado],
    termos: tuple[str, ...],
) -> list[RequisitoNormalizado]:
    return [
        requisito
        for requisito in requisitos
        if any(termo in requisito.conteudo.lower() for termo in termos)
    ]


def _assercoes_de_requisitos(
    requisitos: list[RequisitoNormalizado],
) -> list[str]:
    return [
        f"Resultado declarado em {item.id}: {_resumir(item.conteudo, 180)}"
        for item in requisitos
    ]


def _descrever_passo_automacao(passo: PassoAutomacao) -> str:
    partes = [f"Executar a ação estruturada '{passo.acao.value}'"]
    if passo.localizador:
        partes.append(
            f"no localizador {passo.localizador.tipo.value} '{passo.localizador.valor}'"
        )
    if passo.chave_dado:
        partes.append(f"usando o dado de teste '{passo.chave_dado}'")
    elif passo.valor is not None:
        partes.append("com o valor declarado")
    return " ".join(partes) + "."


def _cenario_fluxo_feliz(
    indice: int,
    requisito: RequisitoNormalizado,
    entrada: EntradaE2ENormalizada,
    analise: AnaliseSuperficie,
    validacao: ValidacaoContratoE2E,
) -> CenarioE2E:
    passos: list[str] = []
    for alvo in entrada.rotas_ou_telas:
        destino = alvo.rota or alvo.nome
        passos.append(f"Acessar a rota ou tela declarada: {destino}.")
        passos.extend(f"Executar a ação declarada: {acao}." for acao in alvo.acoes)
        passos.extend(
            _descrever_passo_automacao(passo) for passo in alvo.passos_automacao
        )
    passos.append(f"Exercitar o comportamento descrito pelo requisito {requisito.id}.")

    lacunas: list[str] = []
    if analise.tipo_sistema in {TipoSistema.WEB, TipoSistema.FULLSTACK}:
        if not entrada.rotas_ou_telas:
            lacunas.append("A rota ou tela inicial do fluxo não foi informada.")
    if analise.tipo_sistema in {TipoSistema.API, TipoSistema.FULLSTACK}:
        if not entrada.contratos_api:
            lacunas.append("O contrato API participante do fluxo não foi informado.")

    assercoes = [
        f"O comportamento observável atende ao requisito {requisito.id}: "
        f"{_resumir(requisito.conteudo, 180)}"
    ]
    return CenarioE2E(
        id=f"E2E-{indice:03d}",
        nome=f"Fluxo feliz de {requisito.id}: {_resumir(requisito.conteudo)}",
        categoria=CategoriaCenario.FLUXO_FELIZ,
        objetivo=f"Validar o comportamento principal declarado em {requisito.id}.",
        requisitos_origem=[requisito.id],
        precondicoes=_precondicoes(entrada),
        passos=passos,
        dados_teste=_dados_declarados(entrada),
        assercoes=assercoes,
        dependencias=_dependencias_declaradas(entrada),
        lacunas=lacunas,
        pronto_para_automacao=(
            validacao.pode_gerar_codigo and not lacunas and bool(assercoes)
        ),
    )


def _cenario_falha_externa(
    indice: int,
    entrada: EntradaE2ENormalizada,
    validacao: ValidacaoContratoE2E,
) -> CenarioE2E:
    dependencias = _dependencias_declaradas(entrada)
    requisitos = _requisitos_com_termos(
        entrada.requisitos,
        ("falha", "erro", "indispon", "fallback", "rejeit"),
    )
    lacunas: list[str] = []
    passos: list[str] = []
    mocks: list[str] = []
    if dependencias:
        passos.append(f"Simular indisponibilidade de {dependencias[0]}.")
        mocks.append(f"Stub de indisponibilidade para {dependencias[0]}.")
    else:
        lacunas.append("Nenhuma dependência externa foi declarada.")
    assercoes = _assercoes_de_requisitos(requisitos)
    if not assercoes:
        lacunas.append(
            "O comportamento esperado quando a dependência falha não foi declarado."
        )
    return CenarioE2E(
        id=f"E2E-{indice:03d}",
        nome="Falha controlada de dependência externa",
        categoria=CategoriaCenario.FALHA_DEPENDENCIA_EXTERNA,
        objetivo="Validar o comportamento declarado diante de uma dependência indisponível.",
        requisitos_origem=[item.id for item in requisitos],
        precondicoes=_precondicoes(entrada),
        passos=passos,
        dados_teste=_dados_declarados(entrada),
        assercoes=assercoes,
        dependencias=dependencias,
        mocks_stubs=mocks,
        lacunas=lacunas,
        pronto_para_automacao=(
            validacao.pode_gerar_codigo and not lacunas and bool(assercoes)
        ),
    )


def _cenario_timeout(
    indice: int,
    entrada: EntradaE2ENormalizada,
    validacao: ValidacaoContratoE2E,
) -> CenarioE2E:
    dependencias = _dependencias_declaradas(entrada)
    requisitos = _requisitos_com_termos(
        entrada.requisitos,
        ("timeout", "latência", "latencia", "lento", "demora", "tempo limite"),
    )
    lacunas: list[str] = []
    passos: list[str] = []
    mocks: list[str] = []
    if dependencias:
        passos.append(f"Introduzir atraso controlado na resposta de {dependencias[0]}.")
        mocks.append(f"Stub de latência para {dependencias[0]}.")
    else:
        lacunas.append(
            "O componente em que a latência deve ser simulada não foi declarado."
        )
    assercoes = _assercoes_de_requisitos(requisitos)
    if not assercoes:
        lacunas.append("O limite de tempo e a resposta esperada não foram declarados.")
    return CenarioE2E(
        id=f"E2E-{indice:03d}",
        nome="Latência ou timeout no fluxo E2E",
        categoria=CategoriaCenario.TIMEOUT_LATENCIA,
        objetivo="Validar o comportamento temporal explicitamente definido nos requisitos.",
        requisitos_origem=[item.id for item in requisitos],
        precondicoes=_precondicoes(entrada),
        passos=passos,
        dados_teste=_dados_declarados(entrada),
        assercoes=assercoes,
        dependencias=dependencias,
        mocks_stubs=mocks,
        lacunas=lacunas,
        pronto_para_automacao=(
            validacao.pode_gerar_codigo and not lacunas and bool(assercoes)
        ),
    )


def _campos_de_entrada(entrada: EntradaE2ENormalizada) -> list[str]:
    campos: list[str] = []
    for conjunto in entrada.dados_teste:
        campos.extend(str(chave) for chave in conjunto)
    for contrato in entrada.contratos_api:
        for chave in ("payload", "body", "request", "dados", "data"):
            valor = contrato.get(chave)
            if isinstance(valor, dict):
                campos.extend(str(campo) for campo in valor)
    return _unicos(campos)


def _cenario_dados_malformados(
    indice: int,
    entrada: EntradaE2ENormalizada,
    validacao: ValidacaoContratoE2E,
) -> CenarioE2E:
    campos = _campos_de_entrada(entrada)
    requisitos = _requisitos_com_termos(
        entrada.requisitos,
        ("inválid", "invalid", "malform", "obrigatório", "obrigatorio", "ausente"),
    )
    lacunas: list[str] = []
    passos: list[str] = []
    if campos:
        passos.append(
            "Enviar dados inválidos somente nos campos declarados: "
            + ", ".join(campos)
            + "."
        )
    else:
        lacunas.append("Os campos e tipos da massa de teste não foram declarados.")
    assercoes = _assercoes_de_requisitos(requisitos)
    if not assercoes:
        lacunas.append("A resposta esperada para dados inválidos não foi declarada.")
    return CenarioE2E(
        id=f"E2E-{indice:03d}",
        nome="Rejeição de dados malformados",
        categoria=CategoriaCenario.DADOS_MALFORMADOS,
        objetivo="Validar as regras declaradas para entradas inválidas ou incompletas.",
        requisitos_origem=[item.id for item in requisitos],
        precondicoes=_precondicoes(entrada),
        passos=passos,
        dados_teste=_dados_declarados(entrada),
        assercoes=assercoes,
        dependencias=_dependencias_declaradas(entrada),
        lacunas=lacunas,
        pronto_para_automacao=(
            validacao.pode_gerar_codigo and not lacunas and bool(assercoes)
        ),
    )


def mapear_cenarios_e2e(
    entrada: EntradaE2ENormalizada,
    analise: AnaliseSuperficie,
    validacao: ValidacaoContratoE2E,
) -> list[CenarioE2E]:
    """Gera fluxos felizes rastreáveis e os três grupos de risco do P0."""

    if not validacao.pode_gerar_plano:
        return []

    cenarios: list[CenarioE2E] = []
    for requisito in entrada.requisitos:
        cenarios.append(
            _cenario_fluxo_feliz(
                len(cenarios) + 1,
                requisito,
                entrada,
                analise,
                validacao,
            )
        )

    cenarios.append(_cenario_falha_externa(len(cenarios) + 1, entrada, validacao))
    cenarios.append(_cenario_timeout(len(cenarios) + 1, entrada, validacao))
    cenarios.append(_cenario_dados_malformados(len(cenarios) + 1, entrada, validacao))
    return cenarios
