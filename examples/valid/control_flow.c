int main(void) {
    int i = 0;
    while (i < 10) {
        if (i == 5) {
            break;
        }
        i++;
    }
    for (i = 0; i < 3; i++) {
        continue;
    }
    return i;
}

