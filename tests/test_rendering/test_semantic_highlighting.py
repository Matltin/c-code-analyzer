"""Semantic highlighting keeps source fidelity while adding resolved roles."""

import html
import re

from c_analyzer import analyze_source
from c_analyzer.rendering import (
    HighlightCategory,
    classify_tokens,
    render_ansi,
    render_html,
)


ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def test_semantic_categories_include_builtin_parameter_field_and_undefined() -> None:
    source = """
struct Point { int x; };
int show(struct Point point) {
    puts("point");
    missing = point.x;
    return 0;
}
"""
    result = analyze_source(source, "highlight.c")
    highlighted = classify_tokens(
        result.lexer.tokens,
        result.parser.ast,
        result.semantic.model,
    )
    categories = {
        item.token.lexeme: item.category
        for item in highlighted
        if item.token.lexeme in {"puts", "missing", "x"}
    }

    assert categories["puts"] is HighlightCategory.BUILTIN_FUNCTION
    assert categories["missing"] is HighlightCategory.UNDEFINED_IDENTIFIER
    assert categories["x"] is HighlightCategory.FIELD
    point_references = [
        item.category for item in highlighted if item.token.lexeme == "point"
    ]
    assert point_references[-1] is HighlightCategory.PARAMETER


def test_semantic_ansi_and_html_preserve_exact_source() -> None:
    source = 'int main(void) { puts("<&>"); missing = 1; return 0; }\n'
    result = analyze_source(source, "highlight.c")
    ansi = render_ansi(
        source,
        result.lexer.tokens,
        result.parser.ast,
        result.semantic.model,
    )
    document = render_html(
        source,
        result.lexer.tokens,
        result.parser.ast,
        result.semantic.model,
    )
    body = document.split("<pre>", 1)[1].split("</pre>", 1)[0]
    plain_html = re.sub(r"</?span(?: class=\"[^\"]+\")?>", "", body)

    assert ANSI_ESCAPE.sub("", ansi) == source
    assert html.unescape(plain_html) == source
    assert "<script" not in document.lower()
    assert 'class="builtin-function"' in document
    assert 'class="undefined-identifier"' in document

