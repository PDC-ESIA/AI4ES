"""Renderização determinística de jornadas web/API para Playwright/TypeScript."""

import json
import re
from urllib.parse import urljoin

from shared.workspace import get_agent_workspace

from ..schemas import (
    AcaoAutomacao,
    CategoriaCenario,
    CenarioE2E,
    ContratoNegativoE2E,
    EntradaE2ENormalizada,
    LocalizadorPlaywright,
    PassoAutomacao,
    ResultadoGeracaoPlaywright,
    SuperficieContratoNegativo,
    TipoLocalizador,
)


def _literal_ts(valor: object) -> str:
    return json.dumps(valor, ensure_ascii=False)


def _slug(texto: str) -> str:
    seguro = re.sub(r"[^a-zA-Z0-9]+", "_", texto.strip().lower()).strip("_")
    return seguro or "plano_e2e"


def _comentario(texto: str) -> str:
    return " ".join(texto.replace("*/", "* /").split())


def _localizador(localizador: LocalizadorPlaywright) -> str:
    valor = _literal_ts(localizador.valor)
    exato = "true" if localizador.exato else "false"
    if localizador.tipo == TipoLocalizador.ROLE:
        if localizador.nome_acessivel:
            nome = _literal_ts(localizador.nome_acessivel)
            return f"page.getByRole({valor}, {{ name: {nome}, exact: {exato} }})"
        return f"page.getByRole({valor})"
    if localizador.tipo == TipoLocalizador.LABEL:
        return f"page.getByLabel({valor}, {{ exact: {exato} }})"
    if localizador.tipo == TipoLocalizador.TEXT:
        return f"page.getByText({valor}, {{ exact: {exato} }})"
    if localizador.tipo == TipoLocalizador.TEST_ID:
        return f"page.getByTestId({valor})"
    if localizador.tipo == TipoLocalizador.PLACEHOLDER:
        return f"page.getByPlaceholder({valor}, {{ exact: {exato} }})"
    raise ValueError(f"Tipo de localizador não suportado: {localizador.tipo}")


def _resolver_valor(
    passo: PassoAutomacao,
    entrada: EntradaE2ENormalizada,
    dados_adicionais: dict[str, object] | None = None,
) -> object | None:
    if passo.chave_dado:
        if dados_adicionais and passo.chave_dado in dados_adicionais:
            return dados_adicionais[passo.chave_dado]
        for conjunto in entrada.dados_teste:
            if passo.chave_dado in conjunto:
                return conjunto[passo.chave_dado]
        raise ValueError(f"Dado de teste não encontrado: {passo.chave_dado}")
    return passo.valor


def _valor_contrato(contrato: dict, *chaves: str) -> object | None:
    for chave in chaves:
        valor = contrato.get(chave)
        if valor not in (None, "", [], {}):
            return valor
    return None


def _renderizar_contrato_api(
    contrato: dict,
    entrada: EntradaE2ENormalizada,
    indice: int,
) -> list[str]:
    rota = str(
        _valor_contrato(contrato, "rota", "endpoint", "path", "url") or ""
    )
    url = (
        rota
        if rota.startswith(("http://", "https://"))
        else urljoin(entrada.base_url.rstrip("/") + "/", rota.lstrip("/"))
    )
    metodo = str(
        _valor_contrato(contrato, "metodo", "method") or "GET"
    ).upper()
    status = int(
        _valor_contrato(
            contrato,
            "status_esperado",
            "expected_status",
            "status",
        )
    )
    payload = _valor_contrato(
        contrato,
        "payload",
        "body",
        "request",
        "dados",
        "data",
    )
    resposta_esperada = _valor_contrato(
        contrato,
        "resposta_esperada",
        "expected_response",
        "response",
    )
    opcoes = [f"method: {_literal_ts(metodo)}"]
    if payload is not None:
        opcoes.append(f"data: {_literal_ts(payload)}")
    titulo = f"E2E-API-{indice:03d} - {metodo} {rota}"
    linhas = [
        "",
        f"  test({_literal_ts(titulo)}, async ({{ request }}) => {{",
        (
            f"    const response = await request.fetch({_literal_ts(url)}, "
            f"{{ {', '.join(opcoes)} }});"
        ),
        f"    expect(response.status()).toBe({status});",
    ]
    if resposta_esperada is not None:
        linhas.append(
            "    expect(await response.json()).toEqual("
            f"{_literal_ts(resposta_esperada)});"
        )
    linhas.append("  });")
    return linhas


