"""Executa a etapa E2E previamente autorizada pelo action_planner."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from google.adk.tools.tool_context import ToolContext
from pydantic import ValidationError
from shared.tools.planner_tools import plan_validator

from ..schemas import (
    AlvoNavegacao,
    BloqueioE2E,
    CategoriaBloqueio,
    EntradaAutonomaE2E,
    EntradaE2E,
    EntradaE2ENormalizada,
    FrameworkAlvo,
    NivelConfianca,
    ProjetoInspecionadoE2E,
    RespostaE2E,
    ResultadoExecucaoE2E,
    TipoSaida,
    TipoSistema,
)
from .analisar_superficie_sistema import analisar_superficie_sistema
from .executar_playwright import executar_playwright
from .extrair_contrato_textual import extrair_contrato_textual_e2e
from .gerar_playwright_spec import gerar_playwright_spec
from .gerenciar_runtime_alvo import iniciar_runtime_alvo
from .inspecionar_projeto_e2e import inspecionar_projeto_e2e
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


def _hash_arquivo(caminho: str | None) -> str | None:
    if not caminho:
        return None
    arquivo = Path(caminho)
    if not arquivo.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with arquivo.open("rb") as stream:
            for bloco in iter(lambda: stream.read(64 * 1024), b""):
                digest.update(bloco)
    except OSError:
        return None
    return digest.hexdigest()


def _cobertura_cenarios(
    cenarios: list,
    geracao: dict[str, Any] | None,
    resultado: ResultadoExecucaoE2E | None,
) -> dict[str, Any]:
    planejados = len(cenarios)
    ativos = int((geracao or {}).get("testes_ativos", 0) or 0)
    pulados = int((geracao or {}).get("testes_pulados", 0) or 0)
    percentual = round((ativos / planejados) * 100, 2) if planejados else 0.0
    if not geracao or ativos == 0:
        status = "sem_automacao"
    elif pulados == 0 and ativos == planejados:
        status = "completa"
    else:
        status = "parcial"
    return {
        "status": status,
        "cenarios_planejados": planejados,
        "testes_ativos": ativos,
        "testes_pulados": pulados,
        "percentual_automatizado": percentual,
        "execucao_aprovada": bool(
            resultado is not None and resultado.status == "aprovado"
        ),
    }


def _erro_coerencia_execucao(
    geracao: dict[str, Any] | None,
    resultado: ResultadoExecucaoE2E | None,
) -> str | None:
    if (
        geracao is None
        or resultado is None
        or resultado.status
        in {"bloqueado_infraestrutura", "timeout", "erro_execucao"}
    ):
        return None
    ativos = int(geracao.get("testes_ativos", 0) or 0)
    pulados = int(geracao.get("testes_pulados", 0) or 0)
    esperado = ativos + pulados
    if ativos <= 0:
        return "A execução terminou sem nenhum teste ativo gerado."
    if resultado.testes_executados != esperado:
        return (
            "O relatório contabilizou "
            f"{resultado.testes_executados} teste(s), mas o spec declarou {esperado}."
        )
    if resultado.testes_pulados != pulados:
        return (
            "O relatório contabilizou "
            f"{resultado.testes_pulados} teste(s) pulado(s), mas o spec declarou "
            f"{pulados}."
        )
    observados_ativos = resultado.testes_aprovados + resultado.testes_falhos
    if observados_ativos != ativos:
        return (
            "O relatório contabilizou "
            f"{observados_ativos} teste(s) ativo(s), mas o spec declarou {ativos}."
        )
    return None


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


_MARCADORES_ENVELOPE_AUTONOMO = {
    "origem",
    "id_execucao",
    "workspace_projeto",
    "contexto_runtime",
    "politica_execucao",
    "metadados",
}

_CAMPOS_PAYLOAD_E2E_PARCIAL = {
    "codigo_fonte",
    "source_code",
    "tipo_sistema",
    "base_url",
    "rotas_ou_telas",
    "dados_teste",
    "contratos_api",
    "contratos_negativos",
    "negative_contracts",
    "ambiente_execucao",
    "comando_execucao",
    "contexto_runtime",
}

_ALIASES_PAYLOAD_E2E = {
    "requisitos": ("requisitos", "requisito", "requirement", "objetivo", "descricao"),
    "codigo_fonte": ("codigo_fonte", "source_code"),
    "tipo_sistema": ("tipo_sistema", "system_type"),
    "framework_alvo": ("framework_alvo", "target_framework"),
    "base_url": ("base_url",),
    "rotas_ou_telas": ("rotas_ou_telas", "routes_or_screens"),
    "perfis_usuario": ("perfis_usuario", "user_profiles"),
    "dados_teste": ("dados_teste", "test_data"),
    "contratos_api": ("contratos_api", "api_contracts"),
    "contratos_negativos": ("contratos_negativos", "negative_contracts"),
    "ambiente_execucao": ("ambiente_execucao", "execution_environment"),
    "comando_execucao": ("comando_execucao", "execution_command"),
    "restricoes": ("restricoes", "restrictions"),
    "origem": ("origem", "origin"),
    "id_execucao": ("id_execucao", "execution_id"),
    "workspace_projeto": ("workspace_projeto", "project_workspace"),
    "contexto_runtime": ("contexto_runtime", "runtime_context"),
    "politica_execucao": ("politica_execucao", "execution_policy"),
    "metadados": ("metadados", "metadata"),
}

_EXTENSOES_CODIGO_ROTULADO = (
    "cs",
    "go",
    "html",
    "java",
    "js",
    "jsx",
    "php",
    "py",
    "rb",
    "svelte",
    "ts",
    "tsx",
    "vue",
)
_PADRAO_ARQUIVO_ROTULADO = re.compile(
    r"(?im)^[ \t]*"
    r"(?:(?:c[oó]digo(?:[ -]fonte)?|source[ _-]?code)\s*:\s*"
    r"(?:\r?\n[ \t]*)?)?"
    r"(?:arquivo|file)\s*:\s*"
    r"`?(?P<nome>[A-Za-z0-9_. -]+(?:[\\/][A-Za-z0-9_. -]+)*\."
    rf"(?:{'|'.join(_EXTENSOES_CODIGO_ROTULADO)}))`?"
    r"(?P<resto>[^\r\n]*)$"
)
_PADRAO_SECAO_APOS_CODIGO = re.compile(
    r"(?im)^[ \t]*(?:"
    r"api[ _-]?contracts?|"
    r"ambiente(?:[ _-]de)?[ _-]execu[cç][aã]o|"
    r"comando(?:[ _-]de)?[ _-]execu[cç][aã]o|"
    r"configura[cç][aã]o(?:[ _-]de)?[ _-]execu[cç][aã]o|"
    r"contratos?(?:[ _-]de)?[ _-]api|"
    r"contratos?[ _-]negativos?|"
    r"negative[ _-]contracts?|"
    r"restri[cç][oõ]es"
    r")\s*:"
)


def _nome_arquivo_codigo_rotulado(valor: str) -> str | None:
    """Aceita somente caminhos relativos simples de arquivos de código."""

    nome = valor.strip().strip("`\"'").replace("\\", "/")
    if (
        not nome
        or len(nome) > 255
        or nome.startswith("/")
        or re.match(r"^[A-Za-z]:", nome)
    ):
        return None
    partes = nome.split("/")
    if any(
        parte in {"", ".", ".."}
        or not re.fullmatch(r"[A-Za-z0-9_. -]+", parte)
        for parte in partes
    ):
        return None
    extensao = partes[-1].rsplit(".", maxsplit=1)[-1].lower()
    if extensao not in _EXTENSOES_CODIGO_ROTULADO:
        return None
    return nome


def _extrair_blocos_codigo_rotulados(
    texto: str,
) -> tuple[list[dict[str, str]], str]:
    """Separa blocos explicitamente rotulados sem tratar prosa como código."""

    if not isinstance(texto, str) or not texto.strip():
        return [], texto
    texto_limitado = texto[:1_000_000]
    correspondencias = list(_PADRAO_ARQUIVO_ROTULADO.finditer(texto_limitado))
    if not correspondencias:
        return [], texto

    codigos: list[dict[str, str]] = []
    intervalos_remocao: list[tuple[int, int]] = []
    for indice, correspondencia in enumerate(correspondencias):
        nome = _nome_arquivo_codigo_rotulado(correspondencia.group("nome"))
        if nome is None:
            continue
        limite = (
            correspondencias[indice + 1].start()
            if indice + 1 < len(correspondencias)
            else len(texto_limitado)
        )
        sufixo = texto_limitado[correspondencia.end() : limite]
        secao_seguinte = _PADRAO_SECAO_APOS_CODIGO.search(sufixo)
        if secao_seguinte is not None:
            sufixo = sufixo[: secao_seguinte.start()]
            limite = correspondencia.end() + secao_seguinte.start()

        resto_linha = correspondencia.group("resto").strip()
        conteudo = "\n".join(
            parte for parte in (resto_linha, sufixo.strip()) if parte
        )
        conteudo = _remover_cerca_markdown(conteudo)
        if not conteudo or len(conteudo) > 200_000:
            continue
        codigos.append({"nome": nome, "conteudo": conteudo})
        intervalos_remocao.append((correspondencia.start(), limite))

    if not codigos:
        return [], texto
    partes_restantes: list[str] = []
    cursor = 0
    for inicio, fim in sorted(intervalos_remocao):
        partes_restantes.append(texto_limitado[cursor:inicio])
        cursor = max(cursor, fim)
    partes_restantes.append(texto_limitado[cursor:])
    restante = "\n".join(parte.strip() for parte in partes_restantes if parte.strip())
    restante = re.sub(
        r"(?im)^[ \t]*(?:c[oó]digo(?:[ -]fonte)?|source[ _-]?code)\s*:\s*$",
        "",
        restante,
    ).strip()
    return codigos, restante


def _requisito_util_apos_extracao(texto: str) -> str | None:
    """Evita promover seções técnicas remanescentes a requisito funcional."""

    limpo = texto.strip()
    if not limpo:
        return None
    secao_tecnica = _PADRAO_SECAO_APOS_CODIGO.search(limpo)
    if secao_tecnica is not None:
        limpo = limpo[: secao_tecnica.start()].strip()
    limpo = re.sub(
        r"(?im)^[ \t]*(?:c[oó]digo(?:[ -]fonte)?|source[ _-]?code)\s*:\s*$",
        "",
        limpo,
    ).strip()
    if not limpo:
        return None
    return limpo


def _separar_codigo_do_requisito_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Recupera código rotulado que foi transportado dentro de requisitos."""

    separado = dict(payload)
    requisitos_textuais = separado.get("requisitos")
    if not isinstance(requisitos_textuais, str):
        return separado
    codigos_rotulados, requisito_restante = _extrair_blocos_codigo_rotulados(
        requisitos_textuais
    )
    if codigos_rotulados and _valor_ausente(separado.get("codigo_fonte")):
        separado["codigo_fonte"] = codigos_rotulados
    if codigos_rotulados:
        separado["requisitos"] = _requisito_util_apos_extracao(requisito_restante)
    return separado


