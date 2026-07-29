"""Models for deterministic multi-file indexing and navigation."""

from __future__ import annotations

from dataclasses import dataclass, field

from c_analyzer.analysis import AnalysisResult
from c_analyzer.core import Diagnostic
from c_analyzer.semantic import AccessKind, CType, SymbolKind, SymbolNamespace


@dataclass(frozen=True, slots=True, order=True)
class ProjectLocation:
    file: str
    offset: int
    line: int
    column: int
    length: int

    def to_dict(self) -> dict[str, str | int]:
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "length": self.length,
        }


@dataclass(frozen=True, slots=True)
class ProjectReference:
    symbol_id: str
    location: ProjectLocation
    access_kind: AccessKind | None
    is_definition: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            **self.location.to_dict(),
            "symbol_id": self.symbol_id,
            "access_kind": (
                self.access_kind.value if self.access_kind is not None else None
            ),
            "is_definition": self.is_definition,
        }


@dataclass(slots=True)
class ProjectSymbol:
    id: str
    name: str
    kind: SymbolKind
    type: CType
    namespace: SymbolNamespace
    definition: ProjectLocation | None
    declarations: list[ProjectLocation] = field(default_factory=list)
    references: list[ProjectReference] = field(default_factory=list)
    signature: str | None = None
    scope_id: str | None = None
    is_builtin: bool = False
    documentation: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectFile:
    path: str
    source: str
    analysis: AnalysisResult


@dataclass(frozen=True, slots=True)
class DefinitionResult:
    symbol_id: str
    symbol: str
    kind: str
    type: str
    definition: ProjectLocation | None
    declarations: tuple[ProjectLocation, ...]
    is_builtin: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol_id": self.symbol_id,
            "symbol": self.symbol,
            "kind": self.kind,
            "type": self.type,
            "definition": (
                self.definition.to_dict()
                if self.definition is not None
                else "built-in"
                if self.is_builtin
                else None
            ),
            "declarations": [item.to_dict() for item in self.declarations],
            "is_builtin": self.is_builtin,
        }


@dataclass(frozen=True, slots=True)
class ProjectHover:
    name: str
    kind: str
    type: str
    signature: str | None
    scope: str | None
    definition: ProjectLocation | None
    declarations: tuple[ProjectLocation, ...]
    documentation: str | None
    is_builtin: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "type": self.type,
            "signature": self.signature,
            "scope": self.scope,
            "definition": (
                self.definition.to_dict()
                if self.definition is not None
                else "built-in"
                if self.is_builtin
                else None
            ),
            "declarations": [item.to_dict() for item in self.declarations],
            "documentation": self.documentation,
            "is_builtin": self.is_builtin,
        }


@dataclass(frozen=True, slots=True)
class ProjectAnalysis:
    root: str
    files: tuple[ProjectFile, ...]
    symbols: tuple[ProjectSymbol, ...]
    diagnostics: tuple[Diagnostic, ...]
    local_to_project: dict[tuple[str, str], str]

    @property
    def has_errors(self) -> bool:
        return any(item.severity.value == "error" for item in self.diagnostics)

    def file(self, path: str) -> ProjectFile | None:
        normalized = normalize_project_path(path)
        return next((item for item in self.files if item.path == normalized), None)

    def symbol(self, symbol_id: str) -> ProjectSymbol | None:
        return next((item for item in self.symbols if item.id == symbol_id), None)

    def render_index(self) -> str:
        lines = [f"project: {self.root}"]
        for file in self.files:
            lines.append(f"file: {file.path}")
        lines.append("symbols:")
        for symbol in self.symbols:
            definition = (
                "built-in"
                if symbol.is_builtin
                else (
                    f"{symbol.definition.file}:{symbol.definition.line}:"
                    f"{symbol.definition.column}"
                    if symbol.definition is not None
                    else "declaration-only"
                )
            )
            lines.append(
                f"  {symbol.id} {symbol.kind.value} {symbol.name}: "
                f"{symbol.type} [{definition}]"
            )
        return "\n".join(lines)


def normalize_project_path(path: str) -> str:
    """Normalize a project-relative path without depending on the host OS."""
    pieces: list[str] = []
    for piece in path.replace("\\", "/").split("/"):
        if piece in {"", "."}:
            continue
        if piece == "..":
            if pieces:
                pieces.pop()
            continue
        pieces.append(piece)
    if not pieces:
        raise ValueError("project file path must not be empty")
    return "/".join(pieces)

