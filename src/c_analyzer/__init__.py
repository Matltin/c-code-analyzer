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
from c_analyzer.analysis import (
    AnalysisResult,
    analyze_source,
    diagnostics_to_json,
    sort_diagnostics,
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
    "AnalysisResult",
    "analyze_source",
    "diagnostics_to_json",
    "sort_diagnostics",
    "__version__",
]