def _extrair_payload_de_codigo_rotulado(valor: Any) -> dict[str, Any] | None:
    """Busca blocos de arquivo em texto puro ou em wrappers intermediários."""

    raiz = _decodificar_objeto(valor)
    fila: list[tuple[Any, int]] = [(raiz, 0)]
    visitados = 0
    codigos: list[dict[str, str]] = []
    requisito: str | None = None
    assinaturas: set[tuple[str, str]] = set()
    while fila and visitados < 80:
        atual, profundidade = fila.pop(0)
        visitados += 1
        if isinstance(atual, str):
            blocos, restante = _extrair_blocos_codigo_rotulados(atual)
            for bloco in blocos:
                assinatura = (bloco["nome"], bloco["conteudo"])
                if assinatura not in assinaturas:
                    codigos.append(bloco)
                    assinaturas.add(assinatura)
            if blocos and requisito is None:
                requisito = _requisito_util_apos_extracao(restante)
            continue
        if profundidade >= 6:
            continue
        if isinstance(atual, dict):
            chaves_prioritarias = (
                "entrada_original",
                "requisitos",
                "requisito",
                "descricao",
                "content",
            )
            chaves = [
                *[chave for chave in chaves_prioritarias if chave in atual],
                *[chave for chave in atual if chave not in chaves_prioritarias],
            ]
            fila.extend((atual[chave], profundidade + 1) for chave in chaves)
        elif isinstance(atual, list):
            fila.extend((item, profundidade + 1) for item in atual[:30])
    if not codigos:
        return None
    payload: dict[str, Any] = {"codigo_fonte": codigos}
    if requisito:
        payload["requisitos"] = requisito
    return payload


