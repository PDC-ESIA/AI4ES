
from log_parser_tool import parse_log_line, parse_log_lines, parse_log_text, filter_by_level, filter_by_module, parse_pytest_log
from build_fix_prompt import build_fix_prompt_from_error, build_fix_prompt_from_log_entry, build_fix_prompt_from_pytest


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
    {
        "name": "parse_pytest_log",
        "description": (
            "Faz o parse de um traceback completo de pytest e retorna um dicionário estruturado "
            "com file, line, function, error_type, error_message, assertion e raw. "
            "Use quando precisar analisar erros de testes pytest que resultam em tracebacks."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "traceback_text": {
                    "type": "string",
                    "description": "O texto completo do traceback gerado pelo pytest."
                }
            },
            "required": ["traceback_text"]
        },
        "function": parse_pytest_log,
    },
]


CODE_FIX_PROMPT_TOOLS = [
    {
        "name": "build_fix_prompt_from_error",
        "description": (
            "Gera um prompt estruturado para um agente de correção de código "
            "a partir da descrição textual de um erro. "
            "O prompt resultante instrui o agente a identificar a causa raiz, "
            "explicar o problema e reescrever o código corrigido. "
            "Use quando tiver a mensagem de erro ou traceback em formato de texto."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "error_description": {
                    "type": "string",
                    "description": (
                        "Descrição do erro, mensagem de exceção ou traceback completo. "
                        "Ex: 'AssertionError: assert entry.module == \"auth\"' ou "
                        "um traceback completo do pytest."
                    )
                },
                "original_code": {
                    "type": "string",
                    "description": "Código-fonte que precisa ser corrigido (opcional)."
                },
                "test_code": {
                    "type": "string",
                    "description": "Código dos testes que falharam (opcional)."
                },
                "context": {
                    "type": "string",
                    "description": "Contexto adicional sobre o comportamento esperado (opcional)."
                },
                "language": {
                    "type": "string",
                    "description": "Linguagem de programação do código. Padrão: 'Python'."
                }
            },
            "required": ["error_description"]
        },
        "function": build_fix_prompt_from_error,
    },
    {
        "name": "build_fix_prompt_from_log_entry",
        "description": (
            "Gera um prompt estruturado para um agente de correção de código "
            "a partir de uma entrada de log já parseada. "
            "Encadeia diretamente com as tools do log_parser_tool — "
            "passe o dict retornado por parse_log_line como log_entry. "
            "Use quando o erro vier de um log estruturado."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "log_entry": {
                    "type": "object",
                    "description": (
                        "Entrada de log parseada com os campos: "
                        "level, module, message, timestamp, raw, format. "
                        "Retornada por parse_log_line ou parse_log_lines."
                    )
                },
                "original_code": {
                    "type": "string",
                    "description": "Código-fonte que precisa ser corrigido (opcional)."
                },
                "test_code": {
                    "type": "string",
                    "description": "Código dos testes que falharam (opcional)."
                },
                "language": {
                    "type": "string",
                    "description": "Linguagem de programação do código. Padrão: 'Python'."
                }
            },
            "required": ["log_entry"]
        },
        "function": build_fix_prompt_from_log_entry,
    },
    {
        "name": "build_fix_prompt_from_pytest",
        "description": (
            "Gera um prompt estruturado para um agente de correção de código "
            "a partir de um traceback completo de pytest. "
            "Encadeia diretamente com parse_pytest_log — passe o texto do traceback. "
            "Use quando o erro vier de um teste pytest que falhou."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "traceback_text": {
                    "type": "string",
                    "description": "Texto completo do traceback de pytest."
                },
                "original_code": {
                    "type": "string",
                    "description": "Código-fonte que precisa ser corrigido (opcional)."
                },
                "test_code": {
                    "type": "string",
                    "description": "Código dos testes que falharam (opcional)."
                },
                "language": {
                    "type": "string",
                    "description": "Linguagem de programação do código. Padrão: 'Python'."
                }
            },
            "required": ["traceback_text"]
        },
        "function": build_fix_prompt_from_pytest,
    },
]