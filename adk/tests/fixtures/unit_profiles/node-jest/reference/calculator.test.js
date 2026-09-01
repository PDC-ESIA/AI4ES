const { add, divide } = require("../../src/calculator");

describe("calculator", () => {
  test("adds two numbers", () => {
    expect(add(2, 3)).toBe(5);
  });

  test("rejects division by zero", () => {
    expect(() => divide(10, 0)).toThrow(RangeError);
  });
});