def _requisito_derivado_payload_parcial(payload: dict[str, Any]) -> str:
    contratos = payload.get("contratos_negativos") or payload.get(
        "negative_contracts"
    )
    nomes: list[str] = []
    if isinstance(contratos, list):
        for contrato in contratos:
            if isinstance(contrato, dict):
                nome = contrato.get("nome") or contrato.get("name")
                if isinstance(nome, str) and nome.strip():
                    nomes.append(nome.strip())
    if nomes:
        return "Validar os contratos E2E explícitos: " + "; ".join(nomes) + "."
    if not _valor_ausente(
        payload.get("codigo_fonte") or payload.get("source_code")
    ):
        return "Validar o comportamento E2E observável no código-fonte fornecido."
    return "Validar o comportamento E2E descrito na entrada estruturada."


def _extrair_payload_e2e_parcial(valor: Any) -> dict[str, Any] | None:
    raiz = _decodificar_objeto(valor)
    candidatos = [raiz]
    if isinstance(raiz, dict):
        for chave in ("entrada", "input", "payload", "request"):
            filho = _decodificar_objeto(raiz.get(chave))
            if isinstance(filho, dict):
                candidatos.insert(0, filho)

    for candidato in candidatos:
        if not isinstance(candidato, dict):
            continue
        if not _CAMPOS_PAYLOAD_E2E_PARCIAL.intersection(candidato):
            continue
        payload: dict[str, Any] = {}
        for campo, aliases in _ALIASES_PAYLOAD_E2E.items():
            for alias in aliases:
                if alias in candidato and not _valor_ausente(candidato[alias]):
                    payload[campo] = candidato[alias]
                    break

        payload = _separar_codigo_do_requisito_payload(payload)
        if _valor_ausente(payload.get("requisitos")):
            payload["requisitos"] = _requisito_derivado_payload_parcial(payload)

        codigo = payload.get("codigo_fonte")
        nome_arquivo = (
            candidato.get("nome_arquivo")
            or candidato.get("arquivo")
            or candidato.get("filename")
        )
        if (
            isinstance(codigo, str)
            and isinstance(nome_arquivo, str)
            and nome_arquivo.strip()
        ):
            payload["codigo_fonte"] = {
                "nome": nome_arquivo.strip(),
                "conteudo": codigo,
            }
        return payload
    return None


