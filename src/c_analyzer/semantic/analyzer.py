"""Two-pass name resolution with reference tracking."""

from __future__ import annotations

from dataclasses import dataclass

from c_analyzer.ast import (
    AssignmentExpr,
    BinaryExpr,
    BlockStmt,
    CallExpr,
    CharLiteral,
    Declaration,
    ErrorExpr,
    ErrorStmt,
    ExprStmt,
    Expression,
    FloatLiteral,
    ForStmt,
    FunctionDecl,
    FunctionPrototype,
    IdentifierExpr,
    IfStmt,
    IndexExpr,
    InitializerList,
    IntegerLiteral,
    MemberExpr,
    Name,
    Parameter,
    Program,
    ReturnStmt,
    Statement,
    StringLiteral,
    StructDecl,
    TypeRef,
    UnaryExpr,
    VarDecl,
    WhileStmt,
)
from c_analyzer.core import Diagnostic, DiagnosticPhase, Severity, TokenKind
from c_analyzer.semantic.model import SemanticModel
from c_analyzer.semantic.scope_builder import SymbolTableResult, build_symbol_table
from c_analyzer.semantic.symbols import (
    AccessKind,
    Reference,
    Scope,
    Symbol,
    SymbolKind,
    SymbolNamespace,
)
from c_analyzer.semantic.types import (
    ArrayType,
    CHAR,
    CType,
    DOUBLE,
    ERROR,
    FLOAT,
    FunctionType,
    INT,
    PointerType,
    StructType,
    UNKNOWN,
    primitive_type,
)


@dataclass(frozen=True, slots=True)
class SemanticResult:
    model: SemanticModel
    diagnostics: tuple[Diagnostic, ...]


