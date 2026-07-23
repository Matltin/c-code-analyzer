"""Hand-written lexer for the documented C subset."""

from dataclasses import dataclass

from c_analyzer.core import (
    Diagnostic,
    DiagnosticPhase,
    Severity,
    SourcePosition,
    SourceSpan,
    Token,
    TokenKind,
)
from c_analyzer.lexer.rules import (
    DELIMITERS,
    KEYWORDS,
    OPERATORS,
    OPERATOR_LEXEMES_LONGEST_FIRST,
)


VALID_ESCAPES = frozenset({"n", "t", "r", "0", "\\", "'", '"'})


@dataclass(frozen=True, slots=True)
class LexerResult:
    """Tokens and diagnostics produced by one lexer run."""

    tokens: tuple[Token, ...]
    diagnostics: tuple[Diagnostic, ...]


class Lexer:
    """Scan source text once while preserving exact source spans."""

    def __init__(self, source_text: str, file_name: str = "<memory>") -> None:
        if not isinstance(source_text, str):
            raise TypeError("source_text must be a string")
        if not isinstance(file_name, str):
            raise TypeError("file_name must be a string")
        if not file_name.strip():
            raise ValueError("file_name must not be empty")

        self._source = source_text
        self._file_name = file_name
        self._offset = 0
        self._line = 1
        self._column = 1
        self._line_has_only_whitespace = True
        self._tokens: list[Token] = []
        self._diagnostics: list[Diagnostic] = []

    def tokenize(self) -> LexerResult:
        """Tokenize the complete source and always append EOF."""
        while not self._at_end():
            if self._peek().isspace():
                self._advance()
                continue

            start = self._position()
            at_logical_line_start = self._line_has_only_whitespace
            current = self._peek()

            if current == "#" and at_logical_line_start:
                self._scan_preprocessor(start)
            elif self._is_identifier_start(current):
                self._scan_identifier(start)
            elif current.isascii() and current.isdigit():
                self._scan_number(start)
            elif current == "." and self._peek(1).isascii() and self._peek(1).isdigit():
                self._scan_number(start)
            elif current == '"':
                self._scan_string(start)
            elif current == "'":
                self._scan_character(start)
            elif current == "/" and self._peek(1) == "/":
                self._scan_line_comment(start)
            elif current == "/" and self._peek(1) == "*":
                self._scan_block_comment(start)
            elif self._scan_fixed_lexeme(start):
                continue
            else:
                self._advance()
                self._emit_invalid(
                    start,
                    f"unrecognized character {current!r}",
                )

        eof_position = self._position()
        eof_span = SourceSpan(start=eof_position, end=eof_position)
        self._tokens.append(Token(TokenKind.EOF, "", eof_span))
        return LexerResult(
            tokens=tuple(self._tokens),
            diagnostics=tuple(self._diagnostics),
        )

    def _scan_identifier(self, start: SourcePosition) -> None:
        self._advance()
        while self._is_identifier_continue(self._peek()):
            self._advance()

        lexeme = self._slice_from(start)
        kind = KEYWORDS.get(lexeme, TokenKind.IDENTIFIER)
        self._emit_token(kind, start)

    def _scan_number(self, start: SourcePosition) -> None:
        if self._peek() == "0" and self._peek(1) in {"x", "X"}:
            self._advance()
            self._advance()
            digit_start = self._offset
            while self._is_hex_digit(self._peek()):
                self._advance()
            if self._offset == digit_start:
                self._emit_invalid(start, "hexadecimal literal requires a digit")
            else:
                self._emit_token(TokenKind.INTEGER_LITERAL, start)
            return

        if self._peek() == "0" and self._peek(1) in {"b", "B"}:
            self._advance()
            self._advance()
            digit_start = self._offset
            while self._peek() in {"0", "1"}:
                self._advance()
            if self._offset == digit_start:
                self._emit_invalid(start, "binary literal requires a digit")
            else:
                self._emit_token(TokenKind.INTEGER_LITERAL, start)
            return

        is_float = False
        while self._peek().isascii() and self._peek().isdigit():
            self._advance()

        if self._peek() == ".":
            is_float = True
            self._advance()
            while self._peek().isascii() and self._peek().isdigit():
                self._advance()

        invalid_exponent = False
        if self._peek() in {"e", "E"}:
            is_float = True
            self._advance()
            if self._peek() in {"+", "-"}:
                self._advance()
            exponent_start = self._offset
            while self._peek().isascii() and self._peek().isdigit():
                self._advance()
            invalid_exponent = self._offset == exponent_start

        if is_float and self._peek() in {"f", "F"}:
            self._advance()

        if invalid_exponent:
            self._emit_invalid(start, "float exponent requires a digit")
        elif is_float:
            self._emit_token(TokenKind.FLOAT_LITERAL, start)
        else:
            self._emit_token(TokenKind.INTEGER_LITERAL, start)

    def _scan_string(self, start: SourcePosition) -> None:
        self._advance()
        closed = False
        invalid_escape = False

        while not self._at_end() and self._peek() != "\n":
            character = self._advance()
            if character == '"':
                closed = True
                break
            if character == "\\":
                if self._at_end() or self._peek() == "\n":
                    invalid_escape = True
                    break
                escape = self._advance()
                if escape not in VALID_ESCAPES:
                    invalid_escape = True

        messages: list[str] = []
        if not closed:
            messages.append("unterminated string literal")
        if invalid_escape:
            messages.append("invalid escape sequence in string literal")

        if messages:
            self._emit_invalid(start, *messages)
        else:
            self._emit_token(TokenKind.STRING_LITERAL, start)

    def _scan_character(self, start: SourcePosition) -> None:
        self._advance()
        closed = False
        invalid_escape = False
        character_count = 0

        while not self._at_end() and self._peek() != "\n":
            character = self._advance()
            if character == "'":
                closed = True
                break
            if character == "\\":
                if self._at_end() or self._peek() == "\n":
                    invalid_escape = True
                    break
                escape = self._advance()
                invalid_escape = invalid_escape or escape not in VALID_ESCAPES
            character_count += 1

        messages: list[str] = []
        if not closed:
            messages.append("unterminated character literal")
        if invalid_escape:
            messages.append("invalid escape sequence in character literal")
        if closed and character_count != 1:
            messages.append("character literal must contain exactly one character")

        if messages:
            self._emit_invalid(start, *messages)
        else:
            self._emit_token(TokenKind.CHAR_LITERAL, start)

    def _scan_line_comment(self, start: SourcePosition) -> None:
        self._advance()
        self._advance()
        while not self._at_end() and self._peek() != "\n":
            self._advance()
        self._emit_token(TokenKind.LINE_COMMENT, start)

    def _scan_block_comment(self, start: SourcePosition) -> None:
        self._advance()
        self._advance()
        while not self._at_end():
            if self._peek() == "*" and self._peek(1) == "/":
                self._advance()
                self._advance()
                self._emit_token(TokenKind.BLOCK_COMMENT, start)
                return
            self._advance()
        self._emit_invalid(start, "unterminated block comment")

    def _scan_preprocessor(self, start: SourcePosition) -> None:
        while not self._at_end() and self._peek() != "\n":
            self._advance()
        self._emit_token(TokenKind.PREPROCESSOR_DIRECTIVE, start)

    def _scan_fixed_lexeme(self, start: SourcePosition) -> bool:
        for lexeme in OPERATOR_LEXEMES_LONGEST_FIRST:
            if self._source.startswith(lexeme, self._offset):
                for _ in lexeme:
                    self._advance()
                self._emit_token(OPERATORS[lexeme], start)
                return True

        delimiter = self._peek()
        if delimiter in DELIMITERS:
            self._advance()
            self._emit_token(DELIMITERS[delimiter], start)
            return True
        return False

    def _emit_token(self, kind: TokenKind, start: SourcePosition) -> None:
        span = SourceSpan(start=start, end=self._position())
        self._tokens.append(Token(kind, self._slice_from(start), span))

    def _emit_invalid(
        self,
        start: SourcePosition,
        *messages: str,
    ) -> None:
        span = SourceSpan(start=start, end=self._position())
        self._tokens.append(Token(TokenKind.INVALID, self._slice_from(start), span))
        for message in messages:
            self._diagnostics.append(
                Diagnostic(
                    phase=DiagnosticPhase.LEXER,
                    severity=Severity.ERROR,
                    message=message,
                    span=span,
                )
            )

    def _position(self) -> SourcePosition:
        return SourcePosition(
            file=self._file_name,
            line=self._line,
            column=self._column,
            offset=self._offset,
        )

    def _slice_from(self, start: SourcePosition) -> str:
        return self._source[start.offset : self._offset]

    def _peek(self, distance: int = 0) -> str:
        index = self._offset + distance
        if index >= len(self._source):
            return "\0"
        return self._source[index]

    def _advance(self) -> str:
        character = self._source[self._offset]
        self._offset += 1
        if character == "\n":
            self._line += 1
            self._column = 1
            self._line_has_only_whitespace = True
        else:
            self._column += 1
            if character not in {" ", "\t", "\r"}:
                self._line_has_only_whitespace = False
        return character

    def _at_end(self) -> bool:
        return self._offset >= len(self._source)

    @staticmethod
    def _is_identifier_start(character: str) -> bool:
        return character.isascii() and (character.isalpha() or character == "_")

    @staticmethod
    def _is_identifier_continue(character: str) -> bool:
        return character.isascii() and (character.isalnum() or character == "_")

    @staticmethod
    def _is_hex_digit(character: str) -> bool:
        return character.isascii() and (
            character.isdigit() or character.lower() in "abcdef"
        )


def tokenize(source_text: str, file_name: str = "<memory>") -> LexerResult:
    """Convenience API for a complete lexer run."""
    return Lexer(source_text=source_text, file_name=file_name).tokenize()