def _normalizar_envelope_autonomo(
    requisitos: Any,
    codigo_fonte: Any,
) -> tuple[EntradaAutonomaE2E, bool, str]:
    """Adapta entrada legada e envelope interagentes para o mesmo contrato."""

    decodificado = _decodificar_objeto(requisitos)
    eh_envelope = (
        isinstance(decodificado, dict)
        and "requisitos" in decodificado
        and bool(_MARCADORES_ENVELOPE_AUTONOMO.intersection(decodificado))
    )
    if eh_envelope:
        payload = _separar_codigo_do_requisito_payload(dict(decodificado))
        if _valor_ausente(payload.get("codigo_fonte")) and not _valor_ausente(
            codigo_fonte
        ):
            payload["codigo_fonte"] = codigo_fonte
        return EntradaAutonomaE2E.model_validate(payload), True, "envelope_canonico"

    parcial = _extrair_payload_e2e_parcial(decodificado)
    if parcial is not None:
        if _valor_ausente(parcial.get("codigo_fonte")) and not _valor_ausente(
            codigo_fonte
        ):
            parcial["codigo_fonte"] = codigo_fonte
        return (
            EntradaAutonomaE2E.model_validate(parcial),
            True,
            "payload_estruturado_parcial",
        )
    return (
        EntradaAutonomaE2E(
            requisitos=requisitos,
            codigo_fonte=None if _valor_ausente(codigo_fonte) else codigo_fonte,
        ),
        False,
        "entrada_legada",
    )


def _aplicar_descobertas_de_projeto(
    normalizada: EntradaE2ENormalizada,
    inspecao: ProjetoInspecionadoE2E,
) -> list[str]:
    """Usa descobertas apenas para preencher lacunas, nunca para sobrescrever fatos."""

    aplicadas: list[str] = []
    rotas_existentes = {
        alvo.rota for alvo in normalizada.rotas_ou_telas if alvo.rota is not None
    }
    for rota in inspecao.rotas:
        if rota.metodo not in (None, "GET") or rota.rota in rotas_existentes:
            continue
        normalizada.rotas_ou_telas.append(
            AlvoNavegacao(
                nome=f"Rota descoberta {rota.rota}",
                rota=rota.rota,
            )
        )
        rotas_existentes.add(rota.rota)
        aplicadas.append(f"rota:{rota.rota}")

    contratos_existentes = {
        (
            str(contrato.get("metodo") or contrato.get("method") or "").upper(),
            str(
                contrato.get("rota")
                or contrato.get("endpoint")
                or contrato.get("path")
                or ""
            ),
        )
        for contrato in normalizada.contratos_api
    }
    for contrato in inspecao.contratos_api:
        if contrato.metodo.upper() not in {"GET", "HEAD"}:
            # A inspeção não conhece o corpo obrigatório de métodos de escrita.
            # Promovê-los a teste positivo inventaria uma requisição sem contrato.
            continue
        chave = (contrato.metodo.upper(), contrato.rota)
        if chave in contratos_existentes:
            continue
        normalizada.contratos_api.append(contrato.model_dump(mode="json"))
        contratos_existentes.add(chave)
        aplicadas.append(f"contrato_api:{contrato.metodo}:{contrato.rota}")

    if (
        not normalizada.base_url
        and inspecao.perfil_inicializacao == "uvicorn"
        and inspecao.entrypoint
    ):
        normalizada.base_url = "http://127.0.0.1:8000"
        aplicadas.append("base_url:http://127.0.0.1:8000")
    return aplicadas


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
    campos_ausentes: list[str] | None = None,
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
                campos_ausentes=campos_ausentes or ["plano_acao"],
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


_CAMPOS_ASSINATURA_PLANO = {
    "tipo_entrada",
    "modo",
    "tools",
    "lifecycle",
    "hitl_checkpoint",
    "analise_inicial",
    "analise_progressiva",
    "criterios_verificaveis",
    "objetivo_qa",
    "estrategia",
    "checklist_inicial",
    "relatorio_conformidade_esperado",
    "doubt",
}


def _decodificar_json_aninhado(valor: Any) -> Any:
    if not isinstance(valor, str):
        return valor
    texto = _remover_cerca_markdown(valor)
    if not texto or texto[0] not in '[{"':
        return valor
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return valor


def _extrair_fragmentos_json(texto: str) -> list[tuple[Any, int]]:
    """Extrai objetos/arrays JSON balanceados de um handoff textual."""

    fragmentos: list[tuple[Any, int]] = []
    pilha: list[str] = []
    inicio: int | None = None
    dentro_string = False
    escape = False
    pares = {"}": "{", "]": "["}

    for indice, caractere in enumerate(texto[:1_000_000]):
        if inicio is None:
            if caractere in "[{":
                inicio = indice
                pilha = [caractere]
                dentro_string = False
                escape = False
            continue

        if dentro_string:
            if escape:
                escape = False
            elif caractere == "\\":
                escape = True
            elif caractere == '"':
                dentro_string = False
            continue
        if caractere == '"':
            dentro_string = True
        elif caractere in "[{":
            pilha.append(caractere)
        elif caractere in "]}":
            if not pilha or pilha[-1] != pares[caractere]:
                inicio = None
                pilha = []
                continue
            pilha.pop()
            if not pilha:
                bruto = texto[inicio : indice + 1]
                try:
                    fragmentos.append((json.loads(bruto), inicio))
                except json.JSONDecodeError:
                    pass
                if len(fragmentos) >= 20:
                    break
                inicio = None
    return fragmentos


