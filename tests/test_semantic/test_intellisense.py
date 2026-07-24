"""Tests for completion ranking, member completion, and hover."""

from c_analyzer import analyze_source
from c_analyzer.semantic import complete, hover, position_from_line_column


def line_column(source: str, offset: int) -> tuple[int, int]:
    prefix = source[:offset]
    return prefix.count("\n") + 1, offset - prefix.rfind("\n")


def complete_at(source: str, offset: int):
    line, column = line_column(source, offset)
    return complete(analyze_source(source, "intellisense.c"), line, column)


def hover_at(source: str, text: str, occurrence: int = 0):
    starts = []
    cursor = 0
    while True:
        found = source.find(text, cursor)
        if found < 0:
            break
        starts.append(found)
        cursor = found + 1
    offset = starts[occurrence]
    line, column = line_column(source, offset)
    return hover(analyze_source(source, "intellisense.c"), line, column)


def test_general_completion_uses_innermost_scope_and_hides_shadowed_outer() -> None:
    source = """
int value = 1;
int main(void) {
    int value = 2;
    
    return value;
}
"""
    offset = source.index("    \n", source.index("int value = 2")) + 4
    items = complete_at(source, offset)
    values = [item for item in items if item.label == "value"]

    assert len(values) == 1
    assert values[0].kind == "variable"
    assert values[0].symbol_id != next(
        symbol.id
        for symbol in analyze_source(source, "intellisense.c").semantic.model.symbols
        if symbol.name == "value"
        and symbol.scope_id == "scope-0001"
    )


def test_local_variable_is_not_completed_before_its_declaration() -> None:
    source = """
int main(void) {
    int before = 1;
    
    int after = 2;
    return before;
}
"""
    offset = source.index("    \n", source.index("before")) + 4
    labels = {item.label for item in complete_at(source, offset)}

    assert "before" in labels
    assert "after" not in labels
    assert {"printf", "puts", "main"} <= labels


def test_prefix_match_ranks_before_fuzzy_subsequence() -> None:
    source = """
int main(void) {
    int apple = 1;
    int alphaPoint = 2;
    ap
}
"""
    offset = source.index("\n}", source.index("    ap"))
    items = complete_at(source, offset)
    labels = [item.label for item in items]

    assert labels.index("apple") < labels.index("alphaPoint")


def test_dot_and_arrow_member_completion_use_receiver_type() -> None:
    dot_source = """
struct Point { int x; double y; };
int main(void) {
    struct Point point = {1, 2.0};
    point.
}
"""
    arrow_source = """
struct Point { int x; double y; };
int main(void) {
    struct Point *point = 0;
    point->
}
"""
    dot_items = complete_at(dot_source, dot_source.index("\n}", dot_source.index("point.")))
    arrow_items = complete_at(
        arrow_source,
        arrow_source.index("\n}", arrow_source.index("point->")),
    )

    assert [(item.label, item.detail) for item in dot_items] == [
        ("x", "int"),
        ("y", "double"),
    ]
    assert [(item.label, item.detail) for item in arrow_items] == [
        ("x", "int"),
        ("y", "double"),
    ]


def test_argument_completion_ranks_compatible_types_first() -> None:
    source = """
int consume(double value) { return 0; }
int main(void) {
    int number = 1;
    char *text = "hello";
    consume();
    return 0;
}
"""
    offset = source.index("consume();") + len("consume(")
    items = complete_at(source, offset)
    labels = [item.label for item in items]

    assert labels.index("number") < labels.index("text")


def test_incomplete_member_and_argument_contexts_do_not_crash() -> None:
    member_source = """
struct Point { int x; };
int main(void) { struct Point point = {1}; point.
"""
    argument_source = """
int add(int value) { return value; }
int main(void) { int valid = 1; add(val
"""

    member_items = complete_at(member_source, len(member_source))
    argument_items = complete_at(argument_source, len(argument_source))

    assert [item.label for item in member_items] == ["x"]
    assert argument_items[0].label == "valid"


def test_hover_works_for_variable_reference_and_function_call() -> None:
    source = """
int add(int value) { return value; }
int main(void) {
    int number = 1;
    return add(number);
}
"""
    variable = hover_at(source, "number", occurrence=1)
    function = hover_at(source, "add", occurrence=1)

    assert variable is not None
    assert variable.name == "number"
    assert variable.kind == "variable"
    assert variable.type == "int"
    assert variable.definition is not None
    assert function is not None
    assert function.kind == "function"
    assert function.signature == "int add(int)"


def test_hover_works_for_struct_field_and_builtin() -> None:
    source = """
struct Point { int x; };
int main(void) {
    struct Point point = {1};
    puts("hello");
    return point.x;
}
"""
    struct = hover_at(source, "Point", occurrence=1)
    field_offset = source.index("point.x") + len("point.")
    field_line, field_column = line_column(source, field_offset)
    field = hover(
        analyze_source(source, "intellisense.c"),
        field_line,
        field_column,
    )
    builtin = hover_at(source, "puts")

    assert struct is not None and struct.kind == "struct"
    assert field is not None and field.kind == "field"
    assert builtin is not None and builtin.is_builtin
    assert builtin.definition is None
    assert builtin.signature == "int puts(char *text)"


def test_hover_without_symbol_returns_none() -> None:
    source = "int main(void) { return 0; }"
    line, column = line_column(source, source.index(" "))

    assert hover(analyze_source(source, "intellisense.c"), line, column) is None


def test_completion_and_hover_outputs_are_deterministic() -> None:
    source = "int main(void) { int value = 1; return value; }"
    offset = source.index("return")
    first = complete_at(source, offset)
    second = complete_at(source, offset)

    assert first == second
    assert hover_at(source, "value", 1) == hover_at(source, "value", 1)


def test_invalid_cursor_position_is_rejected_cleanly() -> None:
    source = "int main(void) { return 0; }"

    try:
        position_from_line_column(source, "cursor.c", 99, 1)
    except ValueError as error:
        assert "outside the source" in str(error)
    else:
        raise AssertionError("invalid line must be rejected")
