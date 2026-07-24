"""Tests for two-pass name resolution and reference tracking."""

from c_analyzer.ast import (
    AssignmentExpr,
    CallExpr,
    FunctionDecl,
    IdentifierExpr,
    MemberExpr,
    UnaryExpr,
)
from c_analyzer.lexer import tokenize
from c_analyzer.parser import parse
from c_analyzer.semantic import AccessKind, SymbolKind, analyze


def analyze_source(source: str):
    parsed = parse(tokenize(source, "resolution.c").tokens)
    return parsed.ast, analyze(parsed.ast)


def test_forward_function_call_resolves_from_first_pass() -> None:
    program, result = analyze_source(
        """
int main(void) { return later(1); }
int later(int value) { return value; }
"""
    )
    main = program.declarations[0]
    assert isinstance(main, FunctionDecl)
    call = main.body.items[0].value
    assert isinstance(call, CallExpr)
    assert isinstance(call.callee, IdentifierExpr)

    symbol = result.model.symbol_of(call.callee)
    assert symbol is not None and symbol.name == "later"
    assert symbol.references[0].access_kind is AccessKind.CALL


def test_nested_scope_reference_binds_to_shadowing_symbol() -> None:
    program, result = analyze_source(
        """
int value = 1;
int main(void) {
    int value = 2;
    { return value; }
}
"""
    )
    function = program.declarations[1]
    reference = function.body.items[1].items[0].value
    local = result.model.symbol_of(reference)
    global_symbol = result.model.global_scope.lookup_local("value")

    assert local is not None and global_symbol is not None
    assert local.id != global_symbol.id
    assert local.scope_id != global_symbol.scope_id


def test_shadowing_produces_warning() -> None:
    _, result = analyze_source(
        "int value; int main(void) { int value = 1; return value; }"
    )

    assert any(
        item.severity.value == "warning" and "shadows" in item.message
        for item in result.diagnostics
    )


def test_local_is_visible_only_after_its_declaration() -> None:
    _, result = analyze_source(
        "int main(void) { value = 1; int value; return value; }"
    )

    assert any("undefined symbol 'value'" in item.message for item in result.diagnostics)


def test_undefined_identifier_does_not_stop_later_resolution() -> None:
    program, result = analyze_source(
        "int main(void) { missing = 1; int good = 2; return good; }"
    )
    function = program.declarations[0]
    later_reference = function.body.items[2].value

    assert any("undefined symbol 'missing'" in item.message for item in result.diagnostics)
    assert result.model.symbol_of(later_reference).name == "good"


def test_duplicate_declaration_is_reported() -> None:
    _, result = analyze_source("int main(void) { int value; int value; return 0; }")

    assert any("duplicate declaration 'value'" in item.message for item in result.diagnostics)


def test_compatible_prototype_and_definition_share_one_symbol() -> None:
    program, result = analyze_source(
        "int add(int value); int add(int value) { return value; }"
    )
    prototype, definition = program.declarations

    assert not [
        item for item in result.diagnostics if "conflicting declaration" in item.message
    ]
    assert (
        result.model.symbol_of(prototype.name).id
        == result.model.symbol_of(definition.name).id
    )


def test_conflicting_prototype_and_duplicate_definition_are_reported() -> None:
    _, result = analyze_source(
        """
int add(int value);
double add(int value);
int add(int value) { return value; }
int add(int value) { return value; }
"""
    )
    messages = [item.message for item in result.diagnostics]

    assert any("conflicting declaration" in item for item in messages)
    assert any("duplicate function definition" in item for item in messages)


def test_struct_tag_and_dot_field_resolve_in_separate_namespaces() -> None:
    program, result = analyze_source(
        """
struct Point { int x; int y; };
int main(void) { struct Point point = {1, 2}; return point.x; }
"""
    )
    function = program.declarations[1]
    declaration = function.body.items[0]
    member = function.body.items[1].value
    assert isinstance(member, MemberExpr)

    tag = result.model.symbol_of(declaration.type_ref.struct_name)
    field = result.model.symbol_of(member.member)
    assert tag is not None and tag.kind is SymbolKind.STRUCT
    assert field is not None and field.kind is SymbolKind.FIELD
    assert field.references[-1].access_kind is AccessKind.MEMBER_ACCESS


def test_arrow_field_resolves_through_pointer_to_struct() -> None:
    program, result = analyze_source(
        """
struct Point { int x; };
int read(struct Point *point) { return point->x; }
"""
    )
    member = program.declarations[1].body.items[0].value

    assert result.model.symbol_of(member.member).name == "x"
    assert not [item for item in result.diagnostics if "requires" in item.message]


def test_unknown_field_and_invalid_member_operator_are_reported() -> None:
    _, result = analyze_source(
        """
struct Point { int x; };
int main(void) {
    struct Point point = {1};
    int number = 2;
    number.x;
    return point.missing;
}
"""
    )
    messages = [item.message for item in result.diagnostics]

    assert any("requires a struct value" in item for item in messages)
    assert any("unknown field 'missing'" in item for item in messages)


def test_read_write_read_write_and_call_accesses_are_distinct() -> None:
    program, result = analyze_source(
        """
int consume(int value) { return value; }
int main(void) {
    int left;
    int right = 1;
    left = right;
    left++;
    return consume(left);
}
"""
    )
    main = program.declarations[1]
    assignment = main.body.items[2].expression
    increment = main.body.items[3].expression
    call = main.body.items[4].value
    assert isinstance(assignment, AssignmentExpr)
    assert isinstance(increment, UnaryExpr)
    assert isinstance(call, CallExpr)

    left = result.model.symbol_of(assignment.target)
    right = result.model.symbol_of(assignment.value)
    consume = result.model.symbol_of(call.callee)
    assert left is not None and right is not None and consume is not None
    assert [item.access_kind for item in left.references] == [
        AccessKind.WRITE,
        AccessKind.READ_WRITE,
        AccessKind.READ,
    ]
    assert [item.access_kind for item in right.references] == [AccessKind.READ]
    assert consume.references[-1].access_kind is AccessKind.CALL


def test_repeated_analysis_does_not_connect_references_across_runs() -> None:
    source = "int main(void) { int value = 1; return value; }"
    _, first = analyze_source(source)
    _, second = analyze_source(source)
    first_value = next(symbol for symbol in first.model.symbols if symbol.name == "value")
    second_value = next(symbol for symbol in second.model.symbols if symbol.name == "value")

    assert first_value is not second_value
    assert len(first_value.references) == len(second_value.references) == 1

