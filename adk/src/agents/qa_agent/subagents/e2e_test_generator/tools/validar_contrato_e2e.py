"""Validação de suficiência do contrato E2E.

Os bloqueios distinguem o que impede o plano, o código e a execução. Código
Playwright só é liberado para jornadas web com passos estruturados.
"""

from urllib.parse import urlparse

from ..schemas import (
    AcaoAutomacao,
    AnaliseSuperficie,
    BloqueioE2E,
    CategoriaBloqueio,
    EntradaE2ENormalizada,
    NivelConfianca,
    TipoSistema,
    ValidacaoContratoE2E,
)

_ACOES_COM_LOCALIZADOR = {
    AcaoAutomacao.PREENCHER,
    AcaoAutomacao.CLICAR,
    AcaoAutomacao.MARCAR,
    AcaoAutomacao.DESMARCAR,
    AcaoAutomacao.SELECIONAR,
    AcaoAutomacao.PRESSIONAR,
    AcaoAutomacao.VERIFICAR_VISIVEL,
    AcaoAutomacao.VERIFICAR_TEXTO,
}

_ACOES_COM_VALOR = {
    AcaoAutomacao.PREENCHER,
    AcaoAutomacao.SELECIONAR,
    AcaoAutomacao.PRESSIONAR,
    AcaoAutomacao.VERIFICAR_URL,
}

_ACOES_ASSERCAO = {
    AcaoAutomacao.VERIFICAR_VISIVEL,
    AcaoAutomacao.VERIFICAR_TEXTO,
    AcaoAutomacao.VERIFICAR_URL,
}

_PERFIS_COMANDO_PLAYWRIGHT = {
    "playwright test",
    "npx playwright test",
    "pnpm exec playwright test",
    "npm run e2e:test",
}


def _url_valida(url: str | None) -> bool:
    if not url:
        return False
    resultado = urlparse(url)
    return resultado.scheme in {"http", "https"} and bool(resultado.netloc)


def _contrato_possui_massa(entrada: EntradaE2ENormalizada) -> bool:
    if entrada.dados_teste:
        return True
    chaves_massa = {"payload", "body", "request", "dados", "data", "params"}
    return any(
        chaves_massa.intersection(contrato) for contrato in entrada.contratos_api
    )


def _chaves_dados(entrada: EntradaE2ENormalizada) -> set[str]:
    return {str(chave) for conjunto in entrada.dados_teste for chave in conjunto}


def _erros_passos_automacao(entrada: EntradaE2ENormalizada) -> list[str]:
    erros: list[str] = []
    chaves_disponiveis = _chaves_dados(entrada)
    for alvo in entrada.rotas_ou_telas:
        erros.extend(f"{alvo.nome}: {erro}" for erro in alvo.erros_automacao)
        if not alvo.passos_automacao:
            erros.append(f"{alvo.nome}: passos de automação ausentes.")
        elif not any(passo.acao in _ACOES_ASSERCAO for passo in alvo.passos_automacao):
            erros.append(f"{alvo.nome}: passo de verificação ausente.")
        if not alvo.rota:
            erros.append(f"{alvo.nome}: rota ausente.")
        elif not (alvo.rota.startswith("/") or _url_valida(alvo.rota)):
            erros.append(f"{alvo.nome}: rota deve ser relativa ou HTTP(S).")

        for indice, passo in enumerate(alvo.passos_automacao, start=1):
            prefixo = f"{alvo.nome}, passo {indice}"
            if passo.acao in _ACOES_COM_LOCALIZADOR and passo.localizador is None:
                erros.append(f"{prefixo}: localizador semântico ausente.")
            if passo.acao in _ACOES_COM_VALOR and (
                passo.valor is None and not passo.chave_dado
            ):
                erros.append(f"{prefixo}: valor ou chave_dado ausente.")
            if passo.chave_dado and passo.chave_dado not in chaves_disponiveis:
                erros.append(
                    f"{prefixo}: chave_dado '{passo.chave_dado}' não existe em dados_teste."
                )
            if (
                passo.acao == AcaoAutomacao.VERIFICAR_TEXTO
                and passo.localizador is not None
                and passo.localizador.tipo.value != "text"
                and passo.valor is None
                and not passo.chave_dado
            ):
                erros.append(
                    f"{prefixo}: verificar_texto requer texto esperado em valor/chave_dado."
                )
    return erros


