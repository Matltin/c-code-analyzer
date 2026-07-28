struct Point { int x; int y; };

int calculate(int input) {
    return input + 1;
}

int main(void) {
    struct Point point = {1, 2};
    int value = 3;
    int result = calculate(value);
    return result + point.x;
}
