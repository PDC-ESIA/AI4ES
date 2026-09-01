package com.example;

import java.util.HashMap;
import java.util.Map;

public final class InventoryRepository {
    private final Map<String, Integer> stock = new HashMap<>();

    public InventoryRepository(String sku, int quantity) {
        stock.put(sku, quantity);
    }

    public boolean reserve(String sku, int quantity) {
        int available = stock.getOrDefault(sku, 0);
        if (available < quantity) return false;
        stock.put(sku, available - quantity);
        return true;
    }
}
