package com.example;

public final class CheckoutService {
    private final InventoryRepository repository;

    public CheckoutService(InventoryRepository repository) {
        this.repository = repository;
    }

    public String checkout(String sku, int quantity) {
        if (!repository.reserve(sku, quantity)) {
            throw new IllegalStateException("insufficient stock");
        }
        return "reserved:" + sku + ":" + quantity;
    }
}
