"""Mapeamento determinístico de requisitos para cenários E2E."""

import re
from typing import Iterable

from ..schemas import (
    AcaoAutomacao,
    AnaliseSuperficie,
    CategoriaCenario,
    CenarioE2E,
    ContratoNegativoE2E,
    EntradaE2ENormalizada,
    PassoAutomacao,
    RequisitoNormalizado,
    SuperficieContratoNegativo,
    TipoSistema,
    ValidacaoContratoE2E,
)
from .validar_contrato_e2e import erros_contrato_negativo


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
        externa = contrato.get("externa", contrato.get("external"))
        tem_identidade_servico = any(
            contrato.get(chave)
            for chave in ("servico", "service", "nome_servico", "service_name")
        )
        if externa is not True and not tem_identidade_servico:
            continue
        valor = None
        for chave in (
            "servico",
            "service",
            "nome_servico",
            "service_name",
            "nome",
            "name",
            "endpoint",
            "url",
        ):
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


def _requisitos_timeout_comportamental(
    requisitos: list[RequisitoNormalizado],
) -> list[RequisitoNormalizado]:
    """Ignora timeouts que configuram o runner, não o comportamento do SUT."""

    configuracoes = (
        r"timeout\s+por\s+teste",
        r"timeout\s+total",
        r"timeout\s+global",
        r"tempo\s+limite\s+(?:da|de)\s+execu[cç][aã]o",
    )
    encontrados: list[RequisitoNormalizado] = []
    for requisito in requisitos:
        texto = requisito.conteudo.lower()
        for padrao in configuracoes:
            texto = re.sub(
                rf"{padrao}[^.;\n]*",
                "",
                texto,
                flags=re.IGNORECASE,
            )
        if any(
            termo in texto
            for termo in (
                "timeout",
                "latência",
                "latencia",
                "lento",
                "demora",
                "tempo limite",
            )
        ):
            encontrados.append(requisito)
    return encontrados


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
        elif not any(alvo.passos_automacao for alvo in entrada.rotas_ou_telas):
            lacunas.append(
                "Os passos estruturados do fluxo feliz não foram informados."
            )
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
    lacunas.append(
        "A automação de falha externa ainda não possui passos estruturados suportados."
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
        pronto_para_automacao=False,
    )


def _cenario_timeout(
    indice: int,
    entrada: EntradaE2ENormalizada,
    validacao: ValidacaoContratoE2E,
) -> CenarioE2E:
    dependencias = _dependencias_declaradas(entrada)
    requisitos = _requisitos_timeout_comportamental(entrada.requisitos)
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
    lacunas.append(
        "A automação de latência ainda não possui passos estruturados suportados."
    )
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
        pronto_para_automacao=False,
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
    lacunas.append(
        "A automação de dados inválidos ainda não possui passos estruturados suportados."
    )
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
        pronto_para_automacao=False,
    )


def _cenario_negativo_explicito(
    indice: int,
    contrato: ContratoNegativoE2E,
    entrada: EntradaE2ENormalizada,
    analise: AnaliseSuperficie,
    validacao: ValidacaoContratoE2E,
) -> CenarioE2E:
    """Materializa somente fatos declarados no contrato negativo."""

    lacunas = erros_contrato_negativo(entrada, analise, contrato)
    passos: list[str] = []
    assercoes: list[str] = []
    mocks: list[str] = []
    dependencias = [contrato.dependencia] if contrato.dependencia else []
    dados = _dados_declarados(entrada)
    if contrato.dados_teste:
        dados.append(
            "Contrato negativo com campos: "
            + ", ".join(sorted(contrato.dados_teste))
            + "."
        )

    if contrato.superficie == SuperficieContratoNegativo.WEB:
        if contrato.mock_rede is not None:
            mock = contrato.mock_rede
            descricao = (
                f"Mock {mock.metodo} {mock.rota or 'sem rota'} "
                f"com status {mock.status_simulado}"
            )
            if mock.atraso_ms:
                descricao += f" e atraso de {mock.atraso_ms} ms"
            mocks.append(descricao + ".")
            passos.append("Instalar o mock de rede explicitamente declarado.")
        passos.append(f"Acessar a rota declarada: {contrato.rota}.")
        passos.extend(
            _descrever_passo_automacao(passo)
            for passo in contrato.passos_automacao
        )
        assercoes.extend(
            _descrever_passo_automacao(passo)
            for passo in contrato.passos_automacao
            if passo.acao
            in {
                AcaoAutomacao.VERIFICAR_VISIVEL,
                AcaoAutomacao.VERIFICAR_TEXTO,
                AcaoAutomacao.VERIFICAR_URL,
            }
        )
    else:
        passos.append(
            f"Enviar {contrato.metodo} para a rota declarada {contrato.rota}."
        )
        if contrato.categoria == CategoriaCenario.TIMEOUT_LATENCIA:
            assercoes.append(
                f"A chamada excede o timeout explícito de {contrato.timeout_ms} ms."
            )
        elif contrato.status_esperado is not None:
            assercoes.append(
                f"A resposta possui status HTTP {contrato.status_esperado}."
            )
        if "resposta_esperada" in contrato.model_fields_set:
            assercoes.append("O corpo JSON corresponde à resposta declarada.")

    objetivos = {
        CategoriaCenario.FALHA_DEPENDENCIA_EXTERNA: (
            "Validar a resposta controlada à falha explícita de uma dependência."
        ),
        CategoriaCenario.TIMEOUT_LATENCIA: (
            "Validar o comportamento temporal descrito no contrato explícito."
        ),
        CategoriaCenario.DADOS_MALFORMADOS: (
            "Validar a rejeição dos dados inválidos declarados no contrato."
        ),
    }
    return CenarioE2E(
        id=f"E2E-{indice:03d}",
        nome=contrato.nome or f"Cenário negativo {contrato.id}",
        categoria=contrato.categoria,
        objetivo=objetivos[contrato.categoria],
        requisitos_origem=[item.id for item in entrada.requisitos],
        precondicoes=_precondicoes(entrada),
        passos=passos,
        dados_teste=_unicos(dados),
        assercoes=_unicos(assercoes),
        dependencias=_unicos(dependencias),
        mocks_stubs=_unicos(mocks),
        lacunas=lacunas,
        pronto_para_automacao=validacao.pode_gerar_codigo and not lacunas,
        contrato_negativo_id=contrato.id,
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

    geradores_padrao = {
        CategoriaCenario.FALHA_DEPENDENCIA_EXTERNA: _cenario_falha_externa,
        CategoriaCenario.TIMEOUT_LATENCIA: _cenario_timeout,
        CategoriaCenario.DADOS_MALFORMADOS: _cenario_dados_malformados,
    }
    for categoria, gerador_padrao in geradores_padrao.items():
        contratos = [
            contrato
            for contrato in entrada.contratos_negativos
            if contrato.categoria == categoria
        ]
        if not contratos:
            cenarios.append(gerador_padrao(len(cenarios) + 1, entrada, validacao))
            continue
        for contrato in contratos:
            cenarios.append(
                _cenario_negativo_explicito(
                    len(cenarios) + 1,
                    contrato,
                    entrada,
                    analise,
                    validacao,
                )
            )
    return cenarios
