"""Extrai somente dados E2E explicitamente declarados em prompts textuais."""

import re
import unicodedata
from typing import Any


def _capturar(texto: str, padrao: str) -> str | None:
    encontrado = re.search(padrao, texto, flags=re.IGNORECASE | re.MULTILINE)
    if not encontrado:
        return None
    return encontrado.group(1).strip().rstrip(".,;")


def _chave_dado(nome: str) -> str:
    normalizado = unicodedata.normalize("NFKD", nome)
    sem_acentos = "".join(
        caractere for caractere in normalizado if not unicodedata.combining(caractere)
    )
    return re.sub(r"[^a-zA-Z0-9]+", "_", sem_acentos).strip("_").lower() or "valor"


def _linhas_fluxo(texto: str) -> list[str]:
    return [
        encontrado.group(1).strip()
        for encontrado in re.finditer(
            r"(?:^|\s)\d+[.)]\s+(.+?)(?=\s+\d+[.)]\s+|$)",
            texto,
            flags=re.DOTALL,
        )
    ]


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

    if not isinstance(requisitos, str) or not requisitos.strip():
        return {}
    texto = requisitos.strip()

    base_url = _capturar(
        texto,
        r"^\s*[-*]?\s*URL\s+base\s*:\s*(https?://\S+)",
    )
    rota = _capturar(texto, r"^\s*[-*]?\s*Rota\s*:\s*(/\S+)")
    passos, dados, rota_acesso = _extrair_passos(texto)
    rota = rota or rota_acesso

    contrato: dict[str, Any] = {}
    if base_url:
        contrato["base_url"] = base_url
    if base_url or rota:
        contrato["tipo_sistema"] = "web"
    if rota:
        nome = rota.strip("/").replace("-", " ").replace("_", " ").title()
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
