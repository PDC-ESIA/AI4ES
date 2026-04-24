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
    for tool in LOG_PARSER_TOOLS:
        if tool["name"] == tool_name:
            return tool["function"](**tool_input)
    raise ValueError(f"Tool '{tool_name}' não encontrada.")
