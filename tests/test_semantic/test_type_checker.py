"""Tests for Phase 2.3 type checking and initialization analysis."""

from c_analyzer.ast import (
    BinaryExpr,
    CallExpr,
    FunctionDecl,
    IndexExpr,
    MemberExpr,
    VarDecl,
)
from c_analyzer.lexer import tokenize
from c_analyzer.parser import parse
from c_analyzer.semantic import (
    CHAR,
    DOUBLE,
    FLOAT,
    INT,
    PointerType,
    analyze,
)


def analyze_source(source: str):
    parsed = parse(tokenize(source, "types.c").tokens)
    return parsed.ast, analyze(parsed.ast)


def error_messages(result) -> list[str]:
    return [
        item.message
        for item in result.diagnostics
        if item.severity.value == "error"
    ]


def test_literal_types_are_recorded_in_semantic_side_table() -> None:
    program, result = analyze_source(
        """
int main(void) {
    int integer = 1;
    double real = 3.14;
    float small = .5f;
    char letter = 'a';
    char *text = "hello";
    return integer;
}
"""
    )
    declarations = program.declarations[0].body.items[:5]
    assert [result.model.type_of(item.initializer) for item in declarations] == [
        INT,
        DOUBLE,
        FLOAT,
        CHAR,
        PointerType(CHAR),
    ]


def test_numeric_widening_is_allowed_and_narrowing_warns() -> None:
    _, result = analyze_source(
        "int main(void) { float wide = 1; int narrow = 2.5; return narrow; }"
    )

    assert not error_messages(result)
    assert any("narrowing conversion" in item.message for item in result.diagnostics)


def test_assignment_type_mismatch_is_an_error() -> None:
    _, result = analyze_source(
        "int main(void) { int *pointer; pointer = 1; return 0; }"
    )

    assert any("type mismatch in assignment" in item for item in error_messages(result))


def test_address_of_pointer_assignment_and_dereference_are_typed() -> None:
    program, result = analyze_source(
        """
int main(void) {
    int value;
    int *pointer = &value;
    *pointer = 1;
    return 0;
}
"""
    )
    pointer = program.declarations[0].body.items[1]
    assignment = program.declarations[0].body.items[2].expression

    assert result.model.type_of(pointer.initializer) == PointerType(INT)
    assert result.model.type_of(assignment.target) == INT
    assert not error_messages(result)


def test_array_index_and_struct_members_have_element_and_field_types() -> None:
    program, result = analyze_source(
        """
struct Point { int x; };
int main(void) {
    int values[2] = {1, 2};
    struct Point point = {3};
    int first = values[0];
    return point.x + first;
}
"""
    )
    function = program.declarations[1]
    index = function.body.items[2].initializer
    member = function.body.items[3].value.left

    assert isinstance(index, IndexExpr)
    assert isinstance(member, MemberExpr)
    assert result.model.type_of(index) == INT
    assert result.model.type_of(member) == INT
    assert not error_messages(result)


def test_arrow_member_on_pointer_to_struct_has_field_type() -> None:
    program, result = analyze_source(
        """
struct Point { int x; };
int read(struct Point *point) { return point->x; }
"""
    )
    member = program.declarations[1].body.items[0].value

    assert result.model.type_of(member) == INT
    assert not error_messages(result)


def test_pointer_arithmetic_is_out_of_scope() -> None:
    _, result = analyze_source(
        "int main(void) { int *pointer = 0; pointer + 1; return 0; }"
    )

    assert any("requires numeric operands" in item for item in error_messages(result))


def test_comparison_and_logical_expression_result_is_int() -> None:
    program, result = analyze_source(
        "int main(void) { int value = (1 < 2) && 3; return value; }"
    )
    expression = program.declarations[0].body.items[0].initializer

    assert isinstance(expression, BinaryExpr)
    assert result.model.type_of(expression) == INT
    assert not error_messages(result)


def test_function_argument_count_and_type_are_checked() -> None:
    _, result = analyze_source(
        """
int add(int left, int right) { return left + right; }
int main(void) {
    add(1);
    add("wrong", 2);
    return 0;
}
"""
    )
    messages = error_messages(result)

    assert any("wrong number of arguments" in item for item in messages)
    assert any("function call argument 1" in item for item in messages)


def test_return_rules_for_void_nonvoid_and_mismatched_types() -> None:
    _, result = analyze_source(
        """
void bad_void(void) { return 1; }
int bad_empty(void) { return; }
int bad_type(void) { return "text"; }
"""
    )
    messages = error_messages(result)

    assert any("void function must not return a value" in item for item in messages)
    assert any("non-void function must return int" in item for item in messages)
    assert any("type mismatch in return" in item for item in messages)


def test_printf_and_puts_builtin_rules() -> None:
    _, valid = analyze_source(
        'int main(void) { puts("hello"); printf("%d", 1); return 0; }'
    )
    _, invalid = analyze_source(
        "int main(void) { puts(); puts(1); printf(); return 0; }"
    )

    assert not error_messages(valid)
    invalid_messages = error_messages(invalid)
    assert sum("wrong number of arguments" in item for item in invalid_messages) == 2
    assert any("function call argument 1" in item for item in invalid_messages)


def test_use_before_initialization_warning_and_assignment_updates_state() -> None:
    _, result = analyze_source(
        """
int main(void) {
    int value;
    int first = value;
    value = 2;
    return value;
}
"""
    )
    warnings = [
        item.message
        for item in result.diagnostics
        if item.severity.value == "warning"
    ]

    assert sum("before initialization" in item for item in warnings) == 1


def test_both_if_branches_guarantee_initialization() -> None:
    _, result = analyze_source(
        """
int main(void) {
    int value;
    if (1) { value = 1; } else { value = 2; }
    return value;
}
"""
    )

    assert not [
        item for item in result.diagnostics if "before initialization" in item.message
    ]


def test_loop_assignment_does_not_guarantee_initialization_after_loop() -> None:
    _, result = analyze_source(
        """
int main(void) {
    int value;
    while (0) { value = 1; }
    return value;
}
"""
    )

    assert any("before initialization" in item.message for item in result.diagnostics)


def test_unused_local_and_parameter_are_info_diagnostics() -> None:
    _, result = analyze_source(
        "int calculate(int input) { int temporary = 1; return 0; }"
    )
    infos = [
        item.message for item in result.diagnostics if item.severity.value == "info"
    ]

    assert "unused parameter 'input'" in infos
    assert "unused variable 'temporary'" in infos


def test_array_and_struct_initializer_errors_are_reported() -> None:
    _, result = analyze_source(
        """
struct Item { int value; };
int values[1] = {1, 2};
struct Item item = {"wrong"};
"""
    )
    messages = error_messages(result)

    assert any("too many elements in array initializer" in item for item in messages)
    assert any("type mismatch in initializer" in item for item in messages)


def test_invalid_lvalue_is_reported_and_later_expression_is_typed() -> None:
    program, result = analyze_source(
        "int main(void) { 1 = 2; int good = 3 + 4; return good; }"
    )
    good = program.declarations[0].body.items[1]
    assert isinstance(good, VarDecl)

    assert any("invalid lvalue" in item for item in error_messages(result))
    assert result.model.type_of(good.initializer) == INT

