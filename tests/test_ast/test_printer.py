"""Tests for deterministic AST printing."""

from c_analyzer import SourcePosition, SourceSpan
from c_analyzer.ast import IntegerLiteral, Name, Program, TypeRef, VarDecl, print_ast


def span(start: int, end: int) -> SourceSpan:
    return SourceSpan(
        start=SourcePosition("print.c", 1, start + 1, start),
        end=SourcePosition("print.c", 1, end + 1, end),
    )


def test_ast_printer_is_deterministic_and_readable() -> None:
    program = Program(
        span=span(0, 10),
        declarations=[
            VarDecl(
                span=span(0, 10),
                type_ref=TypeRef(span=span(0, 3), keyword="int"),
                name=Name(span=span(4, 5), text="x"),
                initializer=IntegerLiteral(span=span(8, 9), lexeme="1"),
            )
        ],
    )

    assert print_ast(program) == "\n".join(
        [
            "Program",
            "  declarations:",
            "    [0]:",
            "      VarDecl",
            "        type_ref:",
            "          TypeRef",
            "            keyword: 'int'",
            "            struct_name: None",
            "            is_pointer: False",
            "            pointer_span: None",
            "        name:",
            "          Name",
            "            text: 'x'",
            "        array_size: None",
            "        initializer:",
            "          IntegerLiteral",
            "            lexeme: '1'",
        ]
    )

