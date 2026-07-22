"""Tests for the Phase 1.1 token specification tables."""

from types import MappingProxyType

import pytest

from c_analyzer import TokenKind
from c_analyzer.lexer import (
    DELIMITERS,
    KEYWORDS,
    OPERATORS,
    OPERATOR_LEXEMES_LONGEST_FIRST,
    TYPE_KEYWORDS,
)


EXPECTED_KEYWORDS = {
    "int": TokenKind.KW_INT,
    "float": TokenKind.KW_FLOAT,
    "double": TokenKind.KW_DOUBLE,
    "char": TokenKind.KW_CHAR,
    "void": TokenKind.KW_VOID,
    "struct": TokenKind.KW_STRUCT,
    "if": TokenKind.KW_IF,
    "else": TokenKind.KW_ELSE,
    "while": TokenKind.KW_WHILE,
    "for": TokenKind.KW_FOR,
    "return": TokenKind.KW_RETURN,
    "break": TokenKind.KW_BREAK,
    "continue": TokenKind.KW_CONTINUE,
}

EXPECTED_OPERATORS = {
    "+": TokenKind.PLUS,
    "-": TokenKind.MINUS,
    "*": TokenKind.STAR,
    "/": TokenKind.SLASH,
    "%": TokenKind.PERCENT,
    "=": TokenKind.ASSIGN,
    "+=": TokenKind.PLUS_ASSIGN,
    "-=": TokenKind.MINUS_ASSIGN,
    "*=": TokenKind.STAR_ASSIGN,
    "/=": TokenKind.SLASH_ASSIGN,
    "%=": TokenKind.PERCENT_ASSIGN,
    "==": TokenKind.EQUAL_EQUAL,
    "!=": TokenKind.BANG_EQUAL,
    "<": TokenKind.LESS,
    "<=": TokenKind.LESS_EQUAL,
    ">": TokenKind.GREATER,
    ">=": TokenKind.GREATER_EQUAL,
    "&&": TokenKind.LOGICAL_AND,
    "||": TokenKind.LOGICAL_OR,
    "!": TokenKind.LOGICAL_NOT,
    "++": TokenKind.INCREMENT,
    "--": TokenKind.DECREMENT,
    "&": TokenKind.AMPERSAND,
    ".": TokenKind.DOT,
    "->": TokenKind.ARROW,
}

EXPECTED_DELIMITERS = {
    "(": TokenKind.LEFT_PAREN,
    ")": TokenKind.RIGHT_PAREN,
    "{": TokenKind.LEFT_BRACE,
    "}": TokenKind.RIGHT_BRACE,
    "[": TokenKind.LEFT_BRACKET,
    "]": TokenKind.RIGHT_BRACKET,
    ";": TokenKind.SEMICOLON,
    ",": TokenKind.COMMA,
}


def test_keyword_table_matches_documented_scope() -> None:
    assert dict(KEYWORDS) == EXPECTED_KEYWORDS


def test_type_keywords_are_exact() -> None:
    assert TYPE_KEYWORDS == frozenset(
        {
            TokenKind.KW_INT,
            TokenKind.KW_FLOAT,
            TokenKind.KW_DOUBLE,
            TokenKind.KW_CHAR,
            TokenKind.KW_VOID,
            TokenKind.KW_STRUCT,
        }
    )


def test_operator_table_matches_documented_scope() -> None:
    assert dict(OPERATORS) == EXPECTED_OPERATORS


def test_delimiter_table_matches_documented_scope() -> None:
    assert dict(DELIMITERS) == EXPECTED_DELIMITERS


def test_fixed_lexemes_are_not_duplicated_between_tables() -> None:
    all_lexemes = [*KEYWORDS, *OPERATORS, *DELIMITERS]

    assert len(all_lexemes) == len(set(all_lexemes))


def test_general_and_phase_zero_token_kinds_still_exist() -> None:
    required_kinds = {
        TokenKind.EOF,
        TokenKind.INVALID,
        TokenKind.IDENTIFIER,
        TokenKind.INTEGER_LITERAL,
        TokenKind.FLOAT_LITERAL,
        TokenKind.STRING_LITERAL,
        TokenKind.CHAR_LITERAL,
        TokenKind.LINE_COMMENT,
        TokenKind.BLOCK_COMMENT,
        TokenKind.PREPROCESSOR_DIRECTIVE,
    }

    assert len(required_kinds) == 10


def test_longest_match_places_prefixed_operators_first() -> None:
    order = OPERATOR_LEXEMES_LONGEST_FIRST

    for longer in OPERATORS:
        for shorter in OPERATORS:
            if longer != shorter and longer.startswith(shorter):
                assert order.index(longer) < order.index(shorter)

    assert order.index("->") < order.index("-")
    assert order.index("<=") < order.index("<")
    assert order.index("==") < order.index("=")


def test_longest_match_order_is_deterministic() -> None:
    expected_order = tuple(
        sorted(EXPECTED_OPERATORS, key=lambda lexeme: (-len(lexeme), lexeme))
    )

    assert isinstance(OPERATOR_LEXEMES_LONGEST_FIRST, tuple)
    assert OPERATOR_LEXEMES_LONGEST_FIRST == expected_order


def test_rule_collections_are_read_only() -> None:
    assert isinstance(KEYWORDS, MappingProxyType)
    assert isinstance(OPERATORS, MappingProxyType)
    assert isinstance(DELIMITERS, MappingProxyType)
    assert isinstance(TYPE_KEYWORDS, frozenset)

    with pytest.raises(TypeError):
        KEYWORDS["fake"] = TokenKind.IDENTIFIER  # type: ignore[index]

    with pytest.raises(TypeError):
        OPERATORS["@"] = TokenKind.INVALID  # type: ignore[index]

