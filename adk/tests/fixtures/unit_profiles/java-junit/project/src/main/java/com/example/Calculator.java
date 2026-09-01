package com.example;

public final class Calculator {
    private Calculator() {}

    public static int add(int left, int right) {
        return left + right;
    }

    public static double divide(double dividend, double divisor) {
        if (divisor == 0) {
            throw new IllegalArgumentException("divisor must not be zero");
        }
        return dividend / divisor;
    }
}
