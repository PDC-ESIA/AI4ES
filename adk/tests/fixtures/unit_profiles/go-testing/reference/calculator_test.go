package calculator

import "testing"

func TestAdd(t *testing.T) {
	if result := Add(2, 3); result != 5 {
		t.Fatalf("Add(2, 3) = %d; want 5", result)
	}
}

func TestDivideRejectsZero(t *testing.T) {
	if _, err := Divide(10, 0); err == nil {
		t.Fatal("Divide(10, 0) should return an error")
	}
}
