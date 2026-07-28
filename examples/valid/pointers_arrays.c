int main(void) {
    int value = 1;
    int *ptr = &value;
    int values[3] = {1, 2, 3};
    return *ptr + values[0];
}

