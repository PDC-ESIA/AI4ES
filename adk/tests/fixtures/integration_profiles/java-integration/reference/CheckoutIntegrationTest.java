package com.example;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

class CheckoutIntegrationTest {
    @Test
    void checkoutReservesInventory() {
        var service = new CheckoutService(new InventoryRepository("CAMERA", 2));
        assertEquals("reserved:CAMERA:1", service.checkout("CAMERA", 1));
    }

    @Test
    void checkoutRejectsInsufficientInventory() {
        var service = new CheckoutService(new InventoryRepository("CAMERA", 0));
        assertThrows(IllegalStateException.class, () -> service.checkout("CAMERA", 1));
    }
}