def _renderizar_passo(
    passo: PassoAutomacao,
    entrada: EntradaE2ENormalizada,
    dados_adicionais: dict[str, object] | None = None,
) -> str:
    valor = _resolver_valor(passo, entrada, dados_adicionais)
    alvo = _localizador(passo.localizador) if passo.localizador else None

    if passo.acao == AcaoAutomacao.PREENCHER:
        return f"await {alvo}.fill({_literal_ts(str(valor))});"
    if passo.acao == AcaoAutomacao.CLICAR:
        return f"await {alvo}.click();"
    if passo.acao == AcaoAutomacao.MARCAR:
        return f"await {alvo}.check();"
    if passo.acao == AcaoAutomacao.DESMARCAR:
        return f"await {alvo}.uncheck();"
    if passo.acao == AcaoAutomacao.SELECIONAR:
        return f"await {alvo}.selectOption({_literal_ts(str(valor))});"
    if passo.acao == AcaoAutomacao.PRESSIONAR:
        return f"await {alvo}.press({_literal_ts(str(valor))});"
    if passo.acao == AcaoAutomacao.VERIFICAR_VISIVEL:
        return f"await expect({alvo}).toBeVisible();"
    if passo.acao == AcaoAutomacao.VERIFICAR_TEXTO:
        if valor is None:
            return f"await expect({alvo}).toBeVisible();"
        return f"await expect({alvo}).toContainText({_literal_ts(str(valor))});"
    if passo.acao == AcaoAutomacao.VERIFICAR_URL:
        esperado = str(valor)
        if esperado.startswith("/") and entrada.base_url:
            esperado = urljoin(entrada.base_url.rstrip("/") + "/", esperado.lstrip("/"))
        return f"await expect(page).toHaveURL({_literal_ts(esperado)});"
    raise ValueError(f"Ação não suportada: {passo.acao}")


def _url_relativa_alvo(base_url: str | None, rota: str | None) -> str:
    if not base_url or not rota or not rota.startswith("/") or rota.startswith("//"):
        raise ValueError("Contrato negativo possui URL ausente ou fora do sistema alvo.")
    return urljoin(base_url.rstrip("/") + "/", rota.lstrip("/"))


def _renderizar_contrato_negativo(
    contrato: ContratoNegativoE2E,
    entrada: EntradaE2ENormalizada,
    titulo: str,
) -> list[str]:
    """Renderiza apenas operações tipadas pelo contrato negativo validado."""

    rota = _url_relativa_alvo(entrada.base_url, contrato.rota)
    if contrato.superficie == SuperficieContratoNegativo.API:
        opcoes = [f"method: {_literal_ts(contrato.metodo)}"]
        if "payload" in contrato.model_fields_set:
            opcoes.append(f"data: {_literal_ts(contrato.payload)}")
        if contrato.categoria == CategoriaCenario.TIMEOUT_LATENCIA:
            opcoes.append(f"timeout: {contrato.timeout_ms}")
            return [
                "",
                f"  test({_literal_ts(titulo)}, async ({{ request }}) => {{",
                "    await expect(",
                (
                    f"      request.fetch({_literal_ts(rota)}, "
                    f"{{ {', '.join(opcoes)} }})"
                ),
                "    ).rejects.toThrow();",
                "  });",
            ]

        linhas = [
            "",
            f"  test({_literal_ts(titulo)}, async ({{ request }}) => {{",
            (
                f"    const response = await request.fetch({_literal_ts(rota)}, "
                f"{{ {', '.join(opcoes)} }});"
            ),
            f"    expect(response.status()).toBe({contrato.status_esperado});",
        ]
        if "resposta_esperada" in contrato.model_fields_set:
            linhas.append(
                "    expect(await response.json()).toEqual("
                f"{_literal_ts(contrato.resposta_esperada)});"
            )
        linhas.append("  });")
        return linhas

    linhas = [
        "",
        f"  test({_literal_ts(titulo)}, async ({{ page }}) => {{",
    ]
    if contrato.mock_rede is not None:
        mock = contrato.mock_rede
        url_mock = _url_relativa_alvo(entrada.base_url, mock.rota)
        linhas.extend(
            [
                f"    await page.route({_literal_ts(url_mock)}, async (route) => {{",
                (
                    "      if (route.request().method() !== "
                    f"{_literal_ts(mock.metodo)}) {{"
                ),
                "        await route.fallback();",
                "        return;",
                "      }",
            ]
        )
        if mock.atraso_ms:
            linhas.append(
                "      await new Promise((resolve) => "
                f"setTimeout(resolve, {mock.atraso_ms}));"
            )
        opcoes_mock = [f"status: {mock.status_simulado}"]
        if "resposta_simulada" in mock.model_fields_set:
            opcoes_mock.extend(
                [
                    "contentType: 'application/json'",
                    f"body: JSON.stringify({_literal_ts(mock.resposta_simulada)})",
                ]
            )
        linhas.extend(
            [
                f"      await route.fulfill({{ {', '.join(opcoes_mock)} }});",
                "    });",
            ]
        )
    linhas.append(f"    await page.goto({_literal_ts(rota)});")
    for passo in contrato.passos_automacao:
        linhas.append(
            f"    {_renderizar_passo(passo, entrada, contrato.dados_teste)}"
        )
    linhas.append("  });")
    return linhas


