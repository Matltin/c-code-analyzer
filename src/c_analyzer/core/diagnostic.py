"""Structured diagnostics shared by future analysis phases."""

from dataclasses import dataclass
from enum import Enum

from c_analyzer.core.source import SourceSpan


class Severity(Enum):
    """How strongly a diagnostic affects the analyzed source."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class DiagnosticPhase(Enum):
    """The project stage that reported a diagnostic."""

    CORE = "core"
    LEXER = "lexer"
    PARSER = "parser"
    SEMANTIC = "semantic"
    ANALYSIS = "analysis"
    IDE = "ide"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A source-aware message produced by a project phase."""

    phase: DiagnosticPhase
    severity: Severity
    message: str
    span: SourceSpan

    def __post_init__(self) -> None:
        if not isinstance(self.phase, DiagnosticPhase):
            raise TypeError("phase must be a DiagnosticPhase")
        if not isinstance(self.severity, Severity):
            raise TypeError("severity must be a Severity")
        if not isinstance(self.message, str):
            raise TypeError("message must be a string")
        if not self.message.strip():
            raise ValueError("message must not be empty")
        if not isinstance(self.span, SourceSpan):
            raise TypeError("span must be a SourceSpan")

    @property
    def length(self) -> int:
        """Return the length of the highlighted source range."""
        return self.span.length

    @property
    def file(self) -> str:
        return self.span.start.file

    @property
    def line(self) -> int:
        return self.span.start.line

    @property
    def column(self) -> int:
        return self.span.start.column

    def to_dict(self) -> dict[str, str | int]:
        """Return the stable machine-readable representation."""
        return {
            "phase": self.phase.value,
            "severity": self.severity.value,
            "message": self.message,
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "length": self.length,
        }

    def __str__(self) -> str:
        position = self.span.start
        return (
            f"{position.file}:{position.line}:{position.column}: "
            f"{self.severity.value}: [{self.phase.value}] {self.message}"
        )