def _extrair_envelope_autonomo_aninhado(
    valor: Any,
) -> tuple[dict[str, Any] | None, str]:
    """Localiza o envelope integral mesmo dentro de wrappers ou texto do ADK."""

    raiz = _decodificar_json_aninhado(valor)
    if isinstance(raiz, str):
        fila = [
            (fragmento, f"$texto[{posicao}]", 0)
            for fragmento, posicao in _extrair_fragmentos_json(raiz)
        ]
    else:
        fila = [(raiz, "$", 0)]

    visitados = 0
    while fila and visitados < 80:
        atual, caminho, profundidade = fila.pop(0)
        visitados += 1
        atual = _decodificar_json_aninhado(atual)
        if isinstance(atual, dict):
            if (
                "requisitos" in atual
                and bool(_MARCADORES_ENVELOPE_AUTONOMO.intersection(atual))
            ):
                return atual, caminho
            if profundidade >= 6:
                continue
            chaves_prioritarias = (
                "entrada_original",
                "requisitos",
                "request",
                "content",
                "plano_acao",
                "validated_plan",
            )
            chaves = [
                *[chave for chave in chaves_prioritarias if chave in atual],
                *[chave for chave in atual if chave not in chaves_prioritarias],
            ]
            for chave in chaves:
                filho = atual[chave]
                if isinstance(filho, (dict, list)) or (
                    isinstance(filho, str)
                    and ("{" in filho or "[" in filho or "```" in filho)
                ):
                    fila.append((filho, f"{caminho}.{chave}", profundidade + 1))
        elif isinstance(atual, list) and profundidade < 6:
            for indice, filho in enumerate(atual[:30]):
                fila.append((filho, f"{caminho}[{indice}]", profundidade + 1))
        elif isinstance(atual, str) and profundidade < 6:
            for fragmento, posicao in _extrair_fragmentos_json(atual):
                fila.append(
                    (
                        fragmento,
                        f"{caminho}.$texto[{posicao}]",
                        profundidade + 1,
                    )
                )
    return None, "$"


def _extrair_plano_aninhado(valor: Any) -> tuple[dict[str, Any] | None, str]:
    """Localiza o plano quando o ADK repassa um recibo ou wrapper intermediário."""

    raiz = _decodificar_json_aninhado(valor)
    if isinstance(raiz, str):
        fila = [
            (fragmento, f"$texto[{posicao}]", 0)
            for fragmento, posicao in _extrair_fragmentos_json(raiz)
        ]
    else:
        fila = [(raiz, "$", 0)]
    melhor: tuple[int, dict[str, Any], str] | None = None
    visitados = 0

    while fila and visitados < 50:
        atual, caminho, profundidade = fila.pop(0)
        visitados += 1
        atual = _decodificar_json_aninhado(atual)
        if isinstance(atual, dict):
            pontuacao = len(_CAMPOS_ASSINATURA_PLANO.intersection(atual))
            if pontuacao and (melhor is None or pontuacao > melhor[0]):
                melhor = (pontuacao, atual, caminho)
            if profundidade >= 4:
                continue
            chaves_prioritarias = (
                "validated_plan",
                "plano_acao",
                "plano",
                "action_plan",
                "result",
                "output",
                "response",
                "content",
            )
            chaves = [
                *[chave for chave in chaves_prioritarias if chave in atual],
                *[chave for chave in atual if chave not in chaves_prioritarias],
            ]
            for chave in chaves:
                filho = atual[chave]
                if isinstance(filho, (dict, list)) or (
                    isinstance(filho, str)
                    and filho.strip().startswith(("{", "[", "```"))
                ):
                    fila.append((filho, f"{caminho}.{chave}", profundidade + 1))
        elif isinstance(atual, list) and profundidade < 4:
            for indice, filho in enumerate(atual[:20]):
                fila.append((filho, f"{caminho}[{indice}]", profundidade + 1))

    if melhor is None:
        return None, "$"
    return melhor[1], melhor[2]


def _texto_do_tool_context(tool_context: ToolContext | None) -> str:
    if tool_context is None:
        return ""
    conteudo = tool_context.user_content
    if conteudo is None or not conteudo.parts:
        return ""
    return "\n".join(
        parte.text.strip()
        for parte in conteudo.parts
        if parte.text and parte.text.strip()
    )


def _validar_plano_acao(
    plano_acao: Any,
) -> tuple[dict[str, Any] | None, dict | None, str]:
    if _valor_ausente(plano_acao):
        return (
            None,
            _resposta_planejamento_invalido(
                "ACTION_PLANNER_OBRIGATORIO",
                "Chame o action_planner antes do E2E e repasse seu JSON integral.",
            ),
            "$",
        )

    plano, origem_estrutura = _extrair_plano_aninhado(plano_acao)
    if plano is None:
        return (
            None,
            _resposta_planejamento_invalido(
                "PLANO_ACAO_INVALIDO",
                "Não foi possível localizar um objeto de plano no retorno do planner.",
            ),
            origem_estrutura,
        )

    validacao = plan_validator(json.dumps(plano, ensure_ascii=False))
    if not validacao["valid"]:
        return (
            None,
            _resposta_planejamento_invalido(
                "PLANO_ACAO_INVALIDO",
                "O plano do action_planner falhou na validação "
                f"(estrutura: {origem_estrutura}): "
                + " ".join(validacao["errors"]),
                ["plano_acao.estrutura"],
            ),
            origem_estrutura,
        )

    plano_normalizado = validacao.get("validated_plan")
    if isinstance(plano_normalizado, dict):
        plano = plano_normalizado

    if "e2e_test_generator" not in plano.get("tools", []):
        return (
            None,
            _resposta_planejamento_invalido(
                "E2E_NAO_SELECIONADO_PELO_PLANNER",
                "O action_planner não selecionou e2e_test_generator neste plano.",
            ),
            origem_estrutura,
        )

    lifecycle = plano.get("lifecycle", {})
    if (
        lifecycle.get("status") != "planejado_para_execucao"
        or lifecycle.get("execution_allowed") is not True
        or lifecycle.get("next_step") != "executar_plano"
    ):
        return (
            None,
            _resposta_planejamento_invalido(
                "E2E_NAO_AUTORIZADO_PELO_PLANNER",
                "O action_planner ainda não autorizou a execução da etapa E2E.",
            ),
            origem_estrutura,
        )

    handoff = plano.get("handoff_context")
    if not isinstance(handoff, dict) or not handoff:
        return (
            None,
            _resposta_planejamento_invalido(
                "HANDOFF_ACTION_PLANNER_AUSENTE",
                "O action_planner precisa fornecer handoff_context para o E2E.",
            ),
            origem_estrutura,
        )
    return plano, None, origem_estrutura


