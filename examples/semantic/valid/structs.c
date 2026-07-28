struct Point {
    int x;
    int y;
};

int sum_point(struct Point *point) {
    return point->x + point->y;
}

int main(void) {
    struct Point point = {2, 3};
    return sum_point(&point);
}
