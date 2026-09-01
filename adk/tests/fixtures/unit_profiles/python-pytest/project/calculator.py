"""Código mínimo usado na demonstração do perfil Python/pytest."""


def add(left: int, right: int) -> int:
    return left + right


def divide(dividend: float, divisor: float) -> float:
    if divisor == 0:
        raise ValueError("divisor must not be zero")
    return dividend / divisor
