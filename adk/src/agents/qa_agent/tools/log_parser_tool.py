import re
import json
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class LogEntry:
    timestamp: str
    level: str
    module: str
    message: str
    raw: str
    format: str = "unknown"


# ── parsers por formato ───────────────────────────────────────────────────────

PATTERN_PADRAO = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})"
    r"\s+(?P<level>DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)"
    r"(?:\s+\[(?P<module>[^\]]+)\])?"
    r"\s+(?P<message>.+)"
)

PATTERN_LOG4J = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}),\d+"
    r"\s+(?P<level>DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)"
    r"\s+(?P<module>\S+)"
    r"\s+-\s+(?P<message>.+)"
)

PATTERN_SYSLOG = re.compile(
    r"(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})"
    r"\s+\S+"
    r"\s+(?P<module>\S+?)(?:\[\d+\])?"
    r":\s+(?P<message>.+)"
)

PATTERN_PYTHON = re.compile(
    r"(?P<level>DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)"
    r":(?P<module>[^:]+)"
    r":(?P<message>.+)"
)

PATTERN_NGINX = re.compile(
    r"(?P<module>\S+)"
    r"\s+-\s+-\s+"
    r"\[(?P<timestamp>\d{2}/\w+/\d{4}:\d{2}:\d{2}:\d{2}\s+[+-]\d{4})\]"
    r'\s+"(?P<message>[^"]+)"'
    r"\s+(?P<status>\d{3})"
    r"\s+\d+"
)

PATTERN_PYTEST = re.compile(
    r'File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<function>\S+)'
)

NIVEL_HTTP = {
    "1": "INFO", "2": "INFO", "3": "INFO",
    "4": "ERROR", "5": "CRITICAL"
}


def _nivel_nginx(status: str) -> str:
    return NIVEL_HTTP.get(status[0], "INFO")


def parse_padrao(raw: str) -> Optional[LogEntry]:
    """Analisar linha de log no formato padrão (timestamp ISO + level + [module] + mensagem).

    Use quando o log segue o padrão genérico adotado por frameworks Python como
    structlog ou loguru com saída em texto simples. No fluxo do QA agent, este
    parser é tentado após json, log4j e antes de nginx/syslog/python na cadeia
    de `parse_line` — cobre a maioria dos logs gerados pelas aplicações alvo dos
    testes de autocorrect (2 ciclos máximos conforme contrato do workflow_qa).

    Args:
        raw: Linha bruta de log no formato
             ``YYYY-MM-DDThh:mm:ss LEVEL [module] mensagem`` (colchetes opcionais).

    Returns:
        LogEntry com format="padrao" e os campos extraídos, ou None se a linha
        não corresponder ao padrão esperado.
    """
    m = PATTERN_PADRAO.match(raw.strip())
    if not m:
        return None
    return LogEntry(
        timestamp=m.group("timestamp"),
        level=m.group("level"),
        module=m.group("module") or "unknown",
        message=m.group("message"),
        raw=raw.strip(),
        format="padrao",
    )


def parse_log4j(raw: str) -> Optional[LogEntry]:
    """Analisar linha de log no formato Log4j/Log4j2 (timestamp com milissegundos, módulo sem colchetes).

    Use quando os logs provêm de aplicações Java/Kotlin que usam Log4j, Log4j2
    ou Logback, ou de qualquer biblioteca que emita o padrão
    ``YYYY-MM-DD hh:mm:ss,mmm LEVEL com.pacote.Classe - mensagem``. No ciclo de
    autocorrect do QA agent o code_fix_agent pode receber stack traces Java; este
    parser é o primeiro a tentar reconhecer o formato estruturado antes de
    recorrer ao fallback raw.

    Args:
        raw: Linha bruta de log com separador ``,`` após os segundos e módulo
             sem espaços separado da mensagem por `` - ``.

    Returns:
        LogEntry com format="log4j" e os campos extraídos, ou None se a linha
        não corresponder ao padrão Log4j esperado.
    """
    m = PATTERN_LOG4J.match(raw.strip())
    if not m:
        return None
    return LogEntry(
        timestamp=m.group("timestamp"),
        level=m.group("level"),
        module=m.group("module"),
        message=m.group("message"),
        raw=raw.strip(),
        format="log4j",
    )


