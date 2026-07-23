"""Deterministic scope tree and declaration collection for Phase 2."""

from __future__ import annotations

from dataclasses import dataclass

from c_analyzer.ast import (
    ASTNode,
    BlockStmt,
    Declaration,
    FieldDecl,
    ForStmt,
    FunctionDecl,
    FunctionPrototype,
    IfStmt,
    IntegerLiteral,
    Parameter,
    Program,
    Statement,
    StructDecl,
    TypeRef,
    VarDecl,
    WhileStmt,
)
from c_analyzer.core import Diagnostic, DiagnosticPhase, Severity, SourcePosition
from c_analyzer.semantic.symbols import (
    Scope,
    ScopeKind,
    Symbol,
    SymbolKind,
    SymbolNamespace,
    render_scope_tree,
)
from c_analyzer.semantic.types import (
    ArrayType,
    CHAR,
    CType,
    FunctionType,
    INT,
    PointerType,
    StructType,
    UNKNOWN,
    primitive_type,
)


@dataclass(frozen=True, slots=True)
class SymbolTableResult:
    """Scope and declaration information created without global state."""

    global_scope: Scope
    scopes: tuple[Scope, ...]
    symbols: tuple[Symbol, ...]
    diagnostics: tuple[Diagnostic, ...]
    node_scopes: dict[int, Scope]
    definition_bindings: dict[int, Symbol]
    struct_scopes: dict[str, Scope]

    def scope_at(self, position: SourcePosition) -> Scope:
        """Return the deepest scope containing the cursor position."""
        candidates = [scope for scope in self.scopes if scope.contains(position)]
        if not candidates:
            return self.global_scope
        return max(candidates, key=lambda scope: (_scope_depth(scope), -scope.span.length))

    def scope_for(self, node: ASTNode) -> Scope:
        return self.node_scopes.get(id(node), self.global_scope)

    def symbol_for_definition(self, node: ASTNode) -> Symbol | None:
        return self.definition_bindings.get(id(node))

    def render(self) -> str:
        return render_scope_tree(self.global_scope)


def _scope_depth(scope: Scope) -> int:
    depth = 0
    current = scope.parent
    while current is not None:
        depth += 1
        current = current.parent
    return depth


