from app.repository import InventoryRepository


class CheckoutService:
    def __init__(self, repository: InventoryRepository):
        self._repository = repository

    def checkout(self, sku: str, quantity: int) -> str:
        if not self._repository.reserve(sku, quantity):
            raise ValueError("insufficient stock")
        return f"reserved:{sku}:{quantity}"
