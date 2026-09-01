import assert from 'node:assert/strict';
import test from 'node:test';

import { InventoryRepository } from '../../src/repository.ts';
import { CheckoutService } from '../../src/service.ts';

test('checkout reserves inventory', () => {
  const service = new CheckoutService(
    new InventoryRepository(new Map([['CAMERA', 2]])),
  );
  assert.equal(service.checkout('CAMERA', 1), 'reserved:CAMERA:1');
});

test('checkout rejects insufficient inventory', () => {
  const service = new CheckoutService(
    new InventoryRepository(new Map([['CAMERA', 0]])),
  );
  assert.throws(() => service.checkout('CAMERA', 1), /insufficient stock/);
});
