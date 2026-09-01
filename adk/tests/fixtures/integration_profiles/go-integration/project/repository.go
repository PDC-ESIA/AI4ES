package checkout

type InventoryRepository struct {
	stock map[string]int
}

func NewInventoryRepository(sku string, quantity int) *InventoryRepository {
	return &InventoryRepository{stock: map[string]int{sku: quantity}}
}

func (r *InventoryRepository) Reserve(sku string, quantity int) bool {
	available := r.stock[sku]
	if available < quantity {
		return false
	}
	r.stock[sku] = available - quantity
	return true
}
