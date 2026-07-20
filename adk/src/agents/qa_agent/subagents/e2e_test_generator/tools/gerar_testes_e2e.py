"""Executa a etapa E2E previamente autorizada pelo action_planner."""

import json
import re
from typing import Any

from pydantic import ValidationError
from shared.tools.planner_tools import plan_validator

from ..schemas import (
    BloqueioE2E,
    CategoriaBloqueio,
    EntradaE2E,
    FrameworkAlvo,
    NivelConfianca,
    RespostaE2E,
    TipoSaida,
    TipoSistema,
)
from .analisar_superficie_sistema import analisar_superficie_sistema
from .executar_playwright import executar_playwright
from .extrair_contrato_textual import extrair_contrato_textual_e2e
from .gerar_playwright_spec import gerar_playwright_spec
from .mapear_cenarios_e2e import mapear_cenarios_e2e
from .normalizar_entrada_e2e import normalizar_entrada_e2e
from .validar_contrato_e2e import validar_contrato_e2e


def _unicos(itens: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in itens if item))


def _slug(texto: str) -> str:
    normalizado = re.sub(r"[^a-zA-Z0-9]+", "_", texto.strip().lower()).strip("_")
    return normalizado or "plano_e2e"


def _arquivos_sugeridos(ids_requisitos: list[str]) -> list[str]:
    nome = _slug(ids_requisitos[0]) if len(ids_requisitos) == 1 else "requisitos_e2e"
    return [f"tests/e2e/{nome}.spec.ts"]


def _nome_base(ids_requisitos: list[str]) -> str:
    return _slug(ids_requisitos[0]) if len(ids_requisitos) == 1 else "requisitos_e2e"


def _valor_ausente(valor: Any) -> bool:
    return valor is None or valor == "" or valor == [] or valor == {}


def _decodificar_objeto(valor: Any) -> Any:
    if not isinstance(valor, str):
        return valor
    texto = valor.strip()
    if not texto or texto[0] not in "[{":
        return valor
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return valor


def _possui_passos_estruturados(valor: Any) -> bool:
    decodificado = _decodificar_objeto(valor)
    itens = decodificado if isinstance(decodificado, list) else [decodificado]
    return any(
        isinstance(item, dict)
        and isinstance(
            item.get("passos_automacao") or item.get("automation_steps"), list
        )
        and bool(item.get("passos_automacao") or item.get("automation_steps"))
        for item in itens
    )


