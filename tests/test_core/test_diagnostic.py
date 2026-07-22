"""Tests for structured and human-readable diagnostics."""

from c_analyzer import (
    Diagnostic,
    DiagnosticPhase,
    Severity,
    SourcePosition,
    SourceSpan,
)


def make_span() -> SourceSpan:
    start = SourcePosition(file="main.c", line=3, column=5, offset=20)
    end = SourcePosition(file="main.c", line=3, column=8, offset=23)
    return SourceSpan(start=start, end=end)


def test_diagnostic_keeps_severity_phase_message_and_position() -> None:
    diagnostic = Diagnostic(
        phase=DiagnosticPhase.CORE,
        severity=Severity.WARNING,
        message="example message",
        span=make_span(),
    )

    assert diagnostic.phase is DiagnosticPhase.CORE
    assert diagnostic.severity is Severity.WARNING
    assert diagnostic.message == "example message"
    assert diagnostic.span.start.line == 3
    assert diagnostic.length == 3


def test_diagnostic_has_readable_text_format() -> None:
    diagnostic = Diagnostic(
        phase=DiagnosticPhase.CORE,
        severity=Severity.ERROR,
        message="invalid model input",
        span=make_span(),
    )

    assert str(diagnostic) == (
        "main.c:3:5: error: [core] invalid model input"
    )