class SemanticAnalyzer:
    """Resolve declarations and names while preserving partial ASTs."""

    def __init__(self, program: Program) -> None:
        self._program = program
        self._table: SymbolTableResult = build_symbol_table(program)
        self._diagnostics: list[Diagnostic] = list(self._table.diagnostics)
        self._bindings: dict[int, Symbol] = dict(self._table.definition_bindings)
        self._types: dict[int, CType] = {}
        self._resolved_function_types: set[str] = set()

    def analyze(self) -> SemanticResult:
        """Run declaration-type resolution and body reference resolution."""
        for declaration in self._program.declarations:
            self._resolve_declaration_types(declaration, self._table.global_scope)

        self._report_shadowing()

        for declaration in self._program.declarations:
            if isinstance(declaration, VarDecl) and declaration.initializer is not None:
                self._resolve_expression(
                    declaration.initializer,
                    self._table.global_scope,
                    AccessKind.READ,
                )
            elif isinstance(declaration, FunctionDecl):
                self._resolve_function_body(declaration)

        model = SemanticModel(
            program=self._program,
            symbol_table=self._table,
            diagnostics=tuple(self._diagnostics),
            bindings=dict(self._bindings),
            types=dict(self._types),
        )
        from c_analyzer.semantic.type_checker import check_types

        model = check_types(model)
        return SemanticResult(model=model, diagnostics=model.diagnostics)

    def _resolve_declaration_types(
        self,
        declaration: Declaration,
        scope: Scope,
    ) -> None:
        if isinstance(declaration, StructDecl):
            struct_scope = self._table.scope_for(declaration)
            struct_symbol = self._table.symbol_for_definition(declaration.name)
            if struct_symbol is not None:
                self._bindings[id(declaration.name)] = struct_symbol
                self._types[id(declaration)] = struct_symbol.type
            for field in declaration.fields:
                field_symbol = self._table.symbol_for_definition(field.name)
                field_type = self._declared_type(
                    field.type_ref,
                    field.array_size,
                    struct_scope,
                )
                if (
                    field_symbol is not None
                    and field_symbol.kind is SymbolKind.FIELD
                    and field_symbol.definition_span == field.name.span
                ):
                    field_symbol.type = field_type
                    self._bindings[id(field.name)] = field_symbol
                self._types[id(field)] = field_type
            return

        if isinstance(declaration, VarDecl):
            symbol = self._table.symbol_for_definition(declaration.name)
            type_ = self._declared_type(
                declaration.type_ref,
                declaration.array_size,
                scope,
            )
            if (
                symbol is not None
                and symbol.kind is SymbolKind.VARIABLE
                and symbol.definition_span == declaration.name.span
            ):
                symbol.type = type_
                self._bindings[id(declaration.name)] = symbol
            self._types[id(declaration)] = type_
            return

        if isinstance(declaration, (FunctionDecl, FunctionPrototype)):
            function_scope = (
                self._table.scope_for(declaration)
                if isinstance(declaration, FunctionDecl)
                else scope
            )
            return_type = self._resolve_type_ref(declaration.return_type, scope)
            parameter_types: list[CType] = []
            for parameter in declaration.parameters:
                parameter_type = self._resolve_type_ref(parameter.type_ref, function_scope)
                if parameter.is_array:
                    parameter_type = PointerType(parameter_type)
                parameter_types.append(parameter_type)
                parameter_symbol = self._table.symbol_for_definition(parameter.name)
                if (
                    parameter_symbol is not None
                    and parameter_symbol.kind is SymbolKind.PARAMETER
                    and parameter_symbol.definition_span == parameter.name.span
                ):
                    parameter_symbol.type = parameter_type
                    self._bindings[id(parameter.name)] = parameter_symbol
                self._types[id(parameter)] = parameter_type
            function_type = FunctionType(return_type, tuple(parameter_types))
            function_symbol = self._table.symbol_for_definition(declaration.name)
            if function_symbol is not None:
                self._bindings[id(declaration.name)] = function_symbol
                if (
                    function_symbol.kind is SymbolKind.FUNCTION
                    and function_symbol.id not in self._resolved_function_types
                ):
                    function_symbol.type = function_type
                    function_symbol.signature = _signature(
                        function_symbol.name,
                        function_type,
                    )
                    self._resolved_function_types.add(function_symbol.id)
            self._types[id(declaration)] = function_type

    def _resolve_function_body(self, declaration: FunctionDecl) -> None:
        self._resolve_block(declaration.body)

    def _resolve_block(self, block: BlockStmt) -> None:
        scope = self._table.scope_for(block)
        for item in block.items:
            if isinstance(item, VarDecl):
                self._resolve_declaration_types(item, scope)
                if item.initializer is not None:
                    self._resolve_expression(item.initializer, scope, AccessKind.READ)
            elif isinstance(item, Statement):
                self._resolve_statement(item, scope)

    def _resolve_statement(self, statement: Statement, scope: Scope) -> None:
        if isinstance(statement, BlockStmt):
            self._resolve_block(statement)
        elif isinstance(statement, ExprStmt):
            self._resolve_expression(statement.expression, scope, AccessKind.READ)
        elif isinstance(statement, IfStmt):
            self._resolve_expression(statement.condition, scope, AccessKind.READ)
            self._resolve_statement(
                statement.then_branch,
                self._table.scope_for(statement.then_branch),
            )
            if statement.else_branch is not None:
                self._resolve_statement(
                    statement.else_branch,
                    self._table.scope_for(statement.else_branch),
                )
        elif isinstance(statement, WhileStmt):
            self._resolve_expression(statement.condition, scope, AccessKind.READ)
            self._resolve_statement(
                statement.body,
                self._table.scope_for(statement.body),
            )
        elif isinstance(statement, ForStmt):
            for_scope = self._table.scope_for(statement)
            if isinstance(statement.initializer, VarDecl):
                self._resolve_declaration_types(statement.initializer, for_scope)
                if statement.initializer.initializer is not None:
                    self._resolve_expression(
                        statement.initializer.initializer,
                        for_scope,
                        AccessKind.READ,
                    )
            elif isinstance(statement.initializer, Expression):
                self._resolve_expression(
                    statement.initializer,
                    for_scope,
                    AccessKind.READ,
                )
            if statement.condition is not None:
                self._resolve_expression(statement.condition, for_scope, AccessKind.READ)
            if statement.update is not None:
                self._resolve_expression(statement.update, for_scope, AccessKind.READ)
            self._resolve_statement(
                statement.body,
                self._table.scope_for(statement.body),
            )
        elif isinstance(statement, ReturnStmt) and statement.value is not None:
            self._resolve_expression(statement.value, scope, AccessKind.READ)
        elif isinstance(statement, (ErrorStmt,)):
            return

    def _resolve_expression(
        self,
        expression: Expression,
        scope: Scope,
        access: AccessKind,
    ) -> CType:
        if isinstance(expression, IdentifierExpr):
            symbol = scope.lookup(
                expression.name.text,
                SymbolNamespace.ORDINARY,
                offset=expression.name.span.start.offset,
            )
            if symbol is None:
                self._error(
                    expression.name,
                    f"undefined symbol '{expression.name.text}'",
                )
                self._types[id(expression)] = ERROR
                return ERROR
            self._bind_reference(expression.name, symbol, access)
            self._types[id(expression)] = symbol.type
            return symbol.type

        if isinstance(expression, IntegerLiteral):
            self._types[id(expression)] = INT
            return INT
        if isinstance(expression, FloatLiteral):
            type_ = FLOAT if expression.lexeme.lower().endswith("f") else DOUBLE
            self._types[id(expression)] = type_
            return type_
        if isinstance(expression, CharLiteral):
            self._types[id(expression)] = CHAR
            return CHAR
        if isinstance(expression, StringLiteral):
            type_ = PointerType(CHAR)
            self._types[id(expression)] = type_
            return type_
        if isinstance(expression, ErrorExpr):
            self._types[id(expression)] = ERROR
            return ERROR

        if isinstance(expression, AssignmentExpr):
            target_access = (
                AccessKind.WRITE
                if expression.operator is TokenKind.ASSIGN
                else AccessKind.READ_WRITE
            )
            target_type = self._resolve_expression(
                expression.target,
                scope,
                target_access,
            )
            self._resolve_expression(expression.value, scope, AccessKind.READ)
            self._types[id(expression)] = target_type
            return target_type

        if isinstance(expression, UnaryExpr):
            operand_access = (
                AccessKind.READ_WRITE
                if expression.operator in {TokenKind.INCREMENT, TokenKind.DECREMENT}
                else AccessKind.READ
            )
            operand_type = self._resolve_expression(
                expression.operand,
                scope,
                operand_access,
            )
            if expression.operator is TokenKind.AMPERSAND:
                type_ = PointerType(operand_type)
            elif expression.operator is TokenKind.STAR and isinstance(
                operand_type,
                PointerType,
            ):
                type_ = operand_type.pointee
            else:
                type_ = operand_type
            self._types[id(expression)] = type_
            return type_

        if isinstance(expression, BinaryExpr):
            left = self._resolve_expression(expression.left, scope, AccessKind.READ)
            self._resolve_expression(expression.right, scope, AccessKind.READ)
            self._types[id(expression)] = left
            return left

        if isinstance(expression, CallExpr):
            if isinstance(expression.callee, IdentifierExpr):
                callee_type = self._resolve_expression(
                    expression.callee,
                    scope,
                    AccessKind.CALL,
                )
            else:
                callee_type = self._resolve_expression(
                    expression.callee,
                    scope,
                    AccessKind.READ,
                )
            for argument in expression.arguments:
                self._resolve_expression(argument, scope, AccessKind.READ)
            type_ = (
                callee_type.return_type
                if isinstance(callee_type, FunctionType)
                else UNKNOWN
            )
            self._types[id(expression)] = type_
            return type_

        if isinstance(expression, IndexExpr):
            target_type = self._resolve_expression(
                expression.target,
                scope,
                AccessKind.READ,
            )
            self._resolve_expression(expression.index, scope, AccessKind.READ)
            if isinstance(target_type, ArrayType):
                type_ = target_type.element_type
            elif isinstance(target_type, PointerType):
                type_ = target_type.pointee
            else:
                type_ = UNKNOWN
            self._types[id(expression)] = type_
            return type_

        if isinstance(expression, MemberExpr):
            target_type = self._resolve_expression(
                expression.target,
                scope,
                AccessKind.READ,
            )
            type_ = self._resolve_member(expression, target_type, scope)
            self._types[id(expression)] = type_
            return type_

        if isinstance(expression, InitializerList):
            for value in expression.values:
                self._resolve_expression(value, scope, AccessKind.READ)
            self._types[id(expression)] = UNKNOWN
            return UNKNOWN

        self._types[id(expression)] = UNKNOWN
        return UNKNOWN

    def _resolve_member(
        self,
        expression: MemberExpr,
        target_type: CType,
        scope: Scope,
    ) -> CType:
        struct_type: StructType | None = None
        if expression.operator is TokenKind.DOT:
            if isinstance(target_type, StructType):
                struct_type = target_type
            elif target_type not in {UNKNOWN, ERROR}:
                self._error(expression.operator_span, "'.' requires a struct value")
        elif expression.operator is TokenKind.ARROW:
            if isinstance(target_type, PointerType) and isinstance(
                target_type.pointee,
                StructType,
            ):
                struct_type = target_type.pointee
            elif target_type not in {UNKNOWN, ERROR}:
                self._error(
                    expression.operator_span,
                    "'->' requires a pointer to struct",
                )

        if struct_type is None:
            return ERROR if target_type is ERROR else UNKNOWN

        tag = scope.lookup(struct_type.name, SymbolNamespace.TAG)
        if tag is None:
            self._error(expression.member, f"undefined struct '{struct_type.name}'")
            return ERROR
        struct_scope = self._table.struct_scopes.get(tag.id)
        if struct_scope is None:
            return ERROR
        field = struct_scope.lookup_local(
            expression.member.text,
            SymbolNamespace.FIELD,
        )
        if field is None:
            self._error(
                expression.member,
                f"unknown field '{expression.member.text}' in {struct_type}",
            )
            return ERROR
        self._bind_reference(expression.member, field, AccessKind.MEMBER_ACCESS)
        return field.type

    def _declared_type(
        self,
        type_ref: TypeRef,
        array_size: Expression | None,
        scope: Scope,
    ) -> CType:
        base = self._resolve_type_ref(type_ref, scope)
        if array_size is None:
            return base
        size = None
        if isinstance(array_size, IntegerLiteral):
            try:
                size = int(array_size.lexeme, 0)
            except ValueError:
                size = None
        return ArrayType(base, size)

    def _resolve_type_ref(self, type_ref: TypeRef, scope: Scope) -> CType:
        if type_ref.keyword != "struct":
            try:
                base: CType = primitive_type(type_ref.keyword)
            except KeyError:
                base = UNKNOWN
        elif type_ref.struct_name is None:
            base = ERROR
        else:
            tag = scope.lookup(type_ref.struct_name.text, SymbolNamespace.TAG)
            if tag is None:
                self._error(
                    type_ref.struct_name,
                    f"undefined struct '{type_ref.struct_name.text}'",
                )
                base = ERROR
            else:
                self._bind_reference(
                    type_ref.struct_name,
                    tag,
                    AccessKind.TYPE_REFERENCE,
                )
                base = StructType(tag.name, tag.id)
        type_ = PointerType(base) if type_ref.is_pointer else base
        self._types[id(type_ref)] = type_
        return type_

    def _bind_reference(
        self,
        name: Name,
        symbol: Symbol,
        access_kind: AccessKind,
    ) -> None:
        self._bindings[id(name)] = symbol
        reference = Reference(
            symbol_id=symbol.id,
            span=name.span,
            access_kind=access_kind,
        )
        symbol.references.append(reference)
        if access_kind in {
            AccessKind.READ,
            AccessKind.READ_WRITE,
            AccessKind.CALL,
            AccessKind.MEMBER_ACCESS,
            AccessKind.TYPE_REFERENCE,
        }:
            symbol.is_used = True

    def _report_shadowing(self) -> None:
        for scope in self._table.scopes:
            if scope.parent is None:
                continue
            for symbol in scope.symbols[SymbolNamespace.ORDINARY].values():
                if symbol.kind is not SymbolKind.VARIABLE:
                    continue
                outer = scope.parent.lookup(symbol.name)
                if outer is None or outer.kind not in {
                    SymbolKind.VARIABLE,
                    SymbolKind.PARAMETER,
                }:
                    continue
                if symbol.definition_span is not None:
                    self._diagnostics.append(
                        Diagnostic(
                            phase=DiagnosticPhase.SEMANTIC,
                            severity=Severity.WARNING,
                            message=(
                                f"variable '{symbol.name}' shadows outer declaration"
                            ),
                            span=symbol.definition_span,
                        )
                    )

    def _error(self, node_or_span, message: str) -> None:
        span = node_or_span.span if hasattr(node_or_span, "span") else node_or_span
        self._diagnostics.append(
            Diagnostic(
                phase=DiagnosticPhase.SEMANTIC,
                severity=Severity.ERROR,
                message=message,
                span=span,
            )
        )


def _signature(name: str, function_type: FunctionType) -> str:
    parameters = [str(item) for item in function_type.parameter_types]
    if function_type.variadic:
        parameters.append("...")
    return f"{function_type.return_type} {name}({', '.join(parameters)})"


def analyze(program: Program) -> SemanticResult:
    """Run a fresh semantic analysis with no cross-file mutable state."""
    return SemanticAnalyzer(program).analyze()
