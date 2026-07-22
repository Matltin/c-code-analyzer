"""Tests for the public package imports."""


def test_core_models_are_importable_from_package() -> None:
    from c_analyzer import (
        Diagnostic,
        DiagnosticPhase,
        Severity,
        SourcePosition,
        SourceSpan,
        Token,
        TokenKind,
    )

    exported_models = {
        Diagnostic,
        DiagnosticPhase,
        Severity,
        SourcePosition,
        SourceSpan,
        Token,
        TokenKind,
    }

    assert len(exported_models) == 7

