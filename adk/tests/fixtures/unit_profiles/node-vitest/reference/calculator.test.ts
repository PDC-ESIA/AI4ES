import { describe, expect, it } from "vitest";

import { add, divide } from "../../src/calculator";

describe("calculator", () => {
  it("adds two numbers", () => {
    expect(add(2, 3)).toBe(5);
  });

  it("rejects division by zero", () => {
    expect(() => divide(10, 0)).toThrow(RangeError);
  });
});
