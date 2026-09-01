package checkout

import "errors"

type CheckoutService struct {
	repository *InventoryRepository
}

func NewCheckoutService(repository *InventoryRepository) *CheckoutService {
	return &CheckoutService{repository: repository}
}

func (s *CheckoutService) Checkout(sku string, quantity int) (string, error) {
	if !s.repository.Reserve(sku, quantity) {
		return "", errors.New("insufficient stock")
	}
	return "reserved:" + sku + ":1", nil
}
