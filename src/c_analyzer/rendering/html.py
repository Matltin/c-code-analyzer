"""Self-contained, escaped HTML renderer without JavaScript."""

from __future__ import annotations

from html import escape

from c_analyzer.ast import Program
from c_analyzer.core import Token
from c_analyzer.rendering.highlight import classify_tokens
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from c_analyzer.semantic import SemanticModel


CSS = """
body { margin: 0; background: #1e1e1e; color: #d4d4d4; }
pre { margin: 0; padding: 1rem; tab-size: 4; white-space: pre-wrap; }
.keyword { color: #569cd6; font-weight: bold; }
.type { color: #4ec9b0; }
.function-declaration, .function-call { color: #dcdcaa; }
.variable { color: #d4d4d4; }
.parameter { color: #9cdcfe; }
.struct-name { color: #6a9955; }
.field { color: #c8c86a; }
.number { color: #ce9178; }
.text { color: #6a9955; }
.operator { color: #d4d4d4; }
.comment { color: #808080; font-style: italic; }
.preprocessor { color: #c586c0; }
.invalid { color: #f44747; text-decoration: underline; }
.builtin-function { color: #c586c0; font-weight: bold; }
.undefined-identifier { color: #f44747; text-decoration: underline; }
""".strip()


def render_html(
    source: str,
    tokens: tuple[Token, ...] | list[Token],
    program: Program,
    semantic_model: SemanticModel | None = None,
) -> str:
    """Return a self-contained HTML document preserving exact source text."""
    parts: list[str] = []
    cursor = 0
    for highlighted in classify_tokens(tokens, program, semantic_model):
        token = highlighted.token
        start = token.span.start.offset
        end = token.span.end.offset
        if start < cursor:
            continue
        parts.append(escape(source[cursor:start]))
        text = escape(source[start:end])
        if highlighted.category is None:
            parts.append(text)
        else:
            css_class = highlighted.category.value
            parts.append(f'<span class="{css_class}">{text}</span>')
        cursor = end
    parts.append(escape(source[cursor:]))
    body = "".join(parts)
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<style>{CSS}</style></head><body><pre>{body}</pre></body></html>"
    )
