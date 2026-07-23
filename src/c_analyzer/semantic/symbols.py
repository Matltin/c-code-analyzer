"""Scope, symbol, namespace, and reference models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from c_analyzer.core import SourcePosition, SourceSpan
from c_analyzer.semantic.types import CType


class ScopeKind(Enum):
    GLOBAL = "global"
    FUNCTION = "function"
    BLOCK = "block"
    STRUCT = "struct"


class SymbolKind(Enum):
    VARIABLE = "variable"
    PARAMETER = "parameter"
    FUNCTION = "function"
    STRUCT = "struct"
    FIELD = "field"
    BUILTIN_FUNCTION = "builtin_function"


class SymbolNamespace(Enum):
    ORDINARY = "ordinary"
    TAG = "tag"
    FIELD = "field"


class AccessKind(Enum):
    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"
    CALL = "call"
    TYPE_REFERENCE = "type_reference"
    MEMBER_ACCESS = "member_access"


@dataclass(frozen=True, slots=True)
class Reference:
    """One source occurrence linked to a symbol by deterministic ID."""

    symbol_id: str
    span: SourceSpan
    access_kind: AccessKind


@dataclass(slots=True)
class Symbol:
    """A declaration plus the references collected for it."""

    id: str
    name: str
    kind: SymbolKind
    type: CType
    scope_id: str
    definition_span: SourceSpan | None
    references: list[Reference] = field(default_factory=list)
    signature: str | None = None
    is_initialized: bool = False
    is_used: bool = False
    visible_from: int = 0


def _empty_namespaces() -> dict[SymbolNamespace, dict[str, Symbol]]:
    return {
        SymbolNamespace.ORDINARY: {},
        SymbolNamespace.TAG: {},
        SymbolNamespace.FIELD: {},
    }


@dataclass(slots=True)
class Scope:
    """A lexical scope with three separate C namespaces."""

    id: str
    kind: ScopeKind
    parent: Scope | None
    span: SourceSpan
    children: list[Scope] = field(default_factory=list)
    symbols: dict[SymbolNamespace, dict[str, Symbol]] = field(
        default_factory=_empty_namespaces
    )

    def add_symbol(
        self,
        symbol: Symbol,
        namespace: SymbolNamespace = SymbolNamespace.ORDINARY,
    ) -> bool:
        """Add locally and return False when that namespace already has the name."""
        local = self.symbols[namespace]
        if symbol.name in local:
            return False
        local[symbol.name] = symbol
        return True

    def lookup_local(
        self,
        name: str,
        namespace: SymbolNamespace = SymbolNamespace.ORDINARY,
    ) -> Symbol | None:
        return self.symbols[namespace].get(name)

    def lookup(
        self,
        name: str,
        namespace: SymbolNamespace = SymbolNamespace.ORDINARY,
        *,
        offset: int | None = None,
    ) -> Symbol | None:
        """Look from this scope outwards, respecting declaration visibility."""
        current: Scope | None = self
        while current is not None:
            symbol = current.lookup_local(name, namespace)
            if symbol is not None and (
                offset is None or symbol.visible_from <= offset
            ):
                return symbol
            current = current.parent
        return None

    @property
    def all_symbols(self) -> tuple[Symbol, ...]:
        """Return symbols in deterministic namespace and insertion order."""
        return tuple(
            symbol
            for namespace in SymbolNamespace
            for symbol in self.symbols[namespace].values()
        )

    def contains(self, position: SourcePosition) -> bool:
        return (
            position.file == self.span.start.file
            and self.span.start.offset <= position.offset <= self.span.end.offset
        )


def render_scope_tree(root: Scope) -> str:
    """Return a deterministic, readable scope and symbol tree."""
    lines: list[str] = []

    def visit(scope: Scope, depth: int) -> None:
        indent = "  " * depth
        lines.append(f"{indent}{scope.id} {scope.kind.value}")
        for namespace in SymbolNamespace:
            for symbol in scope.symbols[namespace].values():
                lines.append(
                    f"{indent}  {namespace.value}: {symbol.id} "
                    f"{symbol.kind.value} {symbol.name}: {symbol.type}"
                )
        for child in scope.children:
            visit(child, depth + 1)

    visit(root, 0)
    return "\n".join(lines)

