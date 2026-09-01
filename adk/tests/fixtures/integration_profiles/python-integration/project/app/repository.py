class InventoryRepository:
    def __init__(self, stock: dict[str, int]):
        self._stock = stock

    def reserve(self, sku: str, quantity: int) -> bool:
        available = self._stock.get(sku, 0)
        if available < quantity:
            return False
        self._stock[sku] = available - quantity
        return True