def _calcular_confianca(
    entrada: EntradaE2ENormalizada,
    analise: AnaliseSuperficie,
    pode_gerar_plano: bool,
) -> tuple[NivelConfianca, float]:
    if not pode_gerar_plano:
        return NivelConfianca.BAIXO, 0.0

    pontuacao = 0.35 if entrada.requisitos else 0.0
    if analise.tipo_sistema != TipoSistema.DESCONHECIDO:
        pontuacao += 0.15

    tem_seletores = any(
        alvo.seletores or any(passo.localizador for passo in alvo.passos_automacao)
        for alvo in entrada.rotas_ou_telas
    )
    tem_codigo_ou_seletores = bool(entrada.codigo_fonte or tem_seletores)
    tipo = analise.tipo_sistema

    if tipo == TipoSistema.WEB:
        pontuacao += 0.10 if _url_valida(entrada.base_url) else 0.0
        pontuacao += 0.10 if entrada.rotas_ou_telas else 0.0
        pontuacao += 0.15 if tem_codigo_ou_seletores else 0.0
    elif tipo == TipoSistema.API:
        pontuacao += 0.35 if entrada.contratos_api else 0.0
    elif tipo == TipoSistema.FULLSTACK:
        pontuacao += 0.08 if _url_valida(entrada.base_url) else 0.0
        pontuacao += 0.08 if entrada.rotas_ou_telas else 0.0
        pontuacao += 0.08 if tem_codigo_ou_seletores else 0.0
        pontuacao += 0.11 if entrada.contratos_api else 0.0

    pontuacao += 0.10 if _contrato_possui_massa(entrada) else 0.0
    pontuacao += 0.05 if entrada.perfis_usuario else 0.0
    pontuacao = round(min(pontuacao, 1.0), 2)

    if pontuacao >= 0.80:
        nivel = NivelConfianca.ALTO
    elif pontuacao >= 0.50:
        nivel = NivelConfianca.MEDIO
    else:
        nivel = NivelConfianca.BAIXO
    return nivel, pontuacao


