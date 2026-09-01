package calculator

import "errors"

func Add(left, right int) int {
	return left + right
}

func Divide(dividend, divisor float64) (float64, error) {
	if divisor == 0 {
		return 0, errors.New("divisor must not be zero")
	}
	return dividend / divisor, nil
}
