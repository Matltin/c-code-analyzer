"""End-to-end Phase 2 pipeline and deterministic diagnostic formatting."""

from __future__ import annotations

from dataclasses import dataclass
import json

from c_analyzer.core import Diagnostic, Severity
from c_analyzer.lexer import LexerResult, tokenize
from c_analyzer.parser import ParserResult, parse
from c_analyzer.semantic import SemanticResult, analyze


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    source_text: str
    file_name: str
    lexer: LexerResult
    parser: ParserResult
    semantic: SemanticResult
    diagnostics: tuple[Diagnostic, ...]

    @property
    def has_errors(self) -> bool:
        return any(item.severity is Severity.ERROR for item in self.diagnostics)


def sort_diagnostics(
    diagnostics: tuple[Diagnostic, ...] | list[Diagnostic],
) -> tuple[Diagnostic, ...]:
    """Deduplicate exact messages and sort them deterministically."""
    unique: dict[tuple[object, ...], Diagnostic] = {}
    for item in diagnostics:
        key = (
            item.phase,
            item.severity,
            item.message,
            item.span.start.file,
            item.span.start.offset,
            item.span.end.offset,
        )
        unique.setdefault(key, item)
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                item.file,
                item.span.start.offset,
                item.span.end.offset,
                item.phase.value,
                item.severity.value,
                item.message,
            ),
        )
    )


def analyze_source(source_text: str, file_name: str) -> AnalysisResult:
    """Run Lexer, Parser, and safe semantic analysis on one source file."""
    lexer_result = tokenize(source_text, file_name)
    parser_result = parse(lexer_result.tokens)
    semantic_result = analyze(parser_result.ast)
    diagnostics = sort_diagnostics(
        [
            *lexer_result.diagnostics,
            *parser_result.diagnostics,
            *semantic_result.diagnostics,
        ]
    )
    return AnalysisResult(
        source_text=source_text,
        file_name=file_name,
        lexer=lexer_result,
        parser=parser_result,
        semantic=semantic_result,
        diagnostics=diagnostics,
    )


def diagnostics_to_json(
    diagnostics: tuple[Diagnostic, ...] | list[Diagnostic],
) -> str:
    """Serialize diagnostics as Unicode-safe, machine-readable JSON."""
    ordered = sort_diagnostics(diagnostics)
    payload = {
        "diagnostics": [item.to_dict() for item in ordered],
        "error_count": sum(item.severity is Severity.ERROR for item in ordered),
        "warning_count": sum(item.severity is Severity.WARNING for item in ordered),
        "info_count": sum(item.severity is Severity.INFO for item in ordered),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

