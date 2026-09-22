"""Extrai somente dados E2E explicitamente declarados em prompts textuais."""

import re
import unicodedata
from typing import Any


def _capturar(texto: str, padrao: str) -> str | None:
    encontrado = re.search(padrao, texto, flags=re.IGNORECASE | re.MULTILINE)
    if not encontrado:
        return None
    return encontrado.group(1).strip().rstrip(".,;:")


def _chave_dado(nome: str) -> str:
    normalizado = unicodedata.normalize("NFKD", nome)
    sem_acentos = "".join(
        caractere for caractere in normalizado if not unicodedata.combining(caractere)
    )
    return re.sub(r"[^a-zA-Z0-9]+", "_", sem_acentos).strip("_").lower() or "valor"


def _texto_requisitos(requisitos: Any) -> str:
    """Recompõe o texto explícito mesmo quando ele chega em artefatos JSON."""
    if isinstance(requisitos, str):
        return requisitos.strip()
    if isinstance(requisitos, list):
        return "\n".join(
            texto for item in requisitos if (texto := _texto_requisitos(item))
        )
    if isinstance(requisitos, dict):
        for chave in (
            "conteudo",
            "content",
            "descricao",
            "description",
            "requisito",
            "requirement",
            "texto",
        ):
            if chave in requisitos:
                texto = _texto_requisitos(requisitos[chave])
                if texto:
                    return texto
    return ""


def _linhas_fluxo(texto: str) -> list[str]:
    numeradas = [
        encontrado.group(1).strip()
        for encontrado in re.finditer(
            r"(?:^|\s)\d+[.)]\s+(.+?)(?=\s+\d+[.)]\s+|$)",
            texto,
            flags=re.DOTALL,
        )
    ]
    if numeradas:
        return numeradas

    inicio = re.search(
        r"\b(?:verificar|validar|preencher|clicar)\b",
        texto,
        flags=re.IGNORECASE,
    )
    if not inicio:
        return []
    trecho = texto[inicio.start() :]
    fim = re.search(
        r"\.\s*(?:gere|execute|retorne)\b",
        trecho,
        flags=re.IGNORECASE,
    )
    if fim:
        trecho = trecho[: fim.start()]

    acoes = list(
        re.finditer(
            r"\b(?:verificar|validar|preencher|clicar)\b",
            trecho,
            flags=re.IGNORECASE,
        )
    )
    linhas: list[str] = []
    for indice, acao in enumerate(acoes):
        fim_acao = acoes[indice + 1].start() if indice + 1 < len(acoes) else None
        linha = trecho[acao.start() : fim_acao].strip(" ,;.\n\r")
        linha = re.sub(r"\s+e\s*$", "", linha, flags=re.IGNORECASE)
        if linha:
            linhas.append(linha)
    return linhas


def _extrair_passos(
    texto: str,
) -> tuple[list[dict[str, Any]], dict[str, str], str | None]:
    passos: list[dict[str, Any]] = []
    dados: dict[str, str] = {}
    rota_acesso: str | None = None

    for linha in _linhas_fluxo(texto):
        acesso = re.search(
            r"\bacessar\s+(?:(?:a\s+)?rota\s+)?(/[^\s.,;]+)",
            linha,
            flags=re.IGNORECASE,
        )
        if acesso:
            rota_acesso = acesso.group(1)
            continue

        preencher = re.search(
            r"""\bpreencher\s+(?:o\s+)?campo\s+com\s+nome\s+acess\S*\s+
            ["']([^"']+)["']\s+usando\s+["']([^"']+)["']""",
            linha,
            flags=re.IGNORECASE | re.VERBOSE,
        )
        if preencher:
            nome, valor = preencher.groups()
            chave = _chave_dado(nome)
            dados[chave] = valor
            passos.append(
                {
                    "acao": "preencher",
                    "localizador": {"tipo": "label", "valor": nome},
                    "chave_dado": chave,
                }
            )
            continue

        preencher_simples = re.search(
            r"""\bpreencher\s+(?:o\s+)?campo\s+["']([^"']+)["']\s+
            (?:com|usando)\s+["']([^"']+)["']""",
            linha,
            flags=re.IGNORECASE | re.VERBOSE,
        )
        if preencher_simples:
            nome, valor = preencher_simples.groups()
            chave = _chave_dado(nome)
            dados[chave] = valor
            passos.append(
                {
                    "acao": "preencher",
                    "localizador": {"tipo": "label", "valor": nome},
                    "chave_dado": chave,
                }
            )
            continue

        clicar = re.search(
            r"""\bclicar\s+(?:no|na)\s+(bot\S*|link)\s+com\s+nome\s+
            acess\S*\s+["']([^"']+)["']""",
            linha,
            flags=re.IGNORECASE | re.VERBOSE,
        )
        if clicar:
            elemento, nome = clicar.groups()
            role = "button" if elemento.lower().startswith("bot") else "link"
            passos.append(
                {
                    "acao": "clicar",
                    "localizador": {
                        "tipo": "role",
                        "valor": role,
                        "nome_acessivel": nome,
                    },
                }
            )
            continue

        clicar_texto = re.search(
            r"""\bclicar\s+(?:em|no|na)\s+["']([^"']+)["']""",
            linha,
            flags=re.IGNORECASE,
        )
        if clicar_texto:
            passos.append(
                {
                    "acao": "clicar",
                    "localizador": {
                        "tipo": "text",
                        "valor": clicar_texto.group(1),
                    },
                }
            )
            continue

        verificar_texto = re.search(
            r"""\bverificar\b.*?\btexto\s+["']([^"']+)["'].*?
            (?:aparece|vis[ií]vel|exibid[oa])""",
            linha,
            flags=re.IGNORECASE | re.VERBOSE,
        )
        if verificar_texto:
            passos.append(
                {
                    "acao": "verificar_visivel",
                    "localizador": {
                        "tipo": "text",
                        "valor": verificar_texto.group(1),
                    },
                }
            )
            continue

        verificar_conteudo = re.search(
            r"""\b(?:verificar|validar)\b.*?\b(?:t[ií]tulo|mensagem|texto)\s+["']([^"']+)["']""",
            linha,
            flags=re.IGNORECASE,
        )
        if verificar_conteudo:
            passos.append(
                {
                    "acao": "verificar_visivel",
                    "localizador": {
                        "tipo": "text",
                        "valor": verificar_conteudo.group(1),
                    },
                }
            )

    return passos, dados, rota_acesso


