"""Validação de suficiência do contrato E2E.

Os bloqueios distinguem o que impede o plano, o código e a execução. Código
Playwright é liberado para jornadas web estruturadas ou contratos HTTP verificáveis.
"""

import ipaddress
from urllib.parse import urlparse

from ..schemas import (
    AcaoAutomacao,
    AnaliseSuperficie,
    BloqueioE2E,
    CategoriaBloqueio,
    CategoriaCenario,
    ContratoNegativoE2E,
    EntradaE2ENormalizada,
    NivelConfianca,
    SuperficieContratoNegativo,
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

_ACOES_MUTACAO = {
    AcaoAutomacao.PREENCHER,
    AcaoAutomacao.CLICAR,
    AcaoAutomacao.MARCAR,
    AcaoAutomacao.DESMARCAR,
    AcaoAutomacao.SELECIONAR,
    AcaoAutomacao.PRESSIONAR,
}

_METODOS_HTTP = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}

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


def _url_loopback(url: str | None) -> bool:
    if not _url_valida(url):
        return False
    hostname = (urlparse(url).hostname or "").lower()
    if hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _contrato_possui_massa(entrada: EntradaE2ENormalizada) -> bool:
    if entrada.dados_teste:
        return True
    chaves_massa = {"payload", "body", "request", "dados", "data", "params"}
    return any(
        chaves_massa.intersection(contrato) for contrato in entrada.contratos_api
    )


def _valor_contrato(contrato: dict, *chaves: str) -> object | None:
    for chave in chaves:
        valor = contrato.get(chave)
        if valor not in (None, "", [], {}):
            return valor
    return None


def _metodo_contrato(contrato: dict) -> str:
    return str(_valor_contrato(contrato, "metodo", "method") or "GET").upper()


def _contratos_api_invalidos(entrada: EntradaE2ENormalizada) -> list[str]:
    erros: list[str] = []
    for indice, contrato in enumerate(entrada.contratos_api, start=1):
        rota = _valor_contrato(contrato, "rota", "endpoint", "path", "url")
        metodo = _metodo_contrato(contrato)
        status = _valor_contrato(
            contrato,
            "status_esperado",
            "expected_status",
            "status",
        )
        if not isinstance(rota, str) or not (
            rota.startswith("/") or _url_valida(rota)
        ):
            erros.append(f"Contrato {indice}: rota HTTP(S) ausente ou inválida.")
        if metodo not in _METODOS_HTTP:
            erros.append(f"Contrato {indice}: método HTTP não suportado ({metodo}).")
        if not isinstance(status, int) or not 100 <= status <= 599:
            erros.append(f"Contrato {indice}: status esperado ausente ou inválido.")
    return erros


