"""Public package interface for c-code-analyzer."""

from c_analyzer.core import (
    Diagnostic,
    DiagnosticPhase,
    Severity,
    SourcePosition,
    SourceSpan,
    Token,
    TokenKind,
)

__version__ = "0.1.0"

__all__ = [
    "Diagnostic",
    "DiagnosticPhase",
    "Severity",
    "SourcePosition",
    "SourceSpan",
    "Token",
    "TokenKind",
    "__version__",
]

