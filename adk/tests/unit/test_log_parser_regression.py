"""Testes de regressão do log_parser_tool.

Cobre o bug do crash `asdict() should be called on dataclass instances`:
`parse_pytest_log` estava indevidamente na lista `PARSERS` e retornava dict
(nunca None), fazendo `parse_log_line` estourar em linhas em branco.
"""

from dataclasses import is_dataclass

from shared.tools.log_parser_tool import (
    LogEntry,
    PARSERS,
    parse_line,
    parse_log_line,
    parse_log_text,
    parse_pytest_log,
)


def test_parsers_respeitam_contrato_logentry_ou_none():
    # Toda linha (inclusive vazia) deve produzir LogEntry ou None — nunca dict.
    for line in ["", "   ", "linha qualquer", "2024-01-01T00:00:00 INFO [mod] msg"]:
        entry = parse_line(line)
        assert entry is None or is_dataclass(entry)


def test_parse_pytest_log_fora_de_parsers():
    # parse_pytest_log tem contrato distinto (retorna dict) e NÃO deve estar
    # na cadeia line-a-line de PARSERS.
    assert parse_pytest_log not in PARSERS


def test_linha_em_branco_nao_estoura_e_retorna_none():
    # Regressão direta do TypeError: asdict() em linha vazia.
    assert parse_log_line("") is None
    assert parse_log_line("   ") is None


def test_parse_log_text_com_linhas_em_branco():
    texto = "linha1\n\nlinha2\n   \nlinha3\n"
    resultado = parse_log_text(texto)
    # Não lança e ignora as linhas em branco (3 linhas com conteúdo).
    assert isinstance(resultado, list)
    assert len(resultado) == 3
    assert all(isinstance(item, dict) for item in resultado)


def test_parse_log_text_com_traceback_pytest_nao_estoura():
    traceback_text = (
        'Traceback (most recent call last):\n'
        '  File "test_x.py", line 7, in test_falha\n'
        '    assert 2 + 2 == 5\n'
        '\n'
        'E    assert (2 + 2) == 5\n'
        'test_x.py:7: AssertionError\n'
    )
    resultado = parse_log_text(traceback_text)
    # As linhas do traceback viram entradas raw; linha em branco é ignorada.
    assert isinstance(resultado, list)
    assert all(isinstance(item, dict) for item in resultado)
    assert len(resultado) == 5


def test_parse_pytest_log_ainda_funciona_standalone():
    # A função continua acessível e retorna dict estruturado.
    parsed = parse_pytest_log('test_x.py:7: AssertionError')
    assert isinstance(parsed, dict)
    assert parsed["error_type"] == " AssertionError"


def test_linha_conhecida_vira_dict_completo():
    line = "2024-01-01T12:00:00 ERROR [auth] falha de login"
    parsed = parse_log_line(line)
    assert isinstance(parsed, dict)
    assert parsed["level"] == "ERROR"
    assert parsed["module"] == "auth"
    assert parsed["format"] == "padrao"


def test_logentry_e_dataclass():
    assert is_dataclass(LogEntry)
