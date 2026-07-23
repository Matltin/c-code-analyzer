"""Type checking and conservative structural initialization analysis."""

from __future__ import annotations

from c_analyzer.ast import (
    AssignmentExpr,
    BinaryExpr,
    BlockStmt,
    CallExpr,
    CharLiteral,
    ErrorExpr,
    ErrorStmt,
    ExprStmt,
    Expression,
    FloatLiteral,
    ForStmt,
    FunctionDecl,
    IdentifierExpr,
    IfStmt,
    IndexExpr,
    InitializerList,
    IntegerLiteral,
    MemberExpr,
    Program,
    ReturnStmt,
    Statement,
    StringLiteral,
    StructDecl,
    UnaryExpr,
    VarDecl,
    WhileStmt,
)
from c_analyzer.core import Diagnostic, DiagnosticPhase, Severity, TokenKind
from c_analyzer.semantic.model import SemanticModel
from c_analyzer.semantic.symbols import (
    AccessKind,
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
    VOID,
    common_numeric_type,
    is_numeric,
    numeric_rank,
)


_COMPARISON_OPERATORS = {
    TokenKind.EQUAL_EQUAL,
    TokenKind.BANG_EQUAL,
    TokenKind.LESS,
    TokenKind.LESS_EQUAL,
    TokenKind.GREATER,
    TokenKind.GREATER_EQUAL,
}
_LOGICAL_OPERATORS = {TokenKind.LOGICAL_AND, TokenKind.LOGICAL_OR}
_ARITHMETIC_OPERATORS = {
    TokenKind.PLUS,
    TokenKind.MINUS,
    TokenKind.STAR,
    TokenKind.SLASH,
    TokenKind.PERCENT,
}
_COMPOUND_ASSIGNMENTS = {
    TokenKind.PLUS_ASSIGN,
    TokenKind.MINUS_ASSIGN,
    TokenKind.STAR_ASSIGN,
    TokenKind.SLASH_ASSIGN,
    TokenKind.PERCENT_ASSIGN,
}


