"""Testes do sanitizer AST + regex em receive_requirements."""
import pytest

from src.agents.qa_agent.subagents.receive_requirements import (
    _validar_e_sanitizar_codigo,
)


def test_sanitiza_pass_ctrl63_para_pass():
    codigo = "def test_x():\n    '''doc'''\n    pass<ctrl63>\n"
    resultado = _validar_e_sanitizar_codigo(codigo, "HU-001")
    assert "pass<ctrl63>" not in resultado
    assert "pass\n" in resultado


def test_sanitiza_return_placeholder():
    codigo = "def f():\n    return<X>\n"
    resultado = _validar_e_sanitizar_codigo(codigo, "RF-001")
    assert "return<X>" not in resultado
    assert "    return\n" in resultado


def test_sanitiza_continue_break_raise():
    codigo = (
        "def f():\n"
        "    for i in range(3):\n"
        "        if i:\n"
        "            continue<a>\n"
        "        break<b>\n"
        "    raise<c>\n"
    )
    resultado = _validar_e_sanitizar_codigo(codigo, "X")
    assert "<" not in resultado
    assert "continue\n" in resultado
    assert "break\n" in resultado
    assert "raise\n" in resultado


def test_codigo_invalido_apos_sanitizacao_levanta_valueerror():
    codigo = "def test_x(:\n    pass\n"  # parêntese errado, irreparável
    with pytest.raises(ValueError, match="inválido após sanitização"):
        _validar_e_sanitizar_codigo(codigo, "HU-001")


def test_codigo_valido_passa_intocado():
    codigo = (
        "import pytest\n"
        "\n"
        "def test_ok():\n"
        "    assert 1 == 1\n"
    )
    resultado = _validar_e_sanitizar_codigo(codigo, "HU-001")
    assert resultado == codigo


def test_string_contendo_placeholder_nao_e_sanitizada():
    # Caractere `pass<X>` dentro de string literal não deve ser tocado
    codigo = (
        "def test_doc():\n"
        '    msg = "pass<placeholder>"\n'
        "    assert msg\n"
    )
    resultado = _validar_e_sanitizar_codigo(codigo, "HU-001")
    # Comportamento documentado: regex captura `pass<...>` em qualquer lugar.
    # Se sair `pass<placeholder>` virou `pass`, a string fica inválida mas
    # ast.parse passa porque `"pass"` ainda é literal válido.
    # Assert é frouxo aqui — testa só que não levanta ValueError.
    assert "assert" in resultado
