"""Integration tests for recursive-descent parsing and recovery."""

from c_analyzer import TokenKind
from c_analyzer.ast import (
    AssignmentExpr,
    BinaryExpr,
    BreakStmt,
    CallExpr,
    ContinueStmt,
    ForStmt,
    FunctionDecl,
    FunctionPrototype,
    IfStmt,
    IndexExpr,
    InitializerList,
    MemberExpr,
    ReturnStmt,
    StructDecl,
    UnaryExpr,
    VarDecl,
    WhileStmt,
)
from c_analyzer.lexer import tokenize
from c_analyzer.parser import parse


def parse_source(source: str):
    lexer_result = tokenize(source, "parser.c")
    return lexer_result, parse(lexer_result.tokens)


def test_parses_simple_function_and_return() -> None:
    lexer_result, result = parse_source("int main(void) { return 0; }")

    assert not lexer_result.diagnostics
    assert not result.diagnostics
    function = result.ast.declarations[0]
    assert isinstance(function, FunctionDecl)
    assert function.name.text == "main"
    assert isinstance(function.body.items[0], ReturnStmt)


def test_parses_function_prototype() -> None:
    _, result = parse_source("int add(int left, int right);")

    prototype = result.ast.declarations[0]
    assert isinstance(prototype, FunctionPrototype)
    assert [parameter.name.text for parameter in prototype.parameters] == [
        "left",
        "right",
    ]


def test_parses_struct_pointer_array_and_initializer_list() -> None:
    source = """
struct Point { int x; int y; };
struct Point *ptr;
int values[3] = {1, 2, 3};
"""
    _, result = parse_source(source)

    assert not result.diagnostics
    assert isinstance(result.ast.declarations[0], StructDecl)
    pointer = result.ast.declarations[1]
    array = result.ast.declarations[2]
    assert isinstance(pointer, VarDecl)
    assert pointer.type_ref.is_pointer
    assert isinstance(array, VarDecl)
    assert array.array_size is not None
    assert isinstance(array.initializer, InitializerList)


def test_parses_if_while_for_break_continue_and_nested_blocks() -> None:
    source = """
int main(void) {
    int i = 0;
    while (i < 10) {
        if (i == 5) break;
        i++;
    }
    for (i = 0; i < 3; i++) { continue; }
    return i;
}
"""
    _, result = parse_source(source)

    assert not result.diagnostics
    function = result.ast.declarations[0]
    assert isinstance(function, FunctionDecl)
    while_statement = function.body.items[1]
    for_statement = function.body.items[2]
    assert isinstance(while_statement, WhileStmt)
    assert isinstance(while_statement.body.items[0], IfStmt)
    assert isinstance(while_statement.body.items[0].then_branch, BreakStmt)
    assert isinstance(for_statement, ForStmt)
    assert isinstance(for_statement.body.items[0], ContinueStmt)


def test_parses_call_index_member_and_postfix_expression() -> None:
    source = """
int main(void) {
    result = add(values[0], point.x);
    ptr->x++;
    return result;
}
"""
    _, result = parse_source(source)

    assert not result.diagnostics
    function = result.ast.declarations[0]
    assignment = function.body.items[0].expression
    assert isinstance(assignment, AssignmentExpr)
    assert isinstance(assignment.value, CallExpr)
    assert isinstance(assignment.value.arguments[0], IndexExpr)
    assert isinstance(assignment.value.arguments[1], MemberExpr)
    postfix = function.body.items[1].expression
    assert isinstance(postfix, UnaryExpr)
    assert postfix.is_postfix
    assert isinstance(postfix.operand, MemberExpr)


def test_operator_precedence_is_multiplication_before_addition() -> None:
    _, result = parse_source("int x = 1 + 2 * 3;")

    declaration = result.ast.declarations[0]
    assert isinstance(declaration, VarDecl)
    expression = declaration.initializer
    assert isinstance(expression, BinaryExpr)
    assert expression.operator is TokenKind.PLUS
    assert isinstance(expression.right, BinaryExpr)
    assert expression.right.operator is TokenKind.STAR


def test_assignment_is_right_associative() -> None:
    _, result = parse_source("int main(void) { a = b = 5; }")

    function = result.ast.declarations[0]
    expression = function.body.items[0].expression
    assert isinstance(expression, AssignmentExpr)
    assert isinstance(expression.value, AssignmentExpr)


def test_comments_and_preprocessor_are_filtered_for_parser() -> None:
    source = """
#include <stdio.h>
// comment
int main(void) { /* block */ return 0; }
"""
    lexer_result, result = parse_source(source)

    assert any(token.kind is TokenKind.PREPROCESSOR_DIRECTIVE for token in lexer_result.tokens)
    assert any(token.kind is TokenKind.LINE_COMMENT for token in lexer_result.tokens)
    assert not result.diagnostics
    assert isinstance(result.ast.declarations[0], FunctionDecl)


def test_missing_expression_recovers_and_parses_next_declaration() -> None:
    _, result = parse_source("int broken = ; int good = 42;")

    assert any("expected expression" in item.message for item in result.diagnostics)
    assert [declaration.name.text for declaration in result.ast.declarations] == [
        "broken",
        "good",
    ]


def test_missing_semicolon_reports_error_and_keeps_next_statement() -> None:
    source = "int main(void) { int x = 1 return x; }"
    _, result = parse_source(source)

    assert any("expected ';'" in item.message for item in result.diagnostics)
    function = result.ast.declarations[0]
    assert any(isinstance(item, ReturnStmt) for item in function.body.items)


def test_missing_parenthesis_and_brace_produce_partial_ast() -> None:
    source = "int main(void { if (1 { return 1; "
    _, result = parse_source(source)

    messages = [item.message for item in result.diagnostics]
    assert sum("expected ')'" in message for message in messages) >= 2
    assert any("expected '}'" in message for message in messages)
    assert result.ast is not None


def test_multiple_syntax_errors_do_not_stop_later_function() -> None:
    source = """
int first(void) { int x = ; return 1 }
int second(void) { return 2; }
"""
    _, result = parse_source(source)

    assert len(result.diagnostics) >= 2
    assert any(
        isinstance(declaration, FunctionDecl) and declaration.name.text == "second"
        for declaration in result.ast.declarations
    )


def test_invalid_lexer_token_does_not_crash_parser() -> None:
    lexer_result, result = parse_source("int main(void) { @; return 0; }")

    assert lexer_result.diagnostics
    assert result.ast is not None
    assert any("invalid token" in item.message for item in result.diagnostics)

