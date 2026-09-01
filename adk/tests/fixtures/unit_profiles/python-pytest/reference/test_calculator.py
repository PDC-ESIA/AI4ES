import pytest

from calculator import add, divide


def test_add_returns_sum():
    assert add(2, 3) == 5


def test_divide_rejects_zero():
    with pytest.raises(ValueError, match="divisor must not be zero"):
        divide(10, 0)
