"""Guardrails de segurança compartilhados entre agentes que executam código
ou repassam saída de subprocesso (stdout/stderr/tracebacks) para um LLM ou
para o usuário.

Consolida padrões que já existiam duplicados dentro do subagente E2E do QA
(`e2e_test_generator/tools/executar_playwright.py` e
`gerenciar_runtime_alvo.py`) para que outros fluxos — como o pytest_runner —
possam reutilizá-los em vez de reinventar.
"""

from __future__ import annotations

import ast
import ipaddress
import math
import os
import re
from collections import Counter
from urllib.parse import urlparse


def redigir_segredos(texto: str) -> str:
    """Redige credenciais de um texto livre (logs, stdout, tracebacks).

    Uso pretendido: aplicar sobre qualquer saída de subprocesso ou de
    execução de código antes de propagá-la para outro LLM (ex.: prompt de
    correção), para o usuário (relatório final) ou para persistência (cache,
    doubt artifact). Não substitui uma allowlist de ambiente — trata do caso
    em que o segredo já vazou para dentro de um texto e precisa ser mascarado
    antes de propagar adiante.

    Cobre: header Authorization, tokens Bearer, pares chave=valor para
    api_key/access_token/token/password/secret, e credenciais embutidas em
    URL (https://user:senha@host).
    """
    texto = re.sub(
        r"(?i)\b(authorization\s*[:=]\s*)[^\r\n,;]+",
        r"\1[REDACTED]",
        texto,
    )
    texto = re.sub(
        r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+",
        "Bearer [REDACTED]",
        texto,
    )
    texto = re.sub(
        (
            r"(?i)\b(api[_-]?key|access[_-]?token|token|"
            r"password|passwd|secret)\b(\s*[:=]\s*)([^\s,;]+)"
        ),
        r"\1\2[REDACTED]",
        texto,
    )
    return re.sub(
        r"(https?://)([^/\s:@]+):([^@\s/]+)@",
        r"\1[REDACTED]@",
        texto,
        flags=re.IGNORECASE,
    )


_ALLOWLIST_PYTHON = {
    # Paridade com as allowlists do fluxo E2E (_ambiente_minimo_node /
    # _ambiente_minimo_runtime): variáveis de SO necessárias para o
    # interpretador/subprocesso inicializar corretamente.
    "SYSTEMROOT",
    "WINDIR",
    "PATH",
    "PATHEXT",
    "TEMP",
    "TMP",
    # Runtime Python.
    "PYTHONIOENCODING",
    "PYTHONUTF8",
    # Lidas por bibliotecas Python comuns (coverage, pip cache, etc.) para
    # resolver diretório de config/cache do usuário.
    "HOME",
    "USERPROFILE",
}


def ambiente_minimo_python(pythonpath: list[str] | None = None) -> dict[str, str]:
    """Allowlist de variáveis de ambiente para subprocessos Python.

    Evita expor credenciais do processo pai (ex.: GOOGLE_API_KEY,
    DATABASE_URL) a código gerado por LLM e executado via subprocess — mesmo
    padrão já usado no fluxo E2E (`_ambiente_minimo_runtime`).

    Uma variável da allowlist ausente no ambiente do host simplesmente não
    aparece no dict retornado (sem erro, sem string vazia).

    O PYTHONPATH do host NUNCA é herdado: se o chamador precisar de um
    PYTHONPATH no subprocesso, deve passá-lo explicitamente via
    `pythonpath`.
    """
    env = {
        chave: valor
        for chave in _ALLOWLIST_PYTHON
        if (valor := os.environ.get(chave)) is not None
    }
    env["PYTHONIOENCODING"] = "utf-8"
    if pythonpath:
        env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    return env


# ---------------------------------------------------------------------------
# Varredura de riscos em código gerado por LLM (defesa em profundidade sobre
# o allowlist de ambiente do pytest_runner: mesmo que um teste gerado tente
# ler credenciais do processo, executar comandos arbitrários ou falar com a
# rede, o objetivo é barrar isso antes de o código ser persistido/executado).
# ---------------------------------------------------------------------------

_PREFIXOS_RISCO_REDE = ("socket.", "requests.", "httpx.", "aiohttp.", "urllib.request.")

_LOOPBACK_HOSTNAMES = {"localhost"}


def _dotted(node: ast.expr) -> str:
    """Reconstrói `a.b.c` a partir de uma cadeia de ast.Attribute/ast.Name."""
    partes: list[str] = []
    atual = node
    while isinstance(atual, ast.Attribute):
        partes.append(atual.attr)
        atual = atual.value
    if isinstance(atual, ast.Name):
        partes.append(atual.id)
        return ".".join(reversed(partes))
    return ""


