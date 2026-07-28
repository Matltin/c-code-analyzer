int global_value = 10;

int calculate(int input) {
    int result = input;
    {
        int global_value = result;
        result = global_value + 1;
    }
    return result;
}

int main(void) {
    return calculate(global_value);
}
