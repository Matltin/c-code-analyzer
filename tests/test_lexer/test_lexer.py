"""Behavioral tests for the hand-written lexer."""

from c_analyzer import TokenKind
from c_analyzer.lexer import tokenize


def significant_kinds(source: str) -> list[TokenKind]:
    return [
        token.kind
        for token in tokenize(source, "test.c").tokens
        if token.kind
        not in {TokenKind.LINE_COMMENT, TokenKind.BLOCK_COMMENT}
    ]


def test_tokenizes_a_valid_function() -> None:
    result = tokenize("int add(int a, int b) { return a + b; }", "add.c")

    assert not result.diagnostics
    assert [token.kind for token in result.tokens] == [
        TokenKind.KW_INT,
        TokenKind.IDENTIFIER,
        TokenKind.LEFT_PAREN,
        TokenKind.KW_INT,
        TokenKind.IDENTIFIER,
        TokenKind.COMMA,
        TokenKind.KW_INT,
        TokenKind.IDENTIFIER,
        TokenKind.RIGHT_PAREN,
        TokenKind.LEFT_BRACE,
        TokenKind.KW_RETURN,
        TokenKind.IDENTIFIER,
        TokenKind.PLUS,
        TokenKind.IDENTIFIER,
        TokenKind.SEMICOLON,
        TokenKind.RIGHT_BRACE,
        TokenKind.EOF,
    ]


def test_keyword_priority_does_not_break_longer_identifier() -> None:
    result = tokenize("while whileCount", "keyword.c")

    assert [token.kind for token in result.tokens] == [
        TokenKind.KW_WHILE,
        TokenKind.IDENTIFIER,
        TokenKind.EOF,
    ]
    assert result.tokens[1].lexeme == "whileCount"


def test_uses_longest_match_for_operators() -> None:
    result = tokenize("a<=b; p->x; a < = b; p - > x;", "operators.c")

    assert [token.kind for token in result.tokens] == [
        TokenKind.IDENTIFIER,
        TokenKind.LESS_EQUAL,
        TokenKind.IDENTIFIER,
        TokenKind.SEMICOLON,
        TokenKind.IDENTIFIER,
        TokenKind.ARROW,
        TokenKind.IDENTIFIER,
        TokenKind.SEMICOLON,
        TokenKind.IDENTIFIER,
        TokenKind.LESS,
        TokenKind.ASSIGN,
        TokenKind.IDENTIFIER,
        TokenKind.SEMICOLON,
        TokenKind.IDENTIFIER,
        TokenKind.MINUS,
        TokenKind.GREATER,
        TokenKind.IDENTIFIER,
        TokenKind.SEMICOLON,
        TokenKind.EOF,
    ]


def test_tokenizes_decimal_hexadecimal_and_binary_integers() -> None:
    result = tokenize("42 0xFF 0X2a 0b1010 0B11", "numbers.c")

    assert [token.kind for token in result.tokens[:-1]] == [
        TokenKind.INTEGER_LITERAL,
        TokenKind.INTEGER_LITERAL,
        TokenKind.INTEGER_LITERAL,
        TokenKind.INTEGER_LITERAL,
        TokenKind.INTEGER_LITERAL,
    ]
    assert [token.lexeme for token in result.tokens[:-1]] == [
        "42",
        "0xFF",
        "0X2a",
        "0b1010",
        "0B11",
    ]


def test_tokenizes_float_forms() -> None:
    result = tokenize("3.14 1.0e-5 .5f 2E3", "floats.c")

    assert [token.kind for token in result.tokens[:-1]] == [
        TokenKind.FLOAT_LITERAL,
        TokenKind.FLOAT_LITERAL,
        TokenKind.FLOAT_LITERAL,
        TokenKind.FLOAT_LITERAL,
    ]
    assert [token.lexeme for token in result.tokens[:-1]] == [
        "3.14",
        "1.0e-5",
        ".5f",
        "2E3",
    ]


def test_tokenizes_strings_characters_and_valid_escapes() -> None:
    source = r'''"line\n" 'a' '\t' '\'' '\\' '''
    result = tokenize(source, "literals.c")

    assert not result.diagnostics
    assert [token.kind for token in result.tokens[:-1]] == [
        TokenKind.STRING_LITERAL,
        TokenKind.CHAR_LITERAL,
        TokenKind.CHAR_LITERAL,
        TokenKind.CHAR_LITERAL,
        TokenKind.CHAR_LITERAL,
    ]


