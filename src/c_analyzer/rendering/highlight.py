"""Combine lexical categories with contextual AST identifier roles."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
from typing import TYPE_CHECKING

from c_analyzer.ast import (
    ASTNode,
    CallExpr,
    FieldDecl,
    FunctionDecl,
    FunctionPrototype,
    IdentifierExpr,
    MemberExpr,
    Name,
    Parameter,
    Program,
    StructDecl,
    TypeRef,
    VarDecl,
)
from c_analyzer.core import Token, TokenKind
from c_analyzer.lexer import KEYWORDS, OPERATORS, TYPE_KEYWORDS
from c_analyzer.semantic.symbols import AccessKind, SymbolKind

if TYPE_CHECKING:
    from c_analyzer.semantic import SemanticModel


class HighlightCategory(Enum):
    KEYWORD = "keyword"
    TYPE_KEYWORD = "type"
    FUNCTION_DECLARATION = "function-declaration"
    FUNCTION_CALL = "function-call"
    VARIABLE = "variable"
    PARAMETER = "parameter"
    STRUCT_NAME = "struct-name"
    FIELD = "field"
    NUMBER = "number"
    TEXT = "text"
    OPERATOR = "operator"
    COMMENT = "comment"
    PREPROCESSOR = "preprocessor"
    INVALID = "invalid"
    BUILTIN_FUNCTION = "builtin-function"
    UNDEFINED_IDENTIFIER = "undefined-identifier"


@dataclass(frozen=True, slots=True)
class HighlightedToken:
    token: Token
    category: HighlightCategory | None


_CATEGORY_PRIORITY = {
    HighlightCategory.VARIABLE: 10,
    HighlightCategory.PARAMETER: 20,
    HighlightCategory.FIELD: 30,
    HighlightCategory.STRUCT_NAME: 40,
    HighlightCategory.FUNCTION_CALL: 50,
    HighlightCategory.FUNCTION_DECLARATION: 60,
    HighlightCategory.BUILTIN_FUNCTION: 70,
    HighlightCategory.UNDEFINED_IDENTIFIER: 80,
}

_KEYWORD_KINDS = frozenset(KEYWORDS.values())
_OPERATOR_KINDS = frozenset(OPERATORS.values())


def classify_tokens(
    tokens: tuple[Token, ...] | list[Token],
    program: Program,
    semantic_model: SemanticModel | None = None,
) -> tuple[HighlightedToken, ...]:
    """Classify tokens, using AST roles for contextual identifiers."""
    contextual: dict[tuple[int, int], HighlightCategory] = {}
    _collect_context(program, contextual)
    if semantic_model is not None:
        _collect_semantic_context(semantic_model, contextual)
    return tuple(
        HighlightedToken(
            token=token,
            category=_token_category(token, contextual),
        )
        for token in tokens
        if token.kind is not TokenKind.EOF
    )


def _collect_semantic_context(
    model: SemanticModel,
    contextual: dict[tuple[int, int], HighlightCategory],
) -> None:
    for symbol in model.symbols:
        definition_category = _category_for_symbol(symbol.kind, is_call=False)
        if symbol.definition_span is not None and definition_category is not None:
            _mark_span(symbol.definition_span, definition_category, contextual)
        for reference in symbol.references:
            category = _category_for_symbol(
                symbol.kind,
                is_call=reference.access_kind is AccessKind.CALL,
            )
            if category is not None:
                _mark_span(reference.span, category, contextual)
    for diagnostic in model.diagnostics:
        if diagnostic.message.startswith("undefined symbol "):
            _mark_span(
                diagnostic.span,
                HighlightCategory.UNDEFINED_IDENTIFIER,
                contextual,
            )


def _category_for_symbol(
    kind: SymbolKind,
    *,
    is_call: bool,
) -> HighlightCategory | None:
    if kind is SymbolKind.BUILTIN_FUNCTION:
        return HighlightCategory.BUILTIN_FUNCTION
    if kind is SymbolKind.FUNCTION:
        return (
            HighlightCategory.FUNCTION_CALL
            if is_call
            else HighlightCategory.FUNCTION_DECLARATION
        )
    if kind is SymbolKind.PARAMETER:
        return HighlightCategory.PARAMETER
    if kind is SymbolKind.VARIABLE:
        return HighlightCategory.VARIABLE
    if kind is SymbolKind.STRUCT:
        return HighlightCategory.STRUCT_NAME
    if kind is SymbolKind.FIELD:
        return HighlightCategory.FIELD
    return None


def _collect_context(
    node: ASTNode,
    contextual: dict[tuple[int, int], HighlightCategory],
) -> None:
    if isinstance(node, (FunctionDecl, FunctionPrototype)):
        _mark(node.name, HighlightCategory.FUNCTION_DECLARATION, contextual)
    elif isinstance(node, VarDecl):
        _mark(node.name, HighlightCategory.VARIABLE, contextual)
    elif isinstance(node, Parameter):
        _mark(node.name, HighlightCategory.PARAMETER, contextual)
    elif isinstance(node, StructDecl):
        _mark(node.name, HighlightCategory.STRUCT_NAME, contextual)
    elif isinstance(node, FieldDecl):
        _mark(node.name, HighlightCategory.FIELD, contextual)
    elif isinstance(node, TypeRef) and node.struct_name is not None:
        _mark(node.struct_name, HighlightCategory.STRUCT_NAME, contextual)
    elif isinstance(node, MemberExpr):
        _mark(node.member, HighlightCategory.FIELD, contextual)
    elif isinstance(node, IdentifierExpr):
        _mark(node.name, HighlightCategory.VARIABLE, contextual)

    if isinstance(node, CallExpr) and isinstance(node.callee, IdentifierExpr):
        _mark(node.callee.name, HighlightCategory.FUNCTION_CALL, contextual)

    for item in fields(node):
        if item.name in {"span", "inferred_type", "symbol_id"}:
            continue
        value = getattr(node, item.name)
        if isinstance(value, ASTNode):
            _collect_context(value, contextual)
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, ASTNode):
                    _collect_context(child, contextual)


def _mark(
    name: Name,
    category: HighlightCategory,
    contextual: dict[tuple[int, int], HighlightCategory],
) -> None:
    key = (name.span.start.offset, name.span.end.offset)
    previous = contextual.get(key)
    if previous is None or _CATEGORY_PRIORITY[category] > _CATEGORY_PRIORITY[previous]:
        contextual[key] = category


def _mark_span(
    span,
    category: HighlightCategory,
    contextual: dict[tuple[int, int], HighlightCategory],
) -> None:
    key = (span.start.offset, span.end.offset)
    previous = contextual.get(key)
    if previous is None or _CATEGORY_PRIORITY[category] > _CATEGORY_PRIORITY[previous]:
        contextual[key] = category


def _token_category(
    token: Token,
    contextual: dict[tuple[int, int], HighlightCategory],
) -> HighlightCategory | None:
    if token.kind in TYPE_KEYWORDS:
        return HighlightCategory.TYPE_KEYWORD
    if token.kind in _KEYWORD_KINDS:
        return HighlightCategory.KEYWORD
    if token.kind is TokenKind.IDENTIFIER:
        key = (token.span.start.offset, token.span.end.offset)
        return contextual.get(key, HighlightCategory.VARIABLE)
    if token.kind in {TokenKind.INTEGER_LITERAL, TokenKind.FLOAT_LITERAL}:
        return HighlightCategory.NUMBER
    if token.kind in {TokenKind.STRING_LITERAL, TokenKind.CHAR_LITERAL}:
        return HighlightCategory.TEXT
    if token.kind in _OPERATOR_KINDS:
        return HighlightCategory.OPERATOR
    if token.kind in {TokenKind.LINE_COMMENT, TokenKind.BLOCK_COMMENT}:
        return HighlightCategory.COMMENT
    if token.kind is TokenKind.PREPROCESSOR_DIRECTIVE:
        return HighlightCategory.PREPROCESSOR
    if token.kind is TokenKind.INVALID:
        return HighlightCategory.INVALID
    return None
