struct Item { int value; };

int consume(int value) {
    return value;
}

int main(void) {
    int missing_initialization;
    int *pointer = 0;
    pointer = 7;
    consume("wrong");
    struct Item item = {1};
    item.unknown = 3;
    undefined_name = missing_initialization;
    return 0;
}