def test_preserves_line_and_block_comments() -> None:
    result = tokenize("// first\n/* second\nline */ int x;", "comments.c")

    assert [token.kind for token in result.tokens] == [
        TokenKind.LINE_COMMENT,
        TokenKind.BLOCK_COMMENT,
        TokenKind.KW_INT,
        TokenKind.IDENTIFIER,
        TokenKind.SEMICOLON,
        TokenKind.EOF,
    ]
    assert result.tokens[1].lexeme == "/* second\nline */"


def test_tokenizes_preprocessor_only_at_logical_line_start() -> None:
    result = tokenize("  #include <stdio.h>\nint x;", "preprocessor.c")

    assert result.tokens[0].kind is TokenKind.PREPROCESSOR_DIRECTIVE
    assert result.tokens[0].lexeme == "#include <stdio.h>"
    assert result.tokens[1].kind is TokenKind.KW_INT


def test_tracks_line_column_offset_and_tab_as_one_column() -> None:
    result = tokenize("int\tvalue;\n  return value;", "location.c")
    tokens = result.tokens

    assert (tokens[0].span.start.line, tokens[0].span.start.column) == (1, 1)
    assert tokens[0].span.start.offset == 0
    assert (tokens[1].span.start.line, tokens[1].span.start.column) == (1, 5)
    assert tokens[1].span.start.offset == 4
    assert (tokens[3].span.start.line, tokens[3].span.start.column) == (2, 3)
    assert tokens[3].span.start.offset == 13


def test_eof_has_zero_length_span_at_source_end() -> None:
    source = "int x;"
    eof = tokenize(source, "eof.c").tokens[-1]

    assert eof.kind is TokenKind.EOF
    assert eof.lexeme == ""
    assert eof.span.length == 0
    assert eof.span.start.offset == len(source)
    assert eof.span.start == eof.span.end


def test_invalid_character_produces_diagnostic_and_continues() -> None:
    result = tokenize("int x @ 42; int y;", "invalid.c")

    invalid = next(token for token in result.tokens if token.kind is TokenKind.INVALID)
    assert invalid.lexeme == "@"
    assert len(result.diagnostics) == 1
    assert "unrecognized character" in result.diagnostics[0].message
    assert [token.lexeme for token in result.tokens if token.kind is TokenKind.IDENTIFIER] == [
        "x",
        "y",
    ]


def test_unterminated_string_recovers_on_next_line() -> None:
    result = tokenize('"bad\nint y;', "string.c")

    assert result.tokens[0].kind is TokenKind.INVALID
    assert "unterminated string" in result.diagnostics[0].message
    assert any(
        token.kind is TokenKind.KW_INT and token.span.start.line == 2
        for token in result.tokens
    )


def test_unterminated_block_comment_reaches_eof_without_crash() -> None:
    result = tokenize("int x; /* never closed", "comment.c")

    assert result.tokens[-2].kind is TokenKind.INVALID
    assert "unterminated block comment" in result.diagnostics[0].message
    assert result.tokens[-1].kind is TokenKind.EOF


def test_invalid_character_literal_and_escape_are_reported() -> None:
    result = tokenize(r"'' 'ab' '\q'", "characters.c")

    assert [token.kind for token in result.tokens[:-1]] == [
        TokenKind.INVALID,
        TokenKind.INVALID,
        TokenKind.INVALID,
    ]
    assert len(result.diagnostics) == 3
    assert any("exactly one" in diagnostic.message for diagnostic in result.diagnostics)
    assert any("invalid escape" in diagnostic.message for diagnostic in result.diagnostics)


def test_incomplete_hex_and_binary_literals_are_reported() -> None:
    result = tokenize("0x; 0b;", "incomplete.c")

    assert [token.kind for token in result.tokens] == [
        TokenKind.INVALID,
        TokenKind.SEMICOLON,
        TokenKind.INVALID,
        TokenKind.SEMICOLON,
        TokenKind.EOF,
    ]
    assert len(result.diagnostics) == 2


def test_multiple_errors_are_collected_and_later_line_is_tokenized() -> None:
    result = tokenize("@ $\n\"bad\nint ok;", "multiple.c")

    assert len(result.diagnostics) == 3
    assert sum(token.kind is TokenKind.INVALID for token in result.tokens) == 3
    assert any(
        token.kind is TokenKind.IDENTIFIER and token.lexeme == "ok"
        for token in result.tokens
    )