class TypeChecker:
    """Populate expression types and add non-cascading semantic diagnostics."""

    def __init__(self, model: SemanticModel) -> None:
        self._model = model
        self._types = dict(model.types)
        self._diagnostics = list(model.diagnostics)
        self._current_return_type: CType = VOID
        self._current_function: FunctionDecl | None = None

    def check(self) -> SemanticModel:
        global_state = {
            symbol.id
            for symbol in self._model.symbols
            if symbol.kind is SymbolKind.VARIABLE
            and symbol.scope_id == self._model.global_scope.id
        }

        for declaration in self._model.program.declarations:
            if isinstance(declaration, VarDecl):
                self._check_declaration(
                    declaration,
                    self._model.global_scope,
                    global_state,
                    is_global=True,
                )
            elif isinstance(declaration, FunctionDecl):
                self._check_function(declaration, global_state)

        self._report_unused_symbols()
        return SemanticModel(
            program=self._model.program,
            symbol_table=self._model.symbol_table,
            diagnostics=tuple(self._diagnostics),
            bindings=self._model.bindings,
            types=self._types,
        )

    def _check_function(
        self,
        declaration: FunctionDecl,
        global_state: set[str],
    ) -> None:
        symbol = self._model.symbol_of(declaration.name)
        function_type = symbol.type if symbol is not None else UNKNOWN
        self._current_return_type = (
            function_type.return_type
            if isinstance(function_type, FunctionType)
            else UNKNOWN
        )
        self._current_function = declaration

        function_scope = self._model.scope_for(declaration)
        state = set(global_state)
        for parameter in declaration.parameters:
            parameter_symbol = self._model.symbol_of(parameter.name)
            if parameter_symbol is not None:
                state.add(parameter_symbol.id)
                parameter_symbol.is_initialized = True
        self._check_block(declaration.body, state)
        self._current_function = None
        self._current_return_type = VOID

    def _check_block(self, block: BlockStmt, state: set[str]) -> set[str]:
        scope = self._model.scope_for(block)
        current = set(state)
        for item in block.items:
            if isinstance(item, VarDecl):
                self._check_declaration(item, scope, current, is_global=False)
            elif isinstance(item, Statement):
                current = self._check_statement(item, scope, current)
        return current

    def _check_statement(
        self,
        statement: Statement,
        scope: Scope,
        state: set[str],
    ) -> set[str]:
        if isinstance(statement, BlockStmt):
            return self._check_block(statement, state)
        if isinstance(statement, ExprStmt):
            self._check_expression(statement.expression, scope, state, AccessKind.READ)
            return state
        if isinstance(statement, ReturnStmt):
            self._check_return(statement, scope, state)
            return state
        if isinstance(statement, IfStmt):
            self._check_expression(statement.condition, scope, state, AccessKind.READ)
            then_state = self._check_statement(
                statement.then_branch,
                self._model.scope_for(statement.then_branch),
                set(state),
            )
            if statement.else_branch is None:
                return state
            else_state = self._check_statement(
                statement.else_branch,
                self._model.scope_for(statement.else_branch),
                set(state),
            )
            return then_state & else_state
        if isinstance(statement, WhileStmt):
            self._check_expression(statement.condition, scope, state, AccessKind.READ)
            self._check_statement(
                statement.body,
                self._model.scope_for(statement.body),
                set(state),
            )
            return state
        if isinstance(statement, ForStmt):
            for_scope = self._model.scope_for(statement)
            after_initializer = set(state)
            if isinstance(statement.initializer, VarDecl):
                self._check_declaration(
                    statement.initializer,
                    for_scope,
                    after_initializer,
                    is_global=False,
                )
            elif isinstance(statement.initializer, Expression):
                self._check_expression(
                    statement.initializer,
                    for_scope,
                    after_initializer,
                    AccessKind.READ,
                )
            if statement.condition is not None:
                self._check_expression(
                    statement.condition,
                    for_scope,
                    after_initializer,
                    AccessKind.READ,
                )
            loop_state = set(after_initializer)
            self._check_statement(
                statement.body,
                self._model.scope_for(statement.body),
                loop_state,
            )
            if statement.update is not None:
                self._check_expression(
                    statement.update,
                    for_scope,
                    loop_state,
                    AccessKind.READ,
                )
            return after_initializer
        if isinstance(statement, ErrorStmt):
            return state
        return state

    def _check_declaration(
        self,
        declaration: VarDecl,
        scope: Scope,
        state: set[str],
        *,
        is_global: bool,
    ) -> None:
        symbol = self._model.symbol_of(declaration.name)
        declared_type = symbol.type if symbol is not None else UNKNOWN
        owns_symbol = (
            symbol is not None
            and symbol.kind is SymbolKind.VARIABLE
            and symbol.definition_span == declaration.name.span
        )
        self._types[id(declaration)] = declared_type
        if declared_type == VOID:
            self._error(declaration.name, "variable cannot have type void")

        if declaration.initializer is not None:
            self._check_initializer(
                declaration.initializer,
                declared_type,
                scope,
                state,
            )
            if owns_symbol:
                assert symbol is not None
                state.add(symbol.id)
                symbol.is_initialized = True
        elif is_global and owns_symbol:
            assert symbol is not None
            state.add(symbol.id)
            symbol.is_initialized = True

    def _check_initializer(
        self,
        initializer: Expression,
        target_type: CType,
        scope: Scope,
        state: set[str],
    ) -> None:
        if isinstance(initializer, InitializerList):
            self._types[id(initializer)] = target_type
            if isinstance(target_type, ArrayType):
                if (
                    target_type.size is not None
                    and len(initializer.values) > target_type.size
                ):
                    self._error(
                        initializer,
                        "too many elements in array initializer",
                    )
                for value in initializer.values:
                    value_type = self._check_expression(
                        value,
                        scope,
                        state,
                        AccessKind.READ,
                    )
                    self._check_conversion(
                        target_type.element_type,
                        value_type,
                        value,
                        context="initializer",
                    )
                return
            if isinstance(target_type, StructType):
                fields = self._struct_fields(target_type)
                if fields is None:
                    return
                if len(initializer.values) > len(fields):
                    self._error(
                        initializer,
                        "too many elements in struct initializer",
                    )
                for value, field in zip(initializer.values, fields):
                    value_type = self._check_expression(
                        value,
                        scope,
                        state,
                        AccessKind.READ,
                    )
                    self._check_conversion(
                        field.type,
                        value_type,
                        value,
                        context="initializer",
                    )
                return
            self._error(initializer, f"initializer list is invalid for {target_type}")
            for value in initializer.values:
                self._check_expression(value, scope, state, AccessKind.READ)
            return

        source_type = self._check_expression(
            initializer,
            scope,
            state,
            AccessKind.READ,
        )
        self._check_conversion(
            target_type,
            source_type,
            initializer,
            context="initializer",
        )

    def _check_return(
        self,
        statement: ReturnStmt,
        scope: Scope,
        state: set[str],
    ) -> None:
        if statement.value is None:
            if self._current_return_type not in {VOID, UNKNOWN, ERROR}:
                self._error(
                    statement,
                    f"non-void function must return {self._current_return_type}",
                )
            return
        value_type = self._check_expression(
            statement.value,
            scope,
            state,
            AccessKind.READ,
        )
        if self._current_return_type == VOID:
            self._error(statement, "void function must not return a value")
            return
        self._check_conversion(
            self._current_return_type,
            value_type,
            statement.value,
            context="return",
        )

    def _check_expression(
        self,
        expression: Expression,
        scope: Scope,
        state: set[str],
        access: AccessKind,
    ) -> CType:
        if isinstance(expression, IdentifierExpr):
            symbol = self._model.symbol_of(expression)
            type_ = symbol.type if symbol is not None else ERROR
            if (
                symbol is not None
                and access in {AccessKind.READ, AccessKind.READ_WRITE}
                and symbol.kind in {SymbolKind.VARIABLE, SymbolKind.PARAMETER}
                and symbol.scope_id != self._model.global_scope.id
                and symbol.id not in state
            ):
                self._warning(
                    expression.name,
                    f"variable '{symbol.name}' may be used before initialization",
                )
            self._types[id(expression)] = type_
            return type_

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
            target_type = self._check_expression(
                expression.target,
                scope,
                state,
                target_access,
            )
            value_type = self._check_expression(
                expression.value,
                scope,
                state,
                AccessKind.READ,
            )
            if not self._is_lvalue(expression.target):
                self._error(expression.target, "invalid lvalue in assignment")
            elif expression.operator in _COMPOUND_ASSIGNMENTS:
                if not is_numeric(target_type) or not is_numeric(value_type):
                    self._error(
                        expression,
                        "compound assignment requires numeric operands",
                    )
                else:
                    self._check_conversion(
                        target_type,
                        value_type,
                        expression.value,
                        context="assignment",
                    )
            else:
                self._check_conversion(
                    target_type,
                    value_type,
                    expression.value,
                    context="assignment",
                )
            self._mark_assigned(expression.target, state)
            self._types[id(expression)] = target_type
            return target_type

        if isinstance(expression, UnaryExpr):
            if expression.operator is TokenKind.AMPERSAND:
                operand_type = self._check_expression(
                    expression.operand,
                    scope,
                    state,
                    AccessKind.WRITE,
                )
                if not self._is_lvalue(expression.operand):
                    self._error(expression.operand, "address-of requires an lvalue")
                    type_ = ERROR
                else:
                    type_ = PointerType(operand_type)
            elif expression.operator is TokenKind.STAR:
                operand_type = self._check_expression(
                    expression.operand,
                    scope,
                    state,
                    AccessKind.READ,
                )
                if isinstance(operand_type, PointerType):
                    type_ = operand_type.pointee
                elif operand_type in {ERROR, UNKNOWN}:
                    type_ = operand_type
                else:
                    self._error(expression, "dereference requires a pointer")
                    type_ = ERROR
            elif expression.operator in {TokenKind.INCREMENT, TokenKind.DECREMENT}:
                operand_type = self._check_expression(
                    expression.operand,
                    scope,
                    state,
                    AccessKind.READ_WRITE,
                )
                if not self._is_lvalue(expression.operand):
                    self._error(expression.operand, "increment requires an lvalue")
                    type_ = ERROR
                elif not is_numeric(operand_type):
                    self._error(expression, "increment requires a numeric operand")
                    type_ = ERROR
                else:
                    type_ = operand_type
                self._mark_assigned(expression.operand, state)
            else:
                operand_type = self._check_expression(
                    expression.operand,
                    scope,
                    state,
                    AccessKind.READ,
                )
                if expression.operator is TokenKind.LOGICAL_NOT:
                    if not self._is_scalar(operand_type):
                        self._error(expression, "logical not requires a scalar operand")
                        type_ = ERROR
                    else:
                        type_ = INT
                elif not is_numeric(operand_type):
                    if operand_type not in {ERROR, UNKNOWN}:
                        self._error(expression, "unary arithmetic requires a numeric operand")
                    type_ = ERROR
                else:
                    type_ = operand_type
            self._types[id(expression)] = type_
            return type_

        if isinstance(expression, BinaryExpr):
            left_type = self._check_expression(
                expression.left,
                scope,
                state,
                AccessKind.READ,
            )
            right_type = self._check_expression(
                expression.right,
                scope,
                state,
                AccessKind.READ,
            )
            if expression.operator in _ARITHMETIC_OPERATORS:
                if not is_numeric(left_type) or not is_numeric(right_type):
                    if ERROR not in {left_type, right_type}:
                        self._error(
                            expression,
                            "arithmetic operator requires numeric operands",
                        )
                    type_ = ERROR
                elif expression.operator is TokenKind.PERCENT and (
                    left_type not in {CHAR, INT} or right_type not in {CHAR, INT}
                ):
                    self._error(expression, "'%' requires integer operands")
                    type_ = ERROR
                else:
                    type_ = common_numeric_type(left_type, right_type)
            elif expression.operator in _COMPARISON_OPERATORS:
                comparable = (
                    is_numeric(left_type)
                    and is_numeric(right_type)
                    or left_type == right_type
                    and isinstance(left_type, PointerType)
                )
                if not comparable and ERROR not in {left_type, right_type}:
                    self._error(expression, "comparison uses incompatible operand types")
                type_ = INT if comparable else ERROR
            elif expression.operator in _LOGICAL_OPERATORS:
                if not self._is_scalar(left_type) or not self._is_scalar(right_type):
                    if ERROR not in {left_type, right_type}:
                        self._error(
                            expression,
                            "logical operator requires scalar operands",
                        )
                    type_ = ERROR
                else:
                    type_ = INT
            else:
                type_ = UNKNOWN
            self._types[id(expression)] = type_
            return type_

        if isinstance(expression, CallExpr):
            callee_type = self._check_expression(
                expression.callee,
                scope,
                state,
                AccessKind.CALL,
            )
            argument_types = [
                self._check_expression(argument, scope, state, AccessKind.READ)
                for argument in expression.arguments
            ]
            if not isinstance(callee_type, FunctionType):
                if callee_type not in {ERROR, UNKNOWN}:
                    self._error(expression.callee, "called expression is not a function")
                type_ = ERROR
            else:
                required = len(callee_type.parameter_types)
                actual = len(argument_types)
                wrong_count = (
                    actual < required
                    if callee_type.variadic
                    else actual != required
                )
                if wrong_count:
                    self._error(
                        expression,
                        f"wrong number of arguments: expected "
                        f"{'at least ' if callee_type.variadic else ''}{required}, "
                        f"got {actual}",
                    )
                for index, (expected, actual_type, argument) in enumerate(
                    zip(
                        callee_type.parameter_types,
                        argument_types,
                        expression.arguments,
                    ),
                    start=1,
                ):
                    self._check_conversion(
                        expected,
                        actual_type,
                        argument,
                        context=f"function call argument {index}",
                    )
                type_ = callee_type.return_type
            self._types[id(expression)] = type_
            return type_

        if isinstance(expression, IndexExpr):
            target_type = self._check_expression(
                expression.target,
                scope,
                state,
                AccessKind.READ,
            )
            index_type = self._check_expression(
                expression.index,
                scope,
                state,
                AccessKind.READ,
            )
            if index_type not in {CHAR, INT, ERROR, UNKNOWN}:
                self._error(expression.index, "array index must have integer type")
            if isinstance(target_type, ArrayType):
                type_ = target_type.element_type
            elif isinstance(target_type, PointerType):
                type_ = target_type.pointee
            elif target_type in {ERROR, UNKNOWN}:
                type_ = target_type
            else:
                self._error(expression.target, "indexing requires an array or pointer")
                type_ = ERROR
            self._types[id(expression)] = type_
            return type_

        if isinstance(expression, MemberExpr):
            self._check_expression(expression.target, scope, state, AccessKind.READ)
            symbol = self._model.symbol_of(expression.member)
            type_ = symbol.type if symbol is not None else ERROR
            self._types[id(expression)] = type_
            return type_

        if isinstance(expression, InitializerList):
            for value in expression.values:
                self._check_expression(value, scope, state, AccessKind.READ)
            self._types[id(expression)] = UNKNOWN
            return UNKNOWN

        self._types[id(expression)] = UNKNOWN
        return UNKNOWN

    def _check_conversion(
        self,
        target: CType,
        source: CType,
        source_expression: Expression,
        *,
        context: str,
    ) -> None:
        if ERROR in {target, source} or UNKNOWN in {target, source}:
            return
        if target == source:
            return
        if isinstance(target, PointerType) and isinstance(source, ArrayType):
            if target.pointee == source.element_type:
                return
        if isinstance(target, PointerType) and isinstance(
            source_expression,
            IntegerLiteral,
        ):
            try:
                if int(source_expression.lexeme, 0) == 0:
                    return
            except ValueError:
                pass
        if is_numeric(target) and is_numeric(source):
            if numeric_rank(source) > numeric_rank(target):
                self._warning(
                    source_expression,
                    f"narrowing conversion from {source} to {target} in {context}",
                )
            return
        self._error(
            source_expression,
            f"type mismatch in {context}: cannot convert {source} to {target}",
        )

    def _mark_assigned(self, expression: Expression, state: set[str]) -> None:
        if isinstance(expression, IdentifierExpr):
            symbol = self._model.symbol_of(expression)
            if symbol is not None:
                state.add(symbol.id)
                symbol.is_initialized = True

    def _is_lvalue(self, expression: Expression) -> bool:
        if isinstance(expression, IdentifierExpr):
            symbol = self._model.symbol_of(expression)
            return symbol is not None and symbol.kind in {
                SymbolKind.VARIABLE,
                SymbolKind.PARAMETER,
            }
        if isinstance(expression, (IndexExpr, MemberExpr)):
            return True
        return isinstance(expression, UnaryExpr) and expression.operator is TokenKind.STAR

    def _is_scalar(self, type_: CType) -> bool:
        return is_numeric(type_) or isinstance(type_, PointerType)

    def _struct_fields(self, type_: StructType) -> tuple[Symbol, ...] | None:
        tag = self._model.global_scope.lookup(type_.name, SymbolNamespace.TAG)
        if tag is None:
            return None
        scope = self._model.symbol_table.struct_scopes.get(tag.id)
        if scope is None:
            return None
        return tuple(scope.symbols[SymbolNamespace.FIELD].values())

    def _report_unused_symbols(self) -> None:
        for symbol in self._model.symbols:
            if symbol.definition_span is None or symbol.is_used:
                continue
            if symbol.kind is SymbolKind.VARIABLE and (
                symbol.scope_id != self._model.global_scope.id
            ):
                self._info(
                    symbol.definition_span,
                    f"unused variable '{symbol.name}'",
                )
            elif symbol.kind is SymbolKind.PARAMETER:
                self._info(
                    symbol.definition_span,
                    f"unused parameter '{symbol.name}'",
                )

    def _error(self, node_or_span, message: str) -> None:
        self._add_diagnostic(Severity.ERROR, node_or_span, message)

    def _warning(self, node_or_span, message: str) -> None:
        self._add_diagnostic(Severity.WARNING, node_or_span, message)

    def _info(self, node_or_span, message: str) -> None:
        self._add_diagnostic(Severity.INFO, node_or_span, message)

    def _add_diagnostic(self, severity: Severity, node_or_span, message: str) -> None:
        span = node_or_span.span if hasattr(node_or_span, "span") else node_or_span
        self._diagnostics.append(
            Diagnostic(
                phase=DiagnosticPhase.SEMANTIC,
                severity=severity,
                message=message,
                span=span,
            )
        )


def check_types(model: SemanticModel) -> SemanticModel:
    return TypeChecker(model).check()
