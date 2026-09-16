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
import logging
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
    api_key/access_token/token/password/secret (com ou sem aspas ao redor da
    chave e/ou do valor — cobre tanto `api_key=valor`/`api_key: valor`
    quanto o formato JSON `"api_key": "valor"` e o YAML com valor entre
    aspas `api_key: "valor"`), e credenciais embutidas em URL
    (https://user:senha@host).
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
    def _substituir_atribuicao(match: re.Match) -> str:
        chave, aspas_chave, separador, aspas_valor = (
            match.group(1),
            match.group(2),
            match.group(3),
            match.group(4),
        )
        return f"{chave}{aspas_chave}{separador}{aspas_valor}[REDACTED]{aspas_valor}"

    texto = re.sub(
        (
            r"(?i)\b(api[_-]?key|access[_-]?token|token|"
            r"password|passwd|secret)\b"
            # Grupo 4 (aspas do valor) é reaberto via \4 para consumir a
            # aspa de FECHAMENTO real do valor (se houver) — sem isso, ela
            # sobra no texto original e duplica com a aspa que a própria
            # substituição reinsere (ex.: {"api_key": "[REDACTED]""} ao
            # invés de {"api_key": "[REDACTED]"}).
            r"([\"']?)(\s*[:=]\s*)([\"']?)([^\s,;\"']+)\4"
        ),
        _substituir_atribuicao,
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

# Segmento exato (não substring) proibido em qualquer import — a suíte
# materializada pelo QA nunca deve referenciar o workspace fora de si mesma.
_SEGMENTOS_IMPORT_PROIBIDOS = {"coder", "workspace_output"}


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
    pytest_runner (P0), não a única barreira. Também não tenta detectar
    ofuscação de import/sys.path via `getattr`/nomes indiretos — fora de
    escopo, mesma limitação aceita.

    Também detecta import (não regex — só `ast.Import`/`ast.ImportFrom`
    reais) cujo módulo tenha "coder" ou "workspace_output" como segmento
    exato: a suíte materializada nunca deve importar de fora de si mesma
    (ver REGRAS DE ISOLAMENTO em code_fix_agent/prompt.py — "nunca
    referencie workspace_output/coder"). Um módulo como "encoder" não é
    pego (segmento precisa bater exatamente, não por substring).

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
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modulos = (
                [node.module] if isinstance(node, ast.ImportFrom) and node.module
                else [alias.name for alias in node.names] if isinstance(node, ast.Import)
                else []
            )
            for modulo in modulos:
                segmentos = {parte.lower() for parte in modulo.split(".")}
                if segmentos & _SEGMENTOS_IMPORT_PROIBIDOS:
                    riscos.append(
                        f"linha {node.lineno}: import fora da suíte "
                        f"materializada ({modulo}) — nunca referencie "
                        "workspace_output/coder; use a cópia local "
                        "(ex.: from src.modulo import funcao)"
                    )
            continue

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


# ---------------------------------------------------------------------------
# Decisão P3 reutilizável: mesma varredura (riscos + credenciais) usada tanto
# na geração inicial de pytest (receive_requirements.sanitizer) quanto na
# correção do code_fix_agent (shared.tools.qa_test_files.write_qa_test) — um
# único ponto de decisão para não duplicar a lógica de bloqueio nos dois
# lugares.
# ---------------------------------------------------------------------------

_logger_seguranca = logging.getLogger("qa_agent")


def validar_seguranca_codigo(codigo: str, identificador: str) -> None:
    """Levanta ValueError se `codigo` apresentar risco de segurança (P3).

    Reúne `detectar_riscos_codigo` + `detectar_credenciais` numa única
    decisão de bloqueio, com mensagem no mesmo formato usada pelos dois
    chamadores atuais. Não retorna nada quando não há risco (nem sanitiza,
    nem transforma `codigo` — só decide).
    """
    riscos = detectar_riscos_codigo(codigo) + detectar_credenciais(codigo)
    if riscos:
        _logger_seguranca.warning(
            f"[QA] Código para {identificador} bloqueado por risco de "
            f"segurança: {riscos}"
        )
        raise ValueError(
            f"Código para {identificador} apresenta risco de segurança e "
            f"foi bloqueado antes de ser persistido: {'; '.join(riscos)}."
        )


# ---------------------------------------------------------------------------
# Varredura de riscos em specs Playwright (.spec.ts) gerados por LLM — mesma
# motivação de detectar_riscos_codigo, mas para TypeScript, onde não há um
# parser AST disponível aqui; usa regex sobre o texto, como
# detectar_credenciais já faz para outros formatos.
# ---------------------------------------------------------------------------

_PADRAO_PROCESS_ENV = re.compile(r"\bprocess\s*\.\s*env\b")
_PADRAO_REQUIRE_PERIGOSO = re.compile(
    r"require\s*\(\s*[\"'](child_process|fs)[\"']\s*\)"
)
_PADRAO_CHAMADA_REDE_TS = re.compile(
    r"\b(?:fetch|request|axios(?:\.\w+)?)\s*\(\s*[\"'`]([^\"'`]+)[\"'`]"
)


def _host_ts_ou_none(alvo: str) -> str | None:
    """Extrai o host de uma URL usada num spec TS, ou None se for caminho
    relativo (mesma origem do base_url, já validado em outro lugar)."""
    if alvo.startswith("/"):
        return None
    return alvo


def detectar_riscos_spec_ts(codigo_ts: str) -> list[str]:
    """Varre um `.spec.ts` gerado por LLM antes de persistir.

    Detecta: leitura de variável de ambiente do processo Node
    (`process.env`), import de módulo Node de baixo nível
    (`require('child_process')`/`require('fs')`) e requisição de rede
    (`fetch`/`request`/`axios`) para um host literal que não seja
    localhost/127.0.0.1/::1 — mesma política de "execução autônoma restrita
    a loopback" de `detectar_riscos_codigo`. Uma URL relativa (`fetch('/api/x')`)
    é tratada como mesma origem do `base_url` (já validado alhures) e não é
    sinalizada. Uma URL com interpolação de template string
    (`` `${base}/x` ``) não é estaticamente verificável — falha fechada,
    mesmo padrão do restante do pipeline.

    Como não há parser TypeScript disponível aqui, usa regex sobre o texto
    — diferente de `detectar_riscos_codigo` (AST), que é possível só porque
    o Python tem `ast` na biblioteca padrão.

    Retorna lista vazia quando não há risco.
    """
    riscos: list[str] = []
    for numero, linha in enumerate(codigo_ts.splitlines(), start=1):
        if _PADRAO_PROCESS_ENV.search(linha):
            riscos.append(
                f"linha {numero}: leitura de variável de ambiente do "
                "processo (process.env) — specs não devem acessar o "
                "ambiente do host"
            )
        if _PADRAO_REQUIRE_PERIGOSO.search(linha):
            riscos.append(
                f"linha {numero}: import de módulo Node de baixo nível "
                "(child_process/fs) — specs não devem executar processos "
                "nem acessar o filesystem fora do harness Playwright"
            )
        for match in _PADRAO_CHAMADA_REDE_TS.finditer(linha):
            alvo = match.group(1)
            if "${" in alvo:
                riscos.append(
                    f"linha {numero}: requisição de rede com host não "
                    "verificável estaticamente (template string) — "
                    "execução autônoma só pode acessar localhost/127.0.0.1"
                )
                continue
            host = _host_ts_ou_none(alvo)
            if host is None or _eh_loopback(host):
                continue
            riscos.append(
                f"linha {numero}: requisição de rede a host externo "
                f"({alvo}) — execução autônoma só pode acessar "
                "localhost/127.0.0.1/::1"
            )
    return riscos
