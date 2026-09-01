const test = require("node:test");
const assert = require("node:assert/strict");

const { add, divide } = require("../../src/calculator");

test("add returns the sum", () => {
  assert.equal(add(2, 3), 5);
});

test("divide rejects zero", () => {
  assert.throws(() => divide(10, 0), /divisor must not be zero/);
});