def _mapa_aliases_import(arvore: ast.AST) -> dict[str, str]:
    """Resolve `import x as y` / `from x import y as z` para o nome qualificado.

    `import x` sem alias não precisa de entrada aqui: o código vai referenciar
    `x.algo` e `_dotted` já reconstrói a cadeia diretamente.
    """
    aliases: dict[str, str] = {}
    for node in ast.walk(arvore):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if not node.module:
                continue
            for alias in node.names:
                nome_local = alias.asname or alias.name
                aliases[nome_local] = f"{node.module}.{alias.name}"
    return aliases


def _resolver_dotted(dotted: str, aliases: dict[str, str]) -> str:
    if not dotted:
        return dotted
    raiz, _, resto = dotted.partition(".")
    raiz = aliases.get(raiz, raiz)
    return f"{raiz}.{resto}" if resto else raiz


def _eh_loopback(host: str) -> bool:
    alvo = host.strip()
    if "://" in alvo:
        alvo = urlparse(alvo).hostname or ""
    alvo = alvo.strip().lower().rstrip(".")
    if not alvo:
        return False
    if alvo in _LOOPBACK_HOSTNAMES:
        return True
    try:
        return ipaddress.ip_address(alvo).is_loopback
    except ValueError:
        return False


def _host_de_chamada(node: ast.Call) -> str | None:
    """Extrai, quando estaticamente determinável, o host/URL alvo da chamada."""
    if node.args:
        primeiro = node.args[0]
        if isinstance(primeiro, ast.Constant) and isinstance(primeiro.value, str):
            return primeiro.value
        # socket.connect(("host", porta)) / create_connection(("host", porta))
        if isinstance(primeiro, ast.Tuple) and primeiro.elts:
            candidato = primeiro.elts[0]
            if isinstance(candidato, ast.Constant) and isinstance(candidato.value, str):
                return candidato.value
    for kw in node.keywords:
        if kw.arg in {"url", "host"} and isinstance(kw.value, ast.Constant):
            if isinstance(kw.value.value, str):
                return kw.value.value
    return None


def detectar_riscos_codigo(codigo: str) -> list[str]:
    """Analisa Python via AST e lista riscos de segurança em código de teste.

    Usa AST em vez de regex justamente para não confundir `os.environ`
    mencionado dentro de uma string ou de um comentário com o uso real —
    regex sobre código-fonte gera falso positivo nesses casos.

    Detecta: leitura de variável de ambiente (os.environ, os.getenv,
    dotenv.load_dotenv), execução de processo/código dinâmico (subprocess.*,
    os.system, os.popen, eval, exec, compile), import dinâmico (__import__,
    importlib.*) e requisição de rede a host que não seja localhost/loopback
    (socket, requests, httpx, aiohttp, urllib.request) — mesma política de
    "execução autônoma restrita a loopback" já aplicada pelo
    e2e_test_generator (ver LIMITES em e2e_test_generator/prompt.py e
    `_url_loopback` em validar_contrato_e2e.py). Quando o host não pode ser
    determinado estaticamente (variável, f-string, objeto retornado por
    `Session()` reutilizado depois), o padrão é bloquear — falha fechada,
    consistente com o resto do pipeline (ex.: normalização de paths do
    pytest_runner).

    Resolve aliases simples de import (`import x as y`,
    `from x import y as z`) mas não segue atribuições de variável — por
    exemplo, `s = requests.Session(); s.get(url)` não é detectado nessa
    segunda chamada. É uma limitação aceita: esta função é uma camada de
    defesa em profundidade complementar ao allowlist de ambiente do
    pytest_runner (P0), não a única barreira.

    Retorna lista vazia quando não há risco. Código sintaticamente inválido
    também retorna lista vazia — validar sintaxe é responsabilidade de
    `ast.parse` no chamador, não desta função.
    """
    try:
        arvore = ast.parse(codigo)
    except SyntaxError:
        return []

    aliases = _mapa_aliases_import(arvore)
    riscos: list[str] = []

    for node in ast.walk(arvore):
        if isinstance(node, ast.Subscript):
            dotted = _resolver_dotted(_dotted(node.value), aliases)
            if dotted == "os.environ":
                riscos.append(
                    f"linha {node.lineno}: leitura de variável de ambiente "
                    "(os.environ) — testes não devem acessar o ambiente do host"
                )
            continue

        if not isinstance(node, ast.Call):
            continue

        dotted = _resolver_dotted(_dotted(node.func), aliases)
        if not dotted:
            continue

        if dotted in {"os.environ.get", "os.getenv", "dotenv.load_dotenv"}:
            riscos.append(
                f"linha {node.lineno}: leitura de variável de ambiente "
                f"({dotted}) — testes não devem acessar o ambiente do host"
            )
        elif dotted.startswith("subprocess.") or dotted in {
            "os.system",
            "os.popen",
            "eval",
            "exec",
            "compile",
        }:
            riscos.append(
                f"linha {node.lineno}: execução de processo ou código "
                f"dinâmico ({dotted}) — testes não devem executar processos "
                "nem avaliar código arbitrário"
            )
        elif dotted == "__import__" or dotted.startswith("importlib."):
            riscos.append(
                f"linha {node.lineno}: import dinâmico ({dotted}) — pode "
                "contornar as restrições acima carregando módulos em runtime"
            )
        elif dotted.startswith(_PREFIXOS_RISCO_REDE):
            host = _host_de_chamada(node)
            if host is not None and _eh_loopback(host):
                continue
            riscos.append(
                f"linha {node.lineno}: requisição de rede a host externo ou "
                f"não verificável estaticamente ({dotted}) — execução "
                "autônoma só pode acessar localhost/127.0.0.1"
            )

    return riscos


