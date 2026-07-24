"""Construction and source-span tests for AST models."""

from c_analyzer import SourcePosition, SourceSpan, TokenKind
from c_analyzer.ast import (
    AssignmentExpr,
    BinaryExpr,
    BlockStmt,
    BreakStmt,
    CallExpr,
    CharLiteral,
    ContinueStmt,
    EmptyStmt,
    ErrorExpr,
    ErrorStmt,
    ExprStmt,
    FieldDecl,
    FloatLiteral,
    ForStmt,
    FunctionDecl,
    FunctionPrototype,
    IdentifierExpr,
    IfStmt,
    IndexExpr,
    InitializerList,
    IntegerLiteral,
    MemberExpr,
    Name,
    Parameter,
    Program,
    ReturnStmt,
    StringLiteral,
    StructDecl,
    TypeRef,
    UnaryExpr,
    VarDecl,
    WhileStmt,
)


def span(start: int = 0, end: int = 1) -> SourceSpan:
    return SourceSpan(
        start=SourcePosition("ast.c", 1, start + 1, start),
        end=SourcePosition("ast.c", 1, end + 1, end),
    )


def name(text: str, start: int = 0) -> Name:
    return Name(span=span(start, start + len(text)), text=text)


def integer(value: str = "1", start: int = 0) -> IntegerLiteral:
    return IntegerLiteral(span=span(start, start + len(value)), lexeme=value)


def test_declaration_identifier_has_independent_span() -> None:
    declaration = VarDecl(
        span=span(0, 10),
        type_ref=TypeRef(span=span(0, 3), keyword="int"),
        name=name("count", 4),
        initializer=integer("1", 9),
    )

    assert declaration.span == span(0, 10)
    assert declaration.name.span == span(4, 9)
    assert declaration.inferred_type is None
    assert declaration.symbol_id is None


def test_all_required_declaration_nodes_are_constructible() -> None:
    int_type = TypeRef(span=span(0, 3), keyword="int")
    parameter = Parameter(span=span(), type_ref=int_type, name=name("p"))
    field = FieldDecl(span=span(), type_ref=int_type, name=name("field"))
    block = BlockStmt(span=span(), items=[])

    declarations = [
        FunctionDecl(
            span=span(),
            return_type=int_type,
            name=name("main"),
            parameters=[parameter],
            body=block,
        ),
        FunctionPrototype(
            span=span(),
            return_type=int_type,
            name=name("helper"),
            parameters=[],
        ),
        VarDecl(span=span(), type_ref=int_type, name=name("value")),
        StructDecl(span=span(), name=name("Point"), fields=[field]),
        field,
    ]
    program = Program(span=span(), declarations=declarations)

    assert len(program.declarations) == 5


def test_all_required_statement_nodes_are_constructible() -> None:
    condition = integer()
    empty = EmptyStmt(span=span())
    statements = [
        BlockStmt(span=span(), items=[]),
        empty,
        ExprStmt(span=span(), expression=condition),
        IfStmt(span=span(), condition=condition, then_branch=empty),
        WhileStmt(span=span(), condition=condition, body=empty),
        ForStmt(
            span=span(),
            initializer=None,
            condition=None,
            update=None,
            body=empty,
        ),
        ReturnStmt(span=span(), value=condition),
        BreakStmt(span=span()),
        ContinueStmt(span=span()),
        ErrorStmt(span=span(), message="recovered"),
    ]

    assert len(statements) == 10


def test_all_required_expression_nodes_are_constructible() -> None:
    identifier = IdentifierExpr(span=span(), name=name("x"))
    one = integer()
    operator_span = span()
    expressions = [
        identifier,
        one,
        FloatLiteral(span=span(), lexeme="1.5"),
        StringLiteral(span=span(), lexeme='"text"'),
        CharLiteral(span=span(), lexeme="'a'"),
        UnaryExpr(
            span=span(),
            operator=TokenKind.MINUS,
            operator_span=operator_span,
            operand=one,
        ),
        BinaryExpr(
            span=span(),
            left=one,
            operator=TokenKind.PLUS,
            operator_span=operator_span,
            right=one,
        ),
        AssignmentExpr(
            span=span(),
            target=identifier,
            operator=TokenKind.ASSIGN,
            operator_span=operator_span,
            value=one,
        ),
        CallExpr(span=span(), callee=identifier, arguments=[one]),
        IndexExpr(span=span(), target=identifier, index=one),
        MemberExpr(
            span=span(),
            target=identifier,
            operator=TokenKind.DOT,
            operator_span=operator_span,
            member=name("field"),
        ),
        InitializerList(span=span(), values=[one]),
        ErrorExpr(span=span(), message="recovered"),
    ]

    assert len(expressions) == 13