def _aplicar_contrato_textual(
    requisitos: Any,
    campos: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Preenche lacunas com fatos extraídos do próprio requisito original."""

    extraidos = extrair_contrato_textual_e2e(requisitos)
    aplicados: list[str] = []
    resultado = dict(campos)
    for campo in ("tipo_sistema", "base_url", "dados_teste", "comando_execucao"):
        if _valor_ausente(resultado.get(campo)) and campo in extraidos:
            resultado[campo] = extraidos[campo]
            aplicados.append(campo)

    if "rotas_ou_telas" in extraidos and not _possui_passos_estruturados(
        resultado.get("rotas_ou_telas")
    ):
        resultado["rotas_ou_telas"] = extraidos["rotas_ou_telas"]
        aplicados.append("rotas_ou_telas")

    ambiente_extraido = extraidos.get("ambiente_execucao")
    ambiente_atual = _decodificar_objeto(resultado.get("ambiente_execucao"))
    if isinstance(ambiente_extraido, dict):
        if not isinstance(ambiente_atual, dict):
            ambiente_atual = {}
        mesclado = {**ambiente_extraido, **ambiente_atual}
        if mesclado != ambiente_atual:
            resultado["ambiente_execucao"] = mesclado
            aplicados.append("ambiente_execucao")
    return resultado, aplicados


def _resposta_entrada_invalida(mensagem: str) -> dict[str, Any]:
    resposta = RespostaE2E(
        tipo_saida=TipoSaida.BLOQUEADO,
        framework_alvo=FrameworkAlvo.PLAYWRIGHT,
        nivel_confianca=NivelConfianca.BAIXO,
        tipo_sistema=TipoSistema.DESCONHECIDO,
        resumo="A entrada não pôde ser normalizada para o contrato E2E.",
        bloqueios=[
            BloqueioE2E(
                codigo="ENTRADA_INVALIDA",
                categoria=CategoriaBloqueio.ENTRADA,
                mensagem=mensagem,
                campos_ausentes=["requisitos"],
                impede_plano=True,
            )
        ],
        metadados={
            "fase_implementacao": "geracao_playwright",
            "gera_codigo": False,
            "executa_testes": False,
        },
    )
    return resposta.model_dump(mode="json")


def _resposta_planejamento_invalido(
    codigo: str,
    mensagem: str,
) -> dict[str, Any]:
    resposta = RespostaE2E(
        tipo_saida=TipoSaida.BLOQUEADO,
        framework_alvo=FrameworkAlvo.PLAYWRIGHT,
        nivel_confianca=NivelConfianca.BAIXO,
        tipo_sistema=TipoSistema.DESCONHECIDO,
        resumo="O E2E não foi iniciado porque falta autorização do action_planner.",
        bloqueios=[
            BloqueioE2E(
                codigo=codigo,
                categoria=CategoriaBloqueio.ENTRADA,
                mensagem=mensagem,
                campos_ausentes=["plano_acao"],
                impede_plano=True,
            )
        ],
        metadados={
            "fase_implementacao": "geracao_playwright",
            "planejamento_acao": {
                "planner": "action_planner",
                "validado": False,
            },
            "gera_codigo": False,
            "executa_testes": False,
        },
    )
    return resposta.model_dump(mode="json")


def _remover_cerca_markdown(texto: str) -> str:
    texto = texto.strip()
    if not texto.startswith("```"):
        return texto
    linhas = texto.splitlines()
    if linhas and linhas[0].strip().startswith("```"):
        linhas = linhas[1:]
    if linhas and linhas[-1].strip() == "```":
        linhas = linhas[:-1]
    return "\n".join(linhas).strip()


def _validar_plano_acao(plano_acao: str) -> tuple[dict[str, Any] | None, dict | None]:
    if not isinstance(plano_acao, str) or not plano_acao.strip():
        return None, _resposta_planejamento_invalido(
            "ACTION_PLANNER_OBRIGATORIO",
            "Chame o action_planner antes do E2E e repasse seu JSON integral.",
        )

    texto = _remover_cerca_markdown(plano_acao)
    try:
        plano = json.loads(texto)
    except json.JSONDecodeError as exc:
        return None, _resposta_planejamento_invalido(
            "PLANO_ACAO_INVALIDO",
            f"O retorno do action_planner não é JSON válido: {exc.msg}.",
        )
    if not isinstance(plano, dict):
        return None, _resposta_planejamento_invalido(
            "PLANO_ACAO_INVALIDO",
            "O retorno do action_planner deve ser um objeto JSON.",
        )

    validacao = plan_validator(json.dumps(plano, ensure_ascii=False))
    if not validacao["valid"]:
        return None, _resposta_planejamento_invalido(
            "PLANO_ACAO_INVALIDO",
            "O plano do action_planner falhou na validação: "
            + " ".join(validacao["errors"]),
        )

    if "e2e_test_generator" not in plano.get("tools", []):
        return None, _resposta_planejamento_invalido(
            "E2E_NAO_SELECIONADO_PELO_PLANNER",
            "O action_planner não selecionou e2e_test_generator neste plano.",
        )

    lifecycle = plano.get("lifecycle", {})
    if (
        lifecycle.get("status") != "planejado_para_execucao"
        or lifecycle.get("execution_allowed") is not True
        or lifecycle.get("next_step") != "executar_plano"
    ):
        return None, _resposta_planejamento_invalido(
            "E2E_NAO_AUTORIZADO_PELO_PLANNER",
            "O action_planner ainda não autorizou a execução da etapa E2E.",
        )

    handoff = plano.get("handoff_context")
    if not isinstance(handoff, dict) or not handoff:
        return None, _resposta_planejamento_invalido(
            "HANDOFF_ACTION_PLANNER_AUSENTE",
            "O action_planner precisa fornecer handoff_context para o E2E.",
        )
    return plano, None


def gerar_testes_e2e(
    requisitos: str,
    plano_acao: str,
    codigo_fonte: str = "",
    tipo_sistema: str = "",
    framework_alvo: str = "playwright",
    base_url: str = "",
    rotas_ou_telas: str = "",
    perfis_usuario: str = "",
    dados_teste: str = "",
    contratos_api: str = "",
    ambiente_execucao: str = "",
    comando_execucao: str = "",
    restricoes: str = "",
) -> dict:
    """Materializa cenários/specs após o planejamento obrigatório do QA.

    Args:
        requisitos: Requisitos em texto ou JSON serializado.
        plano_acao: JSON integral, validado e autorizado pelo action_planner.
        codigo_fonte: Código relevante em texto ou JSON serializado.
        tipo_sistema: web, api, fullstack, cli ou agentico; vazio para inferir.
        framework_alvo: Framework desejado; o MVP aceita apenas playwright.
        base_url: URL base do sistema web, quando conhecida.
        rotas_ou_telas: Rotas/telas em texto ou JSON serializado.
        perfis_usuario: Perfis de usuário em texto ou JSON serializado.
        dados_teste: Massa de teste em texto ou JSON serializado.
        contratos_api: Endpoints e contratos em texto ou JSON serializado.
        ambiente_execucao: Ambiente em texto ou JSON; apenas avaliado.
        comando_execucao: Perfil Playwright permitido para execução local.
        restricoes: Restrições em texto ou JSON serializado.

    Returns:
        Cenários, código, resultado Playwright ou bloqueios estruturados.
    """

    plano_validado, resposta_bloqueada = _validar_plano_acao(plano_acao)
    if resposta_bloqueada is not None:
        return resposta_bloqueada

    campos_entrada, campos_extraidos = _aplicar_contrato_textual(
        requisitos,
        {
            "codigo_fonte": codigo_fonte,
            "tipo_sistema": tipo_sistema,
            "framework_alvo": framework_alvo,
            "base_url": base_url,
            "rotas_ou_telas": rotas_ou_telas,
            "perfis_usuario": perfis_usuario,
            "dados_teste": dados_teste,
            "contratos_api": contratos_api,
            "ambiente_execucao": ambiente_execucao,
            "comando_execucao": comando_execucao,
            "restricoes": restricoes,
        },
    )
    try:
        entrada = EntradaE2E(
            requisitos=requisitos,
            **campos_entrada,
        )
        normalizada = normalizar_entrada_e2e(entrada)
    except ValidationError as exc:
        campos = ", ".join(
            ".".join(str(parte) for parte in erro["loc"])
            for erro in exc.errors(include_url=False)
        )
        return _resposta_entrada_invalida(
            f"Campos inválidos no contrato de entrada: {campos or 'não identificados'}."
        )
    except (TypeError, ValueError) as exc:
        return _resposta_entrada_invalida(str(exc))

    analise = analisar_superficie_sistema(normalizada)
    validacao = validar_contrato_e2e(normalizada, analise)
    cenarios = mapear_cenarios_e2e(normalizada, analise, validacao)
    ids_requisitos = [item.id for item in normalizada.requisitos]
    arquivos_sugeridos = (
        _arquivos_sugeridos(ids_requisitos) if validacao.pode_gerar_plano else []
    )
    arquivos_gerados: list[str] = []
    bloqueios = list(validacao.bloqueios)
    geracao: dict[str, Any] | None = None
    resultado_execucao = None

    if validacao.pode_gerar_codigo:
        try:
            resultado_geracao = gerar_playwright_spec(
                normalizada,
                cenarios,
                _nome_base(ids_requisitos),
            )
            arquivos_gerados = [resultado_geracao.arquivo]
            geracao = resultado_geracao.model_dump(mode="json")
        except (OSError, ValueError) as exc:
            bloqueios.append(
                BloqueioE2E(
                    codigo="ERRO_GERACAO_PLAYWRIGHT",
                    categoria=CategoriaBloqueio.GERACAO_CODIGO,
                    mensagem=f"Não foi possível gravar o spec Playwright: {exc}",
                    campos_ausentes=[],
                )
            )

    if arquivos_gerados and validacao.pode_executar:
        resultado_execucao = executar_playwright(
            normalizada,
            arquivos_gerados[0],
        )
        if resultado_execucao.status == "bloqueado_infraestrutura":
            bloqueios.append(
                BloqueioE2E(
                    codigo="RUNTIME_PLAYWRIGHT_AUSENTE",
                    categoria=CategoriaBloqueio.EXECUCAO,
                    mensagem=" ".join(resultado_execucao.logs_resumidos),
                    campos_ausentes=["node", "@playwright/test", "chromium"],
                    impede_codigo=False,
                )
            )
        elif resultado_execucao.status in {"timeout", "erro_execucao"}:
            bloqueios.append(
                BloqueioE2E(
                    codigo=(
                        "TIMEOUT_EXECUCAO_PLAYWRIGHT"
                        if resultado_execucao.status == "timeout"
                        else "ERRO_EXECUCAO_PLAYWRIGHT"
                    ),
                    categoria=CategoriaBloqueio.EXECUCAO,
                    mensagem="A execução Playwright não terminou normalmente.",
                    campos_ausentes=[],
                    impede_codigo=False,
                )
            )

    if resultado_execucao and resultado_execucao.status != "bloqueado_infraestrutura":
        tipo_saida = TipoSaida.EXECUTADO
        resumo = (
            f"Playwright executado com status '{resultado_execucao.status}' para "
            f"{len(normalizada.requisitos)} requisito(s)."
        )
    elif arquivos_gerados:
        tipo_saida = TipoSaida.CODIGO_PLAYWRIGHT
        resumo = (
            f"Spec Playwright gerado para {len(normalizada.requisitos)} requisito(s) "
            f"em uma superfície {analise.tipo_sistema.value}."
        )
    elif validacao.pode_gerar_plano:
        tipo_saida = TipoSaida.PLANO_E2E
        resumo = (
            f"Plano E2E criado para {len(normalizada.requisitos)} requisito(s) "
            f"em uma superfície {analise.tipo_sistema.value}."
        )
    else:
        tipo_saida = TipoSaida.BLOQUEADO
        resumo = "O contrato recebido não permite criar um plano E2E seguro."

    validacao_metadados = validacao.model_dump(mode="json")
    if any(item.codigo == "ERRO_GERACAO_PLAYWRIGHT" for item in bloqueios):
        validacao_metadados["pode_gerar_codigo"] = False
        validacao_metadados["pode_executar"] = False
        validacao_metadados["bloqueios"] = [
            item.model_dump(mode="json") for item in bloqueios
        ]

    resposta = RespostaE2E(
        tipo_saida=tipo_saida,
        framework_alvo=normalizada.framework_alvo,
        nivel_confianca=validacao.nivel_confianca,
        tipo_sistema=analise.tipo_sistema,
        resumo=resumo,
        cenarios=cenarios,
        precondicoes=_unicos(
            [item for cenario in cenarios for item in cenario.precondicoes]
        ),
        mocks_stubs=_unicos(
            [item for cenario in cenarios for item in cenario.mocks_stubs]
        ),
        arquivos_sugeridos=arquivos_sugeridos,
        arquivos_gerados=arquivos_gerados,
        resultado_execucao=resultado_execucao,
        bloqueios=bloqueios,
        metadados={
            "fase_implementacao": "execucao_playwright",
            "planejamento_acao": {
                "planner": "action_planner",
                "validado": True,
                "tools": plano_validado["tools"],
                "execution_allowed": plano_validado["lifecycle"]["execution_allowed"],
            },
            "capacidades": {
                "plano_e2e": True,
                "codigo_playwright": True,
                "execucao_playwright": True,
            },
            "origem_classificacao": analise.origem_classificacao,
            "sinais_superficie": analise.sinais_encontrados,
            "campos_extraidos_requisitos": campos_extraidos,
            "resultado_terminal": True,
            "nao_reexecutar": True,
            "validacao_contrato": validacao_metadados,
            "geracao_playwright": geracao,
            "execucao_playwright": (
                resultado_execucao.model_dump(mode="json")
                if resultado_execucao
                else None
            ),
        },
    )
    return resposta.model_dump(mode="json")