def parse_syslog(raw: str) -> Optional[LogEntry]:
    """Analisar linha de log no formato syslog BSD/RFC 3164 (mês abreviado + hostname + daemon).

    Use quando os logs chegam diretamente do sistema operacional Linux/Unix —
    por exemplo, saída de ``/var/log/syslog``, ``journalctl`` ou contêineres que
    redirecionam stderr para o syslog do host. O QA agent pode receber esses logs
    ao inspecionar o ambiente de execução dos testes de integração. Como o syslog
    BSD não carrega nível de severidade na linha, o campo ``level`` é fixado em
    ``"INFO"`` — diferenciando-o de todos os demais parsers da cadeia.

    Args:
        raw: Linha bruta no formato ``Mon DD hh:mm:ss hostname daemon[pid]: mensagem``
             (PID entre colchetes é opcional).

    Returns:
        LogEntry com format="syslog", level="INFO" fixo e os campos extraídos,
        ou None se a linha não corresponder ao padrão syslog.
    """
    m = PATTERN_SYSLOG.match(raw.strip())
    if not m:
        return None
    return LogEntry(
        timestamp=m.group("timestamp"),
        level="INFO",
        module=m.group("module"),
        message=m.group("message"),
        raw=raw.strip(),
        format="syslog",
    )


def parse_python(raw: str) -> Optional[LogEntry]:
    """Analisar linha de log no formato padrão do módulo ``logging`` do Python (sem timestamp).

    Use quando a aplicação testada não configurou um ``Formatter`` customizado e
    usa a saída padrão ``LEVEL:logger_name:mensagem`` produzida por
    ``logging.basicConfig()``. Diferente de ``parse_padrao``, este parser não
    exige timestamp — campo que fica como ``"unknown"`` no LogEntry resultante.
    É acionado depois de padrao/nginx/syslog na cadeia de ``parse_line`` por ser
    menos específico; captura logs de testes unitários que imprimem diretamente
    via ``logging.debug/info/error``.

    Args:
        raw: Linha bruta no formato ``LEVEL:nome_do_logger:mensagem`` sem
             timestamp nem separadores adicionais.

    Returns:
        LogEntry com format="python", timestamp="unknown" e campos extraídos,
        ou None se a linha não corresponder ao padrão do ``logging`` Python.
    """
    m = PATTERN_PYTHON.match(raw.strip())
    if not m:
        return None
    return LogEntry(
        timestamp="unknown",
        level=m.group("level"),
        module=m.group("module"),
        message=m.group("message"),
        raw=raw.strip(),
        format="python",
    )


def parse_nginx(raw: str) -> Optional[LogEntry]:
    """Analisar linha de log no formato Combined Log Format do Nginx/Apache (access log).

    Use quando os testes de integração ou de carga geram logs de acesso HTTP
    que precisam ser inspecionados pelo QA agent — por exemplo, ao validar que
    endpoints retornam os status codes corretos. O nível de severidade é derivado
    do código HTTP via ``_nivel_nginx``: 4xx vira ERROR, 5xx vira CRITICAL e
    demais ficam INFO. O campo ``module`` recebe o IP do cliente (primeiro token
    da linha), e ``message`` contém a requisição HTTP bruta entre aspas.

    Args:
        raw: Linha bruta no formato Nginx Combined:
             ``ip - - [timestamp] "METHOD /path HTTP/x" status bytes``.

    Returns:
        LogEntry com format="nginx" e level derivado do status HTTP,
        ou None se a linha não corresponder ao Combined Log Format.
    """
    m = PATTERN_NGINX.match(raw.strip())
    if not m:
        return None
    status = m.group("status")
    return LogEntry(
        timestamp=m.group("timestamp"),
        level=_nivel_nginx(status),
        module=m.group("module"),
        message=m.group("message"),
        raw=raw.strip(),
        format="nginx",
    )