def _mesclar_campos_ausentes(
    destino: dict[str, Any],
    complemento: dict[str, Any],
) -> None:
    """Mescla somente lacunas, preservando a fonte canônica de maior prioridade."""

    for campo, valor in complemento.items():
        if _valor_ausente(valor):
            continue
        existente = destino.get(campo)
        if _valor_ausente(existente):
            destino[campo] = valor
        elif isinstance(existente, dict) and isinstance(valor, dict):
            _mesclar_campos_ausentes(existente, valor)


def _recuperar_requisitos_do_handoff(
    requisitos: Any,
    plano_validado: dict[str, Any],
    texto_contexto: str = "",
) -> tuple[Any, str]:
    """Compõe a entrada canônica com campos complementares do mesmo handoff."""

    handoff = plano_validado.get("handoff_context", {})
    entrada_original = (
        handoff.get("entrada_original") if isinstance(handoff, dict) else None
    )
    candidatos = (
        (
            entrada_original,
            "action_planner.handoff_context.entrada_original",
        ),
        (texto_contexto, "tool_context.user_content"),
        (requisitos, "argumento_requisitos"),
    )
    payload_mesclado: dict[str, Any] = {}
    origens_aplicadas: list[str] = []
    for candidato, origem in candidatos:
        envelope, caminho = _extrair_envelope_autonomo_aninhado(candidato)
        if envelope is not None:
            _mesclar_campos_ausentes(
                payload_mesclado,
                _separar_codigo_do_requisito_payload(envelope),
            )
            origens_aplicadas.append(f"{origem}:{caminho}")

        parcial = _extrair_payload_e2e_parcial(candidato)
        if parcial is not None:
            _mesclar_campos_ausentes(payload_mesclado, parcial)
            origens_aplicadas.append(
                f"{origem}:payload_estruturado_parcial"
            )

        codigo_rotulado = _extrair_payload_de_codigo_rotulado(candidato)
        if codigo_rotulado is not None:
            _mesclar_campos_ausentes(payload_mesclado, codigo_rotulado)
            origens_aplicadas.append(f"{origem}:codigo_rotulado")

    if payload_mesclado:
        if _valor_ausente(payload_mesclado.get("requisitos")):
            payload_mesclado["requisitos"] = _requisito_derivado_payload_parcial(
                payload_mesclado
            )
        return (
            json.dumps(payload_mesclado, ensure_ascii=False),
            "+".join(_unicos(origens_aplicadas)),
        )

    if not _valor_ausente(requisitos):
        return requisitos, "argumento_requisitos"

    if _valor_ausente(entrada_original):
        return "", "ausente"
    if isinstance(entrada_original, str):
        return entrada_original, "action_planner.handoff_context.entrada_original"
    return (
        json.dumps(entrada_original, ensure_ascii=False),
        "action_planner.handoff_context.entrada_original",
    )


