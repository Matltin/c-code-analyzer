"""Read-only lexical rules for the documented C subset."""

from c_analyzer.lexer.lexer import Lexer, LexerResult, tokenize
from c_analyzer.lexer.rules import (
    DELIMITERS,
    KEYWORDS,
    OPERATORS,
    OPERATOR_LEXEMES_LONGEST_FIRST,
    TYPE_KEYWORDS,
)

__all__ = [
    "DELIMITERS",
    "KEYWORDS",
    "Lexer",
    "LexerResult",
    "OPERATORS",
    "OPERATOR_LEXEMES_LONGEST_FIRST",
    "TYPE_KEYWORDS",
    "tokenize",
]

