export function add(left: number, right: number): number {
  return left + right;
}

export function divide(dividend: number, divisor: number): number {
  if (divisor === 0) {
    throw new RangeError("divisor must not be zero");
  }
  return dividend / divisor;
}