def gerar_testes_e2e(
    requisitos: str = "",
    plano_acao: str = "",
    codigo_fonte: str = "",
    tipo_sistema: str = "",
    framework_alvo: str = "playwright",
    base_url: str = "",
    rotas_ou_telas: str = "",
    perfis_usuario: str = "",
    dados_teste: str = "",
    contratos_api: str = "",
    contratos_negativos: str = "",
    ambiente_execucao: str = "",
    comando_execucao: str = "",
    restricoes: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """Materializa cenários/specs após o planejamento obrigatório do QA.

    Args:
        requisitos: Requisitos/envelope como objeto JSON ou texto serializado.
        plano_acao: Plano/recibo como objeto JSON ou texto serializado.
        codigo_fonte: Código relevante em texto ou JSON serializado.
        tipo_sistema: web, api, fullstack, cli ou agentico; vazio para inferir.
        framework_alvo: Framework desejado; o MVP aceita apenas playwright.
        base_url: URL base do sistema web, quando conhecida.
        rotas_ou_telas: Rotas/telas em texto ou JSON serializado.
        perfis_usuario: Perfis de usuário em texto ou JSON serializado.
        dados_teste: Massa de teste em texto ou JSON serializado.
        contratos_api: Endpoints e contratos em texto ou JSON serializado.
        contratos_negativos: Cenários negativos explícitos em JSON serializado.
        ambiente_execucao: Ambiente em texto ou JSON; apenas avaliado.
        comando_execucao: Perfil Playwright permitido para execução local.
        restricoes: Restrições em texto ou JSON serializado.
        tool_context: Contexto ADK injetado automaticamente; não é argumento do LLM.

    Returns:
        Cenários, código, resultado Playwright ou bloqueios estruturados.
    """

    texto_contexto = _texto_do_tool_context(tool_context)
    plano_acao_efetivo = (
        plano_acao if not _valor_ausente(plano_acao) else texto_contexto
    )
    origem_transporte_plano = (
        "argumento_plano_acao"
        if not _valor_ausente(plano_acao)
        else "tool_context.user_content"
    )
    plano_validado, resposta_bloqueada, origem_estrutura_plano = (
        _validar_plano_acao(plano_acao_efetivo)
    )
    if resposta_bloqueada is not None:
        return resposta_bloqueada

    requisitos_efetivos, origem_requisitos = _recuperar_requisitos_do_handoff(
        requisitos,
        plano_validado,
        texto_contexto,
    )
    if _valor_ausente(requisitos_efetivos):
        return _resposta_entrada_invalida(
            "O requisito está ausente tanto no argumento 'requisitos' quanto em "
            "'handoff_context.entrada_original' do action_planner."
        )

    try:
        (
            envelope,
            envelope_detectado,
            formato_entrada_detectado,
        ) = _normalizar_envelope_autonomo(requisitos_efetivos, codigo_fonte)
        contexto = envelope.contexto_runtime
        ambiente_autonomo = (
            {
                "tipo": "local",
                "browser": "chromium",
                "auto_instalar_runtime": True,
            }
            if envelope.politica_execucao.autonomo
            else {}
        )
        campos_iniciais = {
            "codigo_fonte": envelope.codigo_fonte,
            "tipo_sistema": (
                tipo_sistema or envelope.tipo_sistema or contexto.tipo_sistema
            ),
            "framework_alvo": framework_alvo or envelope.framework_alvo,
            "base_url": base_url or envelope.base_url or contexto.base_url,
            "rotas_ou_telas": rotas_ou_telas or envelope.rotas_ou_telas,
            "perfis_usuario": perfis_usuario or envelope.perfis_usuario,
            "dados_teste": dados_teste or envelope.dados_teste,
            "contratos_api": contratos_api or envelope.contratos_api,
            "contratos_negativos": (
                contratos_negativos
                or envelope.contratos_negativos
                or envelope.metadados.get("contratos_negativos")
            ),
            "ambiente_execucao": (
                ambiente_execucao
                or envelope.ambiente_execucao
                or contexto.ambiente
                or ambiente_autonomo
            ),
            "comando_execucao": (
                comando_execucao
                or envelope.comando_execucao
                or ("npx playwright test" if ambiente_autonomo else "")
            ),
            "restricoes": restricoes or envelope.restricoes,
        }
        campos_entrada, campos_extraidos = _aplicar_contrato_textual(
            envelope.requisitos,
            campos_iniciais,
        )
        entrada = EntradaE2E(
            requisitos=envelope.requisitos,
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

    inspecao_projeto = inspecionar_projeto_e2e(
        normalizada,
        envelope.workspace_projeto,
    )
    descobertas_aplicadas = _aplicar_descobertas_de_projeto(
        normalizada,
        inspecao_projeto,
    )
    analise = analisar_superficie_sistema(normalizada)
    if (
        analise.tipo_sistema == TipoSistema.DESCONHECIDO
        and inspecao_projeto.tipo_sistema != TipoSistema.DESCONHECIDO
    ):
        normalizada.tipo_sistema_informado = inspecao_projeto.tipo_sistema
        analise = analisar_superficie_sistema(normalizada)
    elif {
        analise.tipo_sistema,
        inspecao_projeto.tipo_sistema,
    } == {TipoSistema.WEB, TipoSistema.API}:
        normalizada.tipo_sistema_informado = TipoSistema.FULLSTACK
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
    runtime_alvo = None

    base_url_descoberta = any(
        item.startswith("base_url:") for item in descobertas_aplicadas
    )
    if (
        validacao.pode_gerar_codigo
        and validacao.pode_executar
        and base_url_descoberta
    ):
        runtime_alvo = iniciar_runtime_alvo(
            normalizada,
            inspecao_projeto,
            envelope.workspace_projeto,
            envelope.politica_execucao.max_tentativas,
        )
        if runtime_alvo.status == "pronto" and runtime_alvo.base_url:
            normalizada.base_url = runtime_alvo.base_url
            descobertas_aplicadas.append(
                f"base_url_runtime:{runtime_alvo.base_url}"
            )
            cenarios = mapear_cenarios_e2e(normalizada, analise, validacao)
        else:
            resultado_execucao = ResultadoExecucaoE2E(
                status="bloqueado_infraestrutura",
                logs_resumidos=runtime_alvo.logs,
            )
            bloqueios.append(
                BloqueioE2E(
                    codigo="RUNTIME_ALVO_NAO_INICIADO",
                    categoria=CategoriaBloqueio.EXECUCAO,
                    mensagem=" ".join(runtime_alvo.logs),
                    campos_ausentes=["runtime_alvo"],
                    impede_codigo=False,
                )
            )

    try:
        if validacao.pode_gerar_codigo:
            try:
                resultado_geracao = gerar_playwright_spec(
                    normalizada,
                    cenarios,
                    _nome_base(ids_requisitos),
                )
                arquivos_gerados = [resultado_geracao.arquivo]
                geracao = resultado_geracao.model_dump(mode="json")
            except Exception as exc:  # fronteira da tool: sempre retornar estruturado
                bloqueios.append(
                    BloqueioE2E(
                        codigo="ERRO_GERACAO_PLAYWRIGHT",
                        categoria=CategoriaBloqueio.GERACAO_CODIGO,
                        mensagem=(
                            "Não foi possível gerar o spec Playwright "
                            f"({type(exc).__name__})."
                        ),
                        campos_ausentes=[],
                    )
                )

        if (
            arquivos_gerados
            and validacao.pode_executar
            and resultado_execucao is None
        ):
            try:
                resultado_execucao = executar_playwright(
                    normalizada,
                    arquivos_gerados[0],
                )
            except Exception as exc:  # fronteira da tool: não vazar exceção ao agente
                resultado_execucao = ResultadoExecucaoE2E(
                    status="erro_execucao",
                    logs_resumidos=[
                        "Falha interna controlada durante a execução "
                        f"({type(exc).__name__})."
                    ],
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
            elif resultado_execucao.status == "falhou":
                bloqueios.append(
                    BloqueioE2E(
                        codigo="TESTES_E2E_FALHARAM",
                        categoria=CategoriaBloqueio.EXECUCAO,
                        mensagem=(
                            f"{resultado_execucao.testes_falhos} teste(s) E2E "
                            "falharam; consulte as evidências estruturadas."
                        ),
                        campos_ausentes=[],
                        impede_codigo=False,
                        impede_execucao=False,
                    )
                )
    finally:
        if runtime_alvo is not None:
            runtime_alvo.encerrar()

    erro_coerencia = _erro_coerencia_execucao(geracao, resultado_execucao)
    if erro_coerencia:
        if resultado_execucao is not None:
            resultado_execucao.status = "inconsistente"
        bloqueios.append(
            BloqueioE2E(
                codigo="RELATORIO_EXECUCAO_INCONSISTENTE",
                categoria=CategoriaBloqueio.EXECUCAO,
                mensagem=erro_coerencia,
                campos_ausentes=[],
                impede_codigo=False,
            )
        )

    cobertura_cenarios = _cobertura_cenarios(
        cenarios,
        geracao,
        resultado_execucao,
    )
    integridade_artefatos = {
        "spec_sha256": _hash_arquivo(
            arquivos_gerados[0] if arquivos_gerados else None
        ),
        "relatorio_sha256": _hash_arquivo(
            resultado_execucao.arquivo_relatorio
            if resultado_execucao
            else None
        ),
    }

    if resultado_execucao and resultado_execucao.status != "bloqueado_infraestrutura":
        tipo_saida = TipoSaida.EXECUTADO
        resumo = (
            f"Playwright executado com status '{resultado_execucao.status}' para "
            f"{len(normalizada.requisitos)} requisito(s); cobertura de cenários "
            f"{cobertura_cenarios['status']} "
            f"({cobertura_cenarios['testes_ativos']} ativo(s), "
            f"{cobertura_cenarios['testes_pulados']} pulado(s))."
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
                "origem_transporte": origem_transporte_plano,
                "origem_estrutura": origem_estrutura_plano,
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
            "origem_requisitos": origem_requisitos,
            "entrada_autonoma": {
                "envelope_detectado": envelope_detectado,
                "formato_detectado": formato_entrada_detectado,
                "origem": envelope.origem.value,
                "id_execucao": envelope.id_execucao,
                "politica_execucao": envelope.politica_execucao.model_dump(
                    mode="json"
                ),
                "workspace_projeto_fornecido": bool(envelope.workspace_projeto),
                "hitl_permitido": False,
            },
            "contexto_runtime_declarado": contexto.model_dump(mode="json"),
            "inspecao_projeto": inspecao_projeto.model_dump(mode="json"),
            "descobertas_projeto_aplicadas": descobertas_aplicadas,
            "resultado_terminal": True,
            "nao_reexecutar": True,
            "validacao_contrato": validacao_metadados,
            "geracao_playwright": geracao,
            "execucao_playwright": (
                resultado_execucao.model_dump(mode="json")
                if resultado_execucao
                else None
            ),
            "cobertura_cenarios": cobertura_cenarios,
            "contratos_negativos_explicitos": len(
                normalizada.contratos_negativos
            ),
            "politica_retentativas": {
                "max_tentativas": envelope.politica_execucao.max_tentativas,
                "tentativas_runtime": (
                    runtime_alvo.tentativas if runtime_alvo is not None else 0
                ),
                "reexecucao_funcional_permitida": False,
            },
            "integridade_artefatos": integridade_artefatos,
            "runtime_alvo": (
                runtime_alvo.como_dict() if runtime_alvo is not None else None
            ),
        },
    )
    return resposta.model_dump(mode="json")