def parse_json_log(raw: str) -> Optional[LogEntry]:
    """Analisar linha de log em formato JSON estruturado (structured logging).

    Use quando a aplicação emite logs como objetos JSON por linha — padrão
    adotado por frameworks como structlog (com ``JSONRenderer``), python-json-logger,
    Bunyan (Node.js) ou qualquer serviço que escreva em stdout para coleta por
    fluentd/loki. Este parser é o **primeiro** da cadeia em ``PARSERS`` por ser
    o mais específico e não ambíguo: rejeita linhas que não comecem com ``{`` e
    tolera variações de campo (``message``/``msg``/``text``, ``level``/``severity``/
    ``lvl``, ``module``/``logger``/``service``, ``timestamp``/``time``/``ts``).

    Args:
        raw: Linha bruta contendo um objeto JSON completo em uma única linha;
             linhas que não iniciem com ``{`` são recusadas sem tentativa de parse.

    Returns:
        LogEntry com format="json" e campos normalizados para o schema padrão,
        ou None se a linha não for JSON válido, não começar com ``{`` ou não
        possuir campo de mensagem reconhecível.
    """
    stripped = raw.strip()
    if not stripped.startswith("{"):
        return None
    try:
        d = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    message = d.get("message") or d.get("msg") or d.get("text") or ""
    level   = d.get("level")   or d.get("severity") or d.get("lvl") or "INFO"
    module  = d.get("module")  or d.get("logger")   or d.get("service") or "unknown"
    ts      = d.get("timestamp") or d.get("time")   or d.get("ts") or "unknown"

    if not message:
        return None

    return LogEntry(
        timestamp=str(ts),
        level=level.upper(),
        module=str(module),
        message=str(message),
        raw=stripped,
        format="json",
    )


def parse_raw(raw: str) -> Optional[LogEntry]:
    """Encapsular linha de log sem formato reconhecido como entrada bruta de fallback.

    Use como último recurso na cadeia de ``parse_line``: qualquer linha não-vazia
    que não tenha sido capturada pelos parsers específicos (json, log4j, padrao,
    nginx, syslog, python) chega aqui. O QA agent precisa registrar mesmo linhas
    malformatadas para dar ao code_fix_agent contexto completo durante o ciclo de
    autocorrect — descartar silenciosamente poderia esconder a causa raiz do erro.
    Todos os campos de metadados (timestamp, level, module) são fixados em
    ``"unknown"``/``"UNKNOWN"`` para sinalizar explicitamente a ausência de estrutura.

    Args:
        raw: Linha bruta de qualquer conteúdo textual; linhas em branco ou
             compostas apenas de espaços retornam None.

    Returns:
        LogEntry com format="raw", level="UNKNOWN" e todos os campos de metadados
        como ``"unknown"``, ou None se a linha estiver vazia após strip.
    """
    stripped = raw.strip()
    if not stripped:
        return None
    return LogEntry(
        timestamp="unknown",
        level="UNKNOWN",
        module="unknown",
        message=stripped,
        raw=stripped,
        format="raw",
    )