def _extrair_timeout(texto: str, rotulo: str) -> tuple[int, str] | None:
    encontrado = re.search(
        rf"^\s*[-*]?\s*{rotulo}\s*:\s*(\d+)\s*(ms|milissegundos?|s|segundos?)?",
        texto,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not encontrado:
        return None
    return int(encontrado.group(1)), (encontrado.group(2) or "").lower()


def extrair_contrato_textual_e2e(requisitos: Any) -> dict[str, Any]:
    """Converte declarações explícitas do prompt em campos opcionais da tool.

    A extração é conservadora: nenhum valor é inferido quando não existe uma
    expressão reconhecida no texto original.
    """

    texto = _texto_requisitos(requisitos)
    if not texto:
        return {}

    base_url = _capturar(
        texto,
        r"^\s*[-*]?\s*URL\s+base\s*:\s*(https?://\S+)",
    )
    base_url = base_url or _capturar(texto, r"\b(https?://[^\s,;]+)")
    rota = _capturar(texto, r"^\s*[-*]?\s*Rota\s*:\s*(/\S+)")
    passos, dados, rota_acesso = _extrair_passos(texto)
    rota = rota or rota_acesso or base_url

    contrato: dict[str, Any] = {}
    if base_url:
        contrato["base_url"] = base_url
    if base_url or rota:
        contrato["tipo_sistema"] = "web"
    if rota:
        nome = (
            "Jornada E2E"
            if rota.startswith(("http://", "https://"))
            else rota.strip("/").replace("-", " ").replace("_", " ").title()
        )
        contrato["rotas_ou_telas"] = [
            {
                "nome": nome or "Jornada E2E",
                "rota": rota,
                "passos_automacao": passos,
            }
        ]
    if dados:
        contrato["dados_teste"] = dados

    ambiente = _capturar(texto, r"^\s*[-*]?\s*Ambiente\s*:\s*([^\r\n]+)")
    browser = _capturar(texto, r"^\s*[-*]?\s*Browser\s*:\s*([^\r\n]+)")
    modo = _capturar(texto, r"^\s*[-*]?\s*Modo\s*:\s*([^\r\n]+)")
    timeout_teste = _extrair_timeout(texto, r"Timeout\s+por\s+teste")
    timeout_total = _extrair_timeout(texto, r"Timeout\s+total")
    ambiente_execucao: dict[str, Any] = {}
    if ambiente:
        ambiente_execucao["tipo"] = ambiente.lower()
    if browser:
        ambiente_execucao["browser"] = browser.lower()
    if modo:
        ambiente_execucao["headless"] = modo.lower() == "headless"
    if timeout_teste:
        valor, unidade = timeout_teste
        ambiente_execucao["timeout_teste_ms"] = (
            valor * 1_000 if unidade in {"s", "segundo", "segundos"} else valor
        )
    if timeout_total:
        valor, unidade = timeout_total
        ambiente_execucao["timeout_segundos"] = (
            max(1, valor // 1_000)
            if unidade in {"ms", "milissegundo", "milissegundos"}
            else valor
        )
    if ambiente_execucao:
        contrato["ambiente_execucao"] = ambiente_execucao

    comando = _capturar(
        texto,
        r"^\s*[-*]?\s*Perfil\s+de\s+comando\s+autorizado\s*:\s*([^\r\n]+)",
    )
    if comando:
        contrato["comando_execucao"] = comando
    return contrato
