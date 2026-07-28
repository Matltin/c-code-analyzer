int takes_int(int value) {
    return value;
}

int main(void) {
    int *pointer;
    pointer = 1;
    int narrowed = 2.5;
    puts(42);
    takes_int("wrong");
    return "not an int";
}
