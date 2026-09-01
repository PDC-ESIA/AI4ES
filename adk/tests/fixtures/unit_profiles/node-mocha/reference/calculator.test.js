const assert = require("node:assert/strict");

const { add, divide } = require("../../src/calculator");

describe("calculator", () => {
  it("adds two numbers", () => {
    assert.equal(add(2, 3), 5);
  });

  it("rejects division by zero", () => {
    assert.throws(() => divide(10, 0), RangeError);
  });
});