def validar_contrato_e2e(
    entrada: EntradaE2ENormalizada,
    analise: AnaliseSuperficie,
) -> ValidacaoContratoE2E:
    """Avalia separadamente a suficiência para plano, código e execução."""

    bloqueios: list[BloqueioE2E] = []

    def adicionar(
        codigo: str,
        categoria: CategoriaBloqueio,
        mensagem: str,
        campos: list[str],
        *,
        impede_plano: bool = False,
        impede_codigo: bool = True,
        impede_execucao: bool = True,
    ) -> None:
        bloqueios.append(
            BloqueioE2E(
                codigo=codigo,
                categoria=categoria,
                mensagem=mensagem,
                campos_ausentes=campos,
                impede_plano=impede_plano,
                impede_codigo=impede_codigo,
                impede_execucao=impede_execucao,
            )
        )

    if not entrada.requisitos:
        adicionar(
            "REQUISITOS_AUSENTES",
            CategoriaBloqueio.ENTRADA,
            "É necessário pelo menos um requisito não vazio para criar o plano E2E.",
            ["requisitos"],
            impede_plano=True,
        )

    if not analise.suportado_no_p0:
        adicionar(
            "TIPO_SISTEMA_FORA_DO_ESCOPO_P0",
            CategoriaBloqueio.ESCOPO,
            (
                f"O gerador Playwright não atende sistemas do tipo "
                f"'{analise.tipo_sistema.value}'."
            ),
            ["tipo_sistema"],
            impede_plano=True,
        )

    if analise.tipo_sistema == TipoSistema.DESCONHECIDO:
        adicionar(
            "TIPO_SISTEMA_NAO_IDENTIFICADO",
            CategoriaBloqueio.GERACAO_CODIGO,
            "O plano pode ser criado, mas falta identificar a superfície do sistema.",
            ["tipo_sistema", "rotas_ou_telas", "contratos_api"],
        )

    if entrada.base_url and not _url_valida(entrada.base_url):
        adicionar(
            "BASE_URL_INVALIDA",
            CategoriaBloqueio.GERACAO_CODIGO,
            "A base_url deve usar http ou https e possuir um host válido.",
            ["base_url"],
        )

    tipo = analise.tipo_sistema
    if tipo in {TipoSistema.WEB, TipoSistema.FULLSTACK}:
        if not entrada.base_url:
            adicionar(
                "BASE_URL_AUSENTE",
                CategoriaBloqueio.GERACAO_CODIGO,
                "Falta a URL base usada para abrir o sistema web.",
                ["base_url"],
            )
        if not entrada.rotas_ou_telas:
            adicionar(
                "NAVEGACAO_AUSENTE",
                CategoriaBloqueio.GERACAO_CODIGO,
                "Faltam rotas ou telas que definam a jornada E2E.",
                ["rotas_ou_telas"],
            )
        tem_localizadores_estruturados = any(
            passo.localizador
            for alvo in entrada.rotas_ou_telas
            for passo in alvo.passos_automacao
        )
        if not tem_localizadores_estruturados:
            adicionar(
                "LOCALIZADORES_AUSENTES",
                CategoriaBloqueio.GERACAO_CODIGO,
                (
                    "Faltam localizadores semânticos estruturados nos passos "
                    "de automação."
                ),
                ["rotas_ou_telas[].passos_automacao[].localizador"],
            )
        if entrada.rotas_ou_telas and not any(
            alvo.passos_automacao for alvo in entrada.rotas_ou_telas
        ):
            adicionar(
                "PASSOS_AUTOMACAO_AUSENTES",
                CategoriaBloqueio.GERACAO_CODIGO,
                "Faltam passos estruturados para renderizar comandos Playwright.",
                ["rotas_ou_telas[].passos_automacao"],
            )
        erros_passos = _erros_passos_automacao(entrada)
        if erros_passos:
            adicionar(
                "PASSOS_AUTOMACAO_INCOMPLETOS",
                CategoriaBloqueio.GERACAO_CODIGO,
                "Passos estruturados inválidos: " + " ".join(erros_passos),
                ["rotas_ou_telas[].passos_automacao"],
            )
        tem_assercao = any(
            passo.acao in _ACOES_ASSERCAO
            for alvo in entrada.rotas_ou_telas
            for passo in alvo.passos_automacao
        )
        if entrada.rotas_ou_telas and not tem_assercao:
            adicionar(
                "ASSERCOES_AUTOMATIZAVEIS_AUSENTES",
                CategoriaBloqueio.GERACAO_CODIGO,
                "Falta ao menos um passo estruturado de verificação.",
                ["rotas_ou_telas[].passos_automacao"],
            )

    if tipo in {TipoSistema.API, TipoSistema.FULLSTACK}:
        adicionar(
            "GERACAO_API_FORA_DO_INCREMENTO",
            CategoriaBloqueio.GERACAO_CODIGO,
            "A geração de código deste incremento atende somente jornadas web.",
            ["tipo_sistema=web"],
        )

    if tipo in {TipoSistema.API, TipoSistema.FULLSTACK} and not entrada.contratos_api:
        adicionar(
            "CONTRATOS_API_AUSENTES",
            CategoriaBloqueio.GERACAO_CODIGO,
            "Faltam endpoints, payloads e respostas esperadas da API.",
            ["contratos_api"],
        )

    if tipo in {TipoSistema.WEB, TipoSistema.API, TipoSistema.FULLSTACK}:
        if not _contrato_possui_massa(entrada):
            adicionar(
                "DADOS_TESTE_AUSENTES",
                CategoriaBloqueio.GERACAO_CODIGO,
                "Falta a massa mínima necessária para automatizar o fluxo.",
                ["dados_teste"],
            )

    if not entrada.ambiente_execucao:
        adicionar(
            "AMBIENTE_EXECUCAO_AUSENTE",
            CategoriaBloqueio.EXECUCAO,
            "Nenhum ambiente foi configurado para executar Playwright.",
            ["ambiente_execucao"],
            impede_codigo=False,
        )
    else:
        tipo_ambiente = str(entrada.ambiente_execucao.get("tipo", "local")).lower()
        if tipo_ambiente != "local":
            adicionar(
                "AMBIENTE_EXECUCAO_NAO_SUPORTADO",
                CategoriaBloqueio.EXECUCAO,
                "Este incremento executa Playwright somente no ambiente local.",
                ["ambiente_execucao.tipo=local"],
                impede_codigo=False,
            )
        browser = str(entrada.ambiente_execucao.get("browser", "chromium")).lower()
        if browser != "chromium":
            adicionar(
                "BROWSER_NAO_SUPORTADO",
                CategoriaBloqueio.EXECUCAO,
                "Este incremento executa somente o projeto Chromium.",
                ["ambiente_execucao.browser=chromium"],
                impede_codigo=False,
            )
    if not entrada.comando_execucao:
        adicionar(
            "COMANDO_EXECUCAO_AUSENTE",
            CategoriaBloqueio.EXECUCAO,
            "Nenhum perfil de comando Playwright foi informado.",
            ["comando_execucao"],
            impede_codigo=False,
        )
    elif entrada.comando_execucao.strip().lower() not in _PERFIS_COMANDO_PLAYWRIGHT:
        adicionar(
            "COMANDO_EXECUCAO_NAO_PERMITIDO",
            CategoriaBloqueio.EXECUCAO,
            "Use um perfil Playwright permitido; argumentos arbitrários são bloqueados.",
            ["comando_execucao=npx playwright test"],
            impede_codigo=False,
        )

    pode_gerar_plano = not any(item.impede_plano for item in bloqueios)
    pode_gerar_codigo = pode_gerar_plano and not any(
        item.impede_codigo for item in bloqueios
    )
    pode_executar = pode_gerar_codigo and not any(
        item.impede_execucao for item in bloqueios
    )
    nivel, pontuacao = _calcular_confianca(
        entrada,
        analise,
        pode_gerar_plano,
    )
    return ValidacaoContratoE2E(
        pode_gerar_plano=pode_gerar_plano,
        pode_gerar_codigo=pode_gerar_codigo,
        pode_executar=pode_executar,
        nivel_confianca=nivel,
        pontuacao_confianca=pontuacao,
        bloqueios=bloqueios,
    )
