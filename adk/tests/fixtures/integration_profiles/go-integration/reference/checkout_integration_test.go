package checkout

import "testing"

func TestCheckoutReservesInventory(t *testing.T) {
	service := NewCheckoutService(NewInventoryRepository("CAMERA", 2))
	result, err := service.Checkout("CAMERA", 1)
	if err != nil || result != "reserved:CAMERA:1" {
		t.Fatalf("unexpected checkout result: %q, %v", result, err)
	}
}

func TestCheckoutRejectsInsufficientInventory(t *testing.T) {
	service := NewCheckoutService(NewInventoryRepository("CAMERA", 0))
	if _, err := service.Checkout("CAMERA", 1); err == nil {
		t.Fatal("expected insufficient stock error")
	}
}
