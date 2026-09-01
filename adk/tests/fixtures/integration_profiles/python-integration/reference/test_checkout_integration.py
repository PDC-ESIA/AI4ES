import pytest

from app.repository import InventoryRepository
from app.service import CheckoutService


def test_checkout_reserves_inventory():
    service = CheckoutService(InventoryRepository({"CAMERA": 2}))

    assert service.checkout("CAMERA", 1) == "reserved:CAMERA:1"


def test_checkout_rejects_insufficient_inventory():
    service = CheckoutService(InventoryRepository({"CAMERA": 0}))

    with pytest.raises(ValueError, match="insufficient stock"):
        service.checkout("CAMERA", 1)