class SymbolTableBuilder:
    """Collect declarations and construct every lexical scope deterministically."""

    def __init__(self) -> None:
        self._next_scope = 1
        self._next_symbol = 1
        self._scopes: list[Scope] = []
        self._symbols: list[Symbol] = []
        self._diagnostics: list[Diagnostic] = []
        self._node_scopes: dict[int, Scope] = {}
        self._definition_bindings: dict[int, Symbol] = {}
        self._struct_scopes: dict[str, Scope] = {}
        self._defined_functions: set[str] = set()

    def build(self, program: Program) -> SymbolTableResult:
        global_scope = self._new_scope(ScopeKind.GLOBAL, None, program.span)
        self._node_scopes[id(program)] = global_scope
        self._install_builtins(global_scope)

        for declaration in program.declarations:
            self._collect_global(declaration, global_scope)

        return SymbolTableResult(
            global_scope=global_scope,
            scopes=tuple(self._scopes),
            symbols=tuple(self._symbols),
            diagnostics=tuple(self._diagnostics),
            node_scopes=dict(self._node_scopes),
            definition_bindings=dict(self._definition_bindings),
            struct_scopes=dict(self._struct_scopes),
        )

    def _new_scope(
        self,
        kind: ScopeKind,
        parent: Scope | None,
        span,
    ) -> Scope:
        scope = Scope(
            id=f"scope-{self._next_scope:04d}",
            kind=kind,
            parent=parent,
            span=span,
        )
        self._next_scope += 1
        self._scopes.append(scope)
        if parent is not None:
            parent.children.append(scope)
        return scope

    def _new_symbol(
        self,
        *,
        name: str,
        kind: SymbolKind,
        type_: CType,
        scope: Scope,
        definition_span,
        signature: str | None = None,
        is_initialized: bool = False,
        visible_from: int = 0,
    ) -> Symbol:
        symbol = Symbol(
            id=f"sym-{self._next_symbol:04d}",
            name=name,
            kind=kind,
            type=type_,
            scope_id=scope.id,
            definition_span=definition_span,
            signature=signature,
            is_initialized=is_initialized,
            visible_from=visible_from,
        )
        self._next_symbol += 1
        self._symbols.append(symbol)
        return symbol

    def _install_builtins(self, scope: Scope) -> None:
        char_pointer = PointerType(CHAR)
        builtins = (
            ("printf", FunctionType(INT, (char_pointer,), variadic=True), "int printf(char *format, ...)"),
            ("puts", FunctionType(INT, (char_pointer,)), "int puts(char *text)"),
        )
        for name, type_, signature in builtins:
            symbol = self._new_symbol(
                name=name,
                kind=SymbolKind.BUILTIN_FUNCTION,
                type_=type_,
                scope=scope,
                definition_span=None,
                signature=signature,
                is_initialized=True,
            )
            scope.add_symbol(symbol)

    def _collect_global(self, declaration: Declaration, scope: Scope) -> None:
        self._node_scopes[id(declaration)] = scope
        if isinstance(declaration, StructDecl):
            self._collect_struct(declaration, scope)
        elif isinstance(declaration, (FunctionDecl, FunctionPrototype)):
            self._collect_function(declaration, scope)
        elif isinstance(declaration, VarDecl):
            self._collect_variable(
                declaration,
                scope,
                is_global=True,
            )

    def _collect_struct(self, declaration: StructDecl, parent: Scope) -> None:
        existing = parent.lookup_local(declaration.name.text, SymbolNamespace.TAG)
        if existing is not None:
            self._error(declaration.name, f"duplicate struct tag '{declaration.name.text}'")
            self._definition_bindings[id(declaration.name)] = existing
            return

        symbol_id = f"sym-{self._next_symbol:04d}"
        struct_type = StructType(declaration.name.text, symbol_id)
        symbol = self._new_symbol(
            name=declaration.name.text,
            kind=SymbolKind.STRUCT,
            type_=struct_type,
            scope=parent,
            definition_span=declaration.name.span,
            visible_from=declaration.name.span.end.offset,
        )
        parent.add_symbol(symbol, SymbolNamespace.TAG)
        self._definition_bindings[id(declaration.name)] = symbol

        struct_scope = self._new_scope(ScopeKind.STRUCT, parent, declaration.span)
        self._struct_scopes[symbol.id] = struct_scope
        self._node_scopes[id(declaration)] = struct_scope
        for field in declaration.fields:
            self._node_scopes[id(field)] = struct_scope
            field_type = self._declaration_type(field.type_ref, field.array_size)
            field_symbol = self._new_symbol(
                name=field.name.text,
                kind=SymbolKind.FIELD,
                type_=field_type,
                scope=struct_scope,
                definition_span=field.name.span,
                visible_from=field.name.span.end.offset,
            )
            if not struct_scope.add_symbol(field_symbol, SymbolNamespace.FIELD):
                self._symbols.pop()
                self._next_symbol -= 1
                existing_field = struct_scope.lookup_local(
                    field.name.text,
                    SymbolNamespace.FIELD,
                )
                assert existing_field is not None
                self._definition_bindings[id(field.name)] = existing_field
                self._error(field.name, f"duplicate field '{field.name.text}'")
            else:
                self._definition_bindings[id(field.name)] = field_symbol

    def _collect_function(
        self,
        declaration: FunctionDecl | FunctionPrototype,
        global_scope: Scope,
    ) -> None:
        function_type = FunctionType(
            self._type_from_ref(declaration.return_type),
            tuple(self._parameter_type(item) for item in declaration.parameters),
        )
        signature = _function_signature(declaration.name.text, function_type)
        existing = global_scope.lookup_local(declaration.name.text)

        if existing is None:
            symbol = self._new_symbol(
                name=declaration.name.text,
                kind=SymbolKind.FUNCTION,
                type_=function_type,
                scope=global_scope,
                definition_span=declaration.name.span,
                signature=signature,
                is_initialized=True,
            )
            global_scope.add_symbol(symbol)
        elif existing.kind in {SymbolKind.FUNCTION, SymbolKind.BUILTIN_FUNCTION}:
            symbol = existing
            if existing.type != function_type:
                self._error(
                    declaration.name,
                    f"conflicting declaration for function '{declaration.name.text}'",
                )
            elif isinstance(declaration, FunctionDecl):
                if declaration.name.text in self._defined_functions:
                    self._error(
                        declaration.name,
                        f"duplicate function definition '{declaration.name.text}'",
                    )
                else:
                    self._defined_functions.add(declaration.name.text)
        else:
            symbol = existing
            self._error(
                declaration.name,
                f"duplicate declaration '{declaration.name.text}'",
            )

        if isinstance(declaration, FunctionDecl):
            self._defined_functions.add(declaration.name.text)
        self._definition_bindings[id(declaration.name)] = symbol

        if isinstance(declaration, FunctionPrototype):
            return

        function_scope = self._new_scope(
            ScopeKind.FUNCTION,
            global_scope,
            declaration.span,
        )
        self._node_scopes[id(declaration)] = function_scope
        for parameter in declaration.parameters:
            self._collect_parameter(parameter, function_scope)
        self._collect_block(declaration.body, function_scope)

    def _collect_parameter(self, parameter: Parameter, scope: Scope) -> None:
        self._node_scopes[id(parameter)] = scope
        symbol = self._new_symbol(
            name=parameter.name.text,
            kind=SymbolKind.PARAMETER,
            type_=self._parameter_type(parameter),
            scope=scope,
            definition_span=parameter.name.span,
            is_initialized=True,
            visible_from=parameter.name.span.end.offset,
        )
        if not scope.add_symbol(symbol):
            self._symbols.pop()
            self._next_symbol -= 1
            existing = scope.lookup_local(parameter.name.text)
            assert existing is not None
            self._definition_bindings[id(parameter.name)] = existing
            self._error(parameter.name, f"duplicate parameter '{parameter.name.text}'")
        else:
            self._definition_bindings[id(parameter.name)] = symbol

    def _collect_block(self, block: BlockStmt, parent: Scope) -> Scope:
        scope = self._new_scope(ScopeKind.BLOCK, parent, block.span)
        self._node_scopes[id(block)] = scope
        for item in block.items:
            self._node_scopes[id(item)] = scope
            if isinstance(item, VarDecl):
                self._collect_variable(item, scope, is_global=False)
            elif isinstance(item, BlockStmt):
                self._collect_block(item, scope)
            elif isinstance(item, IfStmt):
                self._collect_statement_scopes(item.then_branch, scope)
                if item.else_branch is not None:
                    self._collect_statement_scopes(item.else_branch, scope)
            elif isinstance(item, WhileStmt):
                self._collect_statement_scopes(item.body, scope)
            elif isinstance(item, ForStmt):
                self._collect_for(item, scope)
        return scope

    def _collect_for(self, statement: ForStmt, parent: Scope) -> None:
        self._node_scopes[id(statement)] = parent
        scope = parent
        if isinstance(statement.initializer, VarDecl):
            scope = self._new_scope(ScopeKind.BLOCK, parent, statement.span)
            self._node_scopes[id(statement)] = scope
            self._collect_variable(statement.initializer, scope, is_global=False)
        self._collect_statement_scopes(statement.body, scope)

    def _collect_statement_scopes(self, statement: Statement, parent: Scope) -> None:
        self._node_scopes[id(statement)] = parent
        if isinstance(statement, BlockStmt):
            self._collect_block(statement, parent)
        elif isinstance(statement, IfStmt):
            self._collect_statement_scopes(statement.then_branch, parent)
            if statement.else_branch is not None:
                self._collect_statement_scopes(statement.else_branch, parent)
        elif isinstance(statement, WhileStmt):
            self._collect_statement_scopes(statement.body, parent)
        elif isinstance(statement, ForStmt):
            self._collect_for(statement, parent)

    def _collect_variable(
        self,
        declaration: VarDecl,
        scope: Scope,
        *,
        is_global: bool,
    ) -> None:
        symbol = self._new_symbol(
            name=declaration.name.text,
            kind=SymbolKind.VARIABLE,
            type_=self._declaration_type(declaration.type_ref, declaration.array_size),
            scope=scope,
            definition_span=declaration.name.span,
            is_initialized=is_global or declaration.initializer is not None,
            visible_from=declaration.name.span.end.offset,
        )
        if not scope.add_symbol(symbol):
            self._symbols.pop()
            self._next_symbol -= 1
            existing = scope.lookup_local(declaration.name.text)
            assert existing is not None
            self._definition_bindings[id(declaration.name)] = existing
            self._error(declaration.name, f"duplicate declaration '{declaration.name.text}'")
        else:
            self._definition_bindings[id(declaration.name)] = symbol

    def _parameter_type(self, parameter: Parameter) -> CType:
        base = self._type_from_ref(parameter.type_ref)
        return PointerType(base) if parameter.is_array else base

    def _declaration_type(self, type_ref: TypeRef, array_size: ASTNode | None) -> CType:
        base = self._type_from_ref(type_ref)
        if array_size is None:
            return base
        size = None
        if isinstance(array_size, IntegerLiteral):
            try:
                size = int(array_size.lexeme, 0)
            except ValueError:
                size = None
        return ArrayType(base, size)

    def _type_from_ref(self, type_ref: TypeRef) -> CType:
        if type_ref.keyword == "struct":
            if type_ref.struct_name is None:
                base: CType = UNKNOWN
            else:
                base = StructType(type_ref.struct_name.text)
        else:
            try:
                base = primitive_type(type_ref.keyword)
            except KeyError:
                base = UNKNOWN
        return PointerType(base) if type_ref.is_pointer else base

    def _error(self, node: ASTNode, message: str) -> None:
        self._diagnostics.append(
            Diagnostic(
                phase=DiagnosticPhase.SEMANTIC,
                severity=Severity.ERROR,
                message=message,
                span=node.span,
            )
        )


def _function_signature(name: str, type_: FunctionType) -> str:
    parameters = [str(item) for item in type_.parameter_types]
    if type_.variadic:
        parameters.append("...")
    return f"{type_.return_type} {name}({', '.join(parameters)})"


def build_symbol_table(program: Program) -> SymbolTableResult:
    """Build an isolated scope tree and declaration table."""
    return SymbolTableBuilder().build(program)