# ---------------------------------------------------------------------------
# Detecção (não redação) de credenciais literais em texto/código gerado.
# ---------------------------------------------------------------------------

_PADRAO_AUTHORIZATION = re.compile(r"(?i)\bauthorization\s*[:=]\s*\S+")
_PADRAO_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_PADRAO_URL_CREDENCIAL = re.compile(r"(?i)https?://[^/\s:@]+:[^@\s/]+@")
_PADRAO_ATRIBUICAO_SUSPEITA = re.compile(
    r"""(?ix)
    \b(api[_-]?key|access[_-]?token|token|password|passwd|secret|senha)\w*
    \s*[:=]\s*
    ['"]([^'"]+)['"]
    """
)

_PLACEHOLDERS_CREDENCIAL = {
    "xxx",
    "fake",
    "dummy",
    "changeme",
    "change_me",
    "change-me",
    "<credencial redigida>",
}

_ENTROPIA_MINIMA_CREDENCIAL = 2.5
_TAMANHO_MINIMO_CREDENCIAL = 6


def _entropia_shannon(texto: str) -> float:
    if not texto:
        return 0.0
    contagem = Counter(texto)
    tamanho = len(texto)
    return -sum(
        (n / tamanho) * math.log2(n / tamanho) for n in contagem.values()
    )


def detectar_credenciais(texto: str) -> list[str]:
    """Identifica prováveis credenciais literais em texto (não redige, só relata).

    Reaproveita os padrões de `redigir_segredos` (header Authorization,
    token Bearer, credencial embutida em URL) e adiciona detecção de valor
    atribuído a um nome suspeito (api_key, token, password, secret, senha)
    cuja string tenha "cara" de segredo real — não um placeholder óbvio
    ("xxx", "fake", "dummy", "changeme", "<credencial redigida>") nem uma
    palavra curta comum. Usa um limiar de entropia de Shannon para reduzir
    falso positivo em valores curtos/pouco variados; o placeholder óbvio é
    excluído por correspondência exata, não pela entropia (ex.: "changeme"
    tem entropia relativamente alta para seu tamanho, mas é excluído porque
    está na lista de placeholders, não porque a entropia é baixa).

    Retorna lista vazia quando nada suspeito é encontrado.
    """
    achados: list[str] = []
    for numero, linha in enumerate(texto.splitlines(), start=1):
        if _PADRAO_AUTHORIZATION.search(linha):
            achados.append(f"linha {numero}: possível header Authorization exposto")
        if _PADRAO_BEARER.search(linha):
            achados.append(f"linha {numero}: possível token Bearer exposto")
        if _PADRAO_URL_CREDENCIAL.search(linha):
            achados.append(f"linha {numero}: possível credencial embutida em URL")
        for match in _PADRAO_ATRIBUICAO_SUSPEITA.finditer(linha):
            nome_suspeito, valor = match.group(1), match.group(2)
            valor_normalizado = valor.strip().lower()
            if valor_normalizado in _PLACEHOLDERS_CREDENCIAL:
                continue
            if len(valor) < _TAMANHO_MINIMO_CREDENCIAL:
                continue
            if _entropia_shannon(valor) < _ENTROPIA_MINIMA_CREDENCIAL:
                continue
            achados.append(
                f"linha {numero}: possível credencial atribuída a "
                f"'{nome_suspeito}' (valor com aparência de segredo real)"
            )
    return achados
