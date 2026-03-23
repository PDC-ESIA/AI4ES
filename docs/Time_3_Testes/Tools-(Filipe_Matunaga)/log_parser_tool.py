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

NIVEL_HTTP = {
    "1": "INFO", "2": "INFO", "3": "INFO",
    "4": "ERROR", "5": "CRITICAL"
}


def _nivel_nginx(status: str) -> str:
    return NIVEL_HTTP.get(status[0], "INFO")


def parse_padrao(raw: str) -> Optional[LogEntry]:
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


PARSERS = [
    parse_json_log,
    parse_log4j,
    parse_padrao,
    parse_nginx,
    parse_syslog,
    parse_python,
    parse_raw,
]


def parse_line(raw: str) -> Optional[LogEntry]:
    for parser in PARSERS:
        entry = parser(raw)
        if entry is not None:
            return entry
    return None


# ── tool para agente de testes ────────────────────────────────────────────────

def parse_log_line(line: str) -> dict:
    """
    Faz o parse de uma única linha de log e retorna um dicionário com os campos extraídos.

    Parâmetros:
        line (str): Uma linha de log em qualquer formato suportado
                    (padrão, log4j, syslog, python, nginx, json, raw).

    Retorna:
        dict com os campos: timestamp, level, module, message, raw, format.
        Retorna None se a linha estiver vazia.

    Formatos suportados:
        - padrão:  2024-01-15T10:23:45 ERROR [auth] mensagem
        - log4j:   2024-01-15 10:23:45,123 ERROR com.app.Service - mensagem
        - syslog:  Jan 15 10:23:45 host sshd[1234]: mensagem
        - python:  ERROR:modulo:mensagem
        - nginx:   IP - - [timestamp] "GET /path HTTP/1.1" 404 512
        - json:    {"level":"ERROR","module":"auth","message":"falha"}
        - raw:     qualquer outra linha não vazia (fallback)
    """
    entry = parse_line(line)
    if entry is None:
        return None
    return asdict(entry)


def parse_log_lines(lines: list[str]) -> list[dict]:
    """
    Faz o parse de uma lista de linhas de log.

    Parâmetros:
        lines (list[str]): Lista de linhas de log.

    Retorna:
        Lista de dicionários com os campos de cada entrada.
        Linhas vazias são ignoradas (não aparecem no resultado).
    """
    results = []
    for line in lines:
        entry = parse_log_line(line)
        if entry is not None:
            results.append(entry)
    return results


def parse_log_text(text: str) -> list[dict]:
    """
    Faz o parse de um bloco de texto com múltiplas linhas de log.

    Parâmetros:
        text (str): Texto completo com várias linhas de log.

    Retorna:
        Lista de dicionários com os campos de cada entrada parseada.
    """
    return parse_log_lines(text.splitlines())


def filter_by_level(entries: list[dict], level: str) -> list[dict]:
    """
    Filtra entradas de log por nível de severidade.

    Parâmetros:
        entries (list[dict]): Lista de entradas retornadas por parse_log_lines ou parse_log_text.
        level (str): Nível desejado (ex: "ERROR", "INFO", "WARN", "CRITICAL").

    Retorna:
        Lista filtrada com apenas as entradas do nível especificado.
    """
    return [e for e in entries if e["level"].upper() == level.upper()]


def filter_by_module(entries: list[dict], module: str) -> list[dict]:
    """
    Filtra entradas de log por módulo.

    Parâmetros:
        entries (list[dict]): Lista de entradas retornadas por parse_log_lines ou parse_log_text.
        module (str): Nome do módulo (ex: "auth", "db", "api").

    Retorna:
        Lista filtrada com apenas as entradas do módulo especificado.
    """
    return [e for e in entries if e["module"] == module]


# ── definição da tool para o agente ──────────────────────────────────────────

LOG_PARSER_TOOLS = [
    {
        "name": "parse_log_line",
        "description": (
            "Faz o parse de uma única linha de log e retorna os campos extraídos "
            "(timestamp, level, module, message, format). "
            "Suporta os formatos: padrão, log4j, syslog, python logging, nginx/apache, JSON e raw. "
            "Use quando precisar analisar uma linha isolada de log em um teste."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "line": {
                    "type": "string",
                    "description": "A linha de log a ser parseada."
                }
            },
            "required": ["line"]
        },
        "function": parse_log_line,
    },
    {
        "name": "parse_log_lines",
        "description": (
            "Faz o parse de uma lista de linhas de log e retorna uma lista de entradas estruturadas. "
            "Linhas vazias são ignoradas. "
            "Use quando precisar processar múltiplas linhas individualmente em um teste."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lines": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de linhas de log."
                }
            },
            "required": ["lines"]
        },
        "function": parse_log_lines,
    },
    {
        "name": "parse_log_text",
        "description": (
            "Faz o parse de um bloco de texto com múltiplas linhas de log. "
            "Use quando o log estiver em formato de texto corrido com quebras de linha."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Bloco de texto com as linhas de log separadas por quebras de linha."
                }
            },
            "required": ["text"]
        },
        "function": parse_log_text,
    },
    {
        "name": "filter_by_level",
        "description": (
            "Filtra uma lista de entradas de log por nível de severidade (ex: ERROR, INFO, WARN). "
            "Use após parse_log_lines ou parse_log_text para isolar entradas de um nível específico."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "entries": {
                    "type": "array",
                    "description": "Lista de entradas de log (dicionários retornados pelo parser)."
                },
                "level": {
                    "type": "string",
                    "description": "Nível de log desejado. Ex: 'ERROR', 'INFO', 'WARN', 'CRITICAL'."
                }
            },
            "required": ["entries", "level"]
        },
        "function": filter_by_level,
    },
    {
        "name": "filter_by_module",
        "description": (
            "Filtra uma lista de entradas de log por nome de módulo. "
            "Use após parse_log_lines ou parse_log_text para isolar entradas de um módulo específico."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "entries": {
                    "type": "array",
                    "description": "Lista de entradas de log (dicionários retornados pelo parser)."
                },
                "module": {
                    "type": "string",
                    "description": "Nome do módulo desejado. Ex: 'auth', 'db', 'api'."
                }
            },
            "required": ["entries", "module"]
        },
        "function": filter_by_module,
    },
]


def execute_tool(tool_name: str, tool_input: dict):
    """
    Executa uma tool pelo nome, passando os inputs necessários.
    Use essa função no loop do agente para despachar chamadas de tool.

    Exemplo:
        result = execute_tool("parse_log_line", {"line": "2024-01-15T10:23:45 ERROR [auth] falha"})
    """
    for tool in LOG_PARSER_TOOLS:
        if tool["name"] == tool_name:
            return tool["function"](**tool_input)
    raise ValueError(f"Tool '{tool_name}' não encontrada.")
