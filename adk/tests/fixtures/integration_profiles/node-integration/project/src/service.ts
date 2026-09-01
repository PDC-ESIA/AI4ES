import { InventoryRepository } from './repository.ts';

export class CheckoutService {
  private readonly repository: InventoryRepository;

  constructor(repository: InventoryRepository) {
    this.repository = repository;
  }

  checkout(sku: string, quantity: number): string {
    if (!this.repository.reserve(sku, quantity)) {
      throw new RangeError('insufficient stock');
    }
    return `reserved:${sku}:${quantity}`;
  }
}
