// Adds two integer values.
int add(int left, int right) {
    return left + right;
}

// Recursive function used by the call graph demo.
int factorial(int value) {
    if (value <= 1) {
        return 1;
    }
    return value * factorial(value - 1);
}
