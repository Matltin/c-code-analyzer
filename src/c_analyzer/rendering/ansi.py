"""ANSI terminal renderer that preserves the original source bytes."""

from __future__ import annotations

from c_analyzer.ast import Program
from c_analyzer.core import Token
from c_analyzer.rendering.highlight import HighlightCategory, classify_tokens
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from c_analyzer.semantic import SemanticModel


RESET = "\x1b[0m"

ANSI_STYLES = {
    HighlightCategory.KEYWORD: "\x1b[1;34m",
    HighlightCategory.TYPE_KEYWORD: "\x1b[36m",
    HighlightCategory.FUNCTION_DECLARATION: "\x1b[33m",
    HighlightCategory.FUNCTION_CALL: "\x1b[33m",
    HighlightCategory.VARIABLE: "\x1b[37m",
    HighlightCategory.PARAMETER: "\x1b[96m",
    HighlightCategory.STRUCT_NAME: "\x1b[92m",
    HighlightCategory.FIELD: "\x1b[93m",
    HighlightCategory.NUMBER: "\x1b[38;5;208m",
    HighlightCategory.TEXT: "\x1b[32m",
    HighlightCategory.OPERATOR: "\x1b[37m",
    HighlightCategory.COMMENT: "\x1b[2;3;37m",
    HighlightCategory.PREPROCESSOR: "\x1b[35m",
    HighlightCategory.INVALID: "\x1b[4;31m",
    HighlightCategory.BUILTIN_FUNCTION: "\x1b[1;35m",
    HighlightCategory.UNDEFINED_IDENTIFIER: "\x1b[4;31m",
}


def render_ansi(
    source: str,
    tokens: tuple[Token, ...] | list[Token],
    program: Program,
    semantic_model: SemanticModel | None = None,
) -> str:
    """Return source with ANSI styles around classified token spans."""
    parts: list[str] = []
    cursor = 0
    for highlighted in classify_tokens(tokens, program, semantic_model):
        token = highlighted.token
        start = token.span.start.offset
        end = token.span.end.offset
        if start < cursor:
            continue
        parts.append(source[cursor:start])
        text = source[start:end]
        style = (
            ANSI_STYLES.get(highlighted.category)
            if highlighted.category is not None
            else None
        )
        if style:
            parts.extend((style, text, RESET))
        else:
            parts.append(text)
        cursor = end
    parts.append(source[cursor:])
    return "".join(parts)
