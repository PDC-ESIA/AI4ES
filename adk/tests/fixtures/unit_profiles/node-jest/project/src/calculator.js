function add(left, right) {
  return left + right;
}

function divide(dividend, divisor) {
  if (divisor === 0) {
    throw new RangeError("divisor must not be zero");
  }
  return dividend / divisor;
}

module.exports = { add, divide };