def parse_pytest_log(traceback_text: str) -> dict:
    """Parse de traceback pytest retornando estrutura para análise de erro.

    Args:
        traceback_text: Texto completo do traceback do pytest.

    Returns:
        dict: Dicionário com file, line, function, error_type, error_message, assertion e raw.
    """
    lines = traceback_text.strip().split('\n')
    result = {
        "file": None,
        "line": None,
        "function": None,
        "error_type": None,
        "error_message": None,
        "assertion": None,
        "raw": traceback_text.strip()
    }

    for line in lines:
        line = line.strip()
        # Extrair função de linhas como "def test_falha_proposital():"
        if line.startswith('def ') and 'test_' in line:
            func_name = line.split('(')[0].replace('def ', '').strip()
            result["function"] = func_name
        # Extrair file, line, error_type de linhas como "path/file.py:7: AssertionError"
        elif ':' in line and line.count(':') >= 2:
            parts = line.split(':')
            if len(parts) >= 3:
                file_part = ':'.join(parts[:-2])
                line_part = parts[-2]
                error_part = parts[-1]
                if line_part.isdigit():
                    result["file"] = file_part
                    result["line"] = int(line_part)
                    result["error_type"] = error_part
        # Extrair assertion de linhas como ">    assert 2 + 2 == 5" ou "assert 2 + 2 == 5"
        elif 'assert ' in line:
            if '>    ' in line:
                result["assertion"] = line.replace('>    ', '').strip()
            else:
                result["assertion"] = line.strip()
        # Extrair mensagem de erro de linhas como "E    assert (2 + 2) == 5"
        elif line.startswith('E    '):
            result["error_message"] = line.replace('E    ', '').strip()

    return result


PARSERS = [
    parse_json_log,
    parse_log4j,
    parse_padrao,
    parse_nginx,
    parse_syslog,
    parse_python,
    parse_raw,
    parse_pytest_log,
]


def parse_line(raw: str) -> Optional[LogEntry]:
    """Selecionar e aplicar o parser mais adequado para uma linha de log individual.

    Use como ponto de entrada único quando o formato da linha não é conhecido
    antecipadamente. Itera sobre a lista ordenada ``PARSERS`` (json → log4j →
    padrao → nginx → syslog → python → raw → parse_pytest_log) e retorna o
    resultado do primeiro parser bem-sucedido. A ordem garante que formatos mais
    específicos são tentados antes do fallback ``raw``, evitando que linhas JSON
    ou Log4j sejam tratadas como texto livre. É a função chamada internamente por
    ``parse_log_line``, que converte o LogEntry para dict consumível pelo agente.

    Args:
        raw: Linha bruta de log em qualquer formato suportado pela tool.

    Returns:
        LogEntry preenchido pelo primeiro parser que reconheceu a linha, ou None
        se a linha estiver vazia e nem mesmo ``parse_raw`` conseguir processá-la.
    """
    for parser in PARSERS:
        entry = parser(raw)
        if entry is not None:
            return entry
    return None


# ── tool para agente de testes ────────────────────────────────────────────────

def parse_log_line(line: str) -> dict:
    """Parse de linha única de log detectando formato automaticamente.

    Args:
        line: Linha de log a ser parseada.

    Returns:
        dict: Campos extraídos (timestamp, level, module, message, format) ou None se falhar.

    Note:
        Suporta formatos: padrão, log4j, syslog, python logging, nginx/apache, JSON e raw.
    """
    entry = parse_line(line)
    if entry is None:
        return None
    return asdict(entry)


def parse_log_lines(lines: list[str]) -> list[dict]:
    """Parse de múltiplas linhas de log individualmente.

    Args:
        lines: Lista de linhas de log.

    Returns:
        list[dict]: Lista de entradas estruturadas (linhas vazias ignoradas).
    """
    results = []
    for line in lines:
        entry = parse_log_line(line)
        if entry is not None:
            results.append(entry)
    return results


def parse_log_text(text: str) -> list[dict]:
    """Parse de bloco de texto com múltiplas linhas de log.

    Args:
        text: Bloco de texto com linhas de log separadas por newline.

    Returns:
        list[dict]: Lista de entradas estruturadas.
    """
    return parse_log_lines(text.splitlines())

def execute_tool(tool_name: str, tool_input: dict):
    """Executa tool de log parser pelo nome.

    Args:
        tool_name: Nome da tool (parse_log_line, parse_log_lines, parse_pytest_log).
        tool_input: Dicionário de parâmetros para a tool.

    Returns:
        Resultado da execução da tool.

    Raises:
        ValueError: Se o nome da tool não for encontrado.
    """
    for tool in PARSERS:
        if tool.__name__ == tool_name:
            return tool(**tool_input)
    raise ValueError(f"Tool '{tool_name}' não encontrada.")
