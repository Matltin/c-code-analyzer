"""Shared token models used by every compiler phase."""

from dataclasses import dataclass
from enum import Enum

from c_analyzer.core.source import SourceSpan


class TokenKind(Enum):
    """Token categories for the documented C subset."""

    # General tokens retained from Phase 0.
    IDENTIFIER = "identifier"
    INTEGER_LITERAL = "integer_literal"
    EOF = "eof"
    INVALID = "invalid"

    # Literals, comments, and directives.
    FLOAT_LITERAL = "float_literal"
    STRING_LITERAL = "string_literal"
    CHAR_LITERAL = "char_literal"
    LINE_COMMENT = "line_comment"
    BLOCK_COMMENT = "block_comment"
    PREPROCESSOR_DIRECTIVE = "preprocessor_directive"

    # Keywords.
    KW_INT = "kw_int"
    KW_FLOAT = "kw_float"
    KW_DOUBLE = "kw_double"
    KW_CHAR = "kw_char"
    KW_VOID = "kw_void"
    KW_STRUCT = "kw_struct"
    KW_IF = "kw_if"
    KW_ELSE = "kw_else"
    KW_WHILE = "kw_while"
    KW_FOR = "kw_for"
    KW_RETURN = "kw_return"
    KW_BREAK = "kw_break"
    KW_CONTINUE = "kw_continue"

    # Operators.
    PLUS = "plus"
    MINUS = "minus"
    STAR = "star"
    SLASH = "slash"
    PERCENT = "percent"
    ASSIGN = "assign"
    PLUS_ASSIGN = "plus_assign"
    MINUS_ASSIGN = "minus_assign"
    STAR_ASSIGN = "star_assign"
    SLASH_ASSIGN = "slash_assign"
    PERCENT_ASSIGN = "percent_assign"
    EQUAL_EQUAL = "equal_equal"
    BANG_EQUAL = "bang_equal"
    LESS = "less"
    LESS_EQUAL = "less_equal"
    GREATER = "greater"
    GREATER_EQUAL = "greater_equal"
    LOGICAL_AND = "logical_and"
    LOGICAL_OR = "logical_or"
    LOGICAL_NOT = "logical_not"
    INCREMENT = "increment"
    DECREMENT = "decrement"
    AMPERSAND = "ampersand"
    DOT = "dot"
    ARROW = "arrow"

    # Delimiters.
    LEFT_PAREN = "left_paren"
    RIGHT_PAREN = "right_paren"
    LEFT_BRACE = "left_brace"
    RIGHT_BRACE = "right_brace"
    LEFT_BRACKET = "left_bracket"
    RIGHT_BRACKET = "right_bracket"
    SEMICOLON = "semicolon"
    COMMA = "comma"


@dataclass(frozen=True, slots=True)
class Token:
    """A token kind, its exact source text, and its location."""

    kind: TokenKind
    lexeme: str
    span: SourceSpan

    def __post_init__(self) -> None:
        if not isinstance(self.kind, TokenKind):
            raise TypeError("kind must be a TokenKind")
        if not isinstance(self.lexeme, str):
            raise TypeError("lexeme must be a string")
        if not isinstance(self.span, SourceSpan):
            raise TypeError("span must be a SourceSpan")
