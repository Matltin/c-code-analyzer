// A small structure used for field navigation and rename.
struct Point {
    int x;
    int y;
};

int point_sum(struct Point point) {
    return point.x + point.y;
}
