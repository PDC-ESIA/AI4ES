"""Normalização determinística das entradas do gerador E2E."""

import json
from pathlib import PurePath
from typing import Any

from pydantic import ValidationError

from ..schemas import (
    AlvoNavegacao,
    CodigoFonteNormalizado,
    EntradaE2E,
    EntradaE2ENormalizada,
    LocalizadorPlaywright,
    PassoAutomacao,
    RequisitoNormalizado,
)

_MAX_TOTAL_CARACTERES = 500_000


def _tentar_decodificar_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    texto = value.strip()
    if not texto or texto[0] not in "[{":
        return value
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return value


def _texto_declarado(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "; ".join(texto for item in value if (texto := _texto_declarado(item)))
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip()


def _primeiro_valor(item: dict[str, Any], *chaves: str) -> Any:
    for chave in chaves:
        if chave in item and item[chave] not in (None, "", [], {}):
            return item[chave]
    return None


def _normalizar_booleano(value: Any, padrao: bool = True) -> bool:
    if value is None:
        return padrao
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalizado = value.strip().lower()
        if normalizado in {"true", "1", "sim", "yes"}:
            return True
        if normalizado in {"false", "0", "nao", "não", "no"}:
            return False
    return bool(value)


def _extrair_conteudo_requisito(item: dict[str, Any]) -> str:
    partes: list[str] = []

    titulo = _texto_declarado(_primeiro_valor(item, "titulo", "title", "nome"))
    if titulo:
        partes.append(f"Título: {titulo}")

    descricao = _texto_declarado(
        _primeiro_valor(
            item,
            "conteudo",
            "content",
            "descricao",
            "description",
            "requisito",
            "requirement",
            "texto",
        )
    )
    if descricao:
        partes.append(descricao)

    criterios = _texto_declarado(
        _primeiro_valor(
            item,
            "criterios_aceite",
            "criterios_de_aceite",
            "acceptance_criteria",
        )
    )
    if criterios:
        partes.append(f"Critérios de aceite: {criterios}")

    fluxo = _texto_declarado(
        _primeiro_valor(item, "fluxo_principal", "main_flow", "passos", "steps")
    )
    if fluxo:
        partes.append(f"Fluxo declarado: {fluxo}")

    if partes:
        return "\n".join(dict.fromkeys(partes))
    return json.dumps(item, ensure_ascii=False, sort_keys=True)


def _normalizar_requisitos(raw: Any) -> list[RequisitoNormalizado]:
    raw = _tentar_decodificar_json(raw)
    if raw in (None, "", [], {}):
        return []
    itens = raw if isinstance(raw, list) else [raw]

    requisitos: list[RequisitoNormalizado] = []
    for indice, item in enumerate(itens, start=1):
        if isinstance(item, str):
            conteudo = item.strip()
            if not conteudo:
                continue
            requisitos.append(
                RequisitoNormalizado(
                    id=f"REQ-{indice:03d}",
                    conteudo=conteudo,
                    fonte="texto",
                )
            )
            continue

        if not isinstance(item, dict):
            conteudo = _texto_declarado(item)
            if conteudo:
                requisitos.append(
                    RequisitoNormalizado(
                        id=f"REQ-{indice:03d}",
                        conteudo=conteudo,
                        fonte="valor_estruturado",
                    )
                )
            continue

        identificador = (
            _texto_declarado(
                _primeiro_valor(item, "id_artefato", "id", "requirement_id", "codigo")
            )
            or f"REQ-{indice:03d}"
        )
        tipo = (
            _texto_declarado(
                _primeiro_valor(item, "tipo", "type", "requirement_type")
            ).upper()
            or "REQUISITO"
        )
        conteudo = _extrair_conteudo_requisito(item).strip()
        if not conteudo:
            continue

        requisitos.append(
            RequisitoNormalizado(
                id=identificador,
                tipo=tipo,
                conteudo=conteudo,
                fonte="json",
                metadados={"chaves_originais": sorted(str(chave) for chave in item)},
            )
        )

    return requisitos


def _normalizar_lista_textos(raw: Any) -> list[str]:
    raw = _tentar_decodificar_json(raw)
    if raw in (None, "", [], {}):
        return []
    if isinstance(raw, str):
        partes = raw.replace("\r", "\n").replace(";", "\n").split("\n")
        return list(dict.fromkeys(parte.strip() for parte in partes if parte.strip()))
    if isinstance(raw, dict):
        raw = list(raw.values())
    if not isinstance(raw, list):
        raw = [raw]
    return list(
        dict.fromkeys(texto for item in raw if (texto := _texto_declarado(item)))
    )


_ALIASES_ACAO = {
    "fill": "preencher",
    "click": "clicar",
    "check": "marcar",
    "uncheck": "desmarcar",
    "select": "selecionar",
    "select_option": "selecionar",
    "press": "pressionar",
    "expect_visible": "verificar_visivel",
    "expect_text": "verificar_texto",
    "expect_url": "verificar_url",
}

_ALIASES_LOCALIZADOR = {
    "testid": "test_id",
    "test-id": "test_id",
    "get_by_role": "role",
    "get_by_label": "label",
    "get_by_text": "text",
    "get_by_test_id": "test_id",
    "get_by_placeholder": "placeholder",
}


def _normalizar_localizador(raw: Any) -> LocalizadorPlaywright | None:
    raw = _tentar_decodificar_json(raw)
    if not isinstance(raw, dict):
        return None

    tipo = _texto_declarado(
        _primeiro_valor(raw, "tipo", "type", "kind", "tipo_localizador")
    ).lower()
    valor = _texto_declarado(
        _primeiro_valor(raw, "valor", "value", "seletor", "selector")
    )
    if not tipo:
        for chave in ("role", "label", "text", "test_id", "placeholder"):
            if raw.get(chave):
                tipo = chave
                valor = _texto_declarado(raw[chave])
                break
    tipo = _ALIASES_LOCALIZADOR.get(tipo, tipo)
    if not tipo or not valor:
        return None

    return LocalizadorPlaywright(
        tipo=tipo,
        valor=valor,
        nome_acessivel=(
            _texto_declarado(
                _primeiro_valor(raw, "nome_acessivel", "accessible_name", "name")
            )
            or None
        ),
        exato=_normalizar_booleano(raw.get("exato", raw.get("exact"))),
    )


def _normalizar_passos_automacao(raw: Any) -> tuple[list[PassoAutomacao], list[str]]:
    raw = _tentar_decodificar_json(raw)
    if raw in (None, "", [], {}):
        return [], []
    itens = raw if isinstance(raw, list) else [raw]
    passos: list[PassoAutomacao] = []
    erros: list[str] = []

    for indice, item in enumerate(itens, start=1):
        if not isinstance(item, dict):
            erros.append(f"Passo {indice}: esperado objeto estruturado.")
            continue
        acao = _texto_declarado(
            _primeiro_valor(item, "acao", "action", "tipo", "type")
        ).lower()
        acao = _ALIASES_ACAO.get(acao, acao)
        localizador_raw = _primeiro_valor(item, "localizador", "locator")
        if localizador_raw is None and any(
            chave in item
            for chave in (
                "tipo_localizador",
                "seletor",
                "selector",
                "role",
                "label",
                "text",
                "test_id",
                "placeholder",
            )
        ):
            localizador_raw = item

        try:
            passos.append(
                PassoAutomacao(
                    acao=acao,
                    localizador=_normalizar_localizador(localizador_raw),
                    valor=_primeiro_valor(item, "valor", "value", "tecla", "key"),
                    chave_dado=(
                        _texto_declarado(
                            _primeiro_valor(
                                item,
                                "chave_dado",
                                "data_key",
                                "dado_teste",
                            )
                        )
                        or None
                    ),
                )
            )
        except (ValidationError, ValueError) as exc:
            detalhe = (
                exc.errors()[0]["type"]
                if isinstance(exc, ValidationError)
                else str(exc)
            )
            erros.append(f"Passo {indice}: contrato inválido ({detalhe}).")
    return passos, erros


def _normalizar_alvos(raw: Any) -> list[AlvoNavegacao]:
    raw = _tentar_decodificar_json(raw)
    if raw in (None, "", [], {}):
        return []
    if isinstance(raw, str):
        raw = _normalizar_lista_textos(raw)
    itens = raw if isinstance(raw, list) else [raw]

    alvos: list[AlvoNavegacao] = []
    for item in itens:
        if isinstance(item, str):
            texto = item.strip()
            if not texto:
                continue
            rota = texto if texto.startswith(("/", "http://", "https://")) else None
            alvos.append(AlvoNavegacao(nome=texto, rota=rota))
            continue
        if not isinstance(item, dict):
            continue

        rota = (
            _texto_declarado(_primeiro_valor(item, "rota", "route", "path", "url"))
            or None
        )
        nome = (
            _texto_declarado(
                _primeiro_valor(item, "nome", "name", "tela", "screen", "titulo")
            )
            or rota
        )
        if not nome:
            continue
        passos_raw = _primeiro_valor(
            item,
            "passos_automacao",
            "automation_steps",
        )
        passos_genericos = _primeiro_valor(item, "passos", "steps")
        if (
            passos_raw is None
            and isinstance(passos_genericos, list)
            and any(isinstance(passo, dict) for passo in passos_genericos)
        ):
            passos_raw = passos_genericos
        passos_automacao, erros_automacao = _normalizar_passos_automacao(passos_raw)
        acoes_raw = _primeiro_valor(item, "acoes", "actions")
        if acoes_raw is None and not passos_automacao:
            acoes_raw = passos_genericos
        alvos.append(
            AlvoNavegacao(
                nome=nome,
                rota=rota,
                seletores=_normalizar_lista_textos(
                    _primeiro_valor(item, "seletores", "selectors", "test_ids")
                ),
                acoes=_normalizar_lista_textos(acoes_raw),
                passos_automacao=passos_automacao,
                erros_automacao=erros_automacao,
            )
        )
    return alvos


def _inferir_linguagem(nome: str) -> str | None:
    extensao = PurePath(nome).suffix.lower()
    return {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".java": "java",
        ".cs": "csharp",
    }.get(extensao)


def _normalizar_codigo_fonte(raw: Any) -> list[CodigoFonteNormalizado]:
    raw = _tentar_decodificar_json(raw)
    if raw in (None, "", [], {}):
        return []
    itens = raw if isinstance(raw, list) else [raw]
    codigos: list[CodigoFonteNormalizado] = []

    for indice, item in enumerate(itens, start=1):
        if isinstance(item, str):
            conteudo = item.strip()
            if conteudo:
                codigos.append(
                    CodigoFonteNormalizado(
                        nome=f"codigo_fonte_{indice}.txt",
                        conteudo=conteudo,
                    )
                )
            continue
        if not isinstance(item, dict):
            continue
        nome = (
            _texto_declarado(
                _primeiro_valor(item, "nome", "name", "filename", "arquivo")
            )
            or f"codigo_fonte_{indice}.txt"
        )
        conteudo = _texto_declarado(
            _primeiro_valor(item, "conteudo", "content", "codigo", "code")
        )
        if not conteudo:
            continue
        linguagem = _texto_declarado(
            _primeiro_valor(item, "linguagem", "language")
        ) or _inferir_linguagem(nome)
        codigos.append(
            CodigoFonteNormalizado(
                nome=nome,
                conteudo=conteudo,
                linguagem=linguagem,
            )
        )
    return codigos


def _normalizar_lista_objetos(raw: Any) -> list[dict[str, Any]]:
    raw = _tentar_decodificar_json(raw)
    if raw in (None, "", [], {}):
        return []
    itens = raw if isinstance(raw, list) else [raw]
    normalizados: list[dict[str, Any]] = []
    for item in itens:
        if isinstance(item, dict):
            normalizados.append(item)
        else:
            texto = _texto_declarado(item)
            if texto:
                normalizados.append({"descricao": texto})
    return normalizados


def _normalizar_ambiente(raw: Any) -> dict[str, Any]:
    raw = _tentar_decodificar_json(raw)
    if raw in (None, "", {}):
        return {}
    if isinstance(raw, dict):
        return raw
    return {"tipo": _texto_declarado(raw)}


def _validar_limite(entrada: EntradaE2ENormalizada) -> None:
    total = sum(len(item.conteudo) for item in entrada.requisitos)
    total += sum(len(item.conteudo) for item in entrada.codigo_fonte)
    if total > _MAX_TOTAL_CARACTERES:
        raise ValueError("Entrada E2E excede o limite de 500.000 caracteres para o P0.")


def normalizar_entrada_e2e(
    entrada: EntradaE2E | dict[str, Any],
) -> EntradaE2ENormalizada:
    """Converte texto/JSON e metadados em um contrato comum e validável."""

    entrada_validada = (
        entrada
        if isinstance(entrada, EntradaE2E)
        else EntradaE2E.model_validate(entrada)
    )
    normalizada = EntradaE2ENormalizada(
        requisitos=_normalizar_requisitos(entrada_validada.requisitos),
        codigo_fonte=_normalizar_codigo_fonte(entrada_validada.codigo_fonte),
        tipo_sistema_informado=entrada_validada.tipo_sistema,
        framework_alvo=entrada_validada.framework_alvo,
        base_url=entrada_validada.base_url,
        rotas_ou_telas=_normalizar_alvos(entrada_validada.rotas_ou_telas),
        perfis_usuario=_normalizar_lista_textos(entrada_validada.perfis_usuario),
        dados_teste=_normalizar_lista_objetos(entrada_validada.dados_teste),
        contratos_api=_normalizar_lista_objetos(entrada_validada.contratos_api),
        ambiente_execucao=_normalizar_ambiente(entrada_validada.ambiente_execucao),
        comando_execucao=entrada_validada.comando_execucao,
        restricoes=_normalizar_lista_textos(entrada_validada.restricoes),
    )
    _validar_limite(normalizada)
    return normalizada
