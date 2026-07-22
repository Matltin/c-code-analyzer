"""Source-aware AST nodes for the documented C subset."""

from __future__ import annotations

from dataclasses import dataclass, field

from c_analyzer.core import SourceSpan, TokenKind


@dataclass(slots=True, kw_only=True)
class ASTNode:
    """Base node with fields reserved for later semantic analysis."""

    span: SourceSpan
    inferred_type: str | None = None
    symbol_id: str | None = None


@dataclass(slots=True, kw_only=True)
class Declaration(ASTNode):
    """Base class for declarations."""


@dataclass(slots=True, kw_only=True)
class Statement(ASTNode):
    """Base class for statements."""


@dataclass(slots=True, kw_only=True)
class Expression(ASTNode):
    """Base class for expressions."""


@dataclass(slots=True, kw_only=True)
class Name(ASTNode):
    """A declared or referenced identifier with its exact own span."""

    text: str


@dataclass(slots=True, kw_only=True)
class TypeRef(ASTNode):
    """A primitive or named-struct type with an optional one-level pointer."""

    keyword: str
    struct_name: Name | None = None
    is_pointer: bool = False
    pointer_span: SourceSpan | None = None


@dataclass(slots=True, kw_only=True)
class Program(ASTNode):
    declarations: list[Declaration] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class Parameter(ASTNode):
    type_ref: TypeRef
    name: Name
    is_array: bool = False


@dataclass(slots=True, kw_only=True)
class FieldDecl(Declaration):
    type_ref: TypeRef
    name: Name
    array_size: Expression | None = None


@dataclass(slots=True, kw_only=True)
class VarDecl(Declaration):
    type_ref: TypeRef
    name: Name
    array_size: Expression | None = None
    initializer: Expression | None = None


@dataclass(slots=True, kw_only=True)
class FunctionDecl(Declaration):
    return_type: TypeRef
    name: Name
    parameters: list[Parameter]
    body: BlockStmt


@dataclass(slots=True, kw_only=True)
class FunctionPrototype(Declaration):
    return_type: TypeRef
    name: Name
    parameters: list[Parameter]


@dataclass(slots=True, kw_only=True)
class StructDecl(Declaration):
    name: Name
    fields: list[FieldDecl]


@dataclass(slots=True, kw_only=True)
class BlockStmt(Statement):
    items: list[Declaration | Statement] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class EmptyStmt(Statement):
    pass


@dataclass(slots=True, kw_only=True)
class ExprStmt(Statement):
    expression: Expression


@dataclass(slots=True, kw_only=True)
class IfStmt(Statement):
    condition: Expression
    then_branch: Statement
    else_branch: Statement | None = None


@dataclass(slots=True, kw_only=True)
class WhileStmt(Statement):
    condition: Expression
    body: Statement


@dataclass(slots=True, kw_only=True)
class ForStmt(Statement):
    initializer: Declaration | Expression | None
    condition: Expression | None
    update: Expression | None
    body: Statement


@dataclass(slots=True, kw_only=True)
class ReturnStmt(Statement):
    value: Expression | None = None


@dataclass(slots=True, kw_only=True)
class BreakStmt(Statement):
    pass


@dataclass(slots=True, kw_only=True)
class ContinueStmt(Statement):
    pass


@dataclass(slots=True, kw_only=True)
class ErrorStmt(Statement):
    message: str


@dataclass(slots=True, kw_only=True)
class IdentifierExpr(Expression):
    name: Name


@dataclass(slots=True, kw_only=True)
class IntegerLiteral(Expression):
    lexeme: str


@dataclass(slots=True, kw_only=True)
class FloatLiteral(Expression):
    lexeme: str


@dataclass(slots=True, kw_only=True)
class StringLiteral(Expression):
    lexeme: str


@dataclass(slots=True, kw_only=True)
class CharLiteral(Expression):
    lexeme: str


@dataclass(slots=True, kw_only=True)
class UnaryExpr(Expression):
    operator: TokenKind
    operator_span: SourceSpan
    operand: Expression
    is_postfix: bool = False


@dataclass(slots=True, kw_only=True)
class BinaryExpr(Expression):
    left: Expression
    operator: TokenKind
    operator_span: SourceSpan
    right: Expression


@dataclass(slots=True, kw_only=True)
class AssignmentExpr(Expression):
    target: Expression
    operator: TokenKind
    operator_span: SourceSpan
    value: Expression


@dataclass(slots=True, kw_only=True)
class CallExpr(Expression):
    callee: Expression
    arguments: list[Expression] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class IndexExpr(Expression):
    target: Expression
    index: Expression


@dataclass(slots=True, kw_only=True)
class MemberExpr(Expression):
    target: Expression
    operator: TokenKind
    operator_span: SourceSpan
    member: Name


@dataclass(slots=True, kw_only=True)
class InitializerList(Expression):
    values: list[Expression] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class ErrorExpr(Expression):
    message: str