def _contratos_requerem_massa(entrada: EntradaE2ENormalizada) -> bool:
    return any(
        _metodo_contrato(contrato) in {"POST", "PUT", "PATCH"}
        and _valor_contrato(
            contrato,
            "payload",
            "body",
            "request",
            "dados",
            "data",
        )
        is None
        for contrato in entrada.contratos_api
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


def _rota_relativa_segura(rota: str | None) -> bool:
    return bool(rota and rota.startswith("/") and not rota.startswith("//"))


def erros_contrato_negativo(
    entrada: EntradaE2ENormalizada,
    analise: AnaliseSuperficie,
    contrato: ContratoNegativoE2E,
) -> list[str]:
    """Retorna lacunas que mantêm um contrato negativo em `test.skip`."""

    erros: list[str] = []
    identificador = contrato.id or "sem-id"
    prefixo = f"Contrato negativo {identificador}"
    tipos_compativeis = (
        {TipoSistema.WEB, TipoSistema.FULLSTACK}
        if contrato.superficie == SuperficieContratoNegativo.WEB
        else {TipoSistema.API, TipoSistema.FULLSTACK}
    )
    if analise.tipo_sistema not in tipos_compativeis:
        erros.append(
            f"{prefixo}: superfície {contrato.superficie.value} incompatível "
            f"com o sistema {analise.tipo_sistema.value}."
        )
    if not _rota_relativa_segura(contrato.rota):
        erros.append(
            f"{prefixo}: rota deve ser relativa, iniciar com '/' e permanecer "
            "no sistema alvo."
        )
    if contrato.metodo not in _METODOS_HTTP:
        erros.append(f"{prefixo}: método HTTP não suportado ({contrato.metodo}).")

    if contrato.superficie == SuperficieContratoNegativo.API:
        if contrato.passos_automacao:
            erros.append(
                f"{prefixo}: passos_automacao são aceitos somente em contratos web."
            )
        if contrato.mock_rede is not None:
            erros.append(
                f"{prefixo}: mock_rede não é suportado para chamadas API diretas."
            )
        if contrato.categoria == CategoriaCenario.TIMEOUT_LATENCIA:
            if not contrato.espera_timeout:
                erros.append(
                    f"{prefixo}: espera_timeout=true é obrigatório para timeout API."
                )
            if contrato.timeout_ms is None:
                erros.append(f"{prefixo}: timeout_ms é obrigatório para timeout API.")
            if not contrato.dependencia:
                erros.append(
                    f"{prefixo}: dependência/componente sob latência não declarado."
                )
        elif contrato.status_esperado is None:
            erros.append(f"{prefixo}: status_esperado é obrigatório.")
        if (
            contrato.categoria == CategoriaCenario.DADOS_MALFORMADOS
            and "payload" not in contrato.model_fields_set
        ):
            erros.append(
                f"{prefixo}: payload explícito é obrigatório para dados malformados."
            )
        if (
            contrato.categoria == CategoriaCenario.FALHA_DEPENDENCIA_EXTERNA
            and not contrato.dependencia
        ):
            erros.append(f"{prefixo}: dependência externa não declarada.")
        return erros

    passos = contrato.passos_automacao
    if not passos:
        erros.append(f"{prefixo}: passos_automacao web ausentes.")
    elif not any(passo.acao in _ACOES_ASSERCAO for passo in passos):
        erros.append(f"{prefixo}: passo de verificação web ausente.")

    chaves_disponiveis = _chaves_dados(entrada).union(contrato.dados_teste)
    for indice, passo in enumerate(passos, start=1):
        passo_prefixo = f"{prefixo}, passo {indice}"
        if passo.acao in _ACOES_COM_LOCALIZADOR and passo.localizador is None:
            erros.append(f"{passo_prefixo}: localizador semântico ausente.")
        if passo.acao in _ACOES_COM_VALOR and (
            passo.valor is None and not passo.chave_dado
        ):
            erros.append(f"{passo_prefixo}: valor ou chave_dado ausente.")
        if passo.chave_dado and passo.chave_dado not in chaves_disponiveis:
            erros.append(
                f"{passo_prefixo}: chave_dado '{passo.chave_dado}' não foi declarado."
            )
        if (
            passo.acao == AcaoAutomacao.VERIFICAR_TEXTO
            and passo.localizador is not None
            and passo.localizador.tipo.value != "text"
            and passo.valor is None
            and not passo.chave_dado
        ):
            erros.append(
                f"{passo_prefixo}: verificar_texto requer valor/chave_dado."
            )

    if contrato.categoria in {
        CategoriaCenario.FALHA_DEPENDENCIA_EXTERNA,
        CategoriaCenario.TIMEOUT_LATENCIA,
    }:
        mock = contrato.mock_rede
        if mock is None:
            erros.append(f"{prefixo}: mock_rede explícito é obrigatório.")
        else:
            if not _rota_relativa_segura(mock.rota):
                erros.append(
                    f"{prefixo}: mock_rede.rota deve ser relativa e permanecer "
                    "no sistema alvo."
                )
            if mock.metodo not in _METODOS_HTTP:
                erros.append(
                    f"{prefixo}: método do mock não suportado ({mock.metodo})."
                )
            if mock.status_simulado is None:
                erros.append(f"{prefixo}: mock_rede.status_simulado é obrigatório.")
            if mock.rota == contrato.rota:
                erros.append(
                    f"{prefixo}: rota do mock não pode substituir a própria página."
                )
            if contrato.categoria == CategoriaCenario.FALHA_DEPENDENCIA_EXTERNA:
                if mock.status_simulado is None or mock.status_simulado < 400:
                    erros.append(
                        f"{prefixo}: falha externa exige status_simulado entre 400 e 599."
                    )
            elif mock.atraso_ms <= 0:
                erros.append(
                    f"{prefixo}: timeout/latência exige atraso_ms maior que zero."
                )
        if not contrato.dependencia:
            erros.append(f"{prefixo}: dependência/componente não declarado.")

    if contrato.categoria == CategoriaCenario.DADOS_MALFORMADOS:
        tem_mutacao_explicita = any(
            passo.acao in _ACOES_MUTACAO
            and (
                passo.valor is not None
                or passo.chave_dado is not None
                or passo.acao
                in {
                    AcaoAutomacao.CLICAR,
                    AcaoAutomacao.MARCAR,
                    AcaoAutomacao.DESMARCAR,
                }
            )
            for passo in passos
        )
        if not tem_mutacao_explicita:
            erros.append(
                f"{prefixo}: dados/ações inválidos não foram declarados explicitamente."
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

    erros_negativos_por_id = {
        contrato.id: erros_contrato_negativo(entrada, analise, contrato)
        for contrato in entrada.contratos_negativos
    }
    tem_negativo_web_pronto = any(
        contrato.superficie == SuperficieContratoNegativo.WEB
        and not erros_negativos_por_id.get(contrato.id)
        for contrato in entrada.contratos_negativos
    )
    tem_negativo_api_pronto = any(
        contrato.superficie == SuperficieContratoNegativo.API
        and not erros_negativos_por_id.get(contrato.id)
        for contrato in entrada.contratos_negativos
    )
    sem_fluxo_web_positivo = not any(
        alvo.passos_automacao for alvo in entrada.rotas_ou_telas
    )
    sem_fluxo_api_positivo = not entrada.contratos_api
    negativo_web_substitui_fluxo_ausente = (
        tem_negativo_web_pronto and sem_fluxo_web_positivo
    )
    negativo_api_substitui_fluxo_ausente = (
        tem_negativo_api_pronto and sem_fluxo_api_positivo
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
    tem_passos_web = any(
        alvo.passos_automacao for alvo in entrada.rotas_ou_telas
    )
    validar_web = tipo == TipoSistema.WEB or (
        tipo == TipoSistema.FULLSTACK
        and (tem_passos_web or tem_negativo_web_pronto)
    )
    validar_api = tipo == TipoSistema.API or (
        tipo == TipoSistema.FULLSTACK
        and (
            (bool(entrada.contratos_api) and not tem_passos_web)
            or tem_negativo_api_pronto
        )
    )

    if validar_web:
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
                impede_codigo=not negativo_web_substitui_fluxo_ausente,
                impede_execucao=not negativo_web_substitui_fluxo_ausente,
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
                impede_codigo=not negativo_web_substitui_fluxo_ausente,
                impede_execucao=not negativo_web_substitui_fluxo_ausente,
            )
        if entrada.rotas_ou_telas and not any(
            alvo.passos_automacao for alvo in entrada.rotas_ou_telas
        ):
            adicionar(
                "PASSOS_AUTOMACAO_AUSENTES",
                CategoriaBloqueio.GERACAO_CODIGO,
                "Faltam passos estruturados para renderizar comandos Playwright.",
                ["rotas_ou_telas[].passos_automacao"],
                impede_codigo=not negativo_web_substitui_fluxo_ausente,
                impede_execucao=not negativo_web_substitui_fluxo_ausente,
            )
        erros_passos = _erros_passos_automacao(entrada)
        if erros_passos:
            adicionar(
                "PASSOS_AUTOMACAO_INCOMPLETOS",
                CategoriaBloqueio.GERACAO_CODIGO,
                "Passos estruturados inválidos: " + " ".join(erros_passos),
                ["rotas_ou_telas[].passos_automacao"],
                impede_codigo=not negativo_web_substitui_fluxo_ausente,
                impede_execucao=not negativo_web_substitui_fluxo_ausente,
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
                impede_codigo=not negativo_web_substitui_fluxo_ausente,
                impede_execucao=not negativo_web_substitui_fluxo_ausente,
            )

    if validar_api and not entrada.base_url:
        adicionar(
            "BASE_URL_API_AUSENTE",
            CategoriaBloqueio.GERACAO_CODIGO,
            "Falta a URL base usada para chamar a API.",
            ["base_url"],
        )
    elif entrada.base_url and not _url_loopback(entrada.base_url):
        adicionar(
            "HOST_EXTERNO_NAO_AUTORIZADO",
            CategoriaBloqueio.EXECUCAO,
            (
                "A execução autônoma deste incremento é restrita a localhost "
                "ou endereços IP de loopback."
            ),
            ["base_url=localhost"],
            impede_codigo=False,
        )

    if validar_api and not entrada.contratos_api:
        adicionar(
            "CONTRATOS_API_AUSENTES",
            CategoriaBloqueio.GERACAO_CODIGO,
            "Faltam endpoints, payloads e respostas esperadas da API.",
            ["contratos_api"],
            impede_codigo=not negativo_api_substitui_fluxo_ausente,
            impede_execucao=not negativo_api_substitui_fluxo_ausente,
        )

    erros_contratos = (
        _contratos_api_invalidos(entrada) if validar_api else []
    )
    if erros_contratos:
        adicionar(
            "CONTRATOS_API_INCOMPLETOS",
            CategoriaBloqueio.GERACAO_CODIGO,
            "Contratos API inválidos: " + " ".join(erros_contratos),
            ["contratos_api"],
        )

    if validar_web:
        passos_requerem_dados = any(
            passo.chave_dado
            for alvo in entrada.rotas_ou_telas
            for passo in alvo.passos_automacao
        )
        if passos_requerem_dados and not _contrato_possui_massa(entrada):
            adicionar(
                "DADOS_TESTE_AUSENTES",
                CategoriaBloqueio.GERACAO_CODIGO,
                "Falta a massa referenciada pelos passos de automação.",
                ["dados_teste"],
            )
    elif validar_api and _contratos_requerem_massa(entrada):
        adicionar(
            "DADOS_TESTE_AUSENTES",
            CategoriaBloqueio.GERACAO_CODIGO,
            "Falta payload para um contrato API que envia dados.",
            ["contratos_api[].payload"],
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

    for contrato_negativo in entrada.contratos_negativos:
        erros_negativos = erros_negativos_por_id.get(contrato_negativo.id, [])
        if erros_negativos:
            adicionar(
                "CONTRATO_NEGATIVO_INCOMPLETO",
                CategoriaBloqueio.GERACAO_CODIGO,
                " ".join(erros_negativos),
                [f"contratos_negativos[{contrato_negativo.id}]"],
                impede_codigo=False,
                impede_execucao=False,
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
