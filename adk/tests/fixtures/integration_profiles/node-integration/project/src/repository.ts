export class InventoryRepository {
  private readonly stock: Map<string, number>;

  constructor(stock: Map<string, number>) {
    this.stock = stock;
  }

  reserve(sku: string, quantity: number): boolean {
    const available = this.stock.get(sku) ?? 0;
    if (available < quantity) return false;
    this.stock.set(sku, available - quantity);
    return true;
  }
}