def renderizar_playwright_spec(
    entrada: EntradaE2ENormalizada,
    cenarios: list[CenarioE2E],
) -> tuple[str, int, int]:
    """Produz TypeScript sem interpolar código arbitrário fornecido pelo usuário."""

    ids = ", ".join(item.id for item in entrada.requisitos)
    linhas = [
        "import { test, expect } from '@playwright/test';",
        "",
        f"// Requisitos de origem: {_comentario(ids)}",
        "test.describe('Plano E2E gerado pelo QA Agent', () => {",
    ]

    testes_ativos = 0
    alvos_web = [
        alvo for alvo in entrada.rotas_ou_telas if alvo.passos_automacao
    ]
    if alvos_web:
        for indice, alvo in enumerate(alvos_web, start=1):
            rota = alvo.rota or ""
            url = (
                rota
                if rota.startswith(("http://", "https://"))
                else urljoin(
                    entrada.base_url.rstrip("/") + "/",
                    rota.lstrip("/"),
                )
            )
            titulo = f"E2E-WEB-{indice:03d} - {alvo.nome}"
            linhas.extend(
                [
                    "",
                    f"  test({_literal_ts(titulo)}, async ({{ page }}) => {{",
                    f"    await page.goto({_literal_ts(url)});",
                ]
            )
            for passo in alvo.passos_automacao:
                linhas.append(f"    {_renderizar_passo(passo, entrada)}")
            linhas.append("  });")
            testes_ativos += 1
    else:
        for indice, contrato in enumerate(entrada.contratos_api, start=1):
            linhas.extend(_renderizar_contrato_api(contrato, entrada, indice))
            testes_ativos += 1

    contratos_negativos = {
        contrato.id: contrato
        for contrato in entrada.contratos_negativos
        if contrato.id is not None
    }
    testes_felizes_ativos = testes_ativos
    testes_pulados = 0
    for cenario in cenarios:
        if cenario.categoria == CategoriaCenario.FLUXO_FELIZ:
            if testes_felizes_ativos:
                continue
            motivo = "; ".join(cenario.lacunas) or (
                "Fluxo feliz sem contrato estruturado para automação."
            )
            titulo = f"{cenario.id} - {cenario.nome}"
            linhas.extend(
                [
                    "",
                    f"  test.skip({_literal_ts(titulo)}, async () => {{",
                    f"    // Bloqueado: {_comentario(motivo)}",
                    "  });",
                ]
            )
            testes_pulados += 1
            continue
        contrato = (
            contratos_negativos.get(cenario.contrato_negativo_id)
            if cenario.contrato_negativo_id
            else None
        )
        if cenario.pronto_para_automacao and contrato is not None:
            titulo = f"{cenario.id} - {cenario.nome}"
            linhas.extend(_renderizar_contrato_negativo(contrato, entrada, titulo))
            testes_ativos += 1
            continue
        motivo = "; ".join(cenario.lacunas) or (
            "Cenário sem passos estruturados neste incremento."
        )
        titulo = f"{cenario.id} - {cenario.nome}"
        linhas.extend(
            [
                "",
                f"  test.skip({_literal_ts(titulo)}, async () => {{",
                f"    // Bloqueado: {_comentario(motivo)}",
                "  });",
            ]
        )
        testes_pulados += 1

    linhas.extend(["});", ""])
    return "\n".join(linhas), testes_ativos, testes_pulados


def gerar_playwright_spec(
    entrada: EntradaE2ENormalizada,
    cenarios: list[CenarioE2E],
    nome_base: str,
) -> ResultadoGeracaoPlaywright:
    """Grava um único `.spec.ts` dentro do workspace reservado do subagente."""

    conteudo, testes_ativos, testes_pulados = renderizar_playwright_spec(
        entrada,
        cenarios,
    )
    destino = get_agent_workspace("e2e_test_generator").resolve()
    destino.mkdir(parents=True, exist_ok=True)
    arquivo = (destino / f"{_slug(nome_base)}.spec.ts").resolve()
    if destino not in arquivo.parents:
        raise ValueError("Caminho de saída Playwright escapou do workspace.")
    arquivo.write_text(conteudo, encoding="utf-8")
    return ResultadoGeracaoPlaywright(
        arquivo=str(arquivo),
        testes_ativos=testes_ativos,
        testes_pulados=testes_pulados,
    )
