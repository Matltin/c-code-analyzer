"""Side-table semantic model that leaves the Phase 1 AST unchanged."""

from __future__ import annotations

from dataclasses import dataclass

from c_analyzer.ast import ASTNode, IdentifierExpr, Name, Program
from c_analyzer.core import Diagnostic, SourcePosition
from c_analyzer.semantic.scope_builder import SymbolTableResult
from c_analyzer.semantic.symbols import Scope, Symbol
from c_analyzer.semantic.types import CType, UNKNOWN


@dataclass(frozen=True, slots=True)
class SemanticModel:
    """Bindings and types keyed by AST object identity for one analysis."""

    program: Program
    symbol_table: SymbolTableResult
    diagnostics: tuple[Diagnostic, ...]
    bindings: dict[int, Symbol]
    types: dict[int, CType]

    @property
    def global_scope(self) -> Scope:
        return self.symbol_table.global_scope

    @property
    def scopes(self) -> tuple[Scope, ...]:
        return self.symbol_table.scopes

    @property
    def symbols(self) -> tuple[Symbol, ...]:
        return self.symbol_table.symbols

    def type_of(self, node: ASTNode) -> CType:
        return self.types.get(id(node), UNKNOWN)

    def symbol_of(self, node: ASTNode) -> Symbol | None:
        if isinstance(node, IdentifierExpr):
            return self.bindings.get(id(node.name))
        if isinstance(node, Name):
            return self.bindings.get(id(node))
        return self.bindings.get(id(node))

    def scope_at(self, position: SourcePosition) -> Scope:
        return self.symbol_table.scope_at(position)

    def scope_for(self, node: ASTNode) -> Scope:
        return self.symbol_table.scope_for(node)

    def render_symbols(self) -> str:
        return self.symbol_table.render()

