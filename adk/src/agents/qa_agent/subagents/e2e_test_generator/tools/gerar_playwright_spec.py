"""Renderização determinística de uma jornada web para Playwright/TypeScript."""

import json
import re
from urllib.parse import urljoin

from shared.workspace import get_agent_workspace

from ..schemas import (
    AcaoAutomacao,
    CategoriaCenario,
    CenarioE2E,
    EntradaE2ENormalizada,
    LocalizadorPlaywright,
    PassoAutomacao,
    ResultadoGeracaoPlaywright,
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
) -> object | None:
    if passo.chave_dado:
        for conjunto in entrada.dados_teste:
            if passo.chave_dado in conjunto:
                return conjunto[passo.chave_dado]
        raise ValueError(f"Dado de teste não encontrado: {passo.chave_dado}")
    return passo.valor


def _renderizar_passo(
    passo: PassoAutomacao,
    entrada: EntradaE2ENormalizada,
) -> str:
    valor = _resolver_valor(passo, entrada)
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
    for indice, alvo in enumerate(entrada.rotas_ou_telas, start=1):
        rota = alvo.rota or ""
        url = (
            rota
            if rota.startswith(("http://", "https://"))
            else urljoin(entrada.base_url.rstrip("/") + "/", rota.lstrip("/"))
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

    testes_pulados = 0
    for cenario in cenarios:
        if cenario.categoria == CategoriaCenario.FLUXO_FELIZ:
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
