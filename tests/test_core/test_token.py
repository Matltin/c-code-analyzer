"""Tests for the minimal Phase 0 token model."""

from c_analyzer import SourcePosition, SourceSpan, Token, TokenKind


def test_token_keeps_kind_lexeme_and_span() -> None:
    start = SourcePosition(file="main.c", line=1, column=1, offset=0)
    end = SourcePosition(file="main.c", line=1, column=6, offset=5)
    span = SourceSpan(start=start, end=end)

    token = Token(
        kind=TokenKind.IDENTIFIER,
        lexeme="count",
        span=span,
    )

    assert token.kind is TokenKind.IDENTIFIER
    assert token.lexeme == "count"
    assert token.span == span

