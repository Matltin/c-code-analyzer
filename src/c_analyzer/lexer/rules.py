"""Fixed lexical tables; this module does not scan source code."""

from types import MappingProxyType
from typing import Final, Mapping

from c_analyzer.core.token import TokenKind


KEYWORDS: Final[Mapping[str, TokenKind]] = MappingProxyType(
    {
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
)


TYPE_KEYWORDS: Final[frozenset[TokenKind]] = frozenset(
    {
        TokenKind.KW_INT,
        TokenKind.KW_FLOAT,
        TokenKind.KW_DOUBLE,
        TokenKind.KW_CHAR,
        TokenKind.KW_VOID,
        TokenKind.KW_STRUCT,
    }
)


OPERATORS: Final[Mapping[str, TokenKind]] = MappingProxyType(
    {
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
)


DELIMITERS: Final[Mapping[str, TokenKind]] = MappingProxyType(
    {
        "(": TokenKind.LEFT_PAREN,
        ")": TokenKind.RIGHT_PAREN,
        "{": TokenKind.LEFT_BRACE,
        "}": TokenKind.RIGHT_BRACE,
        "[": TokenKind.LEFT_BRACKET,
        "]": TokenKind.RIGHT_BRACKET,
        ";": TokenKind.SEMICOLON,
        ",": TokenKind.COMMA,
    }
)


OPERATOR_LEXEMES_LONGEST_FIRST: Final[tuple[str, ...]] = tuple(
    sorted(OPERATORS, key=lambda lexeme: (-len(lexeme), lexeme))
)

