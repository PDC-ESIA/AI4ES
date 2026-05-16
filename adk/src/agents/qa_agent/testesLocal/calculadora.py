"""Módulo Calculadora — cenário de teste para o QA Agent."""


def somar(a: float, b: float) -> float:
    """Retorna a soma de dois números."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Os operandos devem ser numéricos.")
    return a + b


def subtrair(a: float, b: float) -> float:
    """Retorna a subtração de a - b."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Os operandos devem ser numéricos.")
    return a - b


def multiplicar(a: float, b: float) -> float:
    """Retorna a multiplicação de dois números."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Os operandos devem ser numéricos.")
    return a * b


def dividir(a: float, b: float) -> float:
    """Retorna a divisão de a por b.

    Raises:
        ZeroDivisionError: Se b for zero.
        TypeError: Se os operandos não forem numéricos.
    """
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("Os operandos devem ser numéricos.")
    if b == 0:
        raise ZeroDivisionError("Divisão por zero não é permitida.")
    return a / b
