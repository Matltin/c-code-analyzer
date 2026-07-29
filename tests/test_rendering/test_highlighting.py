"""AST-aware classification and source-fidelity tests."""

from html.parser import HTMLParser
import re

from c_analyzer.lexer import tokenize
from c_analyzer.parser import parse
from c_analyzer.rendering import (
    HighlightCategory,
    classify_tokens,
    render_ansi,
    render_html,
)


ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


class PreTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_pre = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "pre":
            self.in_pre = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "pre":
            self.in_pre = False

    def handle_data(self, data: str) -> None:
        if self.in_pre:
            self.parts.append(data)


def analyze(source: str):
    lexer_result = tokenize(source, "highlight.c")
    parser_result = parse(lexer_result.tokens)
    return lexer_result, parser_result


def test_contextual_identifier_categories_come_from_ast() -> None:
    source = """
struct Point { int field; };
int add(int parameter) { int variable = parameter; return variable; }
int main(void) { return add(1); }
"""
    lexer_result, parser_result = analyze(source)
    highlighted = classify_tokens(lexer_result.tokens, parser_result.ast)
    roles = [
        (item.token.lexeme, item.category)
        for item in highlighted
        if item.token.lexeme in {"Point", "field", "add", "parameter", "variable"}
    ]

    assert ("Point", HighlightCategory.STRUCT_NAME) in roles
    assert ("field", HighlightCategory.FIELD) in roles
    assert ("add", HighlightCategory.FUNCTION_DECLARATION) in roles
    assert ("add", HighlightCategory.FUNCTION_CALL) in roles
    assert ("parameter", HighlightCategory.PARAMETER) in roles
    assert ("variable", HighlightCategory.VARIABLE) in roles


def test_ansi_rendering_preserves_exact_source() -> None:
    source = "int main(void) {\n\treturn 1 + 2;\n}\n"
    lexer_result, parser_result = analyze(source)

    rendered = render_ansi(source, lexer_result.tokens, parser_result.ast)

    assert ANSI_PATTERN.sub("", rendered) == source
    assert "\x1b[0m" in rendered


def test_html_rendering_preserves_and_escapes_exact_source() -> None:
    source = 'int main(void) { if (1 < 2 && 3 > 0) return "a&<b>"; }\n'
    lexer_result, parser_result = analyze(source)

    rendered = render_html(source, lexer_result.tokens, parser_result.ast)
    parser = PreTextParser()
    parser.feed(rendered)

    assert "".join(parser.parts) == source
    assert "&lt;" in rendered
    assert "&gt;" in rendered
    assert "&amp;" in rendered
    assert "<script" not in rendered.lower()
    assert "<style>" in rendered
    assert "<pre>" in rendered


def test_invalid_token_receives_invalid_category() -> None:
    lexer_result, parser_result = analyze("int main(void) { @; }")

    highlighted = classify_tokens(lexer_result.tokens, parser_result.ast)

    assert any(
        item.category is HighlightCategory.INVALID for item in highlighted
    )

